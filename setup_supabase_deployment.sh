#!/bin/bash
# Interactive script to set up Supabase deployment

set -e

echo "🚀 Supabase Edge Functions Deployment Setup"
echo "============================================"
echo ""

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Installing..."
    brew install supabase/tap/supabase
fi

echo "✅ Supabase CLI installed: $(supabase --version)"
echo ""

# Check if already logged in
if supabase projects list &> /dev/null; then
    echo "✅ Already authenticated with Supabase"
    echo ""
    supabase projects list
    echo ""
else
    echo "📝 Please authenticate with Supabase"
    echo "   This will open a browser window for authentication"
    echo ""
    read -p "Press Enter to continue with 'supabase login'..."
    supabase login
fi

# Get project reference
echo ""
echo "📋 Please provide your Supabase project details:"
echo "   You can find your project ref in the Supabase dashboard URL:"
echo "   https://supabase.com/dashboard/project/YOUR_PROJECT_REF"
echo ""
read -p "Enter your Supabase project reference: " PROJECT_REF

if [ -z "$PROJECT_REF" ]; then
    echo "❌ Project reference is required"
    exit 1
fi

# Link project
echo ""
echo "🔗 Linking Supabase project..."
supabase link --project-ref "$PROJECT_REF"

# Get Render URL
echo ""
echo "🌐 Please provide your Render API URL:"
read -p "Enter your Render API URL (e.g., https://fpl-api-backend.onrender.com): " RENDER_URL

if [ -z "$RENDER_URL" ]; then
    echo "⚠️  Render URL not provided. You can set it later with:"
    echo "   supabase secrets set RENDER_API_URL=https://your-app.onrender.com"
else
    echo ""
    echo "🔐 Setting RENDER_API_URL secret..."
    supabase secrets set RENDER_API_URL="$RENDER_URL"
fi

echo ""
echo "✅ Setup complete! Ready to deploy Edge Functions."
echo ""
echo "📦 To deploy Edge Functions, run:"
echo "   ./deploy_edge_functions.sh"
echo ""
echo "Or deploy manually:"
echo "   supabase functions deploy live-gameweek --no-verify-jwt"
echo "   supabase functions deploy ml-predictions --no-verify-jwt"
echo "   supabase functions deploy ml-recommendations --no-verify-jwt"
echo "   supabase functions deploy optimize-team --no-verify-jwt"
echo ""







