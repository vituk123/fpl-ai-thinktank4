#!/bin/bash
# Setup script for validation tracking system

echo "="*70
echo "SETTING UP VALIDATION TRACKING SYSTEM"
echo "="*70
echo

# Check if Supabase CLI is available
if ! command -v supabase &> /dev/null; then
    echo "⚠️  Supabase CLI not found. Please install it or apply the migration manually."
    echo "   Migration file: supabase/migrations/create_validation_tracking.sql"
    echo
    echo "To apply manually:"
    echo "1. Go to your Supabase dashboard"
    echo "2. Navigate to SQL Editor"
    echo "3. Copy and paste the contents of supabase/migrations/create_validation_tracking.sql"
    echo "4. Run the migration"
    echo
else
    echo "Applying database migration..."
    supabase db push
    echo "✓ Migration applied"
    echo
fi

echo "Validation tracking system is ready!"
echo
echo "Usage:"
echo "  Validate a gameweek: python3 src/validate_predictions.py --gw 17"
echo "  View summary: python3 src/validate_predictions.py --summary"
echo "  Validate all: python3 src/validate_predictions.py --all"
echo

