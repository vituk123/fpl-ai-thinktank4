# PowerShell script to start the frontend web server on Windows
$ErrorActionPreference = "Stop"

$FRONTEND_DIR = "C:\fpl-api\frontend\dist"
$PORT = 3000
$PYTHON = "C:\fpl-api\venv\Scripts\python.exe"
$SCRIPT = "C:\fpl-api\serve_frontend.py"

Write-Host "Starting Frontend Web Server..."
Write-Host "Frontend directory: $FRONTEND_DIR"
Write-Host "Port: $PORT"

# Check if frontend directory exists
if (-not (Test-Path $FRONTEND_DIR)) {
    Write-Host "ERROR: Frontend directory not found: $FRONTEND_DIR" -ForegroundColor Red
    Write-Host "Please build the frontend first: cd frontend && npm run build"
    exit 1
}

# Check if index.html exists
if (-not (Test-Path "$FRONTEND_DIR\index.html")) {
    Write-Host "ERROR: index.html not found in $FRONTEND_DIR" -ForegroundColor Red
    Write-Host "Please build the frontend first: cd frontend && npm run build"
    exit 1
}

# Stop any existing Python processes on this port
Write-Host "Checking for existing processes on port $PORT..."
$existingProcess = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcess) {
    Write-Host "Stopping existing process on port $PORT (PID: $existingProcess)..."
    Stop-Process -Id $existingProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start the server in background
Write-Host "Starting frontend server..."
$process = Start-Process -FilePath $PYTHON -ArgumentList $SCRIPT -WindowStyle Hidden -PassThru -RedirectStandardOutput "C:\fpl-api\frontend_server_output.log" -RedirectStandardError "C:\fpl-api\frontend_server_error.log"

$processId = $process.Id
Write-Host "Frontend server started (PID: $processId)"
Write-Host "Output log: C:\fpl-api\frontend_server_output.log"
Write-Host "Error log: C:\fpl-api\frontend_server_error.log"
Write-Host ""
Write-Host "Waiting 3 seconds for server to initialize..."
Start-Sleep -Seconds 3

# Check if server is running
$serverRunning = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($serverRunning) {
    Write-Host "Frontend server is running on port $PORT" -ForegroundColor Green
    Write-Host "Open http://198.23.185.233:$PORT in your browser"
} else {
    Write-Host "Server may still be starting. Check logs:" -ForegroundColor Yellow
    Write-Host "  Get-Content C:\fpl-api\frontend_server_output.log -Tail 20"
    Write-Host "  Get-Content C:\fpl-api\frontend_server_error.log -Tail 20"
}

Write-Host ""
Write-Host "To stop the server:"
Write-Host "  Stop-Process -Id $processId -Force"
