param(
    [ValidateSet('Start', 'Stop', 'Status', 'Logs')]
    [string]$Action = 'Start',
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
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
$composeFile = Join-Path $PSScriptRoot 'compose.yaml'
$composeArgs = @('compose', '--project-directory', $PSScriptRoot, '-f', $composeFile)
$result = 0
try {
    switch ($Action) {
        'Start' {
            & $dockerPath @composeArgs up --build --wait --wait-timeout 120
            $result = $LASTEXITCODE
            if ($result -eq 0) {
                Write-Host "Website: http://localhost:$Port/"
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
