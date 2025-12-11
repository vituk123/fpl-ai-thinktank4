#!/bin/bash
# Deploy FPL Backend Edge Functions to Supabase

set -e

echo "🚀 Deploying FPL Backend Edge Functions to Supabase..."

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Install it first:"
    echo "   brew install supabase/tap/supabase  # macOS"
    echo "   npm install -g supabase             # Linux/Windows"
    exit 1
fi

# Check if logged in
if ! supabase projects list &> /dev/null; then
    echo "❌ Not logged in to Supabase. Please run:"
    echo "   supabase login"
    exit 1
fi

# Deploy Edge Functions
echo "📦 Deploying Edge Functions..."

echo "  → Deploying live-gameweek function..."
supabase functions deploy live-gameweek --no-verify-jwt

echo "  → Deploying ml-predictions function..."
supabase functions deploy ml-predictions --no-verify-jwt

echo "  → Deploying ml-recommendations function..."
supabase functions deploy ml-recommendations --no-verify-jwt

echo "  → Deploying optimize-team function..."
supabase functions deploy optimize-team --no-verify-jwt

echo "  → Deploying ml-players function..."
supabase functions deploy ml-players --no-verify-jwt

# Set secrets if RENDER_API_URL is provided
if [ -n "$RENDER_API_URL" ]; then
    echo "  → Setting RENDER_API_URL secret..."
    supabase secrets set RENDER_API_URL="$RENDER_API_URL"
else
    echo "  ⚠️  RENDER_API_URL not set. Set it manually with:"
    echo "     supabase secrets set RENDER_API_URL=https://your-render-app.onrender.com"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Edge Functions deployed:"
echo "  - Live Gameweek: https://YOUR_PROJECT.supabase.co/functions/v1/live-gameweek"
echo "  - ML Predictions: https://YOUR_PROJECT.supabase.co/functions/v1/ml-predictions"
echo "  - ML Recommendations: https://YOUR_PROJECT.supabase.co/functions/v1/ml-recommendations"
echo "  - ML Players: https://YOUR_PROJECT.supabase.co/functions/v1/ml-players"
echo "  - Optimize Team: https://YOUR_PROJECT.supabase.co/functions/v1/optimize-team"
echo ""
echo "💡 Test locally first:"
echo "  supabase functions serve live-gameweek"
echo "  supabase functions serve ml-predictions"
echo "  supabase functions serve ml-recommendations"
echo "  supabase functions serve ml-players"
echo "  supabase functions serve optimize-team"

