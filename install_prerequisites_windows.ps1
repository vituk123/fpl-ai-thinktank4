# PowerShell script to install Python and Git on Windows Server
# Run this script on the Windows server via RDP (PowerShell as Administrator)

Write-Host "🚀 Installing Prerequisites for FPL API..." -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ Please run PowerShell as Administrator!" -ForegroundColor Red
    Write-Host "   Right-click PowerShell → Run as administrator" -ForegroundColor Yellow
    exit 1
}

# Step 1: Install Python 3.11
Write-Host "📦 Step 1: Installing Python 3.11..." -ForegroundColor Yellow

# Check if Python is already installed
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
if ($pythonInstalled) {
    $pythonVersion = python --version 2>&1
    Write-Host "   Python is already installed: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "   Downloading Python 3.11 installer..." -ForegroundColor Cyan
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-3.11.9-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing
        Write-Host "   ✅ Download complete" -ForegroundColor Green
        
        Write-Host "   Installing Python (this may take a few minutes)..." -ForegroundColor Cyan
        # Install Python with: Add to PATH, Install for all users, Precompile standard library
        $installArgs = @(
            "/quiet",
            "InstallAllUsers=1",
            "PrependPath=1",
            "Include_test=0",
            "Include_doc=0",
            "Include_pip=1",
            "Include_tcltk=0"
        )
        
        Start-Process -FilePath $pythonInstaller -ArgumentList $installArgs -Wait -NoNewWindow
        
        # Refresh PATH for current session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Verify installation
        Start-Sleep -Seconds 2
        $pythonCheck = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCheck) {
            $version = python --version 2>&1
            Write-Host "   ✅ Python installed successfully: $version" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Python installed but may need a new PowerShell window to use" -ForegroundColor Yellow
            Write-Host "   Please close and reopen PowerShell, then run: python --version" -ForegroundColor Yellow
        }
        
        # Clean up
        Remove-Item $pythonInstaller -ErrorAction SilentlyContinue
    } catch {
        Write-Host "   ❌ Error downloading/installing Python: $_" -ForegroundColor Red
        Write-Host "   Please download manually from: https://www.python.org/downloads/" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 2: Install Git
Write-Host "📦 Step 2: Installing Git..." -ForegroundColor Yellow

# Check if Git is already installed
$gitInstalled = Get-Command git -ErrorAction SilentlyContinue
if ($gitInstalled) {
    $gitVersion = git --version 2>&1
    Write-Host "   Git is already installed: $gitVersion" -ForegroundColor Green
} else {
    Write-Host "   Downloading Git installer..." -ForegroundColor Cyan
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
    $gitInstaller = "$env:TEMP\git-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller -UseBasicParsing
        Write-Host "   ✅ Download complete" -ForegroundColor Green
        
        Write-Host "   Installing Git (this may take a few minutes)..." -ForegroundColor Cyan
        # Install Git silently with default options
        Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT", "/NORESTART" -Wait -NoNewWindow
        
        # Add Git to PATH for current session
        $gitPath = "C:\Program Files\Git\cmd"
        if (Test-Path $gitPath) {
            $env:Path += ";$gitPath"
        }
        
        # Verify installation
        Start-Sleep -Seconds 2
        $gitCheck = Get-Command git -ErrorAction SilentlyContinue
        if ($gitCheck) {
            $version = git --version 2>&1
            Write-Host "   ✅ Git installed successfully: $version" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Git installed but may need a new PowerShell window to use" -ForegroundColor Yellow
            Write-Host "   Please close and reopen PowerShell, then run: git --version" -ForegroundColor Yellow
        }
        
        # Clean up
        Remove-Item $gitInstaller -ErrorAction SilentlyContinue
    } catch {
        Write-Host "   ❌ Error downloading/installing Git: $_" -ForegroundColor Red
        Write-Host "   Please download manually from: https://git-scm.com/download/win" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 3: Configure Firewall
Write-Host "🔥 Step 3: Configuring Windows Firewall..." -ForegroundColor Yellow

try {
    # Check if rule already exists
    $existingRule = Get-NetFirewallRule -DisplayName "FPL API" -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "   ✅ Firewall rule already exists" -ForegroundColor Green
    } else {
        New-NetFirewallRule -DisplayName "FPL API" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow | Out-Null
        Write-Host "   ✅ Firewall rule created for port 8080" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Could not configure firewall: $_" -ForegroundColor Yellow
    Write-Host "   You may need to configure it manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Prerequisites installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Close and reopen PowerShell (to refresh PATH)" -ForegroundColor White
Write-Host "   2. Verify installations:" -ForegroundColor White
Write-Host "      python --version" -ForegroundColor Gray
Write-Host "      git --version" -ForegroundColor Gray
Write-Host "   3. Then run the deployment script from your Mac" -ForegroundColor White
Write-Host ""

