#!/bin/bash
# Setup secrets in Google Cloud Secret Manager

set -e

PROJECT_ID="instant-vent-481016-c0"

echo "🔐 Setting up secrets in Google Cloud Secret Manager..."
echo "   Project: ${PROJECT_ID}"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

# Enable Secret Manager API
echo "📋 Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

echo ""
echo "Please enter your secret values (input will be hidden):"
echo ""

# Create Supabase URL secret
echo "Enter your Supabase URL (e.g., https://xxxxx.supabase.co):"
read -s SUPABASE_URL
if [ ! -z "$SUPABASE_URL" ]; then
    echo "$SUPABASE_URL" | gcloud secrets create supabase-url --data-file=- 2>/dev/null || \
    echo "$SUPABASE_URL" | gcloud secrets versions add supabase-url --data-file=-
    echo "✅ Supabase URL secret created/updated"
else
    echo "⚠️  Skipping Supabase URL (empty input)"
fi

# Create Supabase Key secret
echo ""
echo "Enter your Supabase Anon Key:"
read -s SUPABASE_KEY
if [ ! -z "$SUPABASE_KEY" ]; then
    echo "$SUPABASE_KEY" | gcloud secrets create supabase-key --data-file=- 2>/dev/null || \
    echo "$SUPABASE_KEY" | gcloud secrets versions add supabase-key --data-file=-
    echo "✅ Supabase Key secret created/updated"
else
    echo "⚠️  Skipping Supabase Key (empty input)"
fi

# Create Database Connection String secret
echo ""
echo "Enter your Database Connection String (PostgreSQL URI):"
read -s DB_CONNECTION_STRING
if [ ! -z "$DB_CONNECTION_STRING" ]; then
    echo "$DB_CONNECTION_STRING" | gcloud secrets create db-connection --data-file=- 2>/dev/null || \
    echo "$DB_CONNECTION_STRING" | gcloud secrets versions add db-connection --data-file=-
    echo "✅ Database Connection String secret created/updated"
else
    echo "⚠️  Skipping Database Connection String (empty input)"
fi

# Create API Football Key secret
echo ""
echo "Enter your API Football Key:"
read -s API_FOOTBALL_KEY
if [ ! -z "$API_FOOTBALL_KEY" ]; then
    echo "$API_FOOTBALL_KEY" | gcloud secrets create api-football-key --data-file=- 2>/dev/null || \
    echo "$API_FOOTBALL_KEY" | gcloud secrets versions add api-football-key --data-file=-
    echo "✅ API Football Key secret created/updated"
else
    echo "⚠️  Skipping API Football Key (empty input)"
fi

# Create News API Key secret
echo ""
echo "Enter your News API Key:"
read -s NEWS_API_KEY
if [ ! -z "$NEWS_API_KEY" ]; then
    echo "$NEWS_API_KEY" | gcloud secrets create news-api-key --data-file=- 2>/dev/null || \
    echo "$NEWS_API_KEY" | gcloud secrets versions add news-api-key --data-file=-
    echo "✅ News API Key secret created/updated"
else
    echo "⚠️  Skipping News API Key (empty input)"
fi

echo ""
echo "✅ All secrets setup complete!"
echo ""
echo "📝 To view secrets:"
echo "   gcloud secrets list"
echo ""

