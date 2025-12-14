#!/bin/bash
# Stop the GCE VM (to save costs)

set -e

VM_NAME="fpl-api-vm"
ZONE="us-central1-a"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

echo "⏹️  Stopping VM: ${VM_NAME}..."
gcloud compute instances stop ${VM_NAME} --zone=${ZONE}

echo "✅ VM stopped. You're only charged for disk storage now."
echo "💡 To start again: ./start_vm.sh"

