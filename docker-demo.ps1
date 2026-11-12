param(
    [ValidateSet('Start', 'Stop', 'Status', 'Logs')]
    [string]$Action = 'Start',
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765,
    [switch]$Lan,
    [string]$LanIP
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Test-PrivateIPv4([string]$Address) {
    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsed) -or
        $parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        return $false
    }
    $bytes = $parsed.GetAddressBytes()
    return ($bytes[0] -eq 10 -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168))
}

function Get-LanAddresses {
    foreach ($adapter in [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()) {
        if ($adapter.OperationalStatus -ne 'Up' -or $adapter.NetworkInterfaceType -in @('Loopback', 'Tunnel') -or
            ($adapter.Name + ' ' + $adapter.Description) -match 'WSL|vEthernet|Docker|Hyper-V|VirtualBox|VMware|Loopback') {
            continue
        }
        $properties = $adapter.GetIPProperties()
        $hasGateway = @($properties.GatewayAddresses | Where-Object {
            $_.Address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
            $_.Address.ToString() -ne '0.0.0.0'
        }).Count -gt 0
        foreach ($unicast in $properties.UnicastAddresses) {
            $address = $unicast.Address.ToString()
            if (Test-PrivateIPv4 $address) {
                [pscustomobject]@{ Address = $address; Interface = $adapter.Name; HasGateway = $hasGateway }
            }
        }
    }
}

function Resolve-LanAddress([string]$RequestedIP) {
    $addresses = @(Get-LanAddresses | Sort-Object Address -Unique)
    if ($RequestedIP) {
        if (-not (Test-PrivateIPv4 $RequestedIP)) { throw '-LanIP must be a private IPv4 address on this computer.' }
        $normalized = ([System.Net.IPAddress]::Parse($RequestedIP)).ToString()
        $selected = @($addresses | Where-Object { $_.Address -eq $normalized })
        if ($selected.Count -ne 1) { throw "LAN IP $RequestedIP is not assigned to an active LAN adapter on this computer." }
        return $selected[0].Address
    }
    $candidates = @($addresses | Where-Object { $_.HasGateway })
    if ($candidates.Count -eq 0) { throw 'No active private LAN IPv4 address with a default gateway was found. Connect to the home LAN or use -LanIP with a local private IPv4 address.' }
    if ($candidates.Count -gt 1) {
        $choices = ($candidates | ForEach-Object { "$($_.Address) ($($_.Interface))" }) -join ', '
        throw "More than one LAN address was found: $choices. Select one with -LanIP."
    }
    return $candidates[0].Address
}

$overrideFile = Join-Path $PSScriptRoot 'compose.override.yaml'
$lanMarker = '# 5BMath managed phone LAN'
$hasOverride = Test-Path -LiteralPath $overrideFile
$managedOverride = $hasOverride -and ((Get-Content -LiteralPath $overrideFile -TotalCount 1) -eq $lanMarker)
$phoneIP = $null
if ($Action -eq 'Start' -and ($Lan -or $LanIP -or $managedOverride)) {
    if ($hasOverride -and -not $managedOverride) {
        throw 'compose.override.yaml contains custom configuration. It was kept unchanged; add the LAN binding there or rename it before using -Lan.'
    }
    if (-not $hasOverride -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'compose.override.yml'))) {
        throw 'compose.override.yml contains custom configuration. It was kept unchanged; add the LAN binding there before starting phone testing.'
    }
    if ($env:COMPOSE_FILE) {
        throw "COMPOSE_FILE is set to '$env:COMPOSE_FILE' and can bypass the phone override. Clear it for this launcher or add the LAN configuration to those Compose files."
    }
    $envFile = Join-Path $PSScriptRoot '.env'
    if ((Test-Path -LiteralPath $envFile) -and
        (Select-String -LiteralPath $envFile -Pattern '^\s*(export\s+)?COMPOSE_FILE\s*=' -Quiet)) {
        throw '.env sets COMPOSE_FILE and can bypass the phone override. Remove that setting or add the LAN configuration to those Compose files.'
    }
    $phoneIP = Resolve-LanAddress $LanIP
}

$dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else {
    Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'
}
if (-not (Test-Path -LiteralPath $dockerPath)) {
    Write-Host 'Docker was not found. Install/open Docker Desktop, then try again.'
    exit 1
}
$engine = & $dockerPath info --format '{{.OSType}}' 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Open Docker Desktop and wait until its engine is running, then try again.'
    exit 1
}
if ($engine -ne 'linux') {
    Write-Host 'This project needs Linux containers.'
    exit 1
}
$previousPort = $env:MAM_TOAN_PORT
$env:MAM_TOAN_PORT = [string]$Port
$composeArgs = @('compose', '--project-directory', $PSScriptRoot)
$result = 0
try {
    switch ($Action) {
        'Start' {
            if ($phoneIP) {
                $overrideText = @'
# 5BMath managed phone LAN
# Local machine configuration; START-DEMO refreshes the address after DHCP changes.
services:
  web:
    ports:
      - "LAN_ADDRESS:${MAM_TOAN_PORT:-8765}:8000"
'@
                $overrideText = $overrideText.Replace('LAN_ADDRESS', $phoneIP)
                Set-Content -LiteralPath $overrideFile -Value $overrideText -Encoding UTF8
                & $dockerPath @composeArgs config --quiet
                if ($LASTEXITCODE -ne 0) { throw 'Compose configuration is invalid; the existing container was not changed.' }
            } elseif ($env:COMPOSE_FILE) {
                Write-Host "Using COMPOSE_FILE: $env:COMPOSE_FILE"
            }
            & $dockerPath @composeArgs up --build --wait --wait-timeout 120
            $result = $LASTEXITCODE
            if ($result -eq 0) {
                Write-Host "Website: http://localhost:$Port/"
                if ($phoneIP) {
                    Write-Host "Phone (same home Wi-Fi/LAN): http://${phoneIP}:$Port/goc-hoc-tap/"
                    $firewallMatches = $false
                    try {
                        $rule = Get-NetFirewallRule -Name "5BMath-LAN-$Port" -ErrorAction Stop
                        $addressFilter = $rule | Get-NetFirewallAddressFilter -ErrorAction Stop
                        $portFilter = $rule | Get-NetFirewallPortFilter -ErrorAction Stop
                        $firewallMatches = ($rule.Enabled -eq 'True' -and $rule.Action -eq 'Allow' -and
                            $rule.Direction -eq 'Inbound' -and $addressFilter.LocalAddress -contains $phoneIP -and
                            $portFilter.LocalPort -contains [string]$Port -and $portFilter.Protocol -in @('TCP', '6'))
                    } catch {
                        Write-Host 'Could not verify the phone firewall rule from this window.'
                    }
                    if (-not $firewallMatches) {
                        Write-Host 'To allow the phone connection, open PowerShell as Administrator and run:'
                        Write-Host "& '$PSScriptRoot\scripts\enable-phone-firewall.ps1' -LanIP $phoneIP -Port $Port"
                    }
                }
                Write-Host 'Docker is running the website. You can close this window.'
            } else {
                Write-Host 'Could not start. Check Docker Desktop and whether the port is already in use.'
                Write-Host 'Try another port: .\docker-demo.ps1 -Port 8767'
            }
        }
        'Stop' {
            & $dockerPath @composeArgs stop web
            $result = $LASTEXITCODE
        }
        'Status' {
            & $dockerPath @composeArgs ps --all
            $result = $LASTEXITCODE
        }
        'Logs' {
            & $dockerPath @composeArgs logs --tail 100 web
            $result = $LASTEXITCODE
        }
    }
} finally {
    if ($null -eq $previousPort) { Remove-Item Env:\MAM_TOAN_PORT -ErrorAction SilentlyContinue }
    else { $env:MAM_TOAN_PORT = $previousPort }
}
exit $result
