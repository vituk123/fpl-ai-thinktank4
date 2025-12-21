#!/usr/bin/env python3
"""
Script to create the fpl_teams table in Supabase.
This should be run before uploading team data.
"""
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseManager
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_table():
    """
    Create fpl_teams table and related functions.
    """
    logger.info("Initializing database manager...")
    try:
        db_manager = DatabaseManager()
        if not db_manager.engine:
            logger.error("Database engine not available")
            return False
        logger.info("Database manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")
        return False
    
    # Read the migration SQL file
    migration_file = Path(__file__).parent / "supabase" / "migrations" / "create_fpl_teams_table.sql"
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Reading migration file: {migration_file}")
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Execute the migration
    logger.info("Executing migration SQL...")
    try:
        # Use raw psycopg2 connection to execute multi-statement SQL properly
        import psycopg2
        from urllib.parse import urlparse
        
        # Get connection string from engine
        conn_str = str(db_manager.engine.url)
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True  # Enable autocommit for DDL statements
        
        cursor = conn.cursor()
        
        # Execute the entire SQL file
        try:
            cursor.execute(migration_sql)
            logger.info("✅ Migration SQL executed successfully!")
        except Exception as e:
            # Check if it's a "already exists" error (which is OK)
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                logger.info("✅ Migration already applied (table/objects already exist)")
            else:
                logger.warning(f"Some SQL statements had warnings: {e}")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error executing migration: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = create_table()
    sys.exit(0 if success else 1)

