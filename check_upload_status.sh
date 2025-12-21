#!/bin/bash
# Check the status of the team data upload to Supabase

echo "📊 Checking upload status..."

# Check if upload process is running
echo ""
echo "🔍 Checking for running upload process..."
sshpass -p '$&8$%U9F#&&%' ssh -o StrictHostKeyChecking=no Administrator@198.23.185.233 "tasklist | findstr python" 2>&1 | grep -i python || echo "No Python processes found"

echo ""
echo "💡 To check Supabase data count, run:"
echo "   SELECT COUNT(*) FROM fpl_teams;"
echo ""
echo "📝 To view upload logs, check upload_progress.log or run the upload command again"

