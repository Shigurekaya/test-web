@echo off
REM 双击启动（调用 PowerShell 脚本）
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
