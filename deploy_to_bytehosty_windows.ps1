# PowerShell script to deploy FPL API to Windows Server
# Run this from your local machine (requires SSH access)

$SERVER_IP = "198.23.185.233"
$SERVER_USER = "Administrator"
$SERVER_PASSWORD = '$&8$%U9F#&&%'
$APP_DIR = "C:\fpl-api"
$PORT = 8080

Write-Host "🚀 Deploying FPL API to ByteHosty Windows Server..." -ForegroundColor Green
Write-Host "   Server: $SERVER_IP"
Write-Host "   User: $SERVER_USER"
Write-Host ""

# Test SSH connection
Write-Host "📡 Testing SSH connection..." -ForegroundColor Yellow
$testResult = sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "${SERVER_USER}@${SERVER_IP}" "echo 'Connected'" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ SSH connection failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ SSH connection successful" -ForegroundColor Green
Write-Host ""

# Detect server capabilities
Write-Host "🔍 Detecting server capabilities..." -ForegroundColor Yellow
$pythonVersion = sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" "python --version 2>&1 || python3 --version 2>&1 || echo 'Not found'" 2>&1
$gitVersion = sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" "git --version 2>&1 || echo 'Not found'" 2>&1

Write-Host "   Python: $pythonVersion"
Write-Host "   Git: $gitVersion"
Write-Host ""

# Create app directory
Write-Host "📁 Creating app directory..." -ForegroundColor Yellow
sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" "if not exist `"$APP_DIR`" mkdir `"$APP_DIR`"" 2>&1 | Out-Null

# Copy files using SCP
Write-Host "📦 Copying files to server..." -ForegroundColor Yellow

# Copy requirements.txt
sshpass -p $SERVER_PASSWORD scp -o StrictHostKeyChecking=no requirements.txt "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\" 2>&1 | Out-Null

# Copy config.yml
sshpass -p $SERVER_PASSWORD scp -o StrictHostKeyChecking=no config.yml "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\" 2>&1 | Out-Null

# Copy source code
Write-Host "📦 Copying source code..." -ForegroundColor Yellow
sshpass -p $SERVER_PASSWORD scp -o StrictHostKeyChecking=no -r src "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\" 2>&1 | Out-Null

# Copy models if they exist
if (Test-Path "models") {
    Write-Host "📦 Copying ML models..." -ForegroundColor Yellow
    sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" "if not exist `"$APP_DIR\models`" mkdir `"$APP_DIR\models`"" 2>&1 | Out-Null
    Get-ChildItem -Path "models" -Filter "*.pkl" | ForEach-Object {
        sshpass -p $SERVER_PASSWORD scp -o StrictHostKeyChecking=no $_.FullName "${SERVER_USER}@${SERVER_IP}:${APP_DIR}\models\" 2>&1 | Out-Null
    }
}

# Get environment variables
Write-Host "🔐 Setting up environment variables..." -ForegroundColor Yellow
Write-Host "Please provide the following secrets (or press Enter to use defaults from config.yml):"
Write-Host ""

$SUPABASE_URL = Read-Host "Supabase URL (default: https://sdezcbesdubplacfxibc.supabase.co)"
if ([string]::IsNullOrWhiteSpace($SUPABASE_URL)) {
    $SUPABASE_URL = "https://sdezcbesdubplacfxibc.supabase.co"
}

$SUPABASE_KEY = Read-Host "Supabase Key" -AsSecureString
$SUPABASE_KEY_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($SUPABASE_KEY))

$DB_CONNECTION_STRING = Read-Host "Database Connection String" -AsSecureString
$DB_CONNECTION_STRING_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_CONNECTION_STRING))

$API_FOOTBALL_KEY = Read-Host "API Football Key (default: from config.yml)"
if ([string]::IsNullOrWhiteSpace($API_FOOTBALL_KEY)) {
    $API_FOOTBALL_KEY = "08b18b2d60e1cfea7769c7276226d2d1"
}

$NEWS_API_KEY = Read-Host "News API Key (default: from config.yml)"
if ([string]::IsNullOrWhiteSpace($NEWS_API_KEY)) {
    $NEWS_API_KEY = "pub_a13e0ce062804c5891decaa7ac8a27b9"
}

# Create .env file on server
Write-Host "📝 Creating .env file on server..." -ForegroundColor Yellow
$envContent = @"
SUPABASE_URL=$SUPABASE_URL
SUPABASE_KEY=$SUPABASE_KEY_PLAIN
DB_CONNECTION_STRING=$DB_CONNECTION_STRING_PLAIN
API_FOOTBALL_KEY=$API_FOOTBALL_KEY
NEWS_API_KEY=$NEWS_API_KEY
PYTHON_VERSION=3.11
PORT=$PORT
"@

# Write .env file using PowerShell on remote server
$envContent | sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" "powershell -Command `"Set-Content -Path '$APP_DIR\.env' -Value @'\`n$envContent\`n'@'`"" 2>&1 | Out-Null

# Setup Python environment and install dependencies
Write-Host "🐍 Setting up Python environment..." -ForegroundColor Yellow
$setupScript = @"
cd $APP_DIR
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
"@

sshpass -p $SERVER_PASSWORD ssh -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" $setupScript 2>&1

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Service URL: http://${SERVER_IP}:${PORT}"
Write-Host "📝 Next steps:"
Write-Host "   1. Create a Windows Service (see deploy_to_bytehosty_windows.md)"
Write-Host "   2. Or run manually: cd $APP_DIR && venv\Scripts\activate && python -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port $PORT"
Write-Host "   3. Test: curl http://${SERVER_IP}:${PORT}/api/v1/health"
Write-Host ""

