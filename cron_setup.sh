#!/bin/bash
# Cron Setup Script for Daily News Processing
# This script helps set up the cron job for daily FPL news processing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_LOG="$SCRIPT_DIR/logs/news_processing.log"
CRON_COMMAND="cd $SCRIPT_DIR && source venv/bin/activate && python3 process_news_daily.py >> $CRON_LOG 2>&1"

echo "=========================================="
echo "FPL News Processing - Cron Setup"
echo "=========================================="
echo ""
echo "This script will add a cron job to run daily news processing at midnight."
echo ""
echo "Cron job details:"
echo "  Schedule: 0 0 * * * (daily at midnight)"
echo "  Command: $CRON_COMMAND"
echo "  Log file: $CRON_LOG"
echo ""

# Check if venv exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "⚠️  Warning: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "   Please create it first: python3 -m venv venv"
    echo ""
fi

# Check if logs directory exists
if [ ! -d "$SCRIPT_DIR/logs" ]; then
    echo "Creating logs directory..."
    mkdir -p "$SCRIPT_DIR/logs"
fi

# Ask for confirmation
read -p "Do you want to add this cron job? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create temporary cron file
    TEMP_CRON=$(mktemp)
    
    # Get existing crontab
    crontab -l > "$TEMP_CRON" 2>/dev/null || true
    
    # Check if cron job already exists
    if grep -q "process_news_daily.py" "$TEMP_CRON"; then
        echo "⚠️  Cron job already exists. Removing old entry..."
        grep -v "process_news_daily.py" "$TEMP_CRON" > "${TEMP_CRON}.new"
        mv "${TEMP_CRON}.new" "$TEMP_CRON"
    fi
    
    # Add new cron job
    echo "0 0 * * * $CRON_COMMAND" >> "$TEMP_CRON"
    
    # Install new crontab
    crontab "$TEMP_CRON"
    rm "$TEMP_CRON"
    
    echo ""
    echo "✅ Cron job added successfully!"
    echo ""
    echo "To view your cron jobs, run: crontab -l"
    echo "To remove this cron job, run: crontab -e (then delete the line)"
    echo ""
    echo "The job will run daily at midnight and log to: $CRON_LOG"
else
    echo "Cron job not added."
    echo ""
    echo "To add it manually, run:"
    echo "  crontab -e"
    echo ""
    echo "Then add this line:"
    echo "  0 0 * * * $CRON_COMMAND"
fi

