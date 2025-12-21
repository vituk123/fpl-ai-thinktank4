#!/usr/bin/env python3
"""
Apply validation tracking migration to Supabase
This script attempts to apply the migration via Supabase REST API
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager
import requests
import os

def apply_migration_via_rpc():
    """Try to apply migration via Supabase RPC call"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("⚠️  Supabase credentials not found")
        return False
    
    # Read migration SQL
    with open('supabase/migrations/create_validation_tracking.sql', 'r') as f:
        migration_sql = f.read()
    
    # Supabase doesn't support direct SQL execution via REST API
    # We need to use the dashboard or CLI
    print("="*70)
    print("MIGRATION APPLICATION")
    print("="*70)
    print()
    print("Supabase REST API doesn't support raw SQL execution.")
    print("Please apply the migration using one of these methods:")
    print()
    print("METHOD 1: Supabase Dashboard (Recommended)")
    print("  1. Go to: https://supabase.com/dashboard")
    print("  2. Select your project")
    print("  3. Navigate to: SQL Editor")
    print("  4. Click 'New Query'")
    print("  5. Copy and paste the SQL below:")
    print()
    print("-"*70)
    print(migration_sql)
    print("-"*70)
    print()
    print("  6. Click 'Run'")
    print()
    print("METHOD 2: Supabase CLI")
    print("  supabase db push")
    print()
    return False

if __name__ == "__main__":
    apply_migration_via_rpc()

