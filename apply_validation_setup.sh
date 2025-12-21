#!/bin/bash
# Complete validation setup script

set -e

echo "="*70
echo "VALIDATION TRACKING SETUP"
echo "="*70
echo

# Check if Supabase CLI is available
if command -v supabase &> /dev/null; then
    echo "✓ Supabase CLI found"
    
    # Check if project is linked
    if [ -f supabase/config.toml ]; then
        echo "✓ Supabase project is linked"
        echo
        echo "Applying migration via Supabase CLI..."
        supabase db push
        echo
        echo "✓ Migration applied!"
    else
        echo "⚠️  Supabase project not linked"
        echo
        echo "Linking project..."
        read -p "Enter your Supabase project ref (from dashboard URL): " PROJECT_REF
        supabase link --project-ref "$PROJECT_REF"
        echo
        echo "Applying migration..."
        supabase db push
        echo
        echo "✓ Migration applied!"
    fi
else
    echo "⚠️  Supabase CLI not found"
    echo
    echo "Please apply the migration manually:"
    echo "  1. Go to: https://supabase.com/dashboard/project/sdezcbesdubplacfxibc/sql/new"
    echo "  2. Copy SQL from: supabase/migrations/create_validation_tracking.sql"
    echo "  3. Paste and click 'Run'"
    echo
    exit 1
fi

echo
echo "="*70
echo "VERIFYING SETUP"
echo "="*70
echo

# Test the validation system
python3 src/validate_predictions.py --summary --model-version v5.0 2>&1 | head -20

echo
echo "="*70
echo "SETUP COMPLETE!"
echo "="*70
echo
echo "The validation tracking system is now active."
echo "Predictions will be automatically recorded when generated."
echo
echo "After each gameweek completes, run:"
echo "  python3 src/validate_predictions.py --gw <gameweek> --model-version v5.0"
echo

