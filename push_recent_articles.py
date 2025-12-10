#!/usr/bin/env python3
"""
Push the 10 most recent FPL news articles to Supabase (without AI summarization).
"""
import sys
from pathlib import Path
import yaml
import logging
from datetime import datetime
import hashlib

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from news_client import NewsDataClient
from database import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_article_id(article: dict) -> str:
    """Generate unique article ID from article data."""
    # Use article_id from NewsData.io if available
    if article.get('article_id'):
        return str(article['article_id'])
    
    # Otherwise generate from URL and title
    url = article.get('link') or article.get('url', '')
    title = article.get('title', '')
    combined = f"{url}{title}"
    return hashlib.md5(combined.encode('utf-8')).hexdigest()


def create_raw_articles_table(db_manager: DatabaseManager) -> bool:
    """Create table for raw news articles if it doesn't exist."""
    try:
        with db_manager.engine.connect() as conn:
            with conn.begin():
                conn.execute(db_manager.engine.dialect.do_execute(
                    conn,
                    """
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
                    """
                ))
                conn.execute(db_manager.engine.dialect.do_execute(
                    conn,
                    "CREATE INDEX IF NOT EXISTS idx_news_articles_article_id ON fpl_news_articles(article_id)"
                ))
                conn.execute(db_manager.engine.dialect.do_execute(
                    conn,
                    "CREATE INDEX IF NOT EXISTS idx_news_articles_published_date ON fpl_news_articles(published_date DESC)"
                ))
                logger.info("Raw news articles table created/verified")
                return True
    except Exception as e:
        logger.error(f"Error creating raw news articles table: {e}")
        # Try using Supabase REST API as fallback
        try:
            # Use raw SQL via Supabase
            result = db_manager.supabase_client.rpc('exec_sql', {
                'query': """
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
                    );
                    CREATE INDEX IF NOT EXISTS idx_news_articles_article_id ON fpl_news_articles(article_id);
                    CREATE INDEX IF NOT EXISTS idx_news_articles_published_date ON fpl_news_articles(published_date DESC);
                """
            })
            logger.info("Raw news articles table created via Supabase RPC")
            return True
        except Exception as e2:
            logger.warning(f"Could not create table via RPC either: {e2}")
            return False


def save_raw_article(db_manager: DatabaseManager, article: dict) -> bool:
    """Save a raw article to Supabase."""
    try:
        article_id = generate_article_id(article)
        
        # Parse published date
        published_date = None
        pub_date_str = article.get('pubDate') or article.get('published_date')
        if pub_date_str:
            try:
                # Try ISO format
                published_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            except:
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            published_date = datetime.strptime(pub_date_str, fmt)
                            break
                        except:
                            continue
                except:
                    published_date = datetime.now()
        
        article_data = {
            'article_id': article_id,
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'content': article.get('content', ''),
            'article_url': article.get('link') or article.get('url', ''),
            'source': article.get('source_name', article.get('source', 'Unknown')),
            'source_id': article.get('source_id', ''),
            'published_date': published_date.isoformat() if published_date else None,
            'image_url': article.get('image_url', ''),
            'category': article.get('category', []),
            'language': article.get('language', 'en'),
            'country': article.get('country', ''),
            'updated_at': datetime.now().isoformat()
        }
        
        # Use upsert to handle duplicates
        result = db_manager._execute_with_retry(
            db_manager.supabase_client.table('fpl_news_articles').upsert(
                article_data,
                on_conflict='article_id'
            )
        )
        
        logger.debug(f"Saved article: {article_data['title'][:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Error saving article '{article.get('title', 'N/A')[:50]}...': {e}")
        return False


def main():
    logger.info("=" * 70)
    logger.info("PUSH RECENT ARTICLES TO SUPABASE")
    logger.info("=" * 70)
    
    # Load configuration
    config_path = Path('config.yml')
    if not config_path.exists():
        logger.error("config.yml not found")
        return 1
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # News configuration
    news_config = config.get('news', {})
    news_api_key = news_config.get('api_key')
    
    if not news_api_key:
        logger.error("NewsData.io API key not found in config.yml")
        return 1
    
    # Initialize clients
    logger.info("Initializing clients...")
    news_client = NewsDataClient(api_key=news_api_key)
    db_manager = DatabaseManager()
    
    # Create table if needed
    logger.info("Ensuring database table exists...")
    create_raw_articles_table(db_manager)
    
    # Fetch recent news
    logger.info("\nFetching FPL news articles...")
    news_df = news_client.get_fpl_news(days_back=7, max_results=50)
    
    if news_df.empty:
        logger.warning("No news articles found")
        return 1
    
    logger.info(f"Found {len(news_df)} articles")
    
    # Sort by published date (most recent first) and take top 10
    if 'published_date' in news_df.columns:
        news_df['published_date'] = pd.to_datetime(news_df['published_date'], errors='coerce')
        news_df = news_df.sort_values('published_date', ascending=False)
    
    top_10 = news_df.head(10)
    logger.info(f"\nSelecting 10 most recent articles...")
    
    # Check for existing articles
    try:
        existing_result = db_manager._execute_with_retry(
            db_manager.supabase_client.table('fpl_news_articles').select('article_id')
        )
        existing_ids = {item['article_id'] for item in existing_result.data} if existing_result.data else set()
        logger.info(f"Found {len(existing_ids)} existing articles in database")
    except Exception as e:
        logger.warning(f"Could not check existing articles: {e}")
        existing_ids = set()
    
    # Save articles
    logger.info("\nSaving articles to Supabase...")
    saved_count = 0
    skipped_count = 0
    
    for idx, row in top_10.iterrows():
        article = row.to_dict()
        article_id = generate_article_id(article)
        
        if article_id in existing_ids:
            logger.debug(f"Skipping duplicate: {article.get('title', 'N/A')[:50]}...")
            skipped_count += 1
            continue
        
        if save_raw_article(db_manager, article):
            saved_count += 1
            logger.info(f"  [{saved_count}/10] {article.get('title', 'N/A')[:60]}...")
        else:
            logger.warning(f"  Failed to save: {article.get('title', 'N/A')[:50]}...")
    
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Articles fetched: {len(news_df)}")
    logger.info(f"Articles saved: {saved_count}")
    logger.info(f"Articles skipped (duplicates): {skipped_count}")
    logger.info("=" * 70)
    
    return 0


if __name__ == '__main__':
    import pandas as pd
    sys.exit(main())

