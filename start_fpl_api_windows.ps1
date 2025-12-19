# PowerShell script to start FPL API on Windows Server
# Run this on the Windows server

$APP_DIR = "C:\fpl-api"
$PORT = 8080

Write-Host "🚀 Starting FPL API Server..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path "$APP_DIR\.env")) {
    Write-Host "❌ .env file not found at $APP_DIR\.env" -ForegroundColor Red
    exit 1
}

# Activate virtual environment and start server
Set-Location $APP_DIR
& "$APP_DIR\venv\Scripts\python.exe" -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port $PORT

