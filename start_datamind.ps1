# DataMind One-Click Startup Script for Windows PowerShell
# Usage: .\start_datamind.ps1

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Starting DataMind Predictive Intelligence Platform (v1.0.0.1)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host "[OK] Using virtual environment Python: $PythonExe" -ForegroundColor Green
} else {
    $PythonExe = "python"
    Write-Host "[INFO] Using system Python: $PythonExe" -ForegroundColor Yellow
}

$env:PYTHONPATH = $ScriptDir

# Check version
& $PythonExe (Join-Path $ScriptDir "datamind.py") version

Write-Host "`nLaunching all cluster microservices (Dashboard, Api, Prediction, Ingestion)..." -ForegroundColor Green
& $PythonExe (Join-Path $ScriptDir "datamind.py") start --all --browser
