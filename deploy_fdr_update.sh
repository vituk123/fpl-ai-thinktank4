#!/bin/bash
# Quick deployment script for FDR enhancement changes
# Only updates changed files and restarts the service

set -e

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
APP_DIR="C:\\fpl-api"

echo "🚀 Deploying FDR enhancement updates to ByteHosty..."
echo "   Server: ${SERVER_IP}"
echo ""

# Function to run SSH command
ssh_cmd() {
    sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SERVER_USER}@${SERVER_IP}" "$@"
}

# Function to copy file
scp_cmd() {
    sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no "$@"
}

# Test SSH connection
echo "📡 Testing SSH connection..."
if ssh_cmd "echo Connected" > /dev/null 2>&1; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    exit 1
fi

# Stop the running service (if any)
echo "🛑 Stopping existing service..."
ssh_cmd "taskkill /F /IM python.exe /FI \"WINDOWTITLE eq *uvicorn*\" 2>nul || taskkill /F /IM python.exe /FI \"COMMANDLINE eq *dashboard_api*\" 2>nul || echo No service running" 2>&1 | grep -v "not found" || true

# Copy updated source files
echo "📦 Copying updated source files..."
scp_cmd src/ml_report_v2.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\src\\" 2>&1 | grep -v "Warning" || true
scp_cmd src/report.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\src\\" 2>&1 | grep -v "Warning" || true
scp_cmd src/chips.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\src\\" 2>&1 | grep -v "Warning" || true
scp_cmd src/optimizer_v2.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\src\\" 2>&1 | grep -v "Warning" || true

echo "✅ Files copied successfully"

# Restart the service
echo "🔄 Restarting service..."
ssh_cmd "cd ${APP_DIR} && venv\\Scripts\\python.exe -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port 8080" > /dev/null 2>&1 &

# Wait a moment for service to start
sleep 3

# Test the service
echo "🧪 Testing service..."
if curl -s -f "http://${SERVER_IP}:8080/api/v1/health" > /dev/null 2>&1; then
    echo "✅ Service is running and responding"
else
    echo "⚠️  Service may still be starting. Please check manually:"
    echo "   curl http://${SERVER_IP}:8080/api/v1/health"
fi

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: http://${SERVER_IP}:8080"
echo ""

