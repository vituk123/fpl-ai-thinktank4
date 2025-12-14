#!/bin/bash
# Startup script for GCE VM - runs on first boot
# This script sets up Docker, installs dependencies, and starts the FPL API service

set -e

echo "🚀 Starting FPL API VM setup..."
echo "Timestamp: $(date)"

# Update system packages
echo "📦 Updating system packages..."
apt-get update
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    usermod -aG docker $USER || usermod -aG docker $(whoami)
fi

# Install Google Cloud SDK (for accessing Secret Manager)
echo "☁️ Installing Google Cloud SDK..."
if ! command -v gcloud &> /dev/null; then
    curl https://sdk.cloud.google.com | bash
    export PATH=$HOME/google-cloud-sdk/bin:$PATH
    exec -l $SHELL
fi

# Create app directory
APP_DIR="/opt/fpl-api"
mkdir -p $APP_DIR
cd $APP_DIR

# Clone repository (if not exists) or pull latest
if [ ! -d "$APP_DIR/.git" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/vituk123/fpl-ai-thinktank4.git $APP_DIR || echo "Repository may already exist"
else
    echo "🔄 Pulling latest code..."
    cd $APP_DIR
    git pull origin main || echo "Git pull failed, continuing..."
fi

# Install gcloud auth helper for Docker
echo "🔐 Configuring Docker for GCR..."
gcloud auth configure-docker --quiet || echo "Docker auth configuration skipped"

# Create environment file with secrets from GCP Secret Manager
echo "🔐 Loading secrets from GCP Secret Manager..."
PROJECT_ID="instant-vent-481016-c0"
ENV_FILE="${APP_DIR}/.env"

# Install gcloud if not in PATH
if ! command -v gcloud &> /dev/null; then
    if [ -f "$HOME/google-cloud-sdk/bin/gcloud" ]; then
        export PATH=$HOME/google-cloud-sdk/bin:$PATH
    fi
fi

# Load secrets and create .env file
cat > ${ENV_FILE} << EOF
# Secrets loaded from GCP Secret Manager
SUPABASE_URL=$(gcloud secrets versions access latest --secret=supabase-url --project=${PROJECT_ID} 2>/dev/null || echo "")
SUPABASE_KEY=$(gcloud secrets versions access latest --secret=supabase-key --project=${PROJECT_ID} 2>/dev/null || echo "")
DB_CONNECTION_STRING=$(gcloud secrets versions access latest --secret=db-connection --project=${PROJECT_ID} 2>/dev/null || echo "")
API_FOOTBALL_KEY=$(gcloud secrets versions access latest --secret=api-football-key --project=${PROJECT_ID} 2>/dev/null || echo "")
NEWS_API_KEY=$(gcloud secrets versions access latest --secret=news-api-key --project=${PROJECT_ID} 2>/dev/null || echo "")
PYTHON_VERSION=3.11
PORT=8080
EOF

chmod 600 ${ENV_FILE}

# Create systemd service file
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/fpl-api.service << EOF
[Unit]
Description=FPL API Backend Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable fpl-api.service

echo "✅ VM setup complete!"
echo "Service will start automatically on boot."
echo "To start now: systemctl start fpl-api"
echo ""
echo "📝 Note: First deployment requires:"
echo "   1. Code to be cloned/pulled to ${APP_DIR}"
echo "   2. Run: ./deploy_to_vm.sh from your local machine"

