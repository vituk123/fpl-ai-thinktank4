#!/bin/bash
# Setup Google Compute Engine VM for FPL API Backend

set -e

PROJECT_ID="instant-vent-481016-c0"
VM_NAME="fpl-api-vm"
ZONE="us-central1-a"
MACHINE_TYPE="e2-standard-8"  # 8 vCPUs, 32GB RAM
BOOT_DISK_SIZE="50GB"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

echo "🚀 Setting up GCE VM for FPL API Backend..."
echo "   Project: ${PROJECT_ID}"
echo "   VM Name: ${VM_NAME}"
echo "   Zone: ${ZONE}"
echo "   Machine Type: ${MACHINE_TYPE}"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

# Enable Compute Engine API
echo "📋 Enabling Compute Engine API..."
gcloud services enable compute.googleapis.com

# Create firewall rule for HTTP
echo "🔥 Creating firewall rule for HTTP..."
gcloud compute firewall-rules create allow-http-fpl-api \
    --allow tcp:80 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP traffic to FPL API VM" \
    --target-tags fpl-api \
    2>/dev/null || echo "Firewall rule may already exist"

# Create firewall rule for HTTPS
echo "🔥 Creating firewall rule for HTTPS..."
gcloud compute firewall-rules create allow-https-fpl-api \
    --allow tcp:443 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTPS traffic to FPL API VM" \
    --target-tags fpl-api \
    2>/dev/null || echo "Firewall rule may already exist"

# Read startup script
STARTUP_SCRIPT=$(cat vm-startup-script.sh)

# Create VM instance
echo "🖥️  Creating VM instance..."
gcloud compute instances create ${VM_NAME} \
    --zone=${ZONE} \
    --machine-type=${MACHINE_TYPE} \
    --boot-disk-size=${BOOT_DISK_SIZE} \
    --boot-disk-type=pd-ssd \
    --image-family=${IMAGE_FAMILY} \
    --image-project=${IMAGE_PROJECT} \
    --tags=fpl-api \
    --metadata-from-file startup-script=vm-startup-script.sh \
    --scopes=https://www.googleapis.com/auth/cloud-platform

echo ""
echo "✅ VM created successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Wait for VM to finish startup (2-3 minutes)"
echo "   2. Get VM external IP: gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo "   3. Deploy code: ./deploy_to_vm.sh"
echo "   4. Update Supabase: supabase secrets set GCE_VM_API_URL=http://[VM_IP]"
echo ""

