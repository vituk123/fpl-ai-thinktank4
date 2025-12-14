#!/bin/bash
# View VM and service logs

set -e

VM_NAME="fpl-api-vm"
ZONE="us-central1-a"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

if [ "$1" == "docker" ]; then
    echo "🐳 Docker container logs:"
    gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command="cd /opt/fpl-api && docker compose logs --tail=100 -f"
else
    echo "📋 VM system logs:"
    gcloud compute instances get-serial-port-output ${VM_NAME} --zone=${ZONE} --port=1 | tail -n 50
    echo ""
    echo "💡 For Docker logs, run: ./vm_logs.sh docker"
fi

