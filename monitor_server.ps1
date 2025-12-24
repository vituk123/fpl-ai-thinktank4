# Monitor server process and connections
$PORT = 8080
$monitorDuration = 30  # seconds

Write-Host "Monitoring server for $monitorDuration seconds..." -ForegroundColor Cyan

$startTime = Get-Date
$endTime = $startTime.AddSeconds($monitorDuration)

while ((Get-Date) -lt $endTime) {
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
    $tcpConnections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
    
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Status Check:" -ForegroundColor Yellow
    Write-Host "  Python processes: $($pythonProcesses.Count)"
    if ($pythonProcesses) {
        foreach ($proc in $pythonProcesses) {
            Write-Host "    PID: $($proc.Id), Runtime: $(((Get-Date) - $proc.StartTime).TotalSeconds) seconds"
        }
    }
    
    Write-Host "  TCP connections on port $PORT : $($tcpConnections.Count)"
    if ($tcpConnections) {
        foreach ($conn in $tcpConnections) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { "Unknown" }
            Write-Host "    $($conn.LocalAddress):$($conn.LocalPort) - $($conn.State) - PID: $($conn.OwningProcess) ($procName)"
        }
    }
    
    # Try to connect
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$PORT/api/v1/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  Health check: SUCCESS (Status: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "  Health check: FAILED ($($_.Exception.Message))" -ForegroundColor Red
    }
    
    Start-Sleep -Seconds 2
}

Write-Host "`nMonitoring complete." -ForegroundColor Cyan

