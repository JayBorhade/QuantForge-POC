@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\scripts\launch-local.ps1"
pause
