#!/bin/bash
# Deploy FPL Backend to Google Cloud Run

set -e

PROJECT_ID="instant-vent-481016-c0"
SERVICE_NAME="fpl-api-backend"
REGION="asia-southeast1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying FPL Backend to Google Cloud Run..."
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Service: ${SERVICE_NAME}"

# Set project
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Build and push Docker image using Cloud Build
echo "📦 Building Docker image with Cloud Build..."
gcloud builds submit --tag ${IMAGE_NAME} --timeout=20m

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "PYTHON_VERSION=3.11" \
  --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest,DB_CONNECTION_STRING=db-connection:latest,API_FOOTBALL_KEY=api-football-key:latest,NEWS_API_KEY=news-api-key:latest"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Service URL:"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo "   ${SERVICE_URL}"
echo ""
echo "📝 Next steps:"
echo "   1. Update Supabase secret: supabase secrets set GCP_API_URL=${SERVICE_URL}"
echo "   2. Test the endpoint: curl ${SERVICE_URL}/api/v1/health"
echo "   3. View logs: gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"

