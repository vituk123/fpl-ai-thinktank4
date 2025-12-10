# Complete Setup Instructions

## Current Status

Docker Desktop is being installed. Once installation completes, follow these steps:

## Step 1: Verify Docker Installation

After Docker Desktop installation completes:

```bash
# Check Docker is installed
docker --version

# Check Docker Compose is available
docker-compose --version

# Verify Docker is running (start Docker Desktop if needed)
docker ps
```

**Important**: Make sure Docker Desktop is running (look for the whale icon in your menu bar).

## Step 2: Run Complete Setup

Once Docker is running, execute:

```bash
./setup_docker_and_llamafile.sh
```

This script will:
1. ✅ Verify Docker is installed and running
2. 🔨 Build the Llamafile Docker image (~10-15 minutes)
3. 📥 Download Mistral 7B model (~4.6GB)
4. 🔗 Create model symlink
5. 🚀 Start the Llamafile server
6. ⚙️ Configure Edge Function

## Step 3: Verify Server is Running

```bash
# Test the API
curl http://localhost:11434/v1/models

# Check container status
cd docker/llamafile
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 4: Test Edge Function

```bash
# From project root
supabase functions serve summarize-news --env-file supabase/functions/.env
```

## Manual Setup (Alternative)

If you prefer to do it step by step:

```bash
# 1. Build Docker image
cd docker/llamafile
docker-compose build

# 2. Download model
chmod +x download_model.sh
./download_model.sh
# Select option 1 (Mistral 7B Q5_K_M)

# 3. Create model symlink
ln -s mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model

# 4. Start server
docker-compose up -d

# 5. Configure Edge Function (from project root)
mkdir -p supabase/functions
echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env
```

## Troubleshooting

### Docker Desktop Not Starting
- Check system requirements: https://docs.docker.com/desktop/install/mac-install/
- Restart your computer
- Ensure virtualization is enabled

### Build Fails
- Ensure Docker Desktop is running
- Check available disk space (need ~10GB free)
- View build logs: `cat /tmp/llamafile_build.log`

### Model Download Fails
- Check internet connection
- Try downloading manually from HuggingFace
- Verify disk space (model is ~4.6GB)

### Server Won't Start
- Check logs: `docker-compose logs -f`
- Verify model file exists: `ls -lh models/`
- Check port 11434 is not in use: `lsof -i :11434`

## Next Steps After Setup

1. ✅ Server running on http://localhost:11434
2. ✅ Edge Function configured
3. 🧪 Test with: `python3 process_news_daily.py`
4. 🚀 Deploy to production when ready

