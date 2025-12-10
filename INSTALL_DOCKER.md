# Docker Installation Guide

Docker is required to run the Llamafile server. Follow these steps to install it.

## macOS Installation

### Option 1: Homebrew (Recommended)
```bash
brew install --cask docker
```

### Option 2: Direct Download
1. Visit: https://www.docker.com/products/docker-desktop
2. Download Docker Desktop for Mac
3. Open the `.dmg` file and drag Docker to Applications
4. Launch Docker Desktop from Applications
5. Wait for Docker to start (whale icon in menu bar)

### Verify Installation
```bash
docker --version
docker-compose --version
```

## After Installation

1. **Start Docker Desktop** (if not already running)
   - Look for the Docker whale icon in your menu bar
   - It should be green when running

2. **Verify Docker is running**
   ```bash
   docker ps
   ```

3. **Continue with setup**
   ```bash
   cd docker/llamafile
   docker-compose build
   ```

## Troubleshooting

### Docker command not found
- Make sure Docker Desktop is running
- Restart your terminal
- Check if Docker is in PATH: `echo $PATH`

### Permission denied
- Docker Desktop should handle permissions automatically
- If issues persist, add your user to docker group (Linux) or restart Docker Desktop (macOS)

### Docker Desktop won't start
- Check system requirements: https://docs.docker.com/desktop/install/mac-install/
- Ensure virtualization is enabled in System Settings
- Try restarting your computer

