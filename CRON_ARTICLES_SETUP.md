# Cron Job Setup for Article Push (Every 2 Days)

## Quick Setup

Run the setup script:

```bash
./cron_setup_articles.sh
```

This will:
- Create a cron job that runs `push_recent_articles.py` every 2 days at 2:00 AM
- Set up logging to `logs/article_push.log`
- Preserve any existing cron jobs

## Schedule Details

- **Frequency**: Every 2 days
- **Time**: 2:00 AM
- **Days**: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30 of each month

## Manual Cron Setup

If you prefer to set it up manually:

```bash
crontab -e
```

Add this line:

```
0 2 */2 * * cd /path/to/fpl-ai-thinktank4 && source venv/bin/activate && python3 push_recent_articles.py >> logs/article_push.log 2>&1
```

## Verify Cron Job

```bash
# View all cron jobs
crontab -l

# Check if the job is scheduled
crontab -l | grep push_recent_articles
```

## View Logs

```bash
# View recent logs
tail -f logs/article_push.log

# View last 50 lines
tail -n 50 logs/article_push.log
```

## Remove Cron Job

```bash
# Edit crontab
crontab -e

# Or remove the specific line
crontab -l | grep -v push_recent_articles.py | crontab
```

## Alternative: Every 2 Days at Different Times

If you want to run at a different time, edit the cron expression:

```bash
# Every 2 days at midnight
0 0 */2 * * ...

# Every 2 days at 3:00 AM
0 3 */2 * * ...

# Every 2 days at 6:00 PM
0 18 */2 * * ...
```

## Troubleshooting

### Cron job not running

1. **Check cron service is running:**
   ```bash
   # macOS
   sudo launchctl list | grep cron
   
   # Linux
   sudo systemctl status cron
   ```

2. **Check logs for errors:**
   ```bash
   tail -f logs/article_push.log
   ```

3. **Test script manually:**
   ```bash
   source venv/bin/activate
   python3 push_recent_articles.py
   ```

4. **Check cron has correct paths:**
   - Make sure the full path to `python3` is used
   - Or use `which python3` to find the path

### Permission issues

If cron can't access files:
- Make sure the script is executable: `chmod +x push_recent_articles.py`
- Check file permissions: `ls -la push_recent_articles.py`
- Ensure `.env` file is readable

### Environment variables not loading

Cron runs with minimal environment. If you have issues:
- Use absolute paths in the cron command
- Source your `.env` file explicitly if needed
- Or set environment variables in the crontab entry

## Next Steps

After setting up the cron job:
1. Wait for the first run (or test manually)
2. Check `logs/article_push.log` to verify it's working
3. Monitor the Supabase table to see new articles being added

