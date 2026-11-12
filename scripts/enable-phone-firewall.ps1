param(
    [Parameter(Mandatory = $true)]
    [string]$LanIP,
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765,
    [string]$ResultPath
)
$ErrorActionPreference = 'Stop'
try {
    $ip = [System.Net.IPAddress]::Parse($LanIP)
    $bytes = $ip.GetAddressBytes()
    if ($bytes.Length -ne 4 -or -not (
        $bytes[0] -eq 10 -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
    )) { throw 'Use this computer''s private LAN IPv4 address.' }
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $ip.IPAddressToString)
    if ($addresses.Count -ne 1) { throw 'The LAN IPv4 address must belong to exactly one local adapter.' }
    $address = $addresses[0]
    $network = Get-NetIPConfiguration -InterfaceIndex $address.InterfaceIndex
    if (-not $network.IPv4DefaultGateway) { throw 'The selected adapter has no LAN gateway.' }
    $minimumPrefix = if ($bytes[0] -eq 10) { 8 } elseif ($bytes[0] -eq 172) { 12 } else { 16 }
    if ($address.PrefixLength -lt $minimumPrefix -or $address.PrefixLength -gt 32) {
        throw 'The adapter subnet extends outside its private IPv4 range. Check the LAN configuration before opening the firewall.'
    }
    $subnet = for ($i = 0; $i -lt 4; $i++) {
        $bits = [Math]::Min(8, [Math]::Max(0, $address.PrefixLength - $i * 8))
        $mask = if ($bits -eq 0) { 0 } else { 256 - [Math]::Pow(2, 8 - $bits) }
        $bytes[$i] -band [int]$mask
    }
    $remote = ($subnet -join '.') + '/' + $address.PrefixLength
    $ruleName = "5BMath-LAN-$Port"
    $parameters = @{
        Direction = 'Inbound'; Action = 'Allow'; Enabled = 'True'
        Profile = @('Private', 'Public'); Protocol = 'TCP'; LocalPort = $Port
        LocalAddress = $ip.IPAddressToString; RemoteAddress = $remote
        InterfaceAlias = $address.InterfaceAlias
    }
    if (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue) {
        Set-NetFirewallRule -Name $ruleName @parameters | Out-Null
    } else {
        New-NetFirewallRule -Name $ruleName -DisplayName '5BMath - phone testing on home LAN' @parameters | Out-Null
    }
    $result = "OK: TCP $Port to $LanIP from $remote on $($address.InterfaceAlias)"
    if ($ResultPath) { Set-Content -LiteralPath $ResultPath -Value $result -Encoding UTF8 }
    Write-Output $result
} catch {
    if ($ResultPath) { Set-Content -LiteralPath $ResultPath -Value "ERROR: $($_.Exception.Message)" -Encoding UTF8 }
    Write-Error $_
    exit 1
}
