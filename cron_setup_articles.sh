#!/bin/bash
# Setup cron job to push recent articles every 2 days

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/push_recent_articles.py"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/article_push.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Get the current user's crontab
CRON_TMP=$(mktemp)

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "push_recent_articles.py"; then
    echo "⚠️  Cron job for push_recent_articles.py already exists"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "push_recent_articles.py"
    echo ""
    read -p "Do you want to replace it? (y/n): " replace
    if [ "$replace" != "y" ]; then
        echo "Cancelled. Existing cron job unchanged."
        exit 0
    fi
    # Remove existing entry
    crontab -l 2>/dev/null | grep -v "push_recent_articles.py" > "$CRON_TMP"
else
    # Keep existing crontab entries
    crontab -l 2>/dev/null > "$CRON_TMP" 2>/dev/null || true
fi

# Add new cron job (runs every 2 days at 2:00 AM)
# Cron format: minute hour day month weekday
# To run every 2 days, we use: 0 2 */2 * *
# This runs at 2:00 AM on days 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30
echo "0 2 */2 * * cd $SCRIPT_DIR && source venv/bin/activate && python3 $SCRIPT_PATH >> $LOG_FILE 2>&1" >> "$CRON_TMP"

# Install the new crontab
crontab "$CRON_TMP"
rm "$CRON_TMP"

echo "✅ Cron job installed successfully!"
echo ""
echo "Schedule: Every 2 days at 2:00 AM"
echo "Script: $SCRIPT_PATH"
echo "Log file: $LOG_FILE"
echo ""
echo "To view your cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove this cron job:"
echo "  crontab -e"
echo "  (then delete the line with push_recent_articles.py)"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_FILE"

