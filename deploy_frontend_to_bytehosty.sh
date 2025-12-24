#!/bin/bash
# Deploy frontend to ByteHosty server

set -e

SERVER="198.23.185.233"
USER="Administrator"
PASSWORD='$&8$%U9F#&&%'
REMOTE_DIR="C:/fpl-api/frontend/dist"

echo "Building frontend..."
cd frontend
npm run build

echo "Deploying frontend to ByteHosty..."
cd ..

# Copy frontend dist to server
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no -r frontend/dist/* "$USER@$SERVER:$REMOTE_DIR/"

echo "Frontend deployed successfully!"
echo "Frontend should be accessible at: http://$SERVER:8080/"
