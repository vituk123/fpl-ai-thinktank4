#!/bin/bash
# Check GCE VM status

set -e

VM_NAME="fpl-api-vm"
ZONE="us-central1-a"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

echo "📊 VM Status:"
gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format="table(
    name,
    status,
    machineType.scope(machineTypes):label=MACHINE_TYPE,
    networkInterfaces[0].accessConfigs[0].natIP:label=EXTERNAL_IP
)"

echo ""
echo "🐳 Docker containers on VM:"
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command="docker ps" 2>/dev/null || echo "VM may be stopped or not accessible"

echo ""
echo "📡 Service health:"
VM_IP=$(gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "")
if [ ! -z "$VM_IP" ]; then
    curl -s http://${VM_IP}/api/v1/health | python3 -m json.tool 2>/dev/null || echo "Service not responding"
else
    echo "VM is stopped or has no external IP"
fi

