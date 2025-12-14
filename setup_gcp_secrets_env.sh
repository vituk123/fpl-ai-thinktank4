#!/bin/bash
# Setup secrets in Google Cloud Secret Manager (using environment variables)

set -e

PROJECT_ID="instant-vent-481016-c0"

echo "🔐 Setting up secrets in Google Cloud Secret Manager..."
echo "   Project: ${PROJECT_ID}"
echo ""

# Set project
export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"
gcloud config set project ${PROJECT_ID}

# Enable Secret Manager API
echo "📋 Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

echo ""
echo "Setting up secrets..."
echo ""

# 1. Supabase URL (known)
SUPABASE_URL="https://sdezcbesdubplacfxibc.supabase.co"
echo "$SUPABASE_URL" | gcloud secrets create supabase-url --data-file=- 2>/dev/null || \
echo "$SUPABASE_URL" | gcloud secrets versions add supabase-url --data-file=-
echo "✅ Supabase URL secret created/updated"

# 2. Supabase Key (from env var or prompt)
if [ -z "$SUPABASE_KEY" ]; then
    echo ""
    echo "Enter your Supabase Anon Key (from Supabase Dashboard → Settings → API):"
    read -s SUPABASE_KEY
fi
if [ ! -z "$SUPABASE_KEY" ]; then
    echo "$SUPABASE_KEY" | gcloud secrets create supabase-key --data-file=- 2>/dev/null || \
    echo "$SUPABASE_KEY" | gcloud secrets versions add supabase-key --data-file=-
    echo "✅ Supabase Key secret created/updated"
else
    echo "⚠️  Skipping Supabase Key (empty input)"
fi

# 3. Database Connection String (from env var or prompt)
if [ -z "$DB_CONNECTION_STRING" ]; then
    echo ""
    echo "Enter your Database Connection String (from Supabase Dashboard → Settings → Database → Connection string → URI):"
    read -s DB_CONNECTION_STRING
fi
if [ ! -z "$DB_CONNECTION_STRING" ]; then
    echo "$DB_CONNECTION_STRING" | gcloud secrets create db-connection --data-file=- 2>/dev/null || \
    echo "$DB_CONNECTION_STRING" | gcloud secrets versions add db-connection --data-file=-
    echo "✅ Database Connection String secret created/updated"
else
    echo "⚠️  Skipping Database Connection String (empty input)"
fi

# 4. API Football Key (known)
API_FOOTBALL_KEY="08b18b2d60e1cfea7769c7276226d2d1"
echo ""
echo "$API_FOOTBALL_KEY" | gcloud secrets create api-football-key --data-file=- 2>/dev/null || \
echo "$API_FOOTBALL_KEY" | gcloud secrets versions add api-football-key --data-file=-
echo "✅ API Football Key secret created/updated"

# 5. News API Key (known)
NEWS_API_KEY="pub_a13e0ce062804c5891decaa7ac8a27b9"
echo ""
echo "$NEWS_API_KEY" | gcloud secrets create news-api-key --data-file=- 2>/dev/null || \
echo "$NEWS_API_KEY" | gcloud secrets versions add news-api-key --data-file=-
echo "✅ News API Key secret created/updated"

echo ""
echo "✅ All secrets setup complete!"
echo ""
echo "📝 To view secrets:"
echo "   gcloud secrets list"
echo ""

