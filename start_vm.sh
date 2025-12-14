#!/bin/bash
# Start the GCE VM

set -e

VM_NAME="fpl-api-vm"
ZONE="us-central1-a"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

echo "▶️  Starting VM: ${VM_NAME}..."
gcloud compute instances start ${VM_NAME} --zone=${ZONE}

echo "⏳ Waiting for VM to be ready..."
sleep 30

VM_IP=$(gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "✅ VM started!"
echo "🌐 IP: ${VM_IP}"
echo "📝 Service URL: http://${VM_IP}"

