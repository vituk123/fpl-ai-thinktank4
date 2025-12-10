# Llamafile Docker Server Setup Guide for Supabase Edge Functions

This guide will help you set up a Dockerized Llamafile server for use with the Supabase Edge Function for FPL news summarization.

## Prerequisites

- Supabase project with Edge Functions enabled
- Supabase CLI installed
- Docker and Docker Compose installed on your system

## Step 1: Install Docker

### macOS
```bash
brew install --cask docker
# Or download from: https://www.docker.com/products/docker-desktop
```

### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Or use package manager
sudo apt-get update
sudo apt-get install docker.io docker-compose
```

### Windows
Download Docker Desktop from: https://www.docker.com/products/docker-desktop

## Step 2: Build Llamafile Docker Image

```bash
cd docker/llamafile
docker-compose build
```

This will build the Llamafile container from source (takes ~10-15 minutes).

## Step 3: Download a Model

Run the download script:

```bash
cd docker/llamafile
chmod +x download_model.sh
./download_model.sh
```

Or manually download a model:

```bash
mkdir -p models
cd models
# Download Mistral 7B (recommended for FPL)
wget https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q5_K_M.gguf
cd ..
```

## Step 4: Configure Model Path

Create a symlink to your model:

```bash
cd docker/llamafile
ln -s mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model
```

## Step 5: Start Llamafile Server

```bash
docker-compose up -d
```

The server will run on `http://localhost:11434` by default.

## Step 4: Test Locally

### 4.1 Set Environment Variable

Create or update `supabase/functions/.env`:

```bash
# macOS/Windows (Docker Desktop)
echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env

# Linux (native Docker)
echo "AI_INFERENCE_API_HOST=http://localhost:11434" > supabase/functions/.env
```

### 4.2 Serve Edge Function Locally

```bash
supabase functions serve summarize-news --env-file supabase/functions/.env
```

### 4.3 Test the Function

In another terminal:

```bash
curl -X POST "http://localhost:54321/functions/v1/summarize-news" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mohamed Salah injury update",
    "content": "Liverpool forward Mohamed Salah is a doubt for Gameweek 16",
    "url": "https://example.com"
  }'
```

Replace `YOUR_ANON_KEY` with your Supabase anon key from `.env` file.

## Step 5: Deploy to Production

### 5.1 Deploy Ollama Server

You need to deploy Ollama to a server accessible from Supabase. Options:

**Option A: Deploy to a VPS/Cloud Instance**
- Deploy Ollama on a VPS (DigitalOcean, AWS EC2, etc.)
- Ensure port 11434 is accessible
- Set up firewall rules

**Option B: Use Supabase Hosted (if available)**
- Sign up for early access: https://forms.gle/...
- Use the hosted endpoint when available

### 5.2 Set Function Secret

Once your Ollama server is deployed, set the secret:

```bash
supabase secrets set AI_INFERENCE_API_HOST=https://your-ollama-server.com:11434
```

### 5.3 Deploy Edge Function

```bash
supabase functions deploy summarize-news
```

## Step 6: Verify Deployment

Test the deployed function:

```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/summarize-news" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test article",
    "content": "Test content",
    "url": "https://example.com"
  }'
```

## Troubleshooting

### Llamafile Connection Issues

1. **Check container is running:**
   ```bash
   cd docker/llamafile
   docker-compose ps
   ```

2. **Check container logs:**
   ```bash
   docker-compose logs -f
   ```

3. **Test API directly:**
   ```bash
   curl http://localhost:11434/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral", "messages": [{"role": "user", "content": "Hello"}]}'
   ```

4. **Verify model is mounted:**
   ```bash
   docker-compose exec llamafile ls -la /model
   ```

### Edge Function Errors

1. **Check function logs:**
   ```bash
   supabase functions logs summarize-news
   ```

2. **Verify environment variable:**
   ```bash
   supabase secrets list
   ```

3. **Test locally first:**
   Always test locally before deploying to production.

## Alternative: Using Llamafile

If you prefer Llamafile over Ollama:

1. Download Llamafile: https://github.com/Mozilla-Ocho/llamafile
2. Run: `./llamafile --model mistral`
3. Set `AI_INFERENCE_API_HOST` to your Llamafile server URL

## Model Recommendations

For FPL news summarization:
- **Mistral** (recommended): Fast, good quality, ~4GB RAM
- **Llama 3**: Better quality, ~8GB RAM
- **Mixtral**: Best quality, ~26GB RAM

Choose based on your server resources and quality requirements.

