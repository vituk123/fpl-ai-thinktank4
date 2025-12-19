#!/bin/bash
# Deploy FPL API to ByteHosty VPS

set -e

# Server configuration
SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
APP_DIR="/opt/fpl-api"
PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying FPL API to ByteHosty VPS...${NC}"
echo "   Server: ${SERVER_IP}"
echo "   User: ${SERVER_USER}"
echo ""

# Check if sshpass is installed (for password authentication)
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  sshpass not found. Installing...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass
        else
            echo -e "${RED}❌ Please install sshpass: brew install hudochenkov/sshpass/sshpass${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update && sudo apt-get install -y sshpass || \
        sudo yum install -y sshpass || \
        echo -e "${RED}❌ Please install sshpass manually${NC}"
    fi
fi

# Function to run SSH command with password
ssh_cmd() {
    sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SERVER_USER}@${SERVER_IP}" "$@"
}

# Function to copy file with password
scp_cmd() {
    sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "$@"
}

# Test SSH connection
echo -e "${YELLOW}📡 Testing SSH connection...${NC}"
if ssh_cmd "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${RED}❌ SSH connection failed. Please check:${NC}"
    echo "   1. Server IP is correct: ${SERVER_IP}"
    echo "   2. SSH service is running on the server"
    echo "   3. Firewall allows SSH connections"
    echo "   4. Credentials are correct"
    exit 1
fi

# Detect server OS and capabilities
echo -e "${YELLOW}🔍 Detecting server capabilities...${NC}"
OS_INFO=$(ssh_cmd "uname -a" 2>/dev/null || echo "Unknown")
PYTHON_VERSION=$(ssh_cmd "python3 --version 2>/dev/null || python --version 2>/dev/null || echo 'Not found'" 2>/dev/null || echo "Not found")
DOCKER_VERSION=$(ssh_cmd "docker --version 2>/dev/null || echo 'Not found'" 2>/dev/null || echo "Not found")
DISK_SPACE=$(ssh_cmd "df -h / | tail -1 | awk '{print \$4}'" 2>/dev/null || echo "Unknown")
MEMORY=$(ssh_cmd "free -h 2>/dev/null | grep Mem | awk '{print \$2}' || echo 'Unknown'" 2>/dev/null || echo "Unknown")

echo "   OS: ${OS_INFO}"
echo "   Python: ${PYTHON_VERSION}"
echo "   Docker: ${DOCKER_VERSION}"
echo "   Disk Space: ${DISK_SPACE}"
echo "   Memory: ${MEMORY}"
echo ""

# Determine deployment method
USE_DOCKER=false
if echo "$DOCKER_VERSION" | grep -q "version"; then
    USE_DOCKER=true
    echo -e "${GREEN}✅ Docker detected - will use Docker deployment${NC}"
else
    echo -e "${YELLOW}⚠️  Docker not found - will use direct Python deployment${NC}"
fi

# Create app directory on server
echo -e "${YELLOW}📁 Creating app directory...${NC}"
ssh_cmd "sudo mkdir -p ${APP_DIR} && sudo chown -R ${SERVER_USER}:${SERVER_USER} ${APP_DIR} || sudo chown -R ${SERVER_USER} ${APP_DIR} 2>/dev/null || true"

# Copy essential files
echo -e "${YELLOW}📦 Copying files to server...${NC}"
scp_cmd Dockerfile "${SERVER_USER}@${SERVER_IP}:${APP_DIR}/" 2>/dev/null || echo "Dockerfile copy skipped"
scp_cmd docker-compose.yml "${SERVER_USER}@${SERVER_IP}:${APP_DIR}/" 2>/dev/null || echo "docker-compose.yml copy skipped"
scp_cmd requirements.txt "${SERVER_USER}@${SERVER_IP}:${APP_DIR}/"
scp_cmd config.yml "${SERVER_USER}@${SERVER_IP}:${APP_DIR}/"

# Copy source code
echo -e "${YELLOW}📦 Copying source code...${NC}"
scp_cmd -r src/ "${SERVER_USER}@${SERVER_IP}:${APP_DIR}/"

