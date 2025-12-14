#!/bin/bash
# Deploy FPL API to GCE VM

set -e

PROJECT_ID="instant-vent-481016-c0"
VM_NAME="fpl-api-vm"
ZONE="us-central1-a"
APP_DIR="/opt/fpl-api"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

echo "🚀 Deploying FPL API to GCE VM..."
echo "   VM: ${VM_NAME}"
echo "   Zone: ${ZONE}"
echo ""

# Get VM external IP
VM_IP=$(gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "")

if [ -z "$VM_IP" ]; then
    echo "❌ Could not get VM IP. Is the VM running?"
    echo "   Check status: gcloud compute instances list"
    exit 1
fi

echo "📡 VM IP: ${VM_IP}"
echo ""

# Copy files to VM
echo "📦 Copying files to VM..."
gcloud compute scp --zone=${ZONE} \
    Dockerfile \
    docker-compose.yml \
    requirements.txt \
    ${VM_NAME}:${APP_DIR}/ || echo "Some files may already exist"

# Copy source code
echo "📦 Copying source code..."
gcloud compute scp --zone=${ZONE} --recurse \
    src/ \
    config.yml \
    ${VM_NAME}:${APP_DIR}/ || echo "Source code copy failed, will use git pull on VM"

# SSH into VM and deploy
echo "🔧 Deploying on VM..."
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command="
    # Fix ownership of /opt/fpl-api if it exists
    if [ -d ${APP_DIR} ]; then
        sudo chown -R \$USER:\$USER ${APP_DIR} || true
    else
        sudo mkdir -p ${APP_DIR}
        sudo chown -R \$USER:\$USER ${APP_DIR}
    fi
    
    cd ${APP_DIR} || exit 1
    
    # Clone repo if it doesn't exist
    if [ ! -d '.git' ]; then
        echo '📥 Cloning repository...'
        git clone https://github.com/vituk123/fpl-ai-thinktank4.git . || echo 'Clone failed'
        sudo chown -R \$USER:\$USER . || true
    else
        echo '📥 Pulling latest code from GitHub...'
        git config --global --add safe.directory ${APP_DIR}
        git pull origin main || echo 'Git pull failed, using existing code'
    fi
    
    # Reload secrets into .env file
    echo '🔐 Reloading secrets from GCP Secret Manager...'
    PROJECT_ID='instant-vent-481016-c0'
    sudo tee .env > /dev/null << ENVEOF
SUPABASE_URL=\$(gcloud secrets versions access latest --secret=supabase-url --project=\${PROJECT_ID})
SUPABASE_KEY=\$(gcloud secrets versions access latest --secret=supabase-key --project=\${PROJECT_ID})
DB_CONNECTION_STRING=\$(gcloud secrets versions access latest --secret=db-connection --project=\${PROJECT_ID})
API_FOOTBALL_KEY=\$(gcloud secrets versions access latest --secret=api-football-key --project=\${PROJECT_ID})
NEWS_API_KEY=\$(gcloud secrets versions access latest --secret=news-api-key --project=\${PROJECT_ID})
PYTHON_VERSION=3.11
PORT=8080
ENVEOF
    sudo chmod 600 .env
    sudo chown \$USER:\$USER .env || true
    
    echo '🐳 Building and starting Docker container...'
    docker compose down || true
    docker compose build --no-cache
    docker compose up -d
    
    echo '⏳ Waiting for service to start...'
    sleep 15
    
    echo '✅ Deployment complete!'
    echo '🌐 Service URL: http://${VM_IP}'
    docker compose ps
    echo ''
    echo '📋 Testing health endpoint...'
    curl -s http://localhost:80/api/v1/health | head -n 5 || echo 'Health check failed'
"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Service URL: http://${VM_IP}"
echo "📝 Test: curl http://${VM_IP}/api/v1/health"
echo ""

