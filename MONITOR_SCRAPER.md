# FPL Team Scraper Monitoring Guide

## Quick Status Check

The scraper is **RUNNING** and processing all 12 million FPL team IDs.

### Current Progress
- ✅ **Scraper is active** - Python process running on server
- 📊 **Checkpoint:** 300,000+ IDs processed (2.5% complete)
- ⚡ **Speed:** ~500-600 teams/second
- 📦 **Output:** fpl_teams_full.csv (growing)

## Manual Status Checks

### 1. Check Current Checkpoint
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "type C:\\fpl-api\\checkpoint.txt"
```
This shows the last processed team ID.

### 2. Check File Size and Line Count
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 'powershell -Command "$f = Get-Item \"C:\fpl-api\fpl_teams_full.csv\"; Write-Host \"Size (MB):\" ([math]::Round($f.Length / 1MB, 2)); Write-Host \"Teams:\" ((Get-Content $f.FullName | Measure-Object -Line).Lines - 1)"'
```

### 3. View Recent Log Output
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "powershell -Command \"Get-Content C:\\fpl-api\\scraper.log -Tail 20\""
```

### 4. Check if Process is Running
```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "tasklist | findstr python"
```

## Estimated Completion

At current speed (~550 teams/second):
- **Total batches:** 240 (50K IDs each)
- **Time per batch:** ~90 seconds
- **Total estimated time:** ~6 hours
- **Expected completion:** ~6-7 hours from start

## Resume Capability

If the scraper stops, it will resume from the last checkpoint automatically:

```bash
sshpass -p '$&8$%U9F#&&%' ssh Administrator@198.23.185.233 "cd /d C:\\fpl-api && py scrape_fpl_teams.py --start 1 --end 12000000 --output fpl_teams_full.csv --concurrency 150 --checkpoint checkpoint.txt --batch-size 50000 > scraper.log 2>&1 &"
```

## What Happens Next

Once complete (~6 hours):
1. Download the CSV file (~500MB-1GB estimated)
2. Upload to Supabase database
3. Team search will be fully populated!

## Notes

- The scraper processes in batches of 50,000 IDs
- Checkpoint is saved after each batch
- Most IDs don't have teams (only ~20-30% will have data)
- The scraper handles rate limits and errors automatically

