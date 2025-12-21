#!/usr/bin/env python3
"""
Apply validation tracking migration using direct PostgreSQL connection
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
import re

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_direct_connection_string():
    """Convert pooler connection string to direct connection string."""
    conn_str = os.getenv('DB_CONNECTION_STRING')
    if not conn_str:
        logger.error('DB_CONNECTION_STRING not found in environment')
        return None
    
    # Replace pooler with direct connection
    # Format: postgresql://user:pass@pooler.supabase.com:6543/dbname
    # Direct:  postgresql://user:pass@db.supabase.com:5432/dbname
    
    pattern = r'postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)'
    match = re.match(pattern, conn_str)
    
    if match:
        user, password, host, port, dbname = match.groups()
        
        if 'pooler' in host:
            direct_host = host.replace('pooler', 'db')
            direct_port = port if port and port != '6543' else '5432'
            direct_conn = f'postgresql://{user}:{password}@{direct_host}:{direct_port}/{dbname}'
            logger.info(f'Using direct connection: {direct_host}:{direct_port}')
            return direct_conn
        else:
            logger.info('Using connection string as-is')
            return conn_str
    else:
        logger.warning('Could not parse connection string, using as-is')
        return conn_str


def apply_migration():
    """Apply the validation tracking migration."""
    print("="*70)
    print("APPLYING VALIDATION TRACKING MIGRATION")
    print("="*70)
    print()
    
    conn_str = get_direct_connection_string()
    if not conn_str:
        print("❌ Could not get database connection string")
        print("   Please set DB_CONNECTION_STRING in your environment")
        print("   Or apply migration manually via Supabase Dashboard")
        return False
    
    # Read migration SQL
    migration_path = Path('supabase/migrations/create_validation_tracking.sql')
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(conn_str)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("Executing migration SQL...")
        print()
        
        # Execute the migration
        cur.execute(migration_sql)
        
        print("✓ Migration applied successfully!")
        print()
        
        # Verify table was created
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'validation_tracking'
            );
        """)
        exists = cur.fetchone()[0]
        
        if exists:
            print("✓ Table 'validation_tracking' verified")
            
            # Check columns
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'validation_tracking'
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            print(f"   Columns: {len(columns)}")
            print()
        else:
            print("⚠️  Table creation may have failed")
        
        cur.close()
        conn.close()
        
        print("="*70)
        print("MIGRATION COMPLETE!")
        print("="*70)
        print()
        print("You can now test the validation system:")
        print("  python3 src/validate_predictions.py --summary --model-version v5.0")
        print()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection error: {e}")
        print()
        print("This might be because:")
        print("  1. Direct database connections are disabled in Supabase")
        print("  2. Connection string is incorrect")
        print("  3. IP address is not whitelisted")
        print()
        print("Please apply the migration manually via Supabase Dashboard:")
        print("  1. Go to: https://supabase.com/dashboard")
        print("  2. Select your project → SQL Editor")
        print("  3. Copy SQL from: supabase/migrations/create_validation_tracking.sql")
        print("  4. Paste and run")
        return False
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)

