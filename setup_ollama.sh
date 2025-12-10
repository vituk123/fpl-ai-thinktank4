#!/bin/bash
# Quick setup script for Llamafile Docker Server with Supabase Edge Functions

echo "=========================================="
echo "Llamafile Docker Server Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed."
    echo ""
    echo "Installation options:"
    echo "  macOS:   brew install --cask docker"
    echo "  Linux:   curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    echo "  Windows: Download from https://www.docker.com/products/docker-desktop"
    echo ""
    read -p "Press Enter after installing Docker, or Ctrl+C to cancel..."
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Docker Compose is not installed."
    echo "Please install Docker Compose and try again."
    exit 1
fi

# Navigate to llamafile directory
cd "$(dirname "$0")/docker/llamafile" || exit 1

# Build Docker image
echo ""
echo "Building Llamafile Docker image (this may take 10-15 minutes)..."
if docker-compose build 2>&1 | tee /tmp/llamafile_build.log; then
    echo "✓ Docker image built successfully"
else
    echo "✗ Docker build failed. Check /tmp/llamafile_build.log for details"
    exit 1
fi

# Download model
echo ""
echo "Downloading Mistral 7B model..."
if [ -f "download_model.sh" ]; then
    chmod +x download_model.sh
    echo "1" | ./download_model.sh  # Select Mistral 7B option
else
    echo "Download script not found. Please download model manually."
    echo "See docker/llamafile/README.md for instructions"
fi

# Create model symlink
echo ""
echo "Setting up model symlink..."
if [ -f "models/mistral-7b-instruct-v0.1.Q5_K_M.gguf" ]; then
    ln -sf mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model
    echo "✓ Model symlink created"
else
    echo "⚠ Model not found. Please download it first."
fi

# Start Docker container
echo ""
echo "Starting Llamafile server..."
docker-compose up -d

# Wait for server to be ready
echo ""
echo "Waiting for server to start..."
sleep 5

# Check if server is running
if curl -s http://localhost:11434/v1/models > /dev/null 2>&1; then
    echo "✓ Server is running"
else
    echo "⚠ Server may still be starting. Check logs with: docker-compose logs -f"
fi

# Create .env file for Edge Functions
echo ""
echo "Creating supabase/functions/.env file..."
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

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Verify server: curl http://localhost:11434/v1/models"
echo "2. Test locally: supabase functions serve summarize-news --env-file supabase/functions/.env"
echo "3. Deploy: supabase functions deploy summarize-news"
echo ""
echo "See docker/llamafile/README.md for detailed instructions."

