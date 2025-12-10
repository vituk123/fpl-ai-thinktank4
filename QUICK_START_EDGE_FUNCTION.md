# Quick Start: Supabase Edge Function Setup

## Prerequisites Check

1. **Supabase CLI**: `supabase --version`
   - Install: `brew install supabase/tap/supabase` (macOS) or `npm install -g supabase`

2. **Docker**: `docker --version`
   - Install: `brew install --cask docker` (macOS) or see https://www.docker.com

3. **Docker Compose**: `docker-compose --version` or `docker compose version`
   - Usually included with Docker Desktop

## Quick Setup (15-20 minutes)

### Step 1: Build Docker Image & Download Model
```bash
# Navigate to llamafile directory
cd docker/llamafile

# Build Docker image (takes ~10-15 minutes)
docker-compose build

# Download model
chmod +x download_model.sh
./download_model.sh
# Select option 1 (Mistral 7B Q5_K_M)

# Create model symlink
ln -s mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model
```

### Step 2: Start Llamafile Server
```bash
# Start in background
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 3: Configure Edge Function
```bash
# Create .env file (from project root)
mkdir -p supabase/functions
# macOS/Windows (Docker Desktop)
echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env
# Linux (native Docker)
echo "AI_INFERENCE_API_HOST=http://localhost:11434" > supabase/functions/.env
```

### Step 4: Test Locally
```bash
# In project root
supabase functions serve summarize-news --env-file supabase/functions/.env
```

### Step 5: Test the Function
```bash
# Get your anon key from .env file
ANON_KEY=$(grep SUPABASE_KEY .env | cut -d '=' -f2)

curl -X POST "http://localhost:54321/functions/v1/summarize-news" \
  -H "Authorization: Bearer $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mohamed Salah injury update",
    "content": "Liverpool forward is a doubt for Gameweek 16",
    "url": "https://example.com"
  }'
```

## Deploy to Production

### 1. Deploy Ollama Server
- Deploy to VPS (DigitalOcean, AWS EC2, etc.)
- Ensure port 11434 is accessible
- Start: `ollama serve`

### 2. Set Function Secret
```bash
supabase secrets set AI_INFERENCE_API_HOST=https://your-ollama-server.com:11434
```

### 3. Deploy Function
```bash
supabase functions deploy summarize-news
```

## Test Full Pipeline

```bash
python3 process_news_daily.py
```

## Troubleshooting

**Llamafile not responding?**
```bash
# Check container status
cd docker/llamafile
docker-compose ps

# Check logs
docker-compose logs -f

# Test API
curl http://localhost:11434/v1/models
```

**Function not found?**
```bash
supabase functions list
```

**Connection errors?**
- Check Ollama is running: `ollama list`
- Verify .env file exists: `cat supabase/functions/.env`
- Check logs: `supabase functions logs summarize-news`

## Next Steps

- See `OLLAMA_SETUP.md` for detailed setup
- See `SUPABASE_EDGE_FUNCTION_MIGRATION.md` for full migration guide

