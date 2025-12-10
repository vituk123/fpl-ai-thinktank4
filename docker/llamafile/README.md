# Llamafile Docker Server for FPL News Summarization

This directory contains a Dockerized Llamafile server that provides LLM inference for the Supabase Edge Function.

## Quick Start

### 1. Build the Docker Image

```bash
cd docker/llamafile
docker-compose build
```

### 2. Download a Model

```bash
chmod +x download_model.sh
./download_model.sh
```

Or manually download a model:
```bash
mkdir -p models
cd models
# Download Mistral 7B (recommended)
wget https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/resolve/main/mistral-7b-instruct-v0.1.Q5_K_M.gguf
cd ..
```

### 3. Configure Model Path

Create a symlink or update `docker-compose.yml` to point to your model:

```bash
# Option 1: Create symlink
ln -s mistral-7b-instruct-v0.1.Q5_K_M.gguf models/model

# Option 2: Update docker-compose.yml volumes section
```

### 4. Start the Server

```bash
docker-compose up -d
```

### 5. Verify Server is Running

```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs -f

# Test the API
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Configuration

### Port Mapping

The server runs on port `11434` (Ollama-compatible) by default. To change:

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

### Environment Variables

- `LLAMA_HOST`: Server host (default: 0.0.0.0)
- `LLAMA_PORT`: Server port (default: 8080)

## Model Recommendations

For FPL news summarization:

1. **Mistral 7B Q5_K_M** (Recommended)
   - Size: ~4.6GB
   - Quality: Excellent
   - Speed: Fast
   - Download: `./download_model.sh` → Option 1

2. **Mistral 7B Q4_K_M**
   - Size: ~3.8GB
   - Quality: Good
   - Speed: Very Fast
   - Download: `./download_model.sh` → Option 3

3. **Llama 3 8B Q5_K_M**
   - Size: ~5.1GB
   - Quality: Excellent
   - Speed: Moderate
   - Download: `./download_model.sh` → Option 2

## Integration with Supabase Edge Function

Once the server is running, update your Supabase Edge Function configuration:

### Local Development

In `supabase/functions/.env`:
```
AI_INFERENCE_API_HOST=http://host.docker.internal:11434
```

### Production Deployment

1. Deploy this Docker container to a server (VPS, cloud instance, etc.)
2. Ensure port 11434 is accessible
3. Set Supabase secret:
   ```bash
   supabase secrets set AI_INFERENCE_API_HOST=https://your-server.com:11434
   ```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Verify model exists
ls -lh models/

# Check if port is in use
lsof -i :11434
```

### Model not found

```bash
# Verify model path in container
docker-compose exec llamafile ls -la /model

# Check volume mount
docker-compose config
```

### API not responding

```bash
# Test health endpoint
curl http://localhost:11434/health

# Check container is running
docker-compose ps

# View real-time logs
docker-compose logs -f llamafile
```

## Production Deployment

### Option 1: VPS Deployment

1. Copy this directory to your VPS
2. Install Docker and Docker Compose
3. Build and start:
   ```bash
   docker-compose build
   docker-compose up -d
   ```
4. Set up firewall (allow port 11434)
5. Configure reverse proxy (optional, for HTTPS)

### Option 2: Cloud Platform

Deploy to:
- **DigitalOcean**: Use Docker Droplet
- **AWS EC2**: Use EC2 with Docker
- **Google Cloud Run**: Containerized service
- **Azure Container Instances**: Managed containers

### Security Considerations

1. **Firewall**: Only allow port 11434 from Supabase IPs
2. **HTTPS**: Use reverse proxy (nginx, Traefik) with SSL
3. **Authentication**: Add API key if needed
4. **Resource Limits**: Set memory/CPU limits in docker-compose.yml

## Monitoring

```bash
# View resource usage
docker stats fpl-llamafile-server

# View logs
docker-compose logs -f --tail=100

# Restart service
docker-compose restart
```

## References

- [Docker Llamafile Guide](https://www.docker.com/blog/a-quick-guide-to-containerizing-llamafile-with-docker-for-ai-applications/)
- [Llamafile GitHub](https://github.com/Mozilla-Ocho/llamafile)
- [Supabase Edge Functions AI](https://supabase.com/docs/guides/functions/ai-models)

