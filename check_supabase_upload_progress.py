#!/usr/bin/env python3
"""
Check the progress of FPL teams data upload to Supabase.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

def get_supabase_client() -> Client:
    """Initialize and return Supabase client."""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    try:
        options = ClientOptions(post_timeout=60)
        client = create_client(supabase_url, supabase_key, options=options)
    except:
        client = create_client(supabase_url, supabase_key)
    
    return client

def check_upload_progress():
    """Check how many records are in the fpl_teams table."""
    try:
        client = get_supabase_client()
        
        print("🔍 Checking Supabase upload progress...")
        print("")
        
        # Get total count
        response = client.table('fpl_teams').select('team_id', count='exact').execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f"✅ Total records in fpl_teams table: {total_count:,}")
        print("")
        
        # Estimate progress (assuming ~10M total records)
        estimated_total = 10_000_000
        if total_count > 0:
            progress_pct = min((total_count / estimated_total) * 100, 100)
            print(f"📊 Estimated progress: {progress_pct:.2f}%")
            print(f"   (Assuming ~{estimated_total:,} total records)")
            print("")
        
        # Get sample records
        sample = client.table('fpl_teams').select('*').limit(5).execute()
        if sample.data:
            print("📝 Sample records:")
            for record in sample.data[:3]:
                print(f"   - Team ID: {record.get('team_id')}, Team: {record.get('team_name')}, Manager: {record.get('manager_name')}")
            print("")
        
        if total_count == 0:
            print("⚠️  No records found. Upload may not have started yet.")
        elif total_count < 1000:
            print("⏳ Upload just started or is in early stages...")
        elif total_count < 1_000_000:
            print("⏳ Upload in progress...")
        else:
            print("✅ Upload appears to be well underway!")
            
    except Exception as e:
        error_msg = str(e)
        if "Could not find the table" in error_msg or "PGRST205" in error_msg:
            print("❌ Error: fpl_teams table does not exist in Supabase")
            print("")
            print("You need to create the table first by running the SQL migration:")
            print("  File: supabase/migrations/create_fpl_teams_table.sql")
            print("")
            print("Options:")
            print("  1. Run SQL in Supabase SQL Editor (Dashboard > SQL Editor)")
            print("  2. Or use: supabase db push (if using Supabase CLI)")
        else:
            print(f"❌ Error checking upload progress: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_upload_progress()

