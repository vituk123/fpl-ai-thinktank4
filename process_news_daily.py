#!/usr/bin/env python3
"""
Daily News Processing Script
Fetches FPL news, summarizes with AI, and saves to Supabase.
Designed to run daily via cron job at midnight.
"""
import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from news_client import NewsDataClient
from database import DatabaseManager
from ai_summarizer import AISummarizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/news_processing.log'),
        logging.StreamHandler()
    ]
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
    """Main execution function."""
    logger.info("=" * 70)
    logger.info(f"DAILY NEWS PROCESSING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    try:
        # Load configuration
        config = load_config()
        
        # News configuration
        news_config = config.get('news', {})
        news_api_key = news_config.get('api_key')
        days_back = news_config.get('days_back', 1)  # Default to 1 day for daily processing
        max_results = news_config.get('max_results', 100)
        
        # Edge Function configuration
        edge_function_config = config.get('supabase_edge_function', {})
        function_name = edge_function_config.get('function_name', 'summarize-news')
        
        # Validate configuration
        if not news_api_key:
            logger.error("NewsData.io API key not found in config.yml")
            return 1
        
        # Initialize clients
        logger.info("Initializing clients...")
        news_client = NewsDataClient(api_key=news_api_key)
        db_manager = DatabaseManager()
        
        # AI summarizer uses Supabase Edge Function (no external API keys needed)
        ai_summarizer = AISummarizer(
            supabase_client=db_manager.supabase_client,
            function_name=function_name
        )
        
        # Ensure news summaries table exists
        logger.info("Ensuring database table exists...")
        db_manager.create_news_summaries_table()
        
        # Import and initialize processor
        from news_processor import NewsProcessor
        processor = NewsProcessor(news_client, db_manager, ai_summarizer)
        
        # Process news
        logger.info(f"Processing news from last {days_back} day(s)...")
        stats = processor.fetch_and_summarize_news(
            days_back=days_back,
            max_results=max_results
        )
        
        # Check for errors
        if stats.get('errors'):
            logger.warning(f"Processing completed with {len(stats['errors'])} errors")
            for error in stats['errors'][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        else:
            logger.info("Processing completed successfully")
        
        logger.info("=" * 70)
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error in daily processing: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    sys.exit(main())

