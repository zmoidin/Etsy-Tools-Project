@echo off
:: Ensure script runs from its containing directory
cd /d "%~dp0"

:: Run the run.ps1 script using PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Server process exited with error code %errorlevel%.
    pause
)
