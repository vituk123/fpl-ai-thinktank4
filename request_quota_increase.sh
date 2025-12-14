#!/bin/bash
# Request quota increases for Cloud Run

set -e

PROJECT_ID="instant-vent-481016-c0"
REGION="asia-southeast1"

export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

echo "📋 Requesting Cloud Run Quota Increases..."
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

echo "Current quotas can be viewed at:"
echo "https://console.cloud.google.com/iam-admin/quotas?project=${PROJECT_ID}&service=run.googleapis.com"
echo ""

echo "To request quota increases:"
echo ""
echo "1. Go to: https://console.cloud.google.com/iam-admin/quotas?project=${PROJECT_ID}"
echo ""
echo "2. Filter by: 'Cloud Run API'"
echo ""
echo "3. Request increases for:"
echo "   - CPU allocation per region: Request 8 CPUs (current: 2)"
echo "   - Memory allocation per region: Request 32Gi (current: 4Gi)"
echo ""
echo "4. Fill out the quota increase form with:"
echo "   - Justification: 'Running ML workloads for FPL optimizer requires higher CPU and memory'"
echo "   - Requested value: 8 CPUs, 32Gi memory"
echo ""
echo "Quota increases are typically approved within 24-48 hours."
echo ""
echo "Alternatively, you can use the gcloud CLI (if available):"
echo "  gcloud alpha service-quota quotas update [QUOTA_NAME] --value=[NEW_VALUE]"

