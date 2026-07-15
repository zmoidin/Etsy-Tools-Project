# EtsyTools Dashboard PowerShell Launcher
# Run this in PowerShell to start your local server.

# 1. Set terminal title
$host.UI.RawUI.WindowTitle = "EtsyTools Dashboard Server"

# 2. Print startup banner
Write-Host "=========================================" -ForegroundColor Green
Write-Host "   🎨 Launching EtsyTools Dashboard AI   " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Navigating to project directory..." -ForegroundColor Gray

# 3. Navigate to workspace
Set-Location -Path "c:\QuillSketch\EtsyTools"

# 4. Check if virtual environment exists
if (Test-Path ".\.venv\Scripts\streamlit.exe") {
    Write-Host "Starting Streamlit server..." -ForegroundColor Green
    & ".\.venv\Scripts\streamlit.exe" run app.py
} else {
    Write-Error "Could not find virtual environment streamlit.exe. Make sure it is installed at c:\QuillSketch\EtsyTools\.venv"
}
