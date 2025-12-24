# PowerShell script to start FPL API in background on Windows Server
# Run this on the Windows server

$APP_DIR = "C:\fpl-api"
$PORT = 8080

Write-Host "Starting FPL API Server in background..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path "$APP_DIR\.env")) {
    Write-Host "ERROR: .env file not found at $APP_DIR\.env" -ForegroundColor Red
    exit 1
}

# Stop any existing Python processes on the port
$existingConnections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($existingConnections) {
    $existingProcesses = $existingConnections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $existingProcesses) {
        Write-Host "Stopping existing process (PID: $pid) on port $PORT..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Start server as a persistent background process
Set-Location $APP_DIR
Write-Host "Starting service process..." -ForegroundColor Cyan

# #region agent log
$logData = @{
    location = "start_fpl_api_windows_background.ps1:30"
    message = "Starting server process"
    data = @{
        host = "0.0.0.0"
        port = $PORT
        app_dir = $APP_DIR
    }
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    sessionId = "debug-session"
    runId = "run1"
    hypothesisId = "A"
} | ConvertTo-Json -Compress
Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
# #endregion

# #region agent log
$logData = @{
    location = "start_fpl_api_windows_background.ps1:30"
    message = "About to start process"
    data = @{
        python_exe = "$APP_DIR\venv\Scripts\python.exe"
        arguments = "-m uvicorn src.dashboard_api:app --host 0.0.0.0 --port $PORT"
        working_dir = $APP_DIR
    }
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    sessionId = "debug-session"
    runId = "run2"
    hypothesisId = "F"
} | ConvertTo-Json -Compress
Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
# #endregion

$process = Start-Process -FilePath "$APP_DIR\venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "src.dashboard_api:app", "--host", "0.0.0.0", "--port", "$PORT" `
    -WorkingDirectory $APP_DIR `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput "$APP_DIR\server_output.log" `
    -RedirectStandardError "$APP_DIR\server_error.log"

# #region agent log
$logData = @{
    location = "start_fpl_api_windows_background.ps1:45"
    message = "Server process started"
    data = @{
        pid = $process.Id
        hasExited = $process.HasExited
        exitCode = if ($process.HasExited) { $process.ExitCode } else { $null }
    }
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    sessionId = "debug-session"
    runId = "run1"
    hypothesisId = "A"
} | ConvertTo-Json -Compress
Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
# #endregion

if ($process) {
    Write-Host "Server process started (PID: $($process.Id))" -ForegroundColor Green
} else {
    Write-Host "Server job started (Job ID: $($job.Id)), waiting for process..." -ForegroundColor Yellow
    $process = $null
}
Write-Host "Output log: $APP_DIR\server_output.log" -ForegroundColor Cyan
Write-Host "Error log: $APP_DIR\server_error.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting 5 seconds for service to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# #region agent log
Start-Sleep -Seconds 5
if ($process) {
    $logData = @{
        location = "start_fpl_api_windows_background.ps1:70"
        message = "Checking process status after startup"
        data = @{
            pid = $process.Id
            hasExited = $process.HasExited
            exitCode = if ($process.HasExited) { $process.ExitCode } else { $null }
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        sessionId = "debug-session"
        runId = "run2"
        hypothesisId = "F"
    } | ConvertTo-Json -Compress
    Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
}

$tcpConnections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
$logData = @{
    location = "start_fpl_api_windows_background.ps1:85"
    message = "Checking TCP connections on port"
    data = @{
        port = $PORT
        connectionCount = ($tcpConnections | Measure-Object).Count
        connections = $tcpConnections | Select-Object LocalAddress, LocalPort, State, OwningProcess | ConvertTo-Json -Compress
    }
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    sessionId = "debug-session"
    runId = "run2"
    hypothesisId = "B"
} | ConvertTo-Json -Compress
Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
# #endregion

# Test if service is responding locally
try {
    # #region agent log
    $logData = @{
        location = "start_fpl_api_windows_background.ps1:100"
        message = "Testing localhost connection"
        data = @{
            url = "http://localhost:$PORT/api/v1/health"
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        sessionId = "debug-session"
        runId = "run2"
        hypothesisId = "C"
    } | ConvertTo-Json -Compress
    Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
    # #endregion
    
    $response = Invoke-WebRequest -Uri "http://localhost:$PORT/api/v1/health" -TimeoutSec 5 -ErrorAction Stop
    
    # #region agent log
    $logData = @{
        location = "start_fpl_api_windows_background.ps1:110"
        message = "Localhost connection successful"
        data = @{
            statusCode = $response.StatusCode
            contentLength = $response.Content.Length
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        sessionId = "debug-session"
        runId = "run2"
        hypothesisId = "C"
    } | ConvertTo-Json -Compress
    Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
    # #endregion
    
    Write-Host "Service is responding! Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Service is accessible at: http://0.0.0.0:$PORT" -ForegroundColor Green
} catch {
    # #region agent log
    $logData = @{
        location = "start_fpl_api_windows_background.ps1:125"
        message = "Localhost connection failed"
        data = @{
            error = $_.Exception.Message
            errorType = $_.Exception.GetType().FullName
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        sessionId = "debug-session"
        runId = "run2"
        hypothesisId = "C"
    } | ConvertTo-Json -Compress
    Add-Content -Path "C:\fpl-api\debug_startup.log" -Value $logData
    # #endregion
    
    Write-Host "Service may still be starting. Check logs:" -ForegroundColor Yellow
    Write-Host "  Get-Content $APP_DIR\server_output.log -Tail 20" -ForegroundColor Cyan
    Write-Host "  Get-Content $APP_DIR\server_error.log -Tail 20" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "To check if service is running:" -ForegroundColor Cyan
if ($process) {
    Write-Host ('  Get-Process -Id ' + $process.Id + ' -ErrorAction SilentlyContinue') -ForegroundColor White
    Write-Host ('  Get-Job -Id ' + $job.Id) -ForegroundColor White
} else {
    Write-Host ('  Get-Job -Id ' + $job.Id) -ForegroundColor White
    Write-Host ('  Get-NetTCPConnection -LocalPort ' + $PORT) -ForegroundColor White
}
Write-Host ""
Write-Host "To stop the service:" -ForegroundColor Cyan
if ($process) {
    Write-Host ('  Stop-Process -Id ' + $process.Id + ' -Force') -ForegroundColor White
}
Write-Host ('  Stop-Job -Id ' + $job.Id) -ForegroundColor White
Write-Host ""
