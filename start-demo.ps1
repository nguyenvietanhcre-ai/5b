param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$candidates = @(
    (Join-Path $PSScriptRoot '.venv\Scripts\python.exe'),
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
)
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) { $candidates += $pythonCommand.Source }
$selectedPython = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate) -and $candidate -notlike '*\Microsoft\WindowsApps\python.exe') {
        $selectedPython = $candidate
        break
    }
}
if (-not $selectedPython) {
    Write-Host 'Install Python 3.12+ or use: docker compose up --build'
    exit 1
}
& $selectedPython -m backend --port $Port
exit $LASTEXITCODE
