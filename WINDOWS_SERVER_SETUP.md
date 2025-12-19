# Windows Server Setup Guide - Step by Step

## Prerequisites to Install

Before deploying, you need to install:
1. **Python 3.11**
2. **Git**

---

## Step 1: Install Python 3.11

### Option A: Via RDP (Recommended)

1. **Connect via RDP** to `198.23.185.233` (you already know how)

2. **Open a web browser** on the Windows server (Internet Explorer or Edge)

3. **Download Python 3.11**:
   - Go to: https://www.python.org/downloads/release/python-3110/
   - Scroll down to "Files"
   - Click on: **Windows installer (64-bit)** (the .exe file)

4. **Run the installer**:
   - Double-click the downloaded file
   - ✅ **IMPORTANT**: Check the box "Add Python 3.11 to PATH"
   - Click "Install Now"
   - Wait for installation to complete
   - Click "Close"

5. **Verify installation**:
   - Open PowerShell (not as admin is fine)
   - Type: `python --version`
   - You should see: `Python 3.11.x`

### Option B: Via SSH (Command Line)

If you prefer command line, connect via SSH and run:

```powershell
# Download Python installer
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe" -OutFile "$env:TEMP\python-installer.exe"

# Install Python (silent install with PATH)
Start-Process -FilePath "$env:TEMP\python-installer.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait

# Verify
python --version
```

---

## Step 2: Install Git

### Option A: Via RDP (Recommended)

1. **Open a web browser** on the Windows server

2. **Download Git**:
   - Go to: https://git-scm.com/download/win
   - Click "Download for Windows"
   - The download should start automatically

3. **Run the installer**:
   - Double-click the downloaded file
   - Click "Next" through all the prompts (defaults are fine)
   - Click "Install"
   - Wait for installation
   - Click "Finish"

4. **Verify installation**:
   - Open a NEW PowerShell window (close and reopen)
   - Type: `git --version`
   - You should see: `git version 2.x.x`

### Option B: Via SSH (Command Line)

```powershell
# Download Git installer
Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe" -OutFile "$env:TEMP\git-installer.exe"

# Install Git (silent install)
Start-Process -FilePath "$env:TEMP\git-installer.exe" -ArgumentList "/SILENT" -Wait

# Add Git to PATH for current session
$env:Path += ";C:\Program Files\Git\cmd"

# Verify
git --version
```

---

## Step 3: Configure Windows Firewall

Allow port 8080 for the API:

1. **Open PowerShell as Administrator** (right-click → Run as administrator)

2. **Run this command**:
   ```powershell
   New-NetFirewallRule -DisplayName "FPL API" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
   ```

---

## Step 4: Deploy the Application

Once Python and Git are installed, you can deploy using one of these methods:

### Method 1: Automated Script (After Python/Git installed)

Run from your Mac:
```bash
./deploy_to_bytehosty_windows_simple.sh
```

### Method 2: Manual Deployment via RDP

1. **Connect via RDP**

2. **Open PowerShell**

3. **Clone the repository**:
   ```powershell
   cd C:\
   git clone https://github.com/vituk123/fpl-ai-thinktank4.git
   cd fpl-ai-thinktank4
   ```

4. **Create virtual environment**:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

5. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

6. **Create .env file**:
   Create a file `C:\fpl-ai-thinktank4\.env` with:
   ```
   SUPABASE_URL=https://sdezcbesdubplacfxibc.supabase.co
   SUPABASE_KEY=your-supabase-anon-key-here
   DB_CONNECTION_STRING=postgresql://user:password@host:port/database
   API_FOOTBALL_KEY=08b18b2d60e1cfea7769c7276226d2d1
   NEWS_API_KEY=pub_a13e0ce062804c5891decaa7ac8a27b9
   PYTHON_VERSION=3.11
   PORT=8080
   ```

7. **Start the server**:
   ```powershell
   python -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port 8080
   ```

---

## Step 5: Test the Deployment

From your Mac terminal:
```bash
curl http://198.23.185.233:8080/api/v1/health
```

You should get a JSON response.

---

## Quick Checklist

- [ ] Python 3.11 installed and in PATH
- [ ] Git installed
- [ ] Firewall rule for port 8080 created
- [ ] Application deployed
- [ ] .env file created with correct values
- [ ] Server started and responding

---

## Troubleshooting

**"python is not recognized"**
- Python is not in PATH
- Reinstall Python and make sure "Add to PATH" is checked
- Or restart PowerShell after installation

**"git is not recognized"**
- Git is not in PATH
- Reinstall Git
- Or restart PowerShell after installation

**Port 8080 not accessible**
- Check Windows Firewall rule is created
- Verify the server is running: `netstat -an | findstr 8080`

**Connection refused**
- Make sure the server is running
- Check firewall settings
- Verify the port in the .env file matches

