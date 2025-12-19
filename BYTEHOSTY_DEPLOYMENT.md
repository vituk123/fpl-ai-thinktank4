# ByteHosty VPS Deployment Guide

## Overview
This guide documents the migration from GCE VM to ByteHosty VPS as the primary backend server.

## Server Details
- **IP Address**: 198.23.185.233
- **User**: Administrator
- **Port**: 8080 (default, configurable)

## Changes Made

### 1. Frontend Updates (`frontend/src/services/api.ts`)
- ✅ Removed all GCE VM references (`http://35.192.15.52`)
- ✅ Updated `getCurrentGameweek()` to use ByteHosty as primary
- ✅ Updated `callDashboardEndpoint()` to use ByteHosty as primary with Render fallback
- ✅ Updated `getMLReport()` to use ByteHosty for full ML reports

### 2. Supabase Edge Functions
All Edge Functions updated to use `BYTEHOSTY_API_URL` instead of `GCE_VM_API_URL`:
- ✅ `supabase/functions/ml-report/index.ts`
- ✅ `supabase/functions/ml-recommendations/index.ts`
- ✅ `supabase/functions/ml-players/index.ts`
- ✅ `supabase/functions/optimize-team/index.ts`

**Priority Order**: ByteHosty → GCP Cloud Run → Render

### 3. Deployment Script
Created `deploy_to_bytehosty.sh` with:
- Automatic server capability detection (Docker vs Python)
- SSH password authentication support
- Environment variable setup
- Health check verification

## Deployment Steps

### Step 1: Install sshpass (if needed)
```bash
# macOS
brew install hudochenkov/sshpass/sshpass

# Linux
sudo apt-get install sshpass
# or
sudo yum install sshpass
```

### Step 2: Run Deployment Script
```bash
./deploy_to_bytehosty.sh
```

The script will:
1. Test SSH connection
2. Detect server capabilities (OS, Docker, Python)
3. Copy files to server
4. Prompt for environment variables (or use defaults from config.yml)
5. Deploy using Docker (if available) or direct Python
6. Test health endpoint

### Step 3: Configure Supabase Secrets
After successful deployment, set the ByteHosty API URL in Supabase:

```bash
supabase secrets set BYTEHOSTY_API_URL=http://198.23.185.233:8080
```

### Step 4: Verify Deployment
```bash
# Test health endpoint
curl http://198.23.185.233:8080/api/v1/health

# Test gameweek endpoint
curl http://198.23.185.233:8080/api/v1/gameweek/current
```

## Environment Variables

Required environment variables on ByteHosty server (in `.env` file):

```bash
SUPABASE_URL=https://sdezcbesdubplacfxibc.supabase.co
SUPABASE_KEY=your-supabase-anon-key
DB_CONNECTION_STRING=postgresql://user:password@host:port/database
API_FOOTBALL_KEY=08b18b2d60e1cfea7769c7276226d2d1
NEWS_API_KEY=pub_a13e0ce062804c5891decaa7ac8a27b9
PYTHON_VERSION=3.11
PORT=8080
```

## Service Management

### Docker Deployment
```bash
# SSH to server
ssh Administrator@198.23.185.233

# Navigate to app directory
cd /opt/fpl-api

# View logs
docker compose logs -f

# Restart service
docker compose restart

# Stop service
docker compose down

# Start service
docker compose up -d
```

### Python Deployment (systemd)
```bash
# SSH to server
ssh Administrator@198.23.185.233

# View logs
sudo journalctl -u fpl-api.service -f

# Restart service
sudo systemctl restart fpl-api.service

# Check status
sudo systemctl status fpl-api.service

# Stop service
sudo systemctl stop fpl-api.service

# Start service
sudo systemctl start fpl-api.service
```

## Troubleshooting

### SSH Connection Issues
- Verify server IP: `198.23.185.233`
- Check SSH service is running on server
- Verify firewall allows SSH (port 22)
- Test with: `ssh Administrator@198.23.185.233`

### Service Not Starting
- Check logs (see Service Management above)
- Verify environment variables are set correctly
- Check port 8080 is not in use: `netstat -tuln | grep 8080`
- Verify Python/Docker is installed

### API Not Responding
- Check service is running
- Verify firewall allows port 8080
- Test locally on server: `curl http://localhost:8080/api/v1/health`
- Check CORS configuration in `config.yml`

## Migration Checklist

- [x] Frontend updated to remove GCE VM references
- [x] Frontend updated to use ByteHosty as primary
- [x] Supabase Edge Functions updated
- [x] Deployment script created
- [ ] Backend deployed to ByteHosty
- [ ] Environment variables configured
- [ ] Health endpoint verified
- [ ] Supabase secret `BYTEHOSTY_API_URL` set
- [ ] Frontend tested with new backend
- [ ] All API endpoints verified
- [ ] Performance monitoring in place

## Notes

- The deployment script uses password authentication. For production, consider setting up SSH keys.
- Port 8080 is the default. Change in `deploy_to_bytehosty.sh` if needed.
- ML engine is resource-intensive. Monitor server CPU/memory usage.
- Consider setting up SSL/TLS (HTTPS) for production use.
- Keep Render as fallback for redundancy.

