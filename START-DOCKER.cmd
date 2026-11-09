@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-demo.ps1" -Action Start
if errorlevel 1 pause
