#!/bin/bash
# Upload FPL teams CSV from ByteHosty server to Supabase

SERVER_IP="198.23.185.233"
SERVER_USER="Administrator"
SERVER_PASSWORD='$&8$%U9F#&&%'

echo "🚀 Uploading FPL teams data from server to Supabase..."

sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "${SERVER_USER}@${SERVER_IP}" "powershell -Command \"
    cd C:\\fpl-api;
    
    # Determine Python command
    \$pythonCmd = if (Test-Path 'venv\\Scripts\\python.exe') { 
        Write-Host 'Using venv Python';
        'venv\\Scripts\\python.exe' 
    } else { 
        Write-Host 'Using system Python';
        'py' 
    };
    
    Write-Host '';
    Write-Host 'Starting upload to Supabase...';
    Write-Host 'CSV file: fpl_teams_full.csv';
    Write-Host 'Batch size: 500 records';
    Write-Host '';
    
    # Run upload script with proper escaping
    & \$pythonCmd upload_fpl_teams_to_db.py --csv fpl_teams_full.csv --batch-size 500;
    
    Write-Host '';
    Write-Host 'Upload script completed.';
\"" 2>&1

echo ""
echo "✅ Upload command sent to server"
echo "💡 Check server output above for upload progress"

