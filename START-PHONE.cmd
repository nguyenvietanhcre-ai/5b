@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-demo.ps1" -Action Start -Lan
if errorlevel 1 pause
