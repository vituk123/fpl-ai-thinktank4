#!/bin/bash
# Deploy and run FPL team scraper on ByteHosty server
# This script uploads the scraper, runs it, and uploads results to database

set -e

# Server configuration
SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'
# Windows paths - try common locations
APP_DIR="C:\\fpl-api"
SCRAPER_OUTPUT="fpl_teams.csv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying FPL Team Scraper to ByteHosty VPS...${NC}"
echo "   Server: ${SERVER_IP}"
echo "   User: ${SERVER_USER}"
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  sshpass not found. Installing...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass
        else
            echo -e "${RED}❌ Please install sshpass: brew install hudochenkov/sshpass/sshpass${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y sshpass || \
        sudo yum install -y sshpass || \
        echo -e "${RED}❌ Please install sshpass manually${NC}"
    fi
fi

# Function to run SSH command with password
ssh_cmd() {
    sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SERVER_USER}@${SERVER_IP}" "$@"
}

# Function to copy file with password
scp_cmd() {
    sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "$@"
}

# Test SSH connection
echo -e "${YELLOW}📡 Testing SSH connection...${NC}"
if ssh_cmd "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${RED}❌ SSH connection failed. Please check:${NC}"
    echo "   1. Server IP is correct: ${SERVER_IP}"
    echo "   2. SSH service is running on the server"
    echo "   3. Firewall allows SSH connections"
    echo "   4. Credentials are correct"
    exit 1
fi

# Check if Python is available on server (Windows uses 'py', Linux uses 'python3' or 'python')
echo -e "${YELLOW}🔍 Checking Python installation...${NC}"
PYTHON_VERSION=$(ssh_cmd "py --version 2>&1 || python3 --version 2>&1 || python --version 2>&1 || echo 'Not found'" 2>&1 | tail -1)
echo "   Python: ${PYTHON_VERSION}"

if echo "$PYTHON_VERSION" | grep -q "Not found"; then
    echo -e "${RED}❌ Python not found on server. Please install Python 3.7+${NC}"
    exit 1
fi

# Determine Python command (Windows uses 'py', Linux uses 'python3' or 'python')
if ssh_cmd "py --version 2>&1" > /dev/null 2>&1; then
    PYTHON_CMD="py"
elif ssh_cmd "command -v python3 2>&1" > /dev/null 2>&1 || ssh_cmd "python3 --version 2>&1" > /dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "   Using Python command: ${PYTHON_CMD}"

# Copy scraper script to server
echo -e "${YELLOW}📦 Copying scraper script to server...${NC}"
# Create directory if it doesn't exist (Windows command)
ssh_cmd "if not exist ${APP_DIR} mkdir ${APP_DIR}" 2>&1 | grep -v "not recognized" || true
scp_cmd scrape_fpl_teams.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\" || {
    echo -e "${YELLOW}⚠️  Trying alternate path...${NC}"
    # Try alternate location
    ALT_DIR="C:\\fpl-ai-thinktank4"
    ssh_cmd "if not exist ${ALT_DIR} mkdir ${ALT_DIR}" 2>&1 | grep -v "not recognized" || true
    APP_DIR="${ALT_DIR}"
    scp_cmd scrape_fpl_teams.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\"
}

# Copy upload script to server
echo -e "${YELLOW}📦 Copying upload script to server...${NC}"
scp_cmd upload_fpl_teams_to_db.py "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\"

# Copy requirements if needed (check if aiohttp and tqdm are installed)
echo -e "${YELLOW}🔍 Checking Python dependencies...${NC}"
ssh_cmd "cd /d ${APP_DIR} && ${PYTHON_CMD} -c \"import aiohttp, tqdm\" 2>&1" > /dev/null 2>&1 || {
    echo -e "${YELLOW}⚠️  Installing required dependencies (aiohttp, tqdm)...${NC}"
    ssh_cmd "cd /d ${APP_DIR} && ${PYTHON_CMD} -m pip install --quiet aiohttp tqdm" || {
        echo -e "${RED}❌ Failed to install dependencies. Please install manually: ${PYTHON_CMD} -m pip install aiohttp tqdm${NC}"
        exit 1
    }
}

# Check if src directory exists (for database module) - Windows path check
echo -e "${YELLOW}🔍 Checking for database module...${NC}"
if ssh_cmd "if exist ${APP_DIR}\\src (echo exists) else (echo notfound)" 2>&1 | grep -q "exists"; then
    echo -e "${GREEN}✅ Source directory found${NC}"
else
    echo -e "${YELLOW}⚠️  Source directory not found. Copying src directory...${NC}"
    scp_cmd -r src "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\\"
fi

# Get scraping parameters from command line or use defaults
START_ID=${1:-1}
END_ID=${2:-10000}
CONCURRENCY=${3:-50}

