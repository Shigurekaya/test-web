# Stop knowledge wealth service
# Usage: .\stop.ps1   or   .\stop.ps1 -Port 5000

param(
    [int]$Port = 5000
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$InstanceDir = Join-Path $Root "instance"
$PidFile = Join-Path $InstanceDir "server.pid"
$BootFile = Join-Path $InstanceDir "_boot_server.py"
$stopped = New-Object System.Collections.Generic.List[string]

function Stop-PidSafe([int]$ProcessId) {
    try {
        Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

if (Test-Path $PidFile) {
    $raw = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($raw -match '^\d+$') {
        $targetPid = [int]$raw
        if (Stop-PidSafe $targetPid) {
            $stopped.Add("PID $targetPid (pidfile)") | Out-Null
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    $ownerPid = $c.OwningProcess
    if ($ownerPid -and (Stop-PidSafe $ownerPid)) {
        $stopped.Add("PID $ownerPid (port $Port)") | Out-Null
    }
}

Remove-Item $BootFile -Force -ErrorAction SilentlyContinue

if ($stopped.Count -gt 0) {
    Write-Host "[OK] Service stopped:" -ForegroundColor Green
    foreach ($item in $stopped) {
        Write-Host "  - $item"
    }
} else {
    Write-Host "[INFO] No running service found (port $Port / pidfile)." -ForegroundColor Yellow
}
