# PowerShell script to create Windows Service for FPL API
# Run this on the Windows server as Administrator

$APP_DIR = "C:\fpl-api"
$SERVICE_NAME = "FPL-API"
$DISPLAY_NAME = "FPL API Backend Service"
$DESCRIPTION = "FPL Optimization API Backend Service"

Write-Host "🔧 Creating Windows Service for FPL API..." -ForegroundColor Green

# Check if NSSM is installed
$nssmPath = "C:\Program Files\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    Write-Host "📦 Installing NSSM (Non-Sucking Service Manager)..." -ForegroundColor Yellow
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    $nssmExtract = "$env:TEMP\nssm"
    
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip -UseBasicParsing
    Expand-Archive -Path $nssmZip -DestinationPath $nssmExtract -Force
    
    # Copy to Program Files
    $nssmVersion = Get-ChildItem $nssmExtract -Directory | Select-Object -First 1
    Copy-Item "$($nssmVersion.FullName)\win64\nssm.exe" -Destination $nssmPath -Force
    
    # Clean up
    Remove-Item $nssmZip -Force
    Remove-Item $nssmExtract -Recurse -Force
    
    Write-Host "✅ NSSM installed" -ForegroundColor Green
}

# Remove existing service if it exists
$existingService = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "⚠️  Removing existing service..." -ForegroundColor Yellow
    Stop-Service -Name $SERVICE_NAME -Force -ErrorAction SilentlyContinue
    & $nssmPath remove $SERVICE_NAME confirm
}

# Create new service
Write-Host "📝 Creating service..." -ForegroundColor Yellow
& $nssmPath install $SERVICE_NAME "$APP_DIR\venv\Scripts\python.exe" "-m uvicorn src.dashboard_api:app --host 0.0.0.0 --port 8080"
& $nssmPath set $SERVICE_NAME AppDirectory $APP_DIR
& $nssmPath set $SERVICE_NAME DisplayName $DISPLAY_NAME
& $nssmPath set $SERVICE_NAME Description $DESCRIPTION
& $nssmPath set $SERVICE_NAME Start SERVICE_AUTO_START
& $nssmPath set $SERVICE_NAME AppStdout "$APP_DIR\server.log"
& $nssmPath set $SERVICE_NAME AppStderr "$APP_DIR\server-error.log"

# Set environment variables from .env file
if (Test-Path "$APP_DIR\.env") {
    Write-Host "📝 Loading environment variables from .env file..." -ForegroundColor Yellow
    Get-Content "$APP_DIR\.env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            & $nssmPath set $SERVICE_NAME AppEnvironmentExtra "$key=$value"
        }
    }
}

# Start the service
Write-Host "🚀 Starting service..." -ForegroundColor Yellow
Start-Service -Name $SERVICE_NAME

# Wait a moment
Start-Sleep -Seconds 3

# Check status
$service = Get-Service -Name $SERVICE_NAME
if ($service.Status -eq 'Running') {
    Write-Host "✅ Service created and started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Service Management:" -ForegroundColor Cyan
    Write-Host "   Start:   Start-Service -Name $SERVICE_NAME" -ForegroundColor White
    Write-Host "   Stop:    Stop-Service -Name $SERVICE_NAME" -ForegroundColor White
    Write-Host "   Status:  Get-Service -Name $SERVICE_NAME" -ForegroundColor White
    Write-Host "   Logs:    Get-Content $APP_DIR\server.log -Tail 50" -ForegroundColor White
} else {
    Write-Host "⚠️  Service created but not running. Status: $($service.Status)" -ForegroundColor Yellow
    Write-Host "   Check logs: Get-Content $APP_DIR\server-error.log" -ForegroundColor Yellow
}

