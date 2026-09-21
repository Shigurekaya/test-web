@echo off
REM 双击关闭
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
pause
