param([int]$Port = 8765)
# Compatibility launcher: the server is now Python.
& (Join-Path $PSScriptRoot "start-demo.ps1") -Port $Port
