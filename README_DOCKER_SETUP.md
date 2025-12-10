# 🐳 Docker Llamafile Server - Quick Reference

## ⚡ Quick Start (Once Docker is Installed)

```bash
# Run the automated setup script
./setup_docker_and_llamafile.sh
```

This single command will:
- Build the Docker image
- Download the model
- Start the server
- Configure everything

## 📋 What Was Created

### Docker Files
- `docker/llamafile/Dockerfile` - Container definition
- `docker/llamafile/docker-compose.yml` - Orchestration
- `docker/llamafile/download_model.sh` - Model downloader
- `docker/llamafile/start.sh` - Quick start script

### Setup Scripts
- `setup_docker_and_llamafile.sh` - Complete automated setup
- `setup_ollama.sh` - Updated for Docker (legacy name)

### Documentation
- `DOCKER_LLAMAFILE_SETUP.md` - Detailed Docker guide
- `INSTALL_DOCKER.md` - Docker installation guide
- `SETUP_INSTRUCTIONS.md` - Step-by-step instructions

## 🎯 Current Status

**Docker Installation**: In progress via Homebrew

**Next Steps**:
1. Wait for Docker Desktop installation to complete
2. Launch Docker Desktop (Applications → Docker)
3. Run: `./setup_docker_and_llamafile.sh`

## ✅ Verification Commands

```bash
# Check Docker
docker --version
docker ps

# Check server
curl http://localhost:11434/v1/models

# Check container
cd docker/llamafile
docker-compose ps
```

## 🛠️ Management Commands

```bash
# Start server
cd docker/llamafile && docker-compose up -d

# Stop server
cd docker/llamafile && docker-compose down

# View logs
cd docker/llamafile && docker-compose logs -f

# Restart server
cd docker/llamafile && docker-compose restart
```

## 📚 Full Documentation

- **Docker Setup**: `DOCKER_LLAMAFILE_SETUP.md`
- **Installation**: `INSTALL_DOCKER.md`
- **Step-by-step**: `SETUP_INSTRUCTIONS.md`
- **Migration Guide**: `SUPABASE_EDGE_FUNCTION_MIGRATION.md`

