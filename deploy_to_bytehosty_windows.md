# ByteHosty Windows Server Deployment Guide

## Server Status
- **IP**: 198.23.185.233
- **OS**: Windows Server (detected via RDP port 3389)
- **SSH**: Not available (port 22 not accessible)
- **RDP**: Available (port 3389)

## Deployment Options

### Option 1: Enable OpenSSH Server on Windows (Recommended)

1. **Connect via RDP**:
   - Use Remote Desktop Connection
   - Server: `198.23.185.233`
   - User: `Administrator`
   - Password: `$&8$%U9F#&&%`

2. **Install OpenSSH Server**:
   ```powershell
   # Run PowerShell as Administrator
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Start-Service sshd
   Set-Service -Name sshd -StartupType 'Automatic'
   ```

3. **Configure Firewall**:
   ```powershell
   New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
   ```

4. **Then run the deployment script**:
   ```bash
   ./deploy_to_bytehosty.sh
   ```

### Option 2: Manual Deployment via RDP

1. **Connect via RDP** to the server

2. **Install Python 3.11**:
   - Download from https://www.python.org/downloads/
   - Install with "Add Python to PATH" checked

3. **Install Git**:
   - Download from https://git-scm.com/download/win

4. **Clone Repository**:
   ```cmd
   cd C:\
   git clone https://github.com/vituk123/fpl-ai-thinktank4.git
   cd fpl-ai-thinktank4
   ```

5. **Create Virtual Environment**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

6. **Create .env File**:
   Create `C:\fpl-ai-thinktank4\.env` with:
   ```
   SUPABASE_URL=https://sdezcbesdubplacfxibc.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   DB_CONNECTION_STRING=postgresql://user:password@host:port/database
   API_FOOTBALL_KEY=08b18b2d60e1cfea7769c7276226d2d1
   NEWS_API_KEY=pub_a13e0ce062804c5891decaa7ac8a27b9
   PYTHON_VERSION=3.11
   PORT=8080
   ```

7. **Create Windows Service** (using NSSM - Non-Sucking Service Manager):
   ```cmd
   # Download NSSM from https://nssm.cc/download
   # Extract and run:
   nssm install FPL-API "C:\fpl-ai-thinktank4\venv\Scripts\python.exe" "C:\fpl-ai-thinktank4\venv\Scripts\uvicorn.exe src.dashboard_api:app --host 0.0.0.0 --port 8080"
   nssm set FPL-API AppDirectory "C:\fpl-ai-thinktank4"
   nssm set FPL-API AppEnvironmentExtra "SUPABASE_URL=..." "SUPABASE_KEY=..." "DB_CONNECTION_STRING=..."
   nssm start FPL-API
   ```

### Option 3: Use PowerShell Remoting (WinRM)

If WinRM is enabled, we can use PowerShell remoting:

```powershell
# On your local machine (if WinRM is configured)
$cred = Get-Credential
Enter-PSSession -ComputerName 198.23.185.233 -Credential $cred
```

## Recommended: Enable SSH First

The easiest approach is to enable OpenSSH Server on Windows, then use the automated deployment script.

## Testing After Deployment

```bash
# Test health endpoint
curl http://198.23.185.233:8080/api/v1/health

# Test gameweek endpoint
curl http://198.23.185.233:8080/api/v1/gameweek/current
```

## Firewall Configuration

Make sure Windows Firewall allows port 8080:

```powershell
New-NetFirewallRule -DisplayName "FPL API" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

