# Run automated tests for submission evidence
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] .venv not found. Create it first:" -ForegroundColor Red
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "Running tests..." -ForegroundColor Cyan
# 透传额外参数，例如 .\run_tests.ps1 -- -q -k security
if ($args.Count -gt 0) { & $Python -m pytest @args } else { & $Python -m pytest }
exit $LASTEXITCODE

