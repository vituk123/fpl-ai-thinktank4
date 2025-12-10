#!/usr/bin/env python3
"""
Create table using the specified PostgreSQL connection.
Uses the connection details provided by the user.
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import re
import logging
import sys

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_table():
    """Create the table using the specified connection."""
    # Extract password from DB_CONNECTION_STRING
    db_conn_str = os.getenv('DB_CONNECTION_STRING')
    if not db_conn_str:
        logger.error('DB_CONNECTION_STRING not found in .env')
        logger.info('Please set DB_CONNECTION_STRING in your .env file')
        return False

    # Extract password from connection string
    # Format: postgresql://user:password@host:port/dbname
    match = re.match(r'postgresql://[^:]+:([^@]+)@', db_conn_str)
    if not match:
        logger.error('Could not extract password from connection string')
        return False

    password = match.group(1)

    # Connection parameters (as specified by user)
    conn_params = {
        'host': 'aws-1-ap-south-1.pooler.supabase.com',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres.sdezcbesdubplacfxibc',
        'password': password,
        'connect_timeout': 60  # Longer timeout
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f'Attempt {attempt + 1}/{max_retries}: Connecting to database...')
            logger.info(f'Host: {conn_params["host"]}')
            logger.info(f'Database: {conn_params["database"]}')
            logger.info(f'User: {conn_params["user"]}')

            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            logger.info('✓ Connected successfully!')

            logger.info('Creating table fpl_news_summaries...')
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
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_news_summaries_article_id 
                ON fpl_news_summaries(article_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_news_summaries_published_date 
                ON fpl_news_summaries(published_date DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_news_summaries_relevance 
                ON fpl_news_summaries(fpl_relevance_score DESC)
            ''')

            # Verify table was created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'fpl_news_summaries'
            """)

            result = cursor.fetchone()
            if result:
                logger.info('✓ Table created and verified!')
            else:
                logger.warning('⚠ Table creation may have failed - not found in schema')

            cursor.close()
            conn.close()

            logger.info('=' * 70)
            logger.info('SUCCESS: Table fpl_news_summaries created!')
            logger.info('=' * 70)
            return True

        except psycopg2.OperationalError as e:
            if 'MaxClientsInSessionMode' in str(e) or 'timeout' in str(e).lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    logger.warning(f'Connection pooler busy. Waiting {wait_time} seconds before retry...')
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error('Connection pooler is at max capacity. Please try again later.')
                    logger.info('\nAlternative: Run the SQL manually using psql:')
                    logger.info('psql -h aws-1-ap-south-1.pooler.supabase.com -p 5432 -d postgres -U postgres.sdezcbesdubplacfxibc')
                    logger.info('Then run the SQL from create_news_table.sql')
                    return False
            else:
                logger.error(f'PostgreSQL error: {e}')
                return False
        except Exception as e:
            logger.error(f'Error: {e}', exc_info=True)
            return False

    return False


if __name__ == '__main__':
    logger.info('=' * 70)
    logger.info('Creating fpl_news_summaries table via PostgreSQL')
    logger.info('=' * 70)
    
    success = create_table()
    sys.exit(0 if success else 1)

