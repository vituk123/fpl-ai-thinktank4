# Upload FPL Teams Data to Supabase

## Overview
This guide explains how to upload the FPL teams CSV file from the ByteHosty server to Supabase for use as a fallback search endpoint.

## Prerequisites
- CSV file exists on server at: `C:\fpl-api\fpl_teams_full.csv`
- Upload script exists on server at: `C:\fpl-api\upload_fpl_teams_to_db.py`
- Supabase table `fpl_teams` has been created (run `create_fpl_teams_table.sql` migration)
- Server has Supabase credentials in environment variables or `.env` file

## Steps to Upload

### Option 1: Using SSH Command (Recommended)

```bash
sshpass -p '$&8$%U9F#&&%' ssh -o StrictHostKeyChecking=no Administrator@198.23.185.233 "cmd /c \"cd /d C:\\fpl-api && py upload_fpl_teams_to_db.py --csv fpl_teams_full.csv --batch-size 500\""
```

### Option 2: Using the Upload Script

```bash
./upload_teams_to_supabase_server.sh
```

## What Happens

1. The script reads the CSV file (`fpl_teams_full.csv`) from the server
2. Processes records in batches of 500 (configurable)
3. Uploads to Supabase `fpl_teams` table using upsert (handles duplicates)
4. Progress is logged to console

## Expected Time

- CSV file size: ~556MB (10M+ teams)
- Upload speed depends on network and Supabase rate limits
- Estimated time: 30-60 minutes for full dataset
- Uses batch size of 500 to respect API rate limits

## Verification

After upload, verify data in Supabase:
```sql
SELECT COUNT(*) FROM fpl_teams;
```

Should return approximately 10+ million records.

## Fallback Behavior

Once data is in Supabase:
- Primary search: ByteHosty server (`/api/v1/search/teams`)
- Fallback search: Supabase Edge Function (`/search-teams`)
- Frontend automatically tries Supabase if server search fails

