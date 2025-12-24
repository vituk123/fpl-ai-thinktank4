# PowerShell script to open Windows Firewall port 8080
$ErrorActionPreference = "Stop"

Write-Host "Opening Windows Firewall port 8080 for FastAPI server..."

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName "FPL API Server Port 8080" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule already exists. Removing old rule..."
    Remove-NetFirewallRule -DisplayName "FPL API Server Port 8080" -ErrorAction SilentlyContinue
}

# Create new firewall rule
New-NetFirewallRule -DisplayName "FPL API Server Port 8080" `
    -Direction Inbound `
    -LocalPort 8080 `
    -Protocol TCP `
    -Action Allow `
    -Description "Allow incoming connections to FPL API Server on port 8080"

Write-Host "Firewall rule created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Verifying rule..."
Get-NetFirewallRule -DisplayName "FPL API Server Port 8080" | Select-Object DisplayName, Enabled, Direction, Action

