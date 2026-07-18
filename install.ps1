# EtsyTools PowerShell Installer
# Run this script to set up Python virtual environment and dependencies.
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Green
Write-Host "   🎨 EtsyTools Installation Script     " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# 1. Ensure we are in the script's directory
Set-Location -Path $PSScriptRoot

# 2. Check for Python installation
Write-Host "Checking for Python installation..." -ForegroundColor Gray
$pythonCmd = $null
try {
    # Check if 'python' works
    & python --version | Out-Null
    $pythonCmd = "python"
} catch {
    try {
        # Check if 'py' works (Python Launcher for Windows)
        & py --version | Out-Null
        $pythonCmd = "py"
    } catch {
        Write-Host ""
        Write-Host "❌ Error: Python not found!" -ForegroundColor Red
        Write-Host "Please make sure Python (3.9 or higher is recommended) is installed" -ForegroundColor Yellow
        Write-Host "and added to your PATH environment variable." -ForegroundColor Yellow
        Write-Host "You can download it from: https://www.python.org/downloads/" -ForegroundColor Blue
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

Write-Host "Using Python: $pythonCmd" -ForegroundColor Green

# 3. Create Virtual Environment (.venv)
if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating Python virtual environment (.venv)..." -ForegroundColor Gray
    try {
        & $pythonCmd -m venv .venv
        Write-Host "Virtual environment created successfully." -ForegroundColor Green
    } catch {
        Write-Host "❌ Error: Failed to create virtual environment." -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Yellow
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "Virtual environment (.venv) already exists. Skipping creation." -ForegroundColor Green
}

# 4. Determine venv python path
$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "❌ Error: Virtual environment python executable not found at $venvPython!" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 5. Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Gray
try {
    & $venvPython -m pip install --upgrade pip
} catch {
    Write-Host "⚠️ Warning: Failed to upgrade pip. Proceeding with installation..." -ForegroundColor Yellow
}

# 6. Install dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Gray
try {
    & $venvPython -m pip install -r requirements.txt
    Write-Host "Dependencies installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Failed to install requirements." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

# 7. Setup .env file if it doesn't exist
if (-not (Test-Path ".\.env")) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Gray
    if (Test-Path ".\.env.example") {
        Copy-Item -Path ".\.env.example" -Destination ".\.env"
        Write-Host ".env file created. Please open .env to configure your API keys (e.g. GEMINI_API_KEY) if needed." -ForegroundColor Green
    } else {
        Write-Host "⚠️ Warning: .env.example not found. Creating empty .env file..." -ForegroundColor Yellow
        New-Item -Path ".\.env" -ItemType File | Out-Null
    }
} else {
    Write-Host ".env file already exists." -ForegroundColor Green
}

Write-Host "=========================================" -ForegroundColor Green
Write-Host " 🎉 Setup Complete!" -ForegroundColor Green
Write-Host " You can now start the server by double-clicking 'run.bat'" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Read-Host "Press Enter to finish..."
