param([ValidateRange(1024,65535)][int]$Port = 8768)
$ErrorActionPreference = 'Stop'
$lionProject = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$lionWork = Join-Path $lionProject 'work/lion-animation'
$lionRun = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,6)
$lionContext = Join-Path $lionWork ('context-' + $lionRun)
New-Item -ItemType Directory -Path $lionContext -Force | Out-Null
foreach ($lionDirectory in @('backend','frontend')) {
    Copy-Item -LiteralPath (Join-Path $lionProject $lionDirectory) -Destination (Join-Path $lionContext $lionDirectory) -Recurse
}
Copy-Item -LiteralPath (Join-Path $lionProject 'Dockerfile') -Destination (Join-Path $lionContext 'Dockerfile')
$lionYamlContext = $lionContext.Replace('\','/').Replace("'","''")
$lionCompose = Join-Path $lionWork ('compose-' + $lionRun + '.yaml')
$lionConfig = @"
name: mam-toan-lion
services:
  web:
    image: mam-toan:lion-local-01a1cb4a
    build:
      context: '$lionYamlContext'
      dockerfile: Dockerfile
    ports: ['127.0.0.1:${Port}:8000']
    init: true
    environment: {MAM_TOAN_REVIEW_UPGRADES: '0'}
    restart: unless-stopped
    read_only: true
    tmpfs: [/tmp, '/work:mode=1777']
    volumes: ['shared-db:/data']
    cap_drop: [ALL]
    security_opt: ['no-new-privileges:true']
volumes:
  shared-db:
    external: true
    name: mam-toan_demo-db
"@
[IO.File]::WriteAllText($lionCompose,$lionConfig,[Text.UTF8Encoding]::new($false))
& docker compose -f $lionCompose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed.' }
& docker compose -f $lionCompose up --build --wait --wait-timeout 120
if ($LASTEXITCODE -ne 0) { throw 'Local lion deployment failed.' }
Write-Host "Game Su tu: http://localhost:$Port/linh-vat/"
Write-Host "Compose: $lionCompose"
