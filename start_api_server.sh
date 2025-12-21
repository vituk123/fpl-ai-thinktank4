#!/bin/bash
# Start FPL API server on ByteHosty Windows server (with output logging)

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
APP_DIR="C:\\fpl-api"
LOG_FILE="server_output.log"

echo "🚀 Starting FPL API server on ByteHosty..."

sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "${SERVER_USER}@${SERVER_IP}" "powershell -Command \"
    cd ${APP_DIR};
    
    # Determine Python command
    \$pythonCmd = if (Test-Path 'venv\\Scripts\\python.exe') { 
        'venv\\Scripts\\python.exe' 
    } else { 
        'py' 
    };
    
    Write-Host 'Using Python: ' \$pythonCmd;
    Write-Host 'Starting server on port 8080...';
    
    # Start server and redirect output to log file
    Start-Process -FilePath \$pythonCmd -ArgumentList '-m', 'uvicorn', 'src.dashboard_api:app', '--host', '0.0.0.0', '--port', '8080' -WindowStyle Hidden -RedirectStandardOutput '${LOG_FILE}' -RedirectStandardError '${LOG_FILE}';
    
    Start-Sleep -Seconds 3;
    Write-Host 'Server start command executed';
    Write-Host 'Check logs at: ${APP_DIR}\\${LOG_FILE}';
\"" 2>&1

echo ""
echo "✅ Server start command sent"
echo "💡 Waiting 20 seconds for server to initialize..."
sleep 20

echo ""
echo "🔍 Checking server status..."
curl -s --connect-timeout 5 http://${SERVER_IP}:8080/api/v1/health 2>&1 || echo "Server may still be starting..."

echo ""
echo "📝 To view server logs:"
echo "ssh ${SERVER_USER}@${SERVER_IP} 'type ${APP_DIR}\\${LOG_FILE}'"

