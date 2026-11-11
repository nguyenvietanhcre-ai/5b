param([int]$Port = 8767)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$qaRoot = Join-Path $projectRoot 'work\mascot-animation\bach-tuoc\v1'
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Cổng phải nằm trong 1024–65535.' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Cổng $Port đang được sử dụng; giữ nguyên tiến trình hiện có." }
$pythonCandidates = @(
    (Join-Path $projectRoot '.venv\Scripts\python.exe'),
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
)
$pythonAlias = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue
if ($pythonAlias) { $pythonCandidates += $pythonAlias.Source }
$pythonPath = $null
foreach ($candidate in $pythonCandidates) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    try {
        & $candidate -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonPath = $candidate; break }
    } catch { }
}
if (-not $pythonPath) { throw 'Không tìm thấy Python 3.12+; dùng launcher Python/Docker của dự án.' }
& node (Join-Path $PSScriptRoot 'integrate-bach-tuoc.cjs') --check
if ($LASTEXITCODE -ne 0) { throw 'Cần chạy integrate-bach-tuoc.cjs trên baseline Góc học tập hiện có trước.' }
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
$qaDatabase = Join-Path $qaRoot 'local-qa.sqlite3'
$arguments = '-m backend --host 127.0.0.1 --port ' + $Port + ' --database "' + $qaDatabase + '"'
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $qaRoot 'local-server.stdout.log') -RedirectStandardError (Join-Path $qaRoot 'local-server.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $qaRoot 'local-server.pid')
Write-Output "Đã khởi chạy PID $($process.Id), chờ kiểm tra http://127.0.0.1:$Port/api/health"
Write-Output "Bản thử dùng DB riêng: $qaDatabase; không dùng tài khoản/DB Docker 8765."
