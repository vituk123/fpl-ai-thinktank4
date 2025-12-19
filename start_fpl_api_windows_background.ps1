# PowerShell script to start FPL API in background on Windows Server
# Run this on the Windows server

$APP_DIR = "C:\fpl-api"
$PORT = 8080

Write-Host "🚀 Starting FPL API Server in background..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path "$APP_DIR\.env")) {
    Write-Host "❌ .env file not found at $APP_DIR\.env" -ForegroundColor Red
    exit 1
}

# Start server in background
Set-Location $APP_DIR
$job = Start-Job -ScriptBlock {
    param($appDir, $port)
    Set-Location $appDir
    & "$appDir\venv\Scripts\python.exe" -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port $port
} -ArgumentList $APP_DIR, $PORT

Write-Host "✅ Server started in background (Job ID: $($job.Id))" -ForegroundColor Green
Write-Host "📝 To view logs: Receive-Job -Id $($job.Id)" -ForegroundColor Cyan
Write-Host "📝 To stop: Stop-Job -Id $($job.Id)" -ForegroundColor Cyan
Write-Host ""

