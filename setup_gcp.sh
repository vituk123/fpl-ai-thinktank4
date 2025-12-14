#!/bin/bash
# Master script to set up Google Cloud Platform for FPL Backend

set -e

PROJECT_ID="instant-vent-481016-c0"
REGION="asia-southeast1"

echo "🚀 Setting up Google Cloud Platform for FPL Backend"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found!"
    echo ""
    echo "📦 Install gcloud CLI:"
    echo "   macOS: brew install --cask google-cloud-sdk"
    echo "   Linux: https://cloud.google.com/sdk/docs/install"
    echo ""
    exit 1
fi

echo "✅ gcloud CLI found: $(gcloud --version | head -n 1)"
echo ""

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "🔐 Not logged in to Google Cloud. Running gcloud init..."
    gcloud init
else
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo "✅ Logged in as: ${ACTIVE_ACCOUNT}"
fi

echo ""

# Create project (if it doesn't exist)
echo "📋 Checking/Creating GCP project..."
if gcloud projects describe ${PROJECT_ID} &> /dev/null; then
    echo "✅ Project ${PROJECT_ID} already exists"
else
    echo "📝 Creating project ${PROJECT_ID}..."
    gcloud projects create ${PROJECT_ID} --name="FPL Optimizer Backend"
    echo "✅ Project created"
fi

# Set as default project
echo "📋 Setting default project..."
gcloud config set project ${PROJECT_ID}

# Set default region
echo "📋 Setting default region..."
gcloud config set compute/region ${REGION}

echo ""
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com

echo ""
echo "✅ GCP setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Set up secrets: ./setup_gcp_secrets.sh"
echo "   2. Deploy to Cloud Run: ./deploy_gcp.sh"
echo ""

