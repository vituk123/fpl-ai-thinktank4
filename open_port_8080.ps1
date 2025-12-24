# PowerShell script to open Windows Firewall port 8080
# Run this on the ByteHosty server as Administrator

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName "FPL API Port 8080" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule already exists. Enabling it..."
    Enable-NetFirewallRule -DisplayName "FPL API Port 8080"
} else {
    Write-Host "Creating new firewall rule for port 8080..."
    New-NetFirewallRule -DisplayName "FPL API Port 8080" `
        -Direction Inbound `
        -LocalPort 8080 `
        -Protocol TCP `
        -Action Allow `
        -Profile Any
    Write-Host "Firewall rule created and enabled."
}

Write-Host "Checking rule status..."
Get-NetFirewallRule -DisplayName "FPL API Port 8080" | Select-Object DisplayName, Enabled, Direction | Format-Table

Write-Host "Done! Port 8080 should now be accessible from external networks."