# Validate inputs are numbers
if ! [[ "$START_ID" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}❌ Invalid start ID: ${START_ID}. Must be a number.${NC}"
    exit 1
fi
if ! [[ "$END_ID" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}❌ Invalid end ID: ${END_ID}. Must be a number.${NC}"
    exit 1
fi
if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}❌ Invalid concurrency: ${CONCURRENCY}. Must be a number.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📊 Scraping Parameters:${NC}"
echo "   Starting Team ID: ${START_ID}"
echo "   Ending Team ID: ${END_ID}"
echo "   Concurrency: ${CONCURRENCY}"

echo ""
echo -e "${GREEN}🚀 Starting scraper on server...${NC}"
echo "   Range: ${START_ID} to ${END_ID}"
echo "   Concurrency: ${CONCURRENCY}"
echo "   Output: ${SCRAPER_OUTPUT}"
echo ""

# Run scraper on server (Windows path handling)
echo -e "${YELLOW}🚀 Running scraper on server...${NC}"
ssh_cmd "cd /d ${APP_DIR} && ${PYTHON_CMD} scrape_fpl_teams.py --start ${START_ID} --end ${END_ID} --output ${SCRAPER_OUTPUT} --concurrency ${CONCURRENCY}" || {
    echo -e "${RED}❌ Scraper failed on server${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✅ Scraping completed!${NC}"

# Check if CSV file was created (Windows path check)
echo -e "${YELLOW}🔍 Checking for output file...${NC}"
if ssh_cmd "if exist ${APP_DIR}\\${SCRAPER_OUTPUT} (echo exists) else (echo notfound)" 2>&1 | grep -q "exists"; then
    RECORD_COUNT=$(ssh_cmd "powershell -Command \"(Get-Content '${APP_DIR}\\${SCRAPER_OUTPUT}' | Measure-Object -Line).Lines\"" 2>&1 | tail -1 | tr -d ' ')
    echo -e "${GREEN}✅ CSV file created with ${RECORD_COUNT} lines${NC}"
else
    echo -e "${RED}❌ CSV file not found on server${NC}"
    exit 1
fi

# Check if upload flag is provided (4th argument), default to yes
UPLOAD_CHOICE=${4:-y}
if [[ "$UPLOAD_CHOICE" != "y" && "$UPLOAD_CHOICE" != "Y" && "$UPLOAD_CHOICE" != "n" && "$UPLOAD_CHOICE" != "N" ]]; then
    UPLOAD_CHOICE="y"
fi

echo ""
echo -e "${YELLOW}📤 Database Upload:${NC}"
echo "   Upload to database: ${UPLOAD_CHOICE}"

if [[ "$UPLOAD_CHOICE" == "y" || "$UPLOAD_CHOICE" == "Y" ]]; then
    echo ""
    echo -e "${YELLOW}📤 Uploading to database...${NC}"
    
    # Check if database credentials are available on server
    if ssh_cmd "cd /d ${APP_DIR} && ${PYTHON_CMD} -c \"import os; assert os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_KEY')\" 2>&1" > /dev/null 2>&1; then
        # Database credentials found on server, upload there
        echo -e "${GREEN}✅ Database credentials found on server, uploading from server...${NC}"
        ssh_cmd "cd /d ${APP_DIR} && ${PYTHON_CMD} upload_fpl_teams_to_db.py --csv ${SCRAPER_OUTPUT}" || {
            echo -e "${RED}❌ Database upload failed on server${NC}"
            exit 1
        }
        echo -e "${GREEN}✅ Database upload completed!${NC}"
    else
        # Database credentials not found on server
        echo -e "${YELLOW}⚠️  Database credentials not found in server environment.${NC}"
        echo -e "${YELLOW}   You can:${NC}"
        echo -e "${YELLOW}   1. Set SUPABASE_URL and SUPABASE_KEY on the server${NC}"
        echo -e "${YELLOW}   2. Download the CSV and run upload script locally${NC}"
        # For non-interactive mode, default to downloading
        DOWNLOAD_CHOICE=${5:-y}
        
        if [[ "$DOWNLOAD_CHOICE" == "y" || "$DOWNLOAD_CHOICE" == "Y" ]]; then
            echo -e "${YELLOW}📥 Downloading CSV file...${NC}"
            # Convert Windows path to SCP-friendly format (use forward slashes)
            SCP_PATH=$(echo "${APP_DIR}" | sed 's/\\\\/\//g')
            scp_cmd "${SERVER_USER}@${SERVER_IP}:${SCP_PATH}/${SCRAPER_OUTPUT}" "./${SCRAPER_OUTPUT}" || {
                echo -e "${RED}❌ Failed to download CSV. Please download manually via RDP or set up database credentials on server.${NC}"
                echo -e "${YELLOW}   File location on server: ${APP_DIR}\\${SCRAPER_OUTPUT}${NC}"
                exit 1
            }
            echo -e "${GREEN}✅ CSV downloaded to ./${SCRAPER_OUTPUT}${NC}"
            
            echo -e "${YELLOW}📤 Uploading to database from local machine...${NC}"
            python3 upload_fpl_teams_to_db.py --csv "${SCRAPER_OUTPUT}" || {
                echo -e "${RED}❌ Upload failed. Please check your local database credentials.${NC}"
                exit 1
            }
            echo -e "${GREEN}✅ Database upload completed!${NC}"
        else
            echo -e "${YELLOW}⚠️  Skipping database upload${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Skipping database upload${NC}"
fi

echo ""
echo -e "${GREEN}✅ All done!${NC}"
echo ""
echo "Summary:"
echo "  - Scraper ran on server: ${SERVER_IP}"
echo "  - Output file: ${APP_DIR}/${SCRAPER_OUTPUT} on server"
if [[ "$UPLOAD_CHOICE" == "y" || "$UPLOAD_CHOICE" == "Y" ]]; then
    echo "  - Data uploaded to Supabase fpl_teams table"
fi
echo ""
echo "The team search on the landing page should now work with the new data!"

