# PowerShell script to start FPL API as a persistent service using a different method
$ErrorActionPreference = "Stop"

$APP_DIR = "C:\fpl-api"
$PORT = 8080
$PYTHON = "$APP_DIR\venv\Scripts\python.exe"
$SCRIPT = "$APP_DIR\run_server.py"

Write-Host "Starting FPL API Server as persistent service..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path "$APP_DIR\.env")) {
    Write-Host "ERROR: .env file not found at $APP_DIR\.env" -ForegroundColor Red
    exit 1
}

# Stop any existing processes
$existingConnections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($existingConnections) {
    $existingProcesses = $existingConnections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $existingProcesses) {
        Write-Host "Stopping existing process (PID: $pid) on port $PORT..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Create a Python script that runs the server
$runServerScript = @"
import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    uvicorn.run(
        "src.dashboard_api:app",
        host="0.0.0.0",
        port=$PORT,
        log_level="info"
    )
"@

Set-Content -Path $SCRIPT -Value $runServerScript -Force

# Start the server using PowerShell Start-Job for proper background execution
# This keeps the process alive even if the parent session closes
$job = Start-Job -ScriptBlock {
    param($pythonPath, $scriptPath, $appDir)
    Set-Location $appDir
    & $pythonPath $scriptPath *> "$appDir\server_output.log"
} -ArgumentList $PYTHON, $SCRIPT, $APP_DIR

Write-Host "Server job started (Job ID: $($job.Id))" -ForegroundColor Green

# Wait a moment for the job to start
Start-Sleep -Seconds 3

# Get the actual process ID from the job
$processId = (Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)
$process = if ($processId) { Get-Process -Id $processId -ErrorAction SilentlyContinue } else { $null }

if ($process) {
    Write-Host "Server process started (PID: $($process.Id))" -ForegroundColor Green
} else {
    Write-Host "Server job started, waiting for process to bind to port..." -ForegroundColor Yellow
}
Write-Host "Output log: $APP_DIR\server_output.log" -ForegroundColor Cyan
Write-Host "Error log: $APP_DIR\server_error.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting 10 seconds for service to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if server is running
$tcpConnections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($tcpConnections) {
    Write-Host "Server is listening on port $PORT!" -ForegroundColor Green
    $tcpConnections | Select-Object LocalAddress, LocalPort, State, OwningProcess
} else {
    Write-Host "Server may still be starting. Check logs:" -ForegroundColor Yellow
    Write-Host "  Get-Content $APP_DIR\server_output.log -Tail 30" -ForegroundColor Cyan
    Write-Host "  Get-Content $APP_DIR\server_error.log -Tail 30" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "To check if service is running:" -ForegroundColor Cyan
Write-Host "  Get-Job -Id $($job.Id)" -ForegroundColor White
Write-Host "  Get-NetTCPConnection -LocalPort $PORT" -ForegroundColor White
if ($process) {
    Write-Host "  Get-Process -Id $($process.Id) -ErrorAction SilentlyContinue" -ForegroundColor White
}
Write-Host ""
Write-Host "To stop the service:" -ForegroundColor Cyan
Write-Host "  Stop-Job -Id $($job.Id)" -ForegroundColor White
if ($process) {
    Write-Host "  Stop-Process -Id $($process.Id) -Force" -ForegroundColor White
}
Write-Host ""

