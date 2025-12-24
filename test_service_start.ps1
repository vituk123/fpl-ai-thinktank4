# Test script to start service and capture output
$APP_DIR = "C:\fpl-api"
$PORT = 8080
$LOG_FILE = "$APP_DIR\service_test.log"

Set-Location $APP_DIR

Write-Host "Testing service startup..." -ForegroundColor Yellow
Write-Host "Log file: $LOG_FILE" -ForegroundColor Cyan

# Test Python
Write-Host "`n[1] Testing Python..." -ForegroundColor Yellow
& "$APP_DIR\venv\Scripts\python.exe" --version 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# Test uvicorn import
Write-Host "`n[2] Testing uvicorn import..." -ForegroundColor Yellow
& "$APP_DIR\venv\Scripts\python.exe" -c "import uvicorn; print('uvicorn OK')" 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# Test app import
Write-Host "`n[3] Testing app import..." -ForegroundColor Yellow
& "$APP_DIR\venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'src'); from dashboard_api import app; print('App import OK')" 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# Try starting service (will timeout after 10 seconds)
Write-Host "`n[4] Attempting to start service (10 second test)..." -ForegroundColor Yellow
$job = Start-Job -ScriptBlock {
    param($appDir, $port)
    Set-Location $appDir
    $ErrorActionPreference = "Continue"
    & "$appDir\venv\Scripts\python.exe" -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port $port 2>&1
} -ArgumentList $APP_DIR, $PORT

Start-Sleep -Seconds 10
Write-Host "`n[5] Retrieving job output..." -ForegroundColor Yellow
$output = Receive-Job -Id $job.Id 2>&1
$output | Tee-Object -FilePath $LOG_FILE -Append
$output

Stop-Job -Id $job.Id -ErrorAction SilentlyContinue
Remove-Job -Id $job.Id -Force -ErrorAction SilentlyContinue

Write-Host "`nFull log saved to: $LOG_FILE" -ForegroundColor Green

