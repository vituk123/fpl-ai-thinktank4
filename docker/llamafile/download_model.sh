#!/bin/bash
# Script to download Llamafile models
# Models are downloaded in GGUF format

MODEL_DIR="./models"
mkdir -p "$MODEL_DIR"

echo "=========================================="
echo "Llamafile Model Downloader"
echo "=========================================="
echo ""

# Model options
echo "Available models:"
echo "1. Mistral 7B (Q5_K_M) - ~4.6GB - Recommended for FPL"
echo "2. Llama 3 8B (Q5_K_M) - ~5.1GB"
echo "3. Mistral 7B (Q4_K_M) - ~3.8GB - Smaller, faster"
echo "4. Custom URL"
echo ""

read -p "Select model (1-4): " choice

case $choice in
    1)
        MODEL_URL="https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q5_K_M.gguf"
        MODEL_NAME="mistral-7b-instruct-v0.1.Q5_K_M.gguf"
        ;;
    2)
        MODEL_URL="https://huggingface.co/meta-llama/Llama-3-8B-Instruct/resolve/main/Llama-3-8B-Instruct-Q5_K_M.gguf"
        MODEL_NAME="Llama-3-8B-Instruct-Q5_K_M.gguf"
        ;;
    3)
        MODEL_URL="https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf"
        MODEL_NAME="mistral-7b-instruct-v0.1.Q4_K_M.gguf"
        ;;
    4)
        read -p "Enter model URL: " MODEL_URL
        read -p "Enter model filename: " MODEL_NAME
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

MODEL_PATH="$MODEL_DIR/$MODEL_NAME"

echo ""
echo "Downloading model to: $MODEL_PATH"
echo "This may take a while depending on your connection..."
echo ""

# Download model
if command -v wget &> /dev/null; then
    wget -O "$MODEL_PATH" "$MODEL_URL"
elif command -v curl &> /dev/null; then
    curl -L -o "$MODEL_PATH" "$MODEL_URL"
else
    echo "Error: Neither wget nor curl is installed"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Model downloaded successfully!"
    echo ""
    echo "To use this model, update docker-compose.yml:"
    echo "  volumes:"
    echo "    - ./models/$MODEL_NAME:/model:ro"
    echo ""
    echo "Or create a symlink:"
    echo "  ln -s $MODEL_NAME models/model"
else
    echo ""
    echo "✗ Download failed"
    exit 1
fi

