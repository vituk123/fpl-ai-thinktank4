#!/usr/bin/env python3
"""
Standalone script to upload FPL teams CSV data to Supabase fpl_teams table.
This version only requires supabase-py and python-dotenv (no pandas dependency).
"""
import os
import sys
import csv
import logging
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def read_csv_file(csv_path: str) -> List[Dict]:
    """
    Read the CSV file and return list of records.
    """
    records = []
    logger.info(f"Reading CSV file: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        row_count = 0
        for row in reader:
            row_count += 1
            # Map CSV columns to database columns
            # CSV has: id, team_name, manager_name, region, overall_points, overall_rank
            # Database needs: team_id, team_name, manager_name
            if row.get('id') and row.get('team_name') and row.get('manager_name'):
                records.append({
                    'team_id': int(row['id']),
                    'team_name': row['team_name'].strip(),
                    'manager_name': row['manager_name'].strip()
                })
            
            # Log progress every 100k rows
            if row_count % 100000 == 0:
                logger.info(f"Processed {row_count} rows, {len(records)} valid records so far...")
    
    logger.info(f"Finished reading CSV: {row_count} total rows, {len(records)} valid records")
    return records


def upload_to_supabase(client: Client, records: List[Dict], batch_size: int = 500):
    """
    Upload records to Supabase fpl_teams table using upsert.
    """
    total_records = len(records)
    logger.info(f"Uploading {total_records} records to fpl_teams table (batch size: {batch_size})")
    
    # Process in batches to avoid overwhelming the API
    uploaded = 0
    failed = 0
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size
        
        try:
            # Use upsert to handle duplicates (on team_id)
            response = client.table('fpl_teams').upsert(
                batch,
                on_conflict='team_id'
            ).execute()
            
            uploaded += len(batch)
            logger.info(f"Batch {batch_num}/{total_batches}: Uploaded {len(batch)} records (Total: {uploaded}/{total_records} - {uploaded*100//total_records}%)")
            
        except Exception as e:
            logger.error(f"Error uploading batch {batch_num}/{total_batches}: {e}")
            failed += len(batch)
            # Continue with next batch
    
    logger.info(f"Upload complete: {uploaded} successful, {failed} failed")
    return failed == 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload FPL teams CSV to Supabase database")
    parser.add_argument(
        "--csv",
        type=str,
        default="fpl_teams_full.csv",
        help="Path to CSV file (default: fpl_teams_full.csv)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of records per batch (default: 500)"
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Initialize Supabase client
    logger.info("Initializing Supabase client...")
    try:
        client = get_supabase_client()
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        logger.error("Make sure SUPABASE_URL and SUPABASE_KEY are set in environment variables")
        sys.exit(1)
    
    # Read CSV file
    logger.info(f"Reading CSV file: {csv_path}")
    try:
        records = read_csv_file(str(csv_path))
        logger.info(f"Read {len(records)} records from CSV")
        if not records:
            logger.warning("No valid records found in CSV file")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    # Upload to database
    logger.info("Starting database upload...")
    success = upload_to_supabase(client, records, batch_size=args.batch_size)
    
    if success:
        logger.info("✅ Upload completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Upload completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()

