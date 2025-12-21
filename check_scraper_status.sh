#!/bin/bash
# Check status of FPL team scraper on ByteHosty server

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
APP_DIR="C:\\fpl-api"

# Function to run SSH command
ssh_cmd() {
    sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SERVER_USER}@${SERVER_IP}" "$@"
}

echo "🔍 Checking scraper status on ByteHosty server..."
echo ""

# Check if output file exists and its size
echo "📊 File Status:"
FILE_INFO=$(ssh_cmd "powershell -Command \"\$f = Get-Item '${APP_DIR}\\fpl_teams_full.csv' -ErrorAction SilentlyContinue; if (\$f) { [math]::Round(\$f.Length / 1MB, 2); (Get-Content \$f.FullName | Measure-Object -Line).Lines } else { '0'; '0' }\" 2>&1" | grep -E '^[0-9]+\.?[0-9]*$|^[0-9]+$' | head -2)
FILE_SIZE_MB=$(echo "$FILE_INFO" | head -1)
LINE_COUNT=$(echo "$FILE_INFO" | tail -1)

if [ -n "$FILE_SIZE_MB" ] && [ "$FILE_SIZE_MB" != "0" ]; then
    echo "   ✅ Output file exists: fpl_teams_full.csv"
    echo "   📦 File size: ${FILE_SIZE_MB} MB"
    
    if [[ "$LINE_COUNT" =~ ^[0-9]+$ ]] && [ "$LINE_COUNT" != "0" ]; then
        TEAM_COUNT=$((LINE_COUNT - 1))  # Subtract header
        echo "   📈 Teams found: ${TEAM_COUNT}"
    fi
else
    echo "   ⏳ Output file not created yet"
fi

echo ""

# Check checkpoint
echo "📍 Checkpoint Status:"
CHECKPOINT=$(ssh_cmd "type ${APP_DIR}\\checkpoint.txt 2>&1" 2>&1 | tail -1)
if [[ "$CHECKPOINT" =~ ^[0-9]+$ ]]; then
    PROGRESS=$(echo "scale=2; $CHECKPOINT * 100 / 12000000" | bc)
    echo "   ✅ Last processed ID: ${CHECKPOINT}"
    echo "   📊 Progress: ${PROGRESS}%"
    REMAINING=$((12000000 - CHECKPOINT))
    echo "   ⏳ Remaining: ${REMAINING} IDs"
else
    echo "   ⏳ No checkpoint file yet (scraper may be starting)"
fi

echo ""

# Check if Python process is running
echo "🔄 Process Status:"
PYTHON_PROC=$(ssh_cmd "tasklist | findstr python" 2>&1 | tail -1)
if echo "$PYTHON_PROC" | grep -q "python"; then
    echo "   ✅ Python process is running"
    echo "   $PYTHON_PROC"
else
    echo "   ⚠️  No Python process found - scraper may have completed or stopped"
fi

echo ""

# Check recent log output (last 20 lines)
echo "📝 Recent Log Output:"
LOG_OUTPUT=$(ssh_cmd "powershell -Command \"if (Test-Path '${APP_DIR}\\scraper.log') { Get-Content '${APP_DIR}\\scraper.log' -Tail 10 } else { 'No log file yet' }\" 2>&1" | tail -20)
echo "$LOG_OUTPUT"

echo ""
echo "💡 To view full log: ssh Administrator@${SERVER_IP} 'type C:\\fpl-api\\scraper.log'"
echo "💡 To restart scraper: ./deploy_and_run_team_scraper.sh 1 12000000 150 y"

