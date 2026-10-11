@echo off
setlocal enabledelayedexpansion
title DataMind: Predictive Intelligence & Failure Prevention Platform

cd /d "%~dp0"

echo ================================================================================
echo   DataMind Predictive Maintenance Platform  (v1.0.0.1)
echo ================================================================================
echo.

:: Locate Python executable
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python: !PYTHON_EXE!
) else (
    set "PYTHON_EXE=python"
    echo [INFO] Using system Python: !PYTHON_EXE!
)

set "PYTHONPATH=%~dp0;%PYTHONPATH%"

:: Show platform version
"%PYTHON_EXE%" "%~dp0datamind.py" version
echo.

echo [INFO] Launching microservices cluster and opening Web Console...
echo [INFO] Web Dashboard: http://localhost:8003
echo [INFO] Press Ctrl+C in this terminal window to stop all services.
echo.

:: Launch services with automatic browser open
"%PYTHON_EXE%" "%~dp0datamind.py" start --all --browser

echo.
echo [INFO] DataMind services have shut down.
pause
