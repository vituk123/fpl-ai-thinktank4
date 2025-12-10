# FPL Backend Deployment Guide

This guide covers deploying the FPL Optimizer backend to Render (FastAPI) and Supabase (Edge Functions).

## Architecture

```
Frontend (React/Vite)
    ↓
    ├─→ Supabase Edge Functions (Lightweight: Live Tracker, Predictions)
    └─→ Render FastAPI Backend (Heavy: ML Engine, Recommendations, Optimizer)
              ↓
         Supabase Database (PostgreSQL)
```

## Prerequisites

1. **Supabase Account**: https://supabase.com
2. **Render Account**: https://render.com
3. **Supabase CLI**: `brew install supabase/tap/supabase` (macOS) or `npm install -g supabase`
4. **GitHub Repository**: Your code pushed to GitHub

## Part 1: Deploy FastAPI Backend to Render

### Step 1: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub
3. Connect your GitHub repository

### Step 2: Create Web Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure service:
   - **Name**: `fpl-api-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.dashboard_api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free tier or paid (recommended for ML workloads)

### Step 3: Set Environment Variables

In Render dashboard → Environment Variables, add:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
DB_CONNECTION_STRING=postgresql://user:password@host:port/database
API_FOOTBALL_KEY=your-api-football-key
NEWS_API_KEY=your-news-api-key
FRONTEND_URL=https://your-frontend-domain.com
PORT=8000
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will build and deploy automatically
3. Note your service URL: `https://your-app.onrender.com`

### Step 5: Verify Deployment

```bash
curl https://your-app.onrender.com/api/v1/health
```

## Part 2: Deploy Edge Functions to Supabase

### Step 1: Login to Supabase CLI

```bash
supabase login
```

### Step 2: Link Your Project

```bash
supabase link --project-ref your-project-ref
```

Find your project ref in Supabase dashboard URL: `https://supabase.com/dashboard/project/YOUR_PROJECT_REF`

### Step 3: Set Edge Function Secrets

```bash
# Set Render API URL for proxy functions
supabase secrets set RENDER_API_URL=https://your-app.onrender.com

# Verify secrets
supabase secrets list
```

### Step 4: Deploy Edge Functions

Use the provided deployment script:

```bash
./deploy_edge_functions.sh
```

Or deploy manually:

```bash
supabase functions deploy live-gameweek --no-verify-jwt
supabase functions deploy ml-predictions --no-verify-jwt
supabase functions deploy ml-recommendations --no-verify-jwt
supabase functions deploy optimize-team --no-verify-jwt
```

### Step 5: Verify Deployment

```bash
# Get your anon key from Supabase dashboard
ANON_KEY=your-anon-key

# Test live gameweek endpoint
curl "https://YOUR_PROJECT.supabase.co/functions/v1/live-gameweek?gameweek=16&entry_id=2568103" \
  -H "Authorization: Bearer $ANON_KEY"

# Test ML predictions endpoint
curl "https://YOUR_PROJECT.supabase.co/functions/v1/ml-predictions?gameweek=16" \
  -H "Authorization: Bearer $ANON_KEY"
```

## Part 3: Database Setup

### Step 1: Verify Tables Exist

The `predictions` table should be created automatically. If not, run:

```bash
# Connect to Supabase database
psql "postgresql://user:password@host:port/database"

# Run migration
\i supabase/migrations/ensure_predictions_table.sql
```

Or use Supabase SQL Editor in dashboard to run the migration.

### Step 2: Verify Database Schema

Ensure these tables exist:
- `predictions` - ML model predictions
- `current_season_history` - Player data
- `player_history` - Archived data
- `decisions` - Transfer decisions for learning system

## Part 4: Frontend Configuration

### Step 1: Create Environment Files

Create `frontend/.env.production`:

```env
VITE_API_BASE_URL=https://your-app.onrender.com/api/v1
VITE_SUPABASE_FUNCTIONS_URL=https://YOUR_PROJECT.supabase.co/functions/v1
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

Create `frontend/.env.development`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_FUNCTIONS_URL=http://localhost:54321/functions/v1
VITE_SUPABASE_URL=http://localhost:54321
VITE_SUPABASE_ANON_KEY=your-local-anon-key
```

### Step 2: Update Frontend Build

The frontend API service (`frontend/src/services/api.js`) is already configured to:
- Route live tracking to Edge Functions
- Route ML predictions to Edge Functions
- Route ML recommendations to Edge Functions (which proxy to Render)
- Route other endpoints to Render FastAPI

### Step 3: Deploy Frontend

Deploy your frontend to your preferred platform (Vercel, Netlify, etc.) with the production environment variables.

## Part 5: Testing

### Test User Flow

1. **User enters team ID** on landing page
2. **Frontend validates** team ID via `/api/v1/entry/{entry_id}/info`
3. **Live tracking** uses Edge Function: `/functions/v1/live-gameweek`
4. **ML recommendations** uses Edge Function proxy: `/functions/v1/ml-recommendations`
5. **ML predictions** uses Edge Function: `/functions/v1/ml-predictions`

### Test Endpoints

```bash
# Health check
curl https://your-app.onrender.com/api/v1/health

# Entry info
curl https://your-app.onrender.com/api/v1/entry/2568103/info

# Live gameweek (Edge Function)
curl "https://YOUR_PROJECT.supabase.co/functions/v1/live-gameweek?gameweek=16&entry_id=2568103" \
  -H "Authorization: Bearer $ANON_KEY"

# ML Recommendations (Edge Function → Render)
curl "https://YOUR_PROJECT.supabase.co/functions/v1/ml-recommendations?entry_id=2568103&gameweek=16" \
  -H "Authorization: Bearer $ANON_KEY"

# ML Predictions (Edge Function)
curl "https://YOUR_PROJECT.supabase.co/functions/v1/ml-predictions?gameweek=16" \
  -H "Authorization: Bearer $ANON_KEY"
```

## Troubleshooting

### Render Issues

**Build fails:**
- Check Python version compatibility
- Verify `requirements.txt` includes all dependencies
- Check build logs in Render dashboard

**Service timeout:**
- ML recommendations may take 30-60 seconds
- Increase timeout in Render settings if needed
- Consider upgrading to paid plan for better performance

### Supabase Issues

**Edge Function not found:**
```bash
supabase functions list
```

**Connection errors:**
- Verify `RENDER_API_URL` secret is set correctly
- Check Edge Function logs: `supabase functions logs FUNCTION_NAME`

**Database connection:**
- Verify `DB_CONNECTION_STRING` format
- Check connection pool limits
- Use Supabase connection pooler URL if available

### CORS Issues

If you see CORS errors:
1. Verify `FRONTEND_URL` is set in Render environment variables
2. Check `config.yml` CORS origins includes your frontend domain
3. Verify Edge Functions allow all origins (or specific domain)

## Monitoring

### Render

- View logs: Render dashboard → Logs
- Monitor uptime: Render dashboard → Metrics
- Set up alerts for service failures

### Supabase

- View Edge Function logs: `supabase functions logs FUNCTION_NAME`
- Monitor database: Supabase dashboard → Database → Logs
- Check API usage: Supabase dashboard → API → Usage

## Next Steps

1. Set up CI/CD for automatic deployments
2. Configure monitoring and alerting
3. Set up database backups
4. Implement rate limiting if needed
5. Add authentication if required

## Support

For issues:
1. Check logs in Render dashboard
2. Check Edge Function logs: `supabase functions logs FUNCTION_NAME`
3. Verify environment variables are set correctly
4. Test endpoints individually to isolate issues

