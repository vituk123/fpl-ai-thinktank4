# Migration to Supabase Edge Functions

## Overview

The system has been migrated from external AI APIs (aimlapi.com, OpenRouter) to Supabase Edge Functions using the built-in AI API with a Dockerized Llamafile server.

## What Changed

### Removed
- External AI API dependencies (aimlapi.com, OpenRouter)
- `openai` package dependency (if not used elsewhere)
- External API key configuration

### Added
- Supabase Edge Function: `supabase/functions/summarize-news/index.ts`
- Dockerized Llamafile server: `docker/llamafile/`
- Updated `AISummarizer` to use Edge Function instead of external APIs
- Docker setup scripts and documentation

## Architecture

```
NewsData.io API
      ↓
NewsProcessor
      ↓
AISummarizer (calls Supabase Edge Function)
      ↓
Supabase Edge Function (uses Supabase.ai.Session)
      ↓
Llamafile Docker Server (port 11434)
      ↓
Returns JSON summary
      ↓
Saved to Supabase Database
```

## Setup Instructions

### 1. Install Docker

**macOS:**
```bash
brew install --cask docker
```

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

**Windows:**
Download Docker Desktop from https://www.docker.com/products/docker-desktop

### 2. Quick Setup (Automated)

Run the setup script:
```bash
./setup_ollama.sh
```

This will:
- Check if Docker is installed
- Build Llamafile Docker image
- Download the Mistral model
- Start the Docker container
- Create `.env` file for Edge Functions

### 3. Manual Setup

#### 3.1 Build Docker Image
```bash
cd docker/llamafile
docker-compose build
```

#### 3.2 Download Model
```bash
chmod +x download_model.sh
./download_model.sh
# Select option 1 (Mistral 7B)
ln -s mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model
```

#### 3.3 Start Docker Container
```bash
docker-compose up -d
```

#### 3.4 Configure Edge Function

Create `supabase/functions/.env`:
```bash
# macOS
echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env

# Linux
echo "AI_INFERENCE_API_HOST=http://localhost:11434" > supabase/functions/.env
```

### 4. Test Locally

```bash
supabase functions serve summarize-news --env-file supabase/functions/.env
```

Test the function:
```bash
curl -X POST "http://localhost:54321/functions/v1/summarize-news" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mohamed Salah injury update",
    "content": "Liverpool forward is a doubt for Gameweek 16",
    "url": "https://example.com"
  }'
```

### 5. Deploy to Production

#### 5.1 Deploy Docker Container

Deploy the Llamafile Docker container to a server accessible from Supabase:
- VPS (DigitalOcean, AWS EC2, etc.)
- Ensure Docker is installed
- Copy `docker/llamafile/` directory to server
- Build and start: `docker-compose up -d`
- Ensure port 11434 is accessible
- Set up firewall/security groups

#### 5.2 Set Function Secret

```bash
supabase secrets set AI_INFERENCE_API_HOST=https://your-ollama-server.com:11434
```

#### 5.3 Deploy Edge Function

```bash
supabase functions deploy summarize-news
```

## Configuration

The configuration in `config.yml` has been updated:

```yaml
supabase_edge_function:
  function_name: "summarize-news"
  model: "mistral"  # Ollama model name
  timeout: 60
```

## Benefits

1. **No External API Costs**: Uses self-hosted Ollama (free)
2. **Better Privacy**: Data stays within your Supabase infrastructure
3. **No Rate Limits**: Only limited by your server resources
4. **Full Control**: Choose your model and configuration
5. **Integrated**: Works seamlessly with Supabase ecosystem

## Troubleshooting

### Edge Function Not Found

1. Verify function is deployed:
   ```bash
   supabase functions list
   ```

2. Check function exists:
   ```bash
   ls supabase/functions/summarize-news/
   ```

### Docker Container Connection Errors

1. Verify container is running:
   ```bash
   cd docker/llamafile
   docker-compose ps
   ```

2. Check container logs:
   ```bash
   docker-compose logs -f
   ```

3. Test API directly:
   ```bash
   curl http://localhost:11434/v1/models
   ```

4. Verify model is mounted:
   ```bash
   docker-compose exec llamafile ls -la /model
   ```

### Function Timeout

- Increase timeout in Edge Function code
- Use a faster model (mistral instead of mixtral)
- Optimize prompt length

## Model Selection

Recommended models for FPL news summarization:

- **Mistral** (recommended): Fast, good quality, ~4GB RAM
- **Llama 3**: Better quality, ~8GB RAM  
- **Mixtral**: Best quality, ~26GB RAM

Change model in `supabase/functions/summarize-news/index.ts`:
```typescript
const model = new Supabase.ai.Session('your-model-name')
```

And pull the model:
```bash
ollama pull your-model-name
```

## Next Steps

1. Complete Ollama setup (see `OLLAMA_SETUP.md`)
2. Test Edge Function locally
3. Deploy Ollama server for production
4. Deploy Edge Function to Supabase
5. Run `process_news_daily.py` to test the full pipeline

