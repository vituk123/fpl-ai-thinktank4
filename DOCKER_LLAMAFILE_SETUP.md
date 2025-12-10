# Docker Llamafile Server Setup

This guide explains how to set up a Dockerized Llamafile server for FPL news summarization, avoiding the need to install Ollama directly on your computer.

## Why Docker?

- **Isolated Environment**: No system-wide installations
- **Easy Deployment**: Deploy anywhere Docker runs
- **Consistent**: Same environment across development and production
- **Portable**: Move between machines easily

## Quick Start

### 1. Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose (usually included with Docker Desktop)
- ~5GB free disk space for model

### 2. Automated Setup

```bash
# Run the setup script from project root
./setup_ollama.sh
```

This will:
- Build the Docker image
- Download the Mistral 7B model
- Start the server
- Configure Edge Function environment

### 3. Manual Setup

#### Step 1: Build Docker Image

```bash
cd docker/llamafile
docker-compose build
```

**Note**: First build takes ~10-15 minutes as it compiles Llamafile from source.

#### Step 2: Download Model

```bash
# Run interactive download script
chmod +x download_model.sh
./download_model.sh
# Select option 1 (Mistral 7B Q5_K_M - recommended)

# Or download manually
mkdir -p models
cd models
wget https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q5_K_M.gguf
cd ..
```

#### Step 3: Configure Model Path

```bash
# Create symlink so container can find the model
ln -s mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model
```

#### Step 4: Start Server

```bash
# Start in background
docker-compose up -d

# Or use the start script
./start.sh
```

#### Step 5: Verify Server

```bash
# Check container status
docker-compose ps

# Test API
curl http://localhost:11434/v1/models

# View logs
docker-compose logs -f
```

## Configuration

### Port Configuration

Default port is `11434` (Ollama-compatible). To change:

Edit `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:8080"
```

### Model Selection

Update the volume mount in `docker-compose.yml`:
```yaml
volumes:
  - ./models/YOUR_MODEL.gguf:/model:ro
```

Or create a symlink:
```bash
ln -s YOUR_MODEL.gguf models/model
```

### Resource Limits

Add to `docker-compose.yml` if needed:
```yaml
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4'
```

## Integration with Supabase

### Local Development

1. Ensure Llamafile server is running:
   ```bash
   cd docker/llamafile
   docker-compose ps
   ```

2. Configure Edge Function:
   ```bash
   # From project root
   mkdir -p supabase/functions
   # macOS/Windows
   echo "AI_INFERENCE_API_HOST=http://host.docker.internal:11434" > supabase/functions/.env
   # Linux
   echo "AI_INFERENCE_API_HOST=http://localhost:11434" > supabase/functions/.env
   ```

3. Test Edge Function:
   ```bash
   supabase functions serve summarize-news --env-file supabase/functions/.env
   ```

### Production Deployment

1. **Deploy Docker Container to Server**

   Option A: VPS (DigitalOcean, AWS EC2, etc.)
   ```bash
   # Copy docker/llamafile directory to server
   scp -r docker/llamafile user@server:/path/to/
   
   # On server
   cd /path/to/llamafile
   docker-compose up -d
   ```

   Option B: Cloud Platform
   - **DigitalOcean**: Use Docker Droplet
   - **AWS EC2**: Launch instance with Docker
   - **Google Cloud Run**: Deploy as containerized service
   - **Azure Container Instances**: Managed container deployment

2. **Configure Firewall**
   ```bash
   # Allow port 11434 from Supabase IPs
   sudo ufw allow 11434/tcp
   ```

3. **Set Supabase Secret**
   ```bash
   supabase secrets set AI_INFERENCE_API_HOST=https://your-server.com:11434
   ```

4. **Deploy Edge Function**
   ```bash
   supabase functions deploy summarize-news
   ```

## Model Recommendations

| Model | Size | Quality | Speed | Use Case |
|-------|------|---------|-------|----------|
| Mistral 7B Q5_K_M | 4.6GB | Excellent | Fast | **Recommended** |
| Mistral 7B Q4_K_M | 3.8GB | Good | Very Fast | Resource-constrained |
| Llama 3 8B Q5_K_M | 5.1GB | Excellent | Moderate | Higher quality needed |

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Check if port is in use
lsof -i :11434

# Restart container
docker-compose restart
```

### Model Not Found

```bash
# Verify model exists
ls -lh models/

# Check volume mount
docker-compose config

# Verify in container
docker-compose exec llamafile ls -la /model
```

### API Not Responding

```bash
# Check container is running
docker-compose ps

# Test health
curl http://localhost:11434/health

# View real-time logs
docker-compose logs -f llamafile
```

### Out of Memory

```bash
# Check memory usage
docker stats fpl-llamafile-server

# Use smaller model (Q4_K_M instead of Q5_K_M)
# Or increase Docker memory limit in Docker Desktop settings
```

## Management Commands

```bash
# Start server
docker-compose up -d

# Stop server
docker-compose down

# View logs
docker-compose logs -f

# Restart server
docker-compose restart

# View resource usage
docker stats fpl-llamafile-server

# Rebuild image
docker-compose build --no-cache
```

## Security Considerations

1. **Firewall**: Only allow port 11434 from trusted IPs (Supabase)
2. **HTTPS**: Use reverse proxy (nginx, Traefik) with SSL certificate
3. **Authentication**: Add API key authentication if exposing publicly
4. **Resource Limits**: Set memory/CPU limits to prevent resource exhaustion

## References

- [Docker Llamafile Guide](https://www.docker.com/blog/a-quick-guide-to-containerizing-llamafile-with-docker-for-ai-applications/)
- [Llamafile GitHub](https://github.com/Mozilla-Ocho/llamafile)
- [Supabase Edge Functions AI](https://supabase.com/docs/guides/functions/ai-models)

