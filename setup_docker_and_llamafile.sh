#!/bin/bash
# Complete setup script for Docker and Llamafile

echo "=========================================="
echo "Docker & Llamafile Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "Please install Docker Desktop:"
    echo "  macOS:   brew install --cask docker"
    echo "  Or download from: https://www.docker.com/products/docker-desktop"
    echo ""
    echo "After installing Docker Desktop:"
    echo "1. Launch Docker Desktop"
    echo "2. Wait for it to start (whale icon in menu bar)"
    echo "3. Run this script again"
    exit 1
fi

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "❌ Docker is not running."
    echo ""
    echo "Please:"
    echo "1. Launch Docker Desktop"
    echo "2. Wait for it to start"
    echo "3. Run this script again"
    exit 1
fi

echo "✓ Docker is installed and running"
echo ""

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    exit 1
fi

echo "✓ Docker Compose is available"
echo ""

# Navigate to llamafile directory
cd "$(dirname "$0")/docker/llamafile" || exit 1

# Build Docker image
echo "Building Llamafile Docker image..."
echo "This will take 10-15 minutes on first build..."
echo ""

if docker-compose build 2>&1 | tee /tmp/llamafile_build.log; then
    echo ""
    echo "✓ Docker image built successfully"
else
    echo ""
    echo "❌ Docker build failed. Check /tmp/llamafile_build.log for details"
    exit 1
fi

# Download model
echo ""
echo "Downloading Mistral 7B model..."
echo "This will download ~4.6GB..."
echo ""

if [ -f "download_model.sh" ]; then
    chmod +x download_model.sh
    # Auto-select option 1 (Mistral 7B)
    echo "1" | ./download_model.sh
else
    echo "Download script not found. Downloading manually..."
    mkdir -p models
    cd models
    echo "Downloading Mistral 7B Q5_K_M..."
    if command -v wget &> /dev/null; then
        wget https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q5_K_M.gguf
    elif command -v curl &> /dev/null; then
        curl -L -o mistral-7b-instruct-v0.1.Q5_K_M.gguf https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q5_K_M.gguf
    else
        echo "❌ Neither wget nor curl is installed"
        exit 1
    fi
    cd ..
fi

# Create model symlink
echo ""
echo "Setting up model symlink..."
if [ -f "models/mistral-7b-instruct-v0.1.Q5_K_M.gguf" ]; then
    cd models
    ln -sf mistral-7b-instruct-v0.1.Q5_K_M.gguf model
    cd ..
    echo "✓ Model symlink created"
else
    echo "⚠ Model file not found. Please download it manually."
    exit 1
fi

# Start Docker container
echo ""
echo "Starting Llamafile server..."
docker-compose up -d

# Wait for server to be ready
echo ""
echo "Waiting for server to start (this may take a minute)..."
sleep 10

# Check if server is running
echo ""
echo "Verifying server..."
for i in {1..6}; do
    if curl -s http://localhost:11434/v1/models > /dev/null 2>&1; then
        echo "✓ Server is running on http://localhost:11434"
        break
    else
        echo "Waiting for server... ($i/6)"
        sleep 5
    fi
done

# Create .env file for Edge Function
echo ""
echo "Configuring Edge Function..."
cd ../../ || exit 1
mkdir -p supabase/functions

# Detect OS for correct host
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS (Docker Desktop)
    echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux (native Docker)
    echo "AI_INFERENCE_API_HOST=http://localhost:11434" > supabase/functions/.env
else
    # Windows (Docker Desktop)
    echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env
fi

echo "✓ Edge Function configured"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Server is running at: http://localhost:11434"
echo ""
echo "Next steps:"
echo "1. Test the server: curl http://localhost:11434/v1/models"
echo "2. Test Edge Function: supabase functions serve summarize-news --env-file supabase/functions/.env"
echo ""
echo "To stop the server: cd docker/llamafile && docker-compose down"
echo "To view logs: cd docker/llamafile && docker-compose logs -f"
