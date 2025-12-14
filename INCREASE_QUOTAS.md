# How to Increase GCP Cloud Run Quotas

## Current Limits
- **CPU**: 2 CPUs max
- **Memory**: 4Gi max

## Target Resources (After Quota Increase)
- **CPU**: 8 CPUs (4x increase)
- **Memory**: 32Gi (8x increase)

## Step-by-Step: Request Quota Increases

### Method 1: Via GCP Console (Recommended)

1. **Open Quotas Page**:
   - Go to: https://console.cloud.google.com/iam-admin/quotas?project=instant-vent-481016-c0&service=run.googleapis.com

2. **Request CPU Quota Increase**:
   - Filter by: `run.googleapis.com/cpu_alloc_per_region`
   - Click on the quota
   - Click **"Edit Quotas"**
   - Requested value: **8000** (8 CPUs)
   - Justification: "Running ML workloads for FPL optimizer requires higher CPU for XGBoost model training and predictions. Current 2 CPUs cause timeouts on ML report generation."
   - Submit request

3. **Request Memory Quota Increase**:
   - Filter by: `run.googleapis.com/memory_alloc_per_region`
   - Click on the quota
   - Click **"Edit Quotas"**
   - Requested value: **34359738368** (32Gi in bytes)
   - Justification: "ML model training (XGBoost) and large DataFrame operations require more memory. Current 4Gi causes out-of-memory errors during ML report generation."
   - Submit request

4. **Wait for Approval**:
   - Typically approved within 24-48 hours
   - You'll receive an email when approved

### Method 2: Via gcloud CLI

```bash
# Install alpha component (if not already installed)
gcloud components install alpha

# List current quotas
gcloud alpha service-quota quotas list \
  --service=run.googleapis.com \
  --consumer=projects/instant-vent-481016-c0 \
  --location=asia-southeast1

# Request CPU quota increase (example - may need adjustment)
gcloud alpha service-quota quotas update \
  run.googleapis.com/cpu_alloc_per_region \
  --consumer=projects/instant-vent-481016-c0 \
  --location=asia-southeast1 \
  --value=8000
```

## After Quota Approval

Once quotas are approved, deploy with higher resources:

```bash
./deploy_gcp_high_resources.sh
```

This will deploy with:
- **Memory**: 32Gi
- **CPU**: 8 CPUs
- **Timeout**: 900s (15 minutes)

## Alternative: Use Current Resources

If you want to use the system now with current resources (2 CPUs, 4Gi):

```bash
./deploy_gcp.sh
```

This will work but may be slower for ML operations.

## Check Quota Status

```bash
gcloud alpha service-quota quotas list \
  --service=run.googleapis.com \
  --consumer=projects/instant-vent-481016-c0 \
  --location=asia-southeast1 \
  --format="table(metric,value,limit)"
```