# Copy models directory if it exists
if [ -d "models" ]; then
    echo -e "${YELLOW}📦 Copying ML models...${NC}"
    ssh_cmd "mkdir -p ${APP_DIR}/models"
    scp_cmd -r models/*.pkl "${SERVER_USER}@${SERVER_IP}:${APP_DIR}/models/" 2>/dev/null || echo "Models copy skipped"
fi

# Get environment variables (prompt user or use existing)
echo -e "${YELLOW}🔐 Setting up environment variables...${NC}"
echo "Please provide the following secrets (or press Enter to skip and set manually later):"
echo ""

read -p "Supabase URL (default: https://sdezcbesdubplacfxibc.supabase.co): " SUPABASE_URL
SUPABASE_URL=${SUPABASE_URL:-https://sdezcbesdubplacfxibc.supabase.co}

read -sp "Supabase Key: " SUPABASE_KEY
echo ""

read -sp "Database Connection String: " DB_CONNECTION_STRING
echo ""

read -p "API Football Key (from config.yml or press Enter to use default): " API_FOOTBALL_KEY
API_FOOTBALL_KEY=${API_FOOTBALL_KEY:-08b18b2d60e1cfea7769c7276226d2d1}

read -p "News API Key (from config.yml or press Enter to use default): " NEWS_API_KEY
NEWS_API_KEY=${NEWS_API_KEY:-pub_a13e0ce062804c5891decaa7ac8a27b9}

# Create .env file on server
echo -e "${YELLOW}📝 Creating .env file on server...${NC}"
ssh_cmd "cat > ${APP_DIR}/.env << 'ENVEOF'
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_KEY=${SUPABASE_KEY}
DB_CONNECTION_STRING=${DB_CONNECTION_STRING}
API_FOOTBALL_KEY=${API_FOOTBALL_KEY}
NEWS_API_KEY=${NEWS_API_KEY}
PYTHON_VERSION=3.11
PORT=${PORT}
ENVEOF
chmod 600 ${APP_DIR}/.env"

# Deploy based on method
if [ "$USE_DOCKER" = true ]; then
    echo -e "${YELLOW}🐳 Deploying with Docker...${NC}"
    ssh_cmd "cd ${APP_DIR} && \
        docker compose down || true && \
        docker compose build --no-cache && \
        docker compose up -d"
else
    echo -e "${YELLOW}🐍 Deploying with Python...${NC}"
    
    # Install Python dependencies
    ssh_cmd "cd ${APP_DIR} && \
        python3 -m venv venv || python3.11 -m venv venv || true && \
        source venv/bin/activate && \
        pip install --upgrade pip && \
        pip install -r requirements.txt"
    
    # Create systemd service
    ssh_cmd "sudo tee /etc/systemd/system/fpl-api.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=FPL API Backend Service
After=network.target

[Service]
Type=simple
User=${SERVER_USER}
WorkingDirectory=${APP_DIR}
Environment=\"PATH=${APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin\"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn src.dashboard_api:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF
"
    
    # Enable and start service
    ssh_cmd "sudo systemctl daemon-reload && \
        sudo systemctl enable fpl-api.service && \
        sudo systemctl restart fpl-api.service"
fi

# Wait for service to start
echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
sleep 15

# Test health endpoint
echo -e "${YELLOW}🏥 Testing health endpoint...${NC}"
HEALTH_URL="http://${SERVER_IP}:${PORT}/api/v1/health"
if curl -s --max-time 10 "${HEALTH_URL}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
    echo ""
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo ""
    echo "🌐 Service URL: ${HEALTH_URL}"
    echo "📝 Test: curl ${HEALTH_URL}"
    echo ""
    
    # Show service status
    if [ "$USE_DOCKER" = true ]; then
        ssh_cmd "cd ${APP_DIR} && docker compose ps"
    else
        ssh_cmd "sudo systemctl status fpl-api.service --no-pager -l"
    fi
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "   Please check logs:"
    if [ "$USE_DOCKER" = true ]; then
        echo "   ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker compose logs'"
    else
        echo "   ssh ${SERVER_USER}@${SERVER_IP} 'sudo journalctl -u fpl-api.service -n 50'"
    fi
    exit 1
fi

