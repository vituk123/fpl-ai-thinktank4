#!/bin/bash
# Quick start script for Llamafile Docker server

cd "$(dirname "$0")" || exit 1

echo "Starting Llamafile Docker server..."
docker-compose up -d

echo ""
echo "Waiting for server to start..."
sleep 5

echo ""
echo "Checking server status..."
if curl -s http://localhost:11434/v1/models > /dev/null 2>&1; then
    echo "✓ Server is running on http://localhost:11434"
    echo ""
    echo "View logs: docker-compose logs -f"
    echo "Stop server: docker-compose down"
else
    echo "⚠ Server may still be starting..."
    echo "Check logs: docker-compose logs -f"
fi

