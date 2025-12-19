#!/bin/bash
# Simplified deployment script for Windows Server
# Uses basic Windows commands via SSH

set -e

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
APP_DIR="C:\\fpl-api"
PORT=8080

echo "🚀 Deploying FPL API to ByteHosty Windows Server..."
echo "   Server: ${SERVER_IP}"
echo "   User: ${SERVER_USER}"
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

# Detect capabilities
echo "🔍 Detecting server capabilities..."
PYTHON_CMD=$(ssh_cmd "python --version 2>&1 || python3 --version 2>&1 || echo 'Not found'" 2>&1 | tail -1)
GIT_CMD=$(ssh_cmd "git --version 2>&1 || echo 'Not found'" 2>&1 | tail -1)

echo "   Python: ${PYTHON_CMD}"
echo "   Git: ${GIT_CMD}"
echo ""

# Create app directory
echo "📁 Creating app directory..."
ssh_cmd "if not exist \"${APP_DIR}\" mkdir \"${APP_DIR}\"" 2>&1 | grep -v "not recognized" || true

# Copy files
echo "📦 Copying files to server..."
scp_cmd requirements.txt "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\" 2>&1 | grep -v "Warning" || true
scp_cmd config.yml "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\" 2>&1 | grep -v "Warning" || true

echo "📦 Copying source code..."
scp_cmd -r src "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\" 2>&1 | grep -v "Warning" || true

# Copy models if they exist
if [ -d "models" ]; then
    echo "📦 Copying ML models..."
    ssh_cmd "if not exist \"${APP_DIR}\\models\" mkdir \"${APP_DIR}\\models\"" 2>&1 | grep -v "not recognized" || true
    for model in models/*.pkl; do
        if [ -f "$model" ]; then
            scp_cmd "$model" "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\models\\" 2>&1 | grep -v "Warning" || true
        fi
    done
fi

# Get environment variables
echo "🔐 Setting up environment variables..."
echo "Please provide the following secrets (or press Enter to use defaults):"
echo ""

read -p "Supabase URL (default: https://sdezcbesdubplacfxibc.supabase.co): " SUPABASE_URL
SUPABASE_URL=${SUPABASE_URL:-https://sdezcbesdubplacfxibc.supabase.co}

read -sp "Supabase Key: " SUPABASE_KEY
echo ""

read -sp "Database Connection String: " DB_CONNECTION_STRING
echo ""

read -p "API Football Key (default: 08b18b2d60e1cfea7769c7276226d2d1): " API_FOOTBALL_KEY
API_FOOTBALL_KEY=${API_FOOTBALL_KEY:-08b18b2d60e1cfea7769c7276226d2d1}

read -p "News API Key (default: pub_a13e0ce062804c5891decaa7ac8a27b9): " NEWS_API_KEY
NEWS_API_KEY=${NEWS_API_KEY:-pub_a13e0ce062804c5891decaa7ac8a27b9}

# Create .env file on server using PowerShell
echo "📝 Creating .env file on server..."
ssh_cmd "powershell -Command \"@'
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_KEY=${SUPABASE_KEY}
DB_CONNECTION_STRING=${DB_CONNECTION_STRING}
API_FOOTBALL_KEY=${API_FOOTBALL_KEY}
NEWS_API_KEY=${NEWS_API_KEY}
PYTHON_VERSION=3.11
PORT=${PORT}
'@ | Set-Content -Path '${APP_DIR}\\.env'\""

# Setup Python environment
echo "🐍 Setting up Python environment..."
ssh_cmd "cd ${APP_DIR} && python -m venv venv && venv\\Scripts\\activate && python -m pip install --upgrade pip && pip install -r requirements.txt"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Service URL: http://${SERVER_IP}:${PORT}"
echo "📝 To start the service manually:"
echo "   ssh ${SERVER_USER}@${SERVER_IP}"
echo "   cd ${APP_DIR}"
echo "   venv\\Scripts\\activate"
echo "   python -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port ${PORT}"
echo ""
echo "📝 Test: curl http://${SERVER_IP}:${PORT}/api/v1/health"
echo ""

