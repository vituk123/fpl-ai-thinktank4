#!/usr/bin/env python3
"""
Script to fetch FPL-related news from NewsData.io API
Replaces the Twitter scraper functionality.
"""
import sys
import yaml
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from news_client import NewsDataClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from config.yml."""
    config_path = Path(__file__).parent / "config.yml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def main():
    logger.info("=" * 70)
    logger.info("FPL NEWS COLLECTOR - NewsData.io API")
    logger.info("=" * 70)
    
    # Load configuration
    config = load_config()
    news_config = config.get('news', {})
    api_key = news_config.get('api_key')
    
    if not api_key:
        logger.error("NewsData.io API key not found in config.yml")
        logger.error("Please add your API key to config.yml under 'news.api_key'")
        return 1
    
    # Initialize news client
    logger.info("Initializing NewsData.io client...")
    news_client = NewsDataClient(api_key=api_key)
    
    try:
        # Fetch FPL news
        days_back = news_config.get('days_back', 7)
        max_results = news_config.get('max_results', 200)
        
        logger.info(f"Fetching FPL news from last {days_back} days...")
        news_df = news_client.get_fpl_news(days_back=days_back, max_results=max_results)
        
        if news_df.empty:
            logger.warning("No news articles were found. This could be due to:")
            logger.warning("  - Network connectivity issues")
            logger.warning("  - Invalid API key")
            logger.warning("  - No FPL-related news in the specified time period")
            return 1
        
        # Display summary
        logger.info("\n" + "=" * 70)
        logger.info("NEWS COLLECTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total articles fetched: {len(news_df)}")
        logger.info(f"Unique sources: {news_df['source'].nunique()}")
        
        if 'article_type' in news_df.columns:
            article_types = news_df['article_type'].value_counts()
            logger.info(f"\nArticle types:")
            for article_type, count in article_types.items():
                logger.info(f"  {article_type}: {count}")
        
        if 'has_images' in news_df.columns:
            articles_with_images = news_df['has_images'].sum()
            logger.info(f"\nArticles with images: {articles_with_images}")
        
        # Show sample articles
        logger.info("\n" + "=" * 70)
        logger.info("SAMPLE ARTICLES (first 5)")
        logger.info("=" * 70)
        for idx, row in news_df.head(5).iterrows():
            logger.info(f"\n[{row.get('source', 'Unknown')}] {row.get('date', 'Unknown date')}")
            title = row.get('title', '')
            if title:
                logger.info(f"Title: {title}")
            content = row.get('content', '')
            if len(content) > 200:
                content = content[:200] + "..."
            logger.info(f"{content}")
        
        # Save to CSV
        output_file = "fpl_news_articles.csv"
        news_df.to_csv(output_file, index=False)
        logger.info(f"\n✓ News articles saved to: {output_file}")
        
        # Display API usage info
        stats = news_client.get_usage_stats()
        logger.info(f"\nAPI Usage: {stats.get('note', 'N/A')}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during news collection: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())


