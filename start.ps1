# Start knowledge wealth service
# Usage: .\start.ps1   or   .\start.ps1 -Port 5000

param(
    [int]$Port = 5000,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
$InstanceDir = Join-Path $Root "instance"
$PidFile = Join-Path $InstanceDir "server.pid"
$BootFile = Join-Path $InstanceDir "_boot_server.py"
$LogFile = Join-Path $InstanceDir "server.out.log"

if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] venv python not found: $Python" -ForegroundColor Red
    Write-Host "Create venv first, then: .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

New-Item -ItemType Directory -Force -Path $InstanceDir | Out-Null

function Test-PortInUse([int]$ListenPort) {
    $conn = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

if (Test-Path $PidFile) {
    $oldPidText = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($oldPidText -match '^\d+$') {
        $oldPid = [int]$oldPidText
        if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] Already running (PID=$oldPid). Use .\stop.ps1 first." -ForegroundColor Yellow
            exit 0
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

if (Test-PortInUse $Port) {
    Write-Host "[ERROR] Port $Port is in use. Run .\stop.ps1 or change -Port." -ForegroundColor Red
    exit 1
}

$bootLines = @(
    "import sys",
    "from pathlib import Path",
    "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))",
    "from app import create_app",
    "app = create_app()",
    "app.run(host='$BindHost', port=$Port, debug=False, use_reloader=False)"
)
# Avoid UTF-8 BOM so Python can parse the first line
[System.IO.File]::WriteAllLines($BootFile, $bootLines)

$OutLog = Join-Path $InstanceDir "server.out.log"
$ErrLog = Join-Path $InstanceDir "server.err.log"

Write-Host "Starting knowledge service..." -ForegroundColor Cyan
Write-Host "  URL : http://${BindHost}:$Port"
Write-Host "  Log : $OutLog / $ErrLog"

$proc = Start-Process -FilePath $Python `
    -ArgumentList "`"$BootFile`"" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII

$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 400
    if (Test-PortInUse $Port) {
        $ready = $true
        break
    }
    if ($proc.HasExited) {
        break
    }
}

if (-not $ready) {
    Write-Host "[ERROR] Start failed. See logs:" -ForegroundColor Red
    if (Test-Path $ErrLog) { Get-Content $ErrLog -Tail 40 }
    if (Test-Path $OutLog) { Get-Content $OutLog -Tail 40 }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "[OK] Started PID=$($proc.Id)" -ForegroundColor Green
Write-Host "Open: http://${BindHost}:$Port"
Write-Host "Stop: .\stop.ps1"
