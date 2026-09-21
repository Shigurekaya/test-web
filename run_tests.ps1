# Run automated tests for submission evidence
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] .venv not found" -ForegroundColor Red
    exit 1
}
Write-Host "Running tests..." -ForegroundColor Cyan
& $Python -m unittest discover -s tests -p "test_*.py" -v
exit $LASTEXITCODE
