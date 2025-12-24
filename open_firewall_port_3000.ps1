# PowerShell script to open Windows Firewall port 3000
$ErrorActionPreference = "Stop"

Write-Host "Opening Windows Firewall port 3000 for frontend web server..."

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName "FPL Frontend Server Port 3000" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule already exists. Removing old rule..."
    Remove-NetFirewallRule -DisplayName "FPL Frontend Server Port 3000" -ErrorAction SilentlyContinue
}

# Create new firewall rule
New-NetFirewallRule -DisplayName "FPL Frontend Server Port 3000" `
    -Direction Inbound `
    -LocalPort 3000 `
    -Protocol TCP `
    -Action Allow `
    -Description "Allow incoming connections to FPL Frontend Web Server on port 3000"

Write-Host "Firewall rule created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Verifying rule..."
Get-NetFirewallRule -DisplayName "FPL Frontend Server Port 3000" | Select-Object DisplayName, Enabled, Direction, Action

