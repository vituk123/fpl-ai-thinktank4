# FPL Team Scraper - Progress Tracking

## Current Status

**Target:** Scrape all 12,000,000 FPL teams  
**Started:** December 20, 2025  
**Status:** ✅ **RUNNING**

## Progress

- **Processed:** 200,000 IDs (1.66% complete)
- **Remaining:** 11,800,000 IDs
- **Current Speed:** ~660 teams/second
- **Estimated Time Remaining:** ~5-6 hours at current speed

## Monitoring

### Check Status
```bash
./check_scraper_status.sh
```

### View Live Log
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "type C:\\fpl-api\\scraper.log | more"
```

### Check Checkpoint
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "type C:\\fpl-api\\checkpoint.txt"
```

### Check Output File Size
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "dir C:\\fpl-api\\fpl_teams_full.csv"
```

## Configuration

- **Start ID:** 1
- **End ID:** 12,000,000
- **Concurrency:** 150 concurrent requests
- **Batch Size:** 50,000 IDs per batch
- **Checkpoint File:** checkpoint.txt (allows resume if interrupted)
- **Output File:** fpl_teams_full.csv

## Estimated Completion

At ~660 teams/second:
- **Per batch (50K IDs):** ~76 seconds
- **Total batches:** 240 batches
- **Total time:** ~5-6 hours

## Resume Capability

If the scraper stops for any reason, you can resume from the last checkpoint:

```bash
# The scraper will automatically resume from checkpoint.txt
# Just run the same command again:
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "cd /d C:\\fpl-api && py scrape_fpl_teams.py --start 1 --end 12000000 --output fpl_teams_full.csv --concurrency 150 --checkpoint checkpoint.txt --batch-size 50000"
```

## Next Steps After Completion

1. **Download the CSV:**
   ```bash
   scp Administrator@198.23.185.233:'C:/fpl-api/fpl_teams_full.csv' ./
   ```

2. **Upload to Database:**
   ```bash
   python3 upload_fpl_teams_to_db.py --csv fpl_teams_full.csv --batch-size 5000
   ```

3. **Verify Data:**
   ```sql
   SELECT COUNT(*) FROM fpl_teams;
   ```

## Notes

- The scraper processes in batches and saves progress periodically
- Checkpoint file is updated after each batch
- Output file grows incrementally
- The scraper handles rate limits and errors gracefully
- Most team IDs don't exist, so actual teams found will be much less than 12M

