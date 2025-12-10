#!/usr/bin/env python3
"""
Create fpl_news_articles table using transactional pooler connection (port 6543).
This bypasses the session mode pooler timeout issues.
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def get_transactional_connection_string():
    """Get connection string for transactional pooler (port 6543)."""
    db_connection_string = os.getenv('DB_CONNECTION_STRING')
    if not db_connection_string:
        raise ValueError("DB_CONNECTION_STRING not found in .env")
    
    # Replace port 5432 with 6543 (transactional pooler)
    if ':5432/' in db_connection_string:
        transactional_string = db_connection_string.replace(':5432/', ':6543/')
    elif ':5432' in db_connection_string and '/?' not in db_connection_string:
        # Handle case where port is at end
        transactional_string = db_connection_string.replace(':5432', ':6543')
    else:
        # Try to extract components and rebuild
        # Format: postgresql://user:pass@host:port/dbname
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_connection_string)
        if match:
            user, password, host, port, dbname = match.groups()
            transactional_string = f"postgresql://{user}:{password}@{host}:6543/{dbname}"
        else:
            logger.warning("Could not parse connection string, using as-is")
            transactional_string = db_connection_string
    
    logger.info(f"Using transactional pooler connection (port 6543)")
    return transactional_string

def create_table():
    """Create fpl_news_articles table using transactional pooler."""
    try:
        conn_string = get_transactional_connection_string()
        
        logger.info("Connecting to database via transactional pooler...")
        conn = psycopg2.connect(conn_string, connect_timeout=10)
        conn.autocommit = False  # Use transactions
        
        cursor = conn.cursor()
        
        # Create table
        logger.info("Creating fpl_news_articles table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fpl_news_articles (
                id SERIAL PRIMARY KEY,
                article_id VARCHAR(255) UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                content TEXT,
                article_url TEXT NOT NULL,
                source VARCHAR(255),
                source_id VARCHAR(255),
                published_date TIMESTAMP,
                image_url TEXT,
                category JSONB,
                language VARCHAR(10) DEFAULT 'en',
                country VARCHAR(10),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes
        logger.info("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_articles_article_id 
            ON fpl_news_articles(article_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_articles_published_date 
            ON fpl_news_articles(published_date DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_articles_source 
            ON fpl_news_articles(source)
        """)
        
        # Commit transaction
        conn.commit()
        
        logger.info("✓ Table and indexes created successfully!")
        
        # Verify table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'fpl_news_articles'
            )
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            logger.info("✓ Table verified in database")
            
            # Get column count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'fpl_news_articles'
            """)
            col_count = cursor.fetchone()[0]
            logger.info(f"✓ Table has {col_count} columns")
        else:
            logger.warning("⚠ Table creation may have failed - not found in schema")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        logger.error(f"Connection error: {e}")
        logger.error("Make sure:")
        logger.error("1. Database is accessible")
        logger.error("2. Connection string is correct")
        logger.error("3. Transactional pooler (port 6543) is enabled")
        return False
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("CREATE FPL_NEWS_ARTICLES TABLE (Transactional Pooler)")
    logger.info("=" * 70)
    
    success = create_table()
    
    if success:
        logger.info("")
        logger.info("=" * 70)
        logger.info("SUCCESS! Table created. You can now run:")
        logger.info("  python3 push_recent_articles.py")
        logger.info("=" * 70)
        sys.exit(0)
    else:
        logger.error("")
        logger.error("=" * 70)
        logger.error("FAILED! Please check the errors above.")
        logger.error("=" * 70)
        sys.exit(1)

