#!/usr/bin/env python3
"""
Create table using direct database connection (bypassing pooler).
For Supabase free tier, we'll try the direct connection endpoint.
"""
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
import re

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_direct_connection_string():
    """
    Convert pooler connection string to direct connection string.
    Supabase direct connections use db.supabase.com instead of pooler.supabase.com
    """
    conn_str = os.getenv('DB_CONNECTION_STRING')
    if not conn_str:
        logger.error('DB_CONNECTION_STRING not found in .env')
        return None
    
    # Replace pooler with direct connection
    # Format: postgresql://user:pass@pooler.supabase.com:6543/dbname
    # Direct:  postgresql://user:pass@db.supabase.com:5432/dbname
    
    # Extract components
    pattern = r'postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)'
    match = re.match(pattern, conn_str)
    
    if match:
        user, password, host, port, dbname = match.groups()
        
        # Use direct connection
        if 'pooler' in host:
            # Replace pooler with db
            direct_host = host.replace('pooler', 'db')
            # Use port 5432 for direct connection (or keep original if specified)
            direct_port = port if port and port != '6543' else '5432'
            
            direct_conn = f'postgresql://{user}:{password}@{direct_host}:{direct_port}/{dbname}'
            logger.info(f'Converted to direct connection: {direct_host}:{direct_port}')
            return direct_conn
        else:
            logger.info('Connection string already uses direct connection')
            return conn_str
    else:
        logger.warning('Could not parse connection string, using as-is')
        return conn_str


def create_table():
    """Create the table using direct connection."""
    conn_str = get_direct_connection_string()
    
    if not conn_str:
        return False
    
    try:
        logger.info('Attempting direct database connection...')
        conn = psycopg2.connect(conn_str, connect_timeout=30)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        logger.info('Creating table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fpl_news_summaries (
                id SERIAL PRIMARY KEY,
                article_id VARCHAR(255) UNIQUE NOT NULL,
                title TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                article_url TEXT NOT NULL,
                source VARCHAR(255),
                published_date TIMESTAMP,
                article_type VARCHAR(50),
                fpl_relevance_score DECIMAL(3,2) DEFAULT 0.0,
                key_points JSONB,
                player_names JSONB,
                teams JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        logger.info('Creating indexes...')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_summaries_article_id ON fpl_news_summaries(article_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_summaries_published_date ON fpl_news_summaries(published_date DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_summaries_relevance ON fpl_news_summaries(fpl_relevance_score DESC)')
        
        cursor.close()
        conn.close()
        
        logger.info('✓ Table and indexes created successfully!')
        return True
        
    except Exception as e:
        logger.error(f'Connection failed: {e}')
        logger.info('\nSince direct connection is also failing, the table will be created automatically')
        logger.info('when process_news_daily.py runs (it attempts creation if table doesn\'t exist).')
        logger.info('\nAlternatively, you can create it manually in Supabase SQL Editor:')
        logger.info('1. Go to your Supabase dashboard')
        logger.info('2. Navigate to SQL Editor')
        logger.info('3. Run the SQL from create_news_table.sql')
        return False


if __name__ == '__main__':
    logger.info('=' * 70)
    logger.info('Creating fpl_news_summaries table via direct connection')
    logger.info('=' * 70)
    
    success = create_table()
    sys.exit(0 if success else 1)

