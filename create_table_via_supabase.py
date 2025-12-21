#!/usr/bin/env python3
"""
Create fpl_teams table in Supabase using direct database connection.
This script executes the SQL migration directly via psycopg2.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_table():
    """Create fpl_teams table in Supabase."""
    db_conn_str = os.getenv('DB_CONNECTION_STRING')
    if not db_conn_str:
        logger.error("DB_CONNECTION_STRING not found in environment variables")
        sys.exit(1)
    
    # Read SQL migration file
    sql_file = Path(__file__).parent / 'supabase' / 'migrations' / 'create_fpl_teams_table.sql'
    if not sql_file.exists():
        logger.error(f"SQL file not found: {sql_file}")
        sys.exit(1)
    
    sql_content = sql_file.read_text(encoding='utf-8')
    
    logger.info("Connecting to Supabase database...")
    try:
        conn = psycopg2.connect(db_conn_str)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        logger.info("Executing SQL migration...")
        cursor.execute(sql_content)
        
        logger.info("✅ Table creation SQL executed successfully!")
        
        # Verify table was created
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'fpl_teams'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            logger.info("✅ fpl_teams table verified to exist in database")
            
            # Check if table is empty
            cursor.execute("SELECT COUNT(*) FROM fpl_teams;")
            count = cursor.fetchone()[0]
            logger.info(f"📊 Current record count: {count:,}")
        else:
            logger.warning("⚠️  Table creation may have failed - table not found")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_table()

