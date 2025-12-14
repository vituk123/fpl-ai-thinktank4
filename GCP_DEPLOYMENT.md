# Google Cloud Platform Deployment Guide

This guide walks you through deploying the FPL Backend API to Google Cloud Run with automatic fallback to Render.

## Prerequisites

- Google Cloud account with billing enabled (free trial: $300 credits)
- macOS, Linux, or Windows with shell access
- Homebrew (macOS) or appropriate package manager

## Step 1: Install Google Cloud SDK

### macOS
```bash
brew install --cask google-cloud-sdk
```

### Linux
```bash
# Download and install
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Windows
Download from: https://cloud.google.com/sdk/docs/install

## Step 2: Initialize Google Cloud

Run the setup script:
```bash
./setup_gcp.sh
```

This script will:
- Check if gcloud CLI is installed
- Prompt you to log in to Google Cloud
- Create the project `fpl-optimizer` (if it doesn't exist)
- Enable required APIs:
  - Cloud Run
  - Cloud Build
  - Container Registry
  - Secret Manager
  - Artifact Registry

**Manual alternative:**
```bash
# Login to Google Cloud
gcloud init

# Create project
gcloud projects create fpl-optimizer --name="FPL Optimizer Backend"

# Set as default project
gcloud config set project fpl-optimizer

# Set default region
gcloud config set compute/region asia-southeast1

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

## Step 3: Set Up Secrets

Run the secrets setup script:
```bash
./setup_gcp_secrets.sh
```

This will prompt you to enter:
- **Supabase URL**: Your Supabase project URL (e.g., `https://xxxxx.supabase.co`)
- **Supabase Key**: Your Supabase anon/service role key
- **Database Connection String**: PostgreSQL connection URI
- **API Football Key**: Your API-Football API key
- **News API Key**: Your News API key

**Manual alternative:**
```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secrets (input will be hidden)
echo -n "your-secret-value" | gcloud secrets create secret-name --data-file=-

# Or update existing secret
echo -n "your-secret-value" | gcloud secrets versions add secret-name --data-file=-
```

**Required secrets:**
- `supabase-url`
- `supabase-key`
- `db-connection`
- `api-football-key`
- `news-api-key`

## Step 4: Deploy to Cloud Run

Run the deployment script:
```bash
./deploy_gcp.sh
```

This script will:
1. Build the Docker image using Cloud Build
2. Push the image to Google Container Registry
3. Deploy to Cloud Run with:
   - **Memory**: 4Gi (for ML workloads)
   - **CPU**: 2 cores
   - **Timeout**: 900s (15 minutes)
   - **Max instances**: 10
   - **Min instances**: 0 (pay per request)
   - Secrets mapped as environment variables

**Manual alternative:**
```bash
# Build and push image
gcloud builds submit --tag gcr.io/fpl-optimizer/fpl-api-backend

# Deploy to Cloud Run
gcloud run deploy fpl-api-backend \
  --image gcr.io/fpl-optimizer/fpl-api-backend \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 10 \
  --min-instances 0 \
  --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest,DB_CONNECTION_STRING=db-connection:latest,API_FOOTBALL_KEY=api-football-key:latest,NEWS_API_KEY=news-api-key:latest"
```

## Step 5: Get Service URL

After deployment, get your service URL:
```bash
gcloud run services describe fpl-api-backend \
  --region asia-southeast1 \
  --format 'value(status.url)'
```

Example output:
```
https://fpl-api-backend-xxxxx-xx.a.run.app
```

## Step 6: Configure Supabase Edge Functions

Update your Supabase secrets to include the GCP API URL:

```bash
# Using Supabase CLI
supabase secrets set GCP_API_URL=https://fpl-api-backend-xxxxx-xx.a.run.app

# Or via Supabase Dashboard:
# Settings → Edge Functions → Secrets → Add GCP_API_URL
```

**Important**: Keep `RENDER_API_URL` set as well for fallback support.

## Step 7: Test Deployment

### Test GCP endpoint directly:
```bash
curl https://fpl-api-backend-xxxxx-xx.a.run.app/api/v1/health
```

### Test via Supabase Edge Function:
The edge functions will automatically try GCP first, then fallback to Render if GCP fails.

## Architecture

```
Frontend (React)
    ↓
Supabase Edge Functions
    ├─→ Try GCP Cloud Run (Primary)
    └─→ Fallback to Render (if GCP fails)
              ↓
         Supabase Database
```

## Monitoring

### View logs:
```bash
gcloud run services logs read fpl-api-backend --region asia-southeast1
```

### View service details:
```bash
gcloud run services describe fpl-api-backend --region asia-southeast1
```

### Monitor in Console:
Visit: https://console.cloud.google.com/run

## Cost Optimization

- **Pay per request**: Cloud Run only charges when handling requests
- **Min instances = 0**: No cost when idle (cold starts acceptable)
- **Memory/CPU**: Adjust based on actual usage
- **Monitor usage**: Check GCP Console for actual costs

### Estimated costs (with $300 free credits):
- **Cloud Run**: ~$0.10-0.50 per 1000 requests (depending on memory/CPU)
- **Cloud Build**: ~$0.003 per build minute
- **Container Registry**: ~$0.026 per GB/month
- **Secret Manager**: Free for first 6 secrets

With $300 credits, you can run for several months depending on usage.

## Troubleshooting

### Deployment fails:
- Check that all APIs are enabled
- Verify secrets are created
- Check Cloud Build logs: `gcloud builds list`

### Service timeout:
- Increase timeout in `deploy_gcp.sh` (max 900s for Cloud Run)
- Check service logs for errors

### High latency:
- Consider increasing min instances to 1 (eliminates cold starts)
- Use a region closer to your users
- Check Cloud Run metrics in Console

### Out of memory:
- Increase memory in deployment: `--memory 8Gi`
- Check logs for memory errors

## Updating Deployment

To update the service after code changes:

```bash
# Just run the deploy script again
./deploy_gcp.sh
```

Or manually:
```bash
gcloud builds submit --tag gcr.io/fpl-optimizer/fpl-api-backend
gcloud run deploy fpl-api-backend \
  --image gcr.io/fpl-optimizer/fpl-api-backend \
  --region asia-southeast1
```

## Cleanup

To remove all resources:

```bash
# Delete Cloud Run service
gcloud run services delete fpl-api-backend --region asia-southeast1

# Delete secrets
gcloud secrets delete supabase-url
gcloud secrets delete supabase-key
gcloud secrets delete db-connection
gcloud secrets delete api-football-key
gcloud secrets delete news-api-key

# Delete project (careful!)
gcloud projects delete fpl-optimizer
```

## Next Steps

1. Set up monitoring alerts in GCP Console
2. Configure custom domain (optional)
3. Set up CI/CD pipeline (GitHub Actions, etc.)
4. Enable Cloud CDN for better performance (optional)

