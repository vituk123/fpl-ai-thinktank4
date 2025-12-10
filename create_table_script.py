#!/usr/bin/env python3
"""
Script to create the fpl_news_summaries table via database connection.
"""
import sys
from pathlib import Path
import logging
import time

sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseManager
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_table_with_retries(db_manager: DatabaseManager, max_retries: int = 5):
    """
    Create table with retry logic.
    """
    sql_statements = [
        """
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
        """,
        "CREATE INDEX IF NOT EXISTS idx_news_summaries_article_id ON fpl_news_summaries(article_id)",
        "CREATE INDEX IF NOT EXISTS idx_news_summaries_published_date ON fpl_news_summaries(published_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_news_summaries_relevance ON fpl_news_summaries(fpl_relevance_score DESC)"
    ]
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Connecting to database...")
            
            # Dispose any existing connections
            db_manager.engine.dispose()
            time.sleep(2)  # Wait before retry
            
            with db_manager.engine.connect() as conn:
                with conn.begin():
                    logger.info("Executing CREATE TABLE statement...")
                    conn.execute(text(sql_statements[0]))
                    
                    logger.info("Creating indexes...")
                    for idx_sql in sql_statements[1:]:
                        conn.execute(text(idx_sql))
                    
                    logger.info("✓ Table and indexes created successfully!")
                    return True
                    
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")
                return False
    
    return False


def main():
    logger.info("=" * 70)
    logger.info("Creating fpl_news_summaries table")
    logger.info("=" * 70)
    
    try:
        db_manager = DatabaseManager()
        
        # Try to create table with retries
        success = create_table_with_retries(db_manager, max_retries=5)
        
        if success:
            logger.info("=" * 70)
            logger.info("✓ SUCCESS: Table created!")
            logger.info("=" * 70)
            
            # Verify table exists by trying to query it
            try:
                logger.info("Verifying table exists...")
                result = db_manager.supabase_client.table('fpl_news_summaries').select('id').limit(1).execute()
                logger.info("✓ Table verified via Supabase REST API")
                return 0
            except Exception as e:
                logger.warning(f"Could not verify via REST API (this is okay): {e}")
                logger.info("Table should still be created - verification is optional")
                return 0
        else:
            logger.error("=" * 70)
            logger.error("✗ FAILED: Could not create table after multiple attempts")
            logger.error("=" * 70)
            logger.info("\nAlternative: Create table manually in Supabase SQL Editor:")
            logger.info("Run the SQL from: create_news_table.sql")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

