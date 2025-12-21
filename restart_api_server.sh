#!/bin/bash
# Restart FPL API server on ByteHosty Windows server

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'

echo "🔄 Restarting FPL API server on ByteHosty..."

sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "${SERVER_USER}@${SERVER_IP}" "powershell -Command \"
    # Stop existing Python processes running dashboard_api
    \$processes = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        \$_.CommandLine = (Get-WmiObject Win32_Process -Filter \\\"ProcessId = \$(\$_.Id)\\\").CommandLine;
        \$_.CommandLine -like '*dashboard_api*' -or \$_.CommandLine -like '*uvicorn*'
    };
    if (\$processes) {
        Write-Host 'Stopping existing API processes...';
        \$processes | Stop-Process -Force -ErrorAction SilentlyContinue;
        Start-Sleep -Seconds 3;
    }
    
    # Wait for port to be free
    \$maxWait = 10;
    \$waited = 0;
    while (\$waited -lt \$maxWait) {
        \$listener = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue;
        if (-not \$listener) { break; }
        Start-Sleep -Seconds 1;
        \$waited++;
    }
    
    # Start server
    Write-Host 'Starting API server...';
    cd C:\\fpl-api;
    \$pythonCmd = if (Test-Path 'venv\\Scripts\\python.exe') { 'venv\\Scripts\\python.exe' } else { 'py' };
    Start-Process -FilePath \$pythonCmd -ArgumentList '-m', 'uvicorn', 'src.dashboard_api:app', '--host', '0.0.0.0', '--port', '8080' -WindowStyle Hidden;
    Start-Sleep -Seconds 5;
    Write-Host 'Server started';
\"" 2>&1

echo ""
echo "✅ Server restart command sent"
echo "💡 Waiting 10 seconds for server to start..."
sleep 10

echo ""
echo "🔍 Testing server health..."
curl -s http://${SERVER_IP}:8080/api/v1/health || echo "Server may still be starting..."

echo ""
echo "✅ Done! Check server status at: http://${SERVER_IP}:8080/api/v1/health"

