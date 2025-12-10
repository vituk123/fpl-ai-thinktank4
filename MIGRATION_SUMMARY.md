# Migration Summary: External AI APIs → Supabase Edge Functions

## ✅ Completed Changes

### 1. Created Supabase Edge Function
- **File**: `supabase/functions/summarize-news/index.ts`
- Uses `Supabase.ai.Session` with Ollama/Llamafile
- Handles FPL news summarization with JSON response
- Includes robust error handling and JSON parsing

### 2. Updated AI Summarizer
- **File**: `src/ai_summarizer.py`
- Removed external API dependencies (OpenAI, aimlapi.com, OpenRouter)
- Now uses `supabase.functions.invoke()` to call Edge Function
- Maintains same interface for backward compatibility

### 3. Updated News Processor
- **File**: `src/news_processor.py`
- Modified to accept optional `ai_summarizer` parameter
- Auto-creates `AISummarizer` from `DatabaseManager` if not provided
- No breaking changes to existing functionality

### 4. Updated Daily Processing Script
- **File**: `process_news_daily.py`
- Removed external AI API configuration
- Now uses Supabase Edge Function configuration
- Simplified initialization

### 5. Updated Configuration
- **File**: `config.yml`
- Removed `ai_api` section (external APIs)
- Added `supabase_edge_function` section
- Cleaner, simpler configuration

### 6. Dockerized Llamafile Server
- **Directory**: `docker/llamafile/`
- **Dockerfile**: Containerized Llamafile server
- **docker-compose.yml**: Easy deployment configuration
- **download_model.sh**: Model download script
- **start.sh**: Quick start script

### 7. Documentation & Setup
- **File**: `DOCKER_LLAMAFILE_SETUP.md` - Docker setup guide
- **File**: `OLLAMA_SETUP.md` - Updated for Docker (legacy name)
- **File**: `setup_ollama.sh` - Automated Docker setup script
- **File**: `SUPABASE_EDGE_FUNCTION_MIGRATION.md` - Migration guide
- **File**: `MIGRATION_SUMMARY.md` - This file

## 🚀 Next Steps

### 1. Install Supabase CLI (if not installed)
```bash
# macOS
brew install supabase/tap/supabase

# Or via npm
npm install -g supabase
```

### 2. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 3. Run Setup Script
```bash
./setup_ollama.sh
```

Or manually:
```bash
# Pull model
ollama pull mistral

# Start Ollama (keep running)
ollama serve

# Create .env file
mkdir -p supabase/functions
echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env
```

### 4. Test Locally

First, ensure Llamafile server is running:
```bash
cd docker/llamafile
docker-compose ps  # Should show container running
```

Then test Edge Function:
```bash
# Start Edge Function locally
supabase functions serve summarize-news --env-file supabase/functions/.env

# In another terminal, test it
curl -X POST "http://localhost:54321/functions/v1/summarize-news" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test article",
    "content": "Test content",
    "url": "https://example.com"
  }'
```

### 5. Deploy to Production

#### Deploy Docker Container
- Copy `docker/llamafile/` directory to VPS/cloud instance
- Build and start: `docker-compose up -d`
- Ensure port 11434 is accessible
- Set up firewall rules

#### Set Function Secret
```bash
supabase secrets set AI_INFERENCE_API_HOST=https://your-docker-server.com:11434
```

#### Deploy Edge Function
```bash
supabase functions deploy summarize-news
```

### 6. Test Full Pipeline
```bash
python3 process_news_daily.py
```

## 📋 Removed Dependencies

- `openai` package (if not used elsewhere)
- External AI API keys (aimlapi.com, OpenRouter)
- API rate limiting for external services

## ✨ Benefits

1. **Cost Savings**: No external API costs
2. **Privacy**: Data stays in your infrastructure
3. **No Rate Limits**: Only limited by server resources
4. **Full Control**: Choose your model and configuration
5. **Integrated**: Works seamlessly with Supabase

## 🔧 Configuration

The new configuration in `config.yml`:

```yaml
supabase_edge_function:
  function_name: "summarize-news"
  model: "mistral"  # Ollama model name
  timeout: 60
```

## 📝 Notes

- The Edge Function uses Mistral by default (change in `index.ts`)
- Ensure Ollama is running before testing
- For production, deploy Ollama to a server accessible from Supabase
- The system maintains backward compatibility with existing code

## 🐛 Troubleshooting

See `OLLAMA_SETUP.md` and `SUPABASE_EDGE_FUNCTION_MIGRATION.md` for detailed troubleshooting guides.

