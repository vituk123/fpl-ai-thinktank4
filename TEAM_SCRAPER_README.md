# FPL Team Scraper - Deployment Guide

This guide explains how to deploy and run the FPL team scraper on the Bytehosty server to populate the team/manager search database.

## Overview

The scraper collects FPL team data (team names, manager names, etc.) and stores it in the Supabase `fpl_teams` table, which powers the team/manager search functionality on the landing page.

## Files

- **scrape_fpl_teams.py**: Async scraper that fetches team data from the FPL API
- **upload_fpl_teams_to_db.py**: Script to upload CSV data to Supabase database
- **deploy_and_run_team_scraper.sh**: Automated deployment script for Bytehosty server

## Quick Start

### Option 1: Automated Deployment (Recommended)

Run the deployment script which handles everything:

```bash
./deploy_and_run_team_scraper.sh
```

The script will:
1. Check SSH connection to Bytehosty server
2. Upload the scraper scripts
3. Install dependencies if needed
4. Run the scraper with your specified parameters
5. Optionally upload results to the database

### Option 2: Manual Deployment

#### Step 1: Copy Scripts to Server

```bash
# Using SCP
scp scrape_fpl_teams.py Administrator@198.23.185.233:/opt/fpl-api/
scp upload_fpl_teams_to_db.py Administrator@198.23.185.233:/opt/fpl-api/
```

#### Step 2: SSH into Server

```bash
ssh Administrator@198.23.185.233
cd /opt/fpl-api
```

#### Step 3: Install Dependencies

```bash
pip install aiohttp tqdm
# Or if using python3
pip3 install aiohttp tqdm
```

#### Step 4: Run the Scraper

```bash
# Example: Scrape team IDs 1 to 10000 with 50 concurrent requests
python3 scrape_fpl_teams.py --start 1 --end 10000 --output fpl_teams.csv --concurrency 50
```

**Parameters:**
- `--start`: Starting Team ID (default: 1)
- `--end`: Ending Team ID (default: 1000)
- `--output`: Output CSV file (default: fpl_teams.csv)
- `--concurrency`: Max concurrent requests (default: 50)

**Note:** The scraper will take time depending on the range. For 10,000 teams with concurrency 50, expect ~5-10 minutes.

#### Step 5: Upload to Database

**If running on the server (with database credentials):**

```bash
python3 upload_fpl_teams_to_db.py --csv fpl_teams.csv
```

**If running locally:**

1. Download the CSV:
   ```bash
   scp Administrator@198.23.185.233:/opt/fpl-api/fpl_teams.csv ./
   ```

2. Upload to database:
   ```bash
   python3 upload_fpl_teams_to_db.py --csv fpl_teams.csv
   ```

Make sure your local environment has `SUPABASE_URL` and `SUPABASE_KEY` set.

## Database Schema

The scraper populates the `fpl_teams` table with the following structure:

```sql
CREATE TABLE fpl_teams (
  team_id INTEGER PRIMARY KEY,
  team_name TEXT NOT NULL,
  manager_name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

The upload script uses `UPSERT` (INSERT ... ON CONFLICT) to handle duplicates, so you can safely run it multiple times.

## Integration with Landing Page

Once the data is uploaded to the database, the existing search functionality on the landing page will automatically work. The search uses:

- **Supabase Edge Function**: `/search-teams` (supabase/functions/search-teams/index.ts)
- **PostgreSQL Function**: `search_fpl_teams()` with fuzzy matching (pg_trgm)

The search endpoint is already integrated in `frontend/src/services/api.ts` via `teamSearchApi.searchTeams()`.

## Recommended Scraping Strategy

### Initial Population

For the first run, scrape a large range to build a comprehensive database:

```bash
# Scrape first 100,000 teams
python3 scrape_fpl_teams.py --start 1 --end 100000 --output fpl_teams.csv --concurrency 50
```

This will take approximately 30-60 minutes depending on rate limits.

### Incremental Updates

For regular updates, you can scrape specific ranges or use the auto-population feature in `dashboard_api.py` which adds teams as users access them.

### Rate Limiting

The FPL API may rate limit requests. If you see rate limit errors:
- Reduce `--concurrency` (try 20-30)
- Add delays between batches (modify the script if needed)
- Run during off-peak hours

## Monitoring Progress

The scraper uses `tqdm` to show progress. You'll see a progress bar like:

```
Scraping Teams: 45%|████▌     | 4500/10000 [02:15<02:45]
```

## Troubleshooting

### SSH Connection Issues

If SSH fails:
1. Verify the server IP: `198.23.185.233`
2. Check if OpenSSH is enabled on Windows server
3. Verify credentials

### Python Not Found

If Python is not found:
```bash
# Try python3 instead
python3 scrape_fpl_teams.py ...
```

### Database Upload Fails

1. Check environment variables:
   ```bash
   echo $SUPABASE_URL
   echo $SUPABASE_KEY
   ```

2. Verify database connection:
   ```python
   from database import DatabaseManager
   db = DatabaseManager()
   # Should not throw errors
   ```

3. Check if table exists:
   - Run the migration: `supabase/migrations/create_fpl_teams_table.sql`

### No Results in Search

1. Verify data was uploaded:
   ```sql
   SELECT COUNT(*) FROM fpl_teams;
   ```

2. Check the search endpoint:
   ```bash
   curl "https://sdezcbesdubplacfxibc.supabase.co/functions/v1/search-teams?q=test"
   ```

## Security Notes

- The server password is stored in the deployment script. Consider using SSH keys instead.
- Database credentials should be set as environment variables, not hardcoded.
- The scraper respects rate limits and won't overwhelm the FPL API.

## Performance Tips

1. **Concurrency**: Start with 50, increase if stable, decrease if rate limited
2. **Batch Size**: For uploads, default is 1000 records per batch (good balance)
3. **Indexes**: The database has GIN indexes for fast fuzzy search - ensure they exist
4. **Incremental**: Consider scraping in chunks and uploading incrementally

## Next Steps

After successful deployment:

1. ✅ Data is in `fpl_teams` table
2. ✅ Search endpoint works at `/search-teams`
3. ✅ Landing page search is functional
4. 🔄 Consider setting up a cron job for regular updates

Example cron job (runs weekly on Sundays at 2 AM):
```bash
0 2 * * 0 cd /opt/fpl-api && python3 scrape_fpl_teams.py --start 1 --end 10000 --output fpl_teams_weekly.csv --concurrency 50 && python3 upload_fpl_teams_to_db.py --csv fpl_teams_weekly.csv
```

