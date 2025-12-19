#!/bin/bash
# Final deployment script for Windows Server
# Automatically finds Python and handles Windows paths

set -e

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
APP_DIR="C:\\fpl-api"
PORT=8080

echo "🚀 Deploying FPL API to ByteHosty Windows Server..."
echo "   Server: ${SERVER_IP}"
echo ""

# Function to run SSH command
ssh_cmd() {
    sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SERVER_USER}@${SERVER_IP}" "$@"
}

# Test SSH connection
echo "📡 Testing SSH connection..."
if ssh_cmd "echo Connected" > /dev/null 2>&1; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    exit 1
fi

# Find Python installation
echo "🔍 Finding Python installation..."
PYTHON_PATH=$(ssh_cmd "powershell -Command \"\$py = Get-Command python -ErrorAction SilentlyContinue; if (\$py) { \$py.Source } else { \$locations = @('C:\\Program Files\\Python*', 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python*', 'C:\\Python*'); \$found = \$null; foreach (\$loc in \$locations) { Get-ChildItem -Path \$loc -Recurse -Filter 'python.exe' -ErrorAction SilentlyContinue | Where-Object { \$_.FullName -notmatch 'venv|Scripts\\\\' -and \$_.Directory.Name -eq 'Python311' } | Select-Object -First 1 | ForEach-Object { \$found = \$_.FullName; break } }; if (\$found) { \$found } else { 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe' } }\"" 2>&1 | tail -1)

if [ "$PYTHON_PATH" = "NOT_FOUND" ] || [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python not found. Please install Python 3.11 first."
    echo "   Run the install_prerequisites_windows.ps1 script on the server"
    exit 1
fi

echo "   ✅ Found Python: ${PYTHON_PATH}"

# Find Git
echo "🔍 Finding Git installation..."
GIT_PATH=$(ssh_cmd "powershell -Command \"\$git = Get-Command git -ErrorAction SilentlyContinue; if (\$git) { \$git.Source } else { if (Test-Path 'C:\\Program Files\\Git\\cmd\\git.exe') { 'C:\\Program Files\\Git\\cmd\\git.exe' } else { 'NOT_FOUND' } }\"" 2>&1 | tail -1)

if [ "$GIT_PATH" = "NOT_FOUND" ] || [ -z "$GIT_PATH" ]; then
    echo "❌ Git not found. Please install Git first."
    echo "   Run the install_prerequisites_windows.ps1 script on the server"
    exit 1
fi

echo "   ✅ Found Git: ${GIT_PATH}"
echo ""

# Create app directory
echo "📁 Creating app directory..."
ssh_cmd "if not exist \"${APP_DIR}\" mkdir \"${APP_DIR}\"" 2>&1 | grep -v "not recognized" || true

# Clone or update repository
echo "📥 Setting up repository..."
ssh_cmd "cd /d ${APP_DIR} && if exist .git (\"${GIT_PATH}\" pull) else (if exist . (rmdir /s /q . 2>nul & \"${GIT_PATH}\" clone https://github.com/vituk123/fpl-ai-thinktank4.git .) else (\"${GIT_PATH}\" clone https://github.com/vituk123/fpl-ai-thinktank4.git .))" 2>&1 | grep -v "Warning" || true

# Load environment variables from secrets file
echo ""
echo "🔐 Loading environment variables from secrets file..."
SECRETS_FILE="secrets.bytehosty"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ Secrets file not found: $SECRETS_FILE"
    echo "   Please create it from the template:"
    echo "   cp secrets.bytehosty.example $SECRETS_FILE"
    echo "   Then edit $SECRETS_FILE with your actual secrets"
    exit 1
fi

# Source the secrets file
source "$SECRETS_FILE"

# Validate required variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ] || [ -z "$DB_CONNECTION_STRING" ]; then
    echo "❌ Missing required secrets in $SECRETS_FILE"
    echo "   Required: SUPABASE_URL, SUPABASE_KEY, DB_CONNECTION_STRING"
    exit 1
fi

# Set defaults for optional variables
API_FOOTBALL_KEY=${API_FOOTBALL_KEY:-08b18b2d60e1cfea7769c7276226d2d1}
NEWS_API_KEY=${NEWS_API_KEY:-pub_a13e0ce062804c5891decaa7ac8a27b9}

echo "   ✅ Secrets loaded from $SECRETS_FILE"

# Create .env file
echo "📝 Creating .env file..."
# Create .env file line by line to avoid escaping issues
ssh_cmd "powershell -Command \"@('SUPABASE_URL=${SUPABASE_URL}','SUPABASE_KEY=${SUPABASE_KEY}','DB_CONNECTION_STRING=${DB_CONNECTION_STRING}','API_FOOTBALL_KEY=${API_FOOTBALL_KEY}','NEWS_API_KEY=${NEWS_API_KEY}','PYTHON_VERSION=3.11','PORT=${PORT}') | Set-Content -Path '${APP_DIR}\\.env' -Encoding UTF8\"" 2>&1 | grep -v "Warning" || true

# Setup Python virtual environment
echo "🐍 Setting up Python virtual environment..."
ssh_cmd "cd /d ${APP_DIR} && ${PYTHON_PATH} -m venv venv" 2>&1

# Install dependencies
echo "📦 Installing Python dependencies (this may take a few minutes)..."
ssh_cmd "cd /d ${APP_DIR} && venv\\Scripts\\python.exe -m pip install --upgrade pip" 2>&1
ssh_cmd "cd /d ${APP_DIR} && venv\\Scripts\\pip.exe install -r requirements.txt" 2>&1

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Service URL: http://${SERVER_IP}:${PORT}"
echo ""
echo "📝 To start the server:"
echo "   ssh ${SERVER_USER}@${SERVER_IP}"
echo "   cd ${APP_DIR}"
echo "   venv\\Scripts\\activate"
echo "   python -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port ${PORT}"
echo ""
echo "📝 Or test the deployment:"
echo "   curl http://${SERVER_IP}:${PORT}/api/v1/health"
echo ""

