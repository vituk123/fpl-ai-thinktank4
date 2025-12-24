# Install FPL API as a Windows Scheduled Task that runs at startup
$ErrorActionPreference = "Stop"

$APP_DIR = "C:\fpl-api"
$PORT = 8080
$PYTHON = "$APP_DIR\venv\Scripts\python.exe"
$SCRIPT = "$APP_DIR\run_server.py"
$TASK_NAME = "FPLAPIServer"

Write-Host "Installing FPL API Server as Windows Scheduled Task..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path "$APP_DIR\.env")) {
    Write-Host "ERROR: .env file not found at $APP_DIR\.env" -ForegroundColor Red
    exit 1
}

# Create run_server.py if it doesn't exist
if (-not (Test-Path $SCRIPT)) {
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
    Write-Host "Created $SCRIPT" -ForegroundColor Cyan
}

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue
}

# Create the action (what to run)
$action = New-ScheduledTaskAction -Execute $PYTHON -Argument $SCRIPT -WorkingDirectory $APP_DIR

# Create the trigger (when to run - at startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create the principal (run as SYSTEM for persistence)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Create settings (allow to run on demand, restart on failure)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Register the task
Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "FPL API Server - Runs FastAPI server on port $PORT" | Out-Null

Write-Host "Task registered successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Starting the task now..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TASK_NAME

Start-Sleep -Seconds 10

# Check if server is running
$tcpConnections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($tcpConnections) {
    Write-Host "Server is listening on port $PORT!" -ForegroundColor Green
    $tcpConnections | Select-Object LocalAddress, LocalPort, State, OwningProcess
} else {
    Write-Host "Server may still be starting. Check task status:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $TASK_NAME" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "To manage the service:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName $TASK_NAME" -ForegroundColor White
Write-Host "  Stop-ScheduledTask -TaskName $TASK_NAME" -ForegroundColor White
Write-Host "  Get-ScheduledTask -TaskName $TASK_NAME | Get-ScheduledTaskInfo" -ForegroundColor White
Write-Host "  Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:`$false" -ForegroundColor White
Write-Host ""

