# EtsyTools Dashboard PowerShell Launcher
# Run this in PowerShell to start your local server.

# 1. Set terminal title
$host.UI.RawUI.WindowTitle = "EtsyTools FastAPI Server"

# 2. Print startup banner
Write-Host "=========================================" -ForegroundColor Green
Write-Host "   🎨 Launching EtsyTools FastAPI UI    " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Navigating to project directory..." -ForegroundColor Gray

# 3. Navigate to workspace
Set-Location -Path $PSScriptRoot

# 4. Check if virtual environment exists
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-Host "Starting Uvicorn server..." -ForegroundColor Green
    & ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
} else {
    Write-Error "Could not find .venv Python. Install dependencies first, then rerun this script."
    exit 1
}
