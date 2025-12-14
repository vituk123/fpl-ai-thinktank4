# GCE VM Deployment Guide

This guide covers deploying the FPL API backend to a Google Compute Engine (GCE) VM with 32GB RAM and 8 CPUs for optimal ML workload performance.

## Overview

The GCE VM deployment provides:
- **32GB RAM** and **8 vCPUs** (e2-standard-8 machine type)
- No quota restrictions (unlike Cloud Run)
- Persistent storage for models and cache
- Full control over the environment
- Cost-effective (can be stopped when not in use)

## Prerequisites

1. Google Cloud SDK (`gcloud`) installed and configured
2. GCP project with billing enabled
3. Compute Engine API enabled
4. Secrets configured in GCP Secret Manager (see `setup_gcp_secrets_auto.sh`)

## Quick Start

### 1. Create and Configure VM

```bash
./setup_gce_vm.sh
```

This script:
- Enables Compute Engine API
- Creates firewall rules for HTTP/HTTPS
- Creates the VM instance with startup script
- Configures auto-start on boot

### 2. Deploy Application

Wait 2-3 minutes for VM to finish initial setup, then:

```bash
./deploy_to_vm.sh
```

This script:
- Copies code to VM
- Pulls latest from GitHub
- Loads secrets from GCP Secret Manager
- Builds and starts Docker container

### 3. Get VM IP and Update Supabase

```bash
# Get VM external IP
gcloud compute instances describe fpl-api-vm --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Update Supabase secret
supabase secrets set GCE_VM_API_URL=http://[VM_IP]
```

### 4. Verify Deployment

```bash
# Check VM status
./vm_status.sh

# View logs
./vm_logs.sh

# Test health endpoint
curl http://[VM_IP]/api/v1/health
```

## VM Management

### Start VM

```bash
./start_vm.sh
```

### Stop VM (to save costs)

```bash
./stop_vm.sh
```

When stopped, you only pay for disk storage (~$5/month for 50GB).

### Check Status

```bash
./vm_status.sh
```

### View Logs

```bash
# System logs
./vm_logs.sh

# Docker container logs
./vm_logs.sh docker
```

## Architecture

```
Frontend (React)
    ↓
Supabase Edge Functions
    ├─→ GCE VM (Primary) - FastAPI Backend (32GB RAM, 8 CPUs)
    ├─→ GCP Cloud Run (Fallback) - FastAPI Backend
    └─→ Render (Tertiary Fallback) - FastAPI Backend
              ↓
         Supabase Database
```

## Configuration

### VM Specifications

- **Machine Type**: `e2-standard-8`
- **vCPUs**: 8
- **RAM**: 32GB
- **Zone**: `us-central1-a`
- **Boot Disk**: 50GB SSD
- **OS**: Ubuntu 22.04 LTS

### Environment Variables

Secrets are loaded from GCP Secret Manager:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `DB_CONNECTION_STRING`
- `API_FOOTBALL_KEY`
- `NEWS_API_KEY`

### Docker Resources

The Docker container is configured with:
- **CPU Limit**: 7 CPUs (1 reserved for system)
- **Memory Limit**: 30GB (2GB reserved for system)
- **CPU Reservation**: 4 CPUs
- **Memory Reservation**: 16GB

## Deployment Workflow

1. **VM Setup** (one-time):
   - Run `setup_gce_vm.sh` to create VM
   - VM automatically runs startup script on first boot
   - Startup script installs Docker, clones repo, sets up systemd service

2. **Code Deployment** (ongoing):
   - Run `deploy_to_vm.sh` to deploy latest code
   - Script pulls from GitHub, rebuilds Docker image, restarts service
   - Service auto-restarts on failure via systemd

3. **Updates**:
   - Code changes: Run `deploy_to_vm.sh`
   - Secret changes: Update in GCP Secret Manager, then run `deploy_to_vm.sh` to reload
   - VM configuration: Edit `setup_gce_vm.sh` and recreate VM

## Supabase Integration

All Supabase Edge Functions have been updated to support GCE VM fallback:

1. **ml-report** - ML report generation
2. **ml-recommendations** - Transfer recommendations
3. **ml-players** - ML-enhanced player data
4. **optimize-team** - Team optimization

Fallback priority:
1. GCE VM (primary)
2. GCP Cloud Run (fallback)
3. Render (tertiary fallback)

## Cost Management

### Estimated Monthly Costs

- **VM Running 24/7**: ~$200/month
- **VM Stopped**: ~$5/month (disk storage only)
- **Data Transfer**: ~$0.01/GB

### Cost Optimization Tips

1. **Stop VM when not in use**:
   ```bash
   ./stop_vm.sh
   ```

2. **Use preemptible instances** (80% cost savings):
   - Edit `setup_gce_vm.sh` and add `--preemptible` flag
   - Note: VM can be terminated with 30s notice

3. **Schedule auto-shutdown**:
   - Use Cloud Scheduler to stop VM during off-hours
   - Use Cloud Functions to start VM on-demand

## Troubleshooting

### VM Won't Start

```bash
# Check VM status
gcloud compute instances describe fpl-api-vm --zone=us-central1-a

# View startup logs
gcloud compute instances get-serial-port-output fpl-api-vm --zone=us-central1-a --port=1
```

### Service Not Responding

```bash
# SSH into VM
gcloud compute ssh fpl-api-vm --zone=us-central1-a

# Check Docker containers
docker ps
docker logs fpl-api-backend

# Check systemd service
sudo systemctl status fpl-api
sudo journalctl -u fpl-api -n 50
```

### Secrets Not Loading

```bash
# Verify secrets exist
gcloud secrets list

# Test secret access
gcloud secrets versions access latest --secret=supabase-url

# Check VM service account permissions
gcloud projects get-iam-policy instant-vent-481016-c0
```

### Deployment Fails

```bash
# Check deployment script logs
./deploy_to_vm.sh 2>&1 | tee deploy.log

# Manually SSH and debug
gcloud compute ssh fpl-api-vm --zone=us-central1-a
cd /opt/fpl-api
docker compose logs
```

## Security

- **Firewall Rules**: Only HTTP (80) and HTTPS (443) ports are open
- **SSH Access**: Only via `gcloud compute ssh` (no password auth)
- **Secrets**: Stored in GCP Secret Manager, not in code
- **Service Account**: Minimal permissions (Secret Manager access only)

## Monitoring

### Health Checks

The service exposes a health endpoint:
```
GET http://[VM_IP]/api/v1/health
```

### Logs

- **System Logs**: `gcloud compute instances get-serial-port-output`
- **Docker Logs**: `docker compose logs` (on VM)
- **Application Logs**: Check FastAPI logs in Docker container

### Metrics

Monitor VM usage in GCP Console:
- CPU utilization
- Memory usage
- Network traffic
- Disk I/O

## Next Steps

1. Set up monitoring alerts for high CPU/memory usage
2. Configure auto-scaling (if needed)
3. Set up SSL certificate for HTTPS
4. Configure load balancer for high availability
5. Set up automated backups

## Support

For issues or questions:
1. Check logs: `./vm_logs.sh`
2. Check VM status: `./vm_status.sh`
3. Review this documentation
4. Check GCP Console for VM metrics

