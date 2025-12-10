# Deployment Checklist

Follow these steps in order to deploy your FPL backend.

## Prerequisites ✓

- [ ] GitHub repository created and code pushed
- [ ] Supabase account created at https://supabase.com
- [ ] Render account created at https://render.com
- [ ] Supabase CLI installed (`brew install supabase/tap/supabase` or `npm install -g supabase`)

## Step 1: Get Your Supabase Credentials

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project (or create a new one)
3. Go to **Settings** → **API**
4. Copy these values:
   - **Project URL**: `https://your-project.supabase.co`
   - **anon/public key**: Copy this for `SUPABASE_KEY` and `VITE_SUPABASE_ANON_KEY`
5. Go to **Settings** → **Database**
6. Copy the **Connection string** (URI format) for `DB_CONNECTION_STRING`

**Save these values - you'll need them for Step 2 and Step 3**

## Step 2: Deploy FastAPI to Render

### 2.1 Create Web Service

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure service:
   - **Name**: `fpl-api-backend` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or `.` if needed)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.dashboard_api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: 
     - Free tier works for testing (but slow cold starts)
     - Paid tier recommended for production (better performance)

### 2.2 Set Environment Variables in Render

In Render dashboard → Your service → **Environment**, add:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
DB_CONNECTION_STRING=postgresql://user:password@host:port/database
API_FOOTBALL_KEY=08b18b2d60e1cfea7769c7276226d2d1
NEWS_API_KEY=pub_a13e0ce062804c5891decaa7ac8a27b9
FRONTEND_URL=https://your-frontend-domain.com
PORT=8000
```

**Replace with your actual values from Step 1**

### 2.3 Deploy

1. Click **"Create Web Service"**
2. Wait for build to complete (5-10 minutes)
3. Note your service URL: `https://your-app.onrender.com`

### 2.4 Test Render Deployment

```bash
# Test health endpoint
curl https://your-app.onrender.com/api/v1/health

# Should return: {"status": "healthy", ...}
```

## Step 3: Deploy Edge Functions to Supabase

### 3.1 Login to Supabase CLI

```bash
supabase login
```

### 3.2 Link Your Project

```bash
# Get your project ref from Supabase dashboard URL
# URL format: https://supabase.com/dashboard/project/YOUR_PROJECT_REF

supabase link --project-ref YOUR_PROJECT_REF
```

### 3.3 Set Render API URL Secret

```bash
# Replace with your actual Render URL from Step 2.3
supabase secrets set RENDER_API_URL=https://your-app.onrender.com
```

### 3.4 Deploy Edge Functions

```bash
# Make sure you're in the project root
cd /Users/vitumbikokayuni/Documents/fpl-ai-thinktank4

# Run deployment script
./deploy_edge_functions.sh
```

Or deploy manually:

```bash
supabase functions deploy live-gameweek --no-verify-jwt
supabase functions deploy ml-predictions --no-verify-jwt
supabase functions deploy ml-recommendations --no-verify-jwt
supabase functions deploy optimize-team --no-verify-jwt
```

### 3.5 Verify Edge Functions

```bash
# Get your anon key from Supabase dashboard
ANON_KEY=your-supabase-anon-key

# Test live gameweek endpoint
curl "https://YOUR_PROJECT.supabase.co/functions/v1/live-gameweek?gameweek=16&entry_id=2568103" \
  -H "Authorization: Bearer $ANON_KEY"

# Test ML predictions endpoint
curl "https://YOUR_PROJECT.supabase.co/functions/v1/ml-predictions?gameweek=16" \
  -H "Authorization: Bearer $ANON_KEY"
```

## Step 4: Update Frontend Environment Variables

### 4.1 Create Production Environment File

```bash
cd frontend

# Copy template
cp env.production.template .env.production

# Edit and fill in your values
# Use your actual URLs from Steps 2.3 and 3.5
```

Update `.env.production` with:
- Your Render API URL from Step 2.3
- Your Supabase project URL from Step 1
- Your Supabase anon key from Step 1

### 4.2 Verify Environment File

```bash
# Check that file exists and has correct values
cat .env.production
```

## Step 5: Test Complete Flow

### 5.1 Test with a Real Team ID

Use your FPL team ID or a test ID like `2568103`:

```bash
# 1. Test entry info (Render FastAPI)
curl https://your-app.onrender.com/api/v1/entry/2568103/info

# 2. Test live gameweek (Edge Function)
curl "https://YOUR_PROJECT.supabase.co/functions/v1/live-gameweek?gameweek=16&entry_id=2568103" \
  -H "Authorization: Bearer $ANON_KEY"

# 3. Test ML recommendations (Edge Function → Render)
curl "https://YOUR_PROJECT.supabase.co/functions/v1/ml-recommendations?entry_id=2568103&gameweek=16" \
  -H "Authorization: Bearer $ANON_KEY"

# 4. Test ML predictions (FastAPI)
curl "https://your-app.onrender.com/api/v1/ml/predictions?gameweek=16&entry_id=2568103"
```

### 5.2 Test from Frontend

1. Start your frontend dev server:
```bash
cd frontend
npm run dev
```

2. Open http://localhost:5173 (or your dev port)
3. Enter a team ID on the landing page
4. Verify:
   - ✅ Team validation works
   - ✅ Live tracking loads
   - ✅ Recommendations load (may take 30-60 seconds)
   - ✅ Predictions load

## Troubleshooting

### Render Issues

**Service won't start:**
- Check logs in Render dashboard → Logs
- Verify all environment variables are set
- Check Python version compatibility

**Slow responses:**
- Free tier has cold starts (30-60 seconds on first request)
- Consider upgrading to paid tier
- ML recommendations will always take 30-60 seconds (expected)

### Supabase Issues

**Edge Functions not found:**
```bash
supabase functions list
```

**Connection errors:**
- Verify `RENDER_API_URL` secret is set: `supabase secrets list`
- Check Edge Function logs: `supabase functions logs FUNCTION_NAME`

**CORS errors:**
- Edge Functions allow all origins by default
- If issues persist, check Render CORS settings

### Database Issues

**Predictions table missing:**
```bash
# Connect to Supabase database via SQL Editor
# Run migration: supabase/migrations/ensure_predictions_table.sql
```

## Next Steps After Deployment

1. Set up monitoring (Render dashboard + Supabase logs)
2. Configure custom domain for Render (optional)
3. Set up CI/CD for automatic deployments
4. Configure database backups in Supabase
5. Add rate limiting if needed

## Quick Reference

### Render Service URL
```
https://your-app.onrender.com
```

### Supabase Edge Functions
```
https://YOUR_PROJECT.supabase.co/functions/v1/
```

### Key Endpoints
- Health: `GET /api/v1/health`
- Entry Info: `GET /api/v1/entry/{entry_id}/info`
- Live Gameweek: `GET /functions/v1/live-gameweek?gameweek=X&entry_id=Y`
- ML Recommendations: `GET /functions/v1/ml-recommendations?entry_id=X`
- ML Predictions: `GET /api/v1/ml/predictions?gameweek=X`

