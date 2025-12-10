"""
FPL Sentinel Main Execution Script
Fetches FPL-related news and analyzes for transfer/captaincy recommendations.
Uses NewsData.io API to replace Twitter scraper.
"""
import json
import logging
import sys
import yaml
from pathlib import Path
import pandas as pd
from fpl_api import FPLAPIClient
from sentiment_analyzer import SentimentAnalyzer

# Import NewsData client (replaces Twitter scraper)
try:
    from news_client import NewsDataClient
    NEWS_CLIENT_AVAILABLE = True
except ImportError as e:
    NEWS_CLIENT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"News client not available: {e}. Running in demo mode with sample data.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_players_data(api_client: FPLAPIClient) -> pd.DataFrame:
    """
    Load player data from FPL API.
    
    Args:
        api_client: FPL API client instance
    
    Returns:
        DataFrame with player information
    """
    try:
        bootstrap = api_client.get_bootstrap_static()
        players_df = pd.DataFrame(bootstrap['elements'])
        
        # Select required columns
        required_cols = ['id', 'web_name', 'first_name', 'second_name']
        available_cols = [col for col in required_cols if col in players_df.columns]
        players_df = players_df[available_cols].copy()
        
        logger.info(f"Loaded {len(players_df)} players from FPL API")
        return players_df
    except Exception as e:
        logger.error(f"Failed to load players data: {e}")
        raise


def load_config() -> dict:
    """Load configuration from config.yml."""
    config_path = Path(__file__).parent.parent / "config.yml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("FPL SENTINEL - News Analysis")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = load_config()
        news_config = config.get('news', {})
        api_key = news_config.get('api_key')
        
        # Initialize API client
        api_client = FPLAPIClient()
        
        # Load player data
        logger.info("Loading player data...")
        players_df = load_players_data(api_client)
        
        if players_df.empty:
            logger.error("No player data available")
            return 1
        
        # Initialize sentiment analyzer
        logger.info("Initializing sentiment analyzer...")
        analyzer = SentimentAnalyzer(players_df)
        
        if NEWS_CLIENT_AVAILABLE and api_key:
            # Initialize NewsData client
            logger.info("Initializing NewsData.io client...")
            news_client = NewsDataClient(api_key=api_key)
            
            # Fetch FPL news (last 7 days)
            logger.info("Fetching FPL-related news...")
            days_back = news_config.get('days_back', 7)
            max_results = news_config.get('max_results', 200)
            
            news_df = news_client.get_fpl_news(days_back=days_back, max_results=max_results)
            
            if news_df.empty:
                logger.warning("No news articles found. Check API key and network connection.")
                return 1
            
            logger.info(f"Fetched {len(news_df)} FPL news articles from {news_df['source'].nunique()} sources")
            
            # Convert news format to match expected format (for compatibility with sentiment analyzer)
            # The sentiment analyzer expects 'content' and 'date' columns, which we have
            articles_df = news_df.copy()
            # Rename 'source' to 'username' for compatibility
            if 'source' in articles_df.columns:
                articles_df['username'] = articles_df['source']
            
            tweets_df = articles_df  # Use same variable name for compatibility
        else:
            # Demo mode: Use sample news/articles
            logger.info("Running in DEMO MODE with sample news articles...")
            if not api_key:
                logger.warning("NewsData.io API key not found in config.yml")
            tweets_df = pd.DataFrame([
                {
                    'date': '2025-12-05',
                    'username': 'BBC Sport',
                    'content': 'Bring in Haaland this week, he\'s essential for captaincy. Sell Gabriel, he\'s injured and doubtful.'
                },
                {
                    'date': '2025-12-05',
                    'username': 'Sky Sports',
                    'content': 'Salah is a must-have. Captain him this week. Transfer out Caicedo, he\'s not performing.'
                },
                {
                    'date': '2025-12-05',
                    'username': 'The Athletic',
                    'content': 'Get Saka in your team. He\'s in great form. Drop Pope, he\'s doubtful with low chance of playing.'
                },
                {
                    'date': '2025-12-05',
                    'username': 'ESPN',
                    'content': 'Injury update: Gabriel (Arsenal) - 0% chance. Pope (Newcastle) - 25% chance. Both should be transferred out.'
                },
                {
                    'date': '2025-12-05',
                    'username': 'Guardian',
                    'content': 'Top captaincy picks: Haaland vs Sunderland, Salah vs Leeds. Both excellent options.'
                }
            ])
            logger.info(f"Using {len(tweets_df)} sample articles for demonstration")
        
        # Analyze articles (sentiment analyzer works with news articles too)
        logger.info("Analyzing news articles for recommendations...")
        analysis_results = analyzer.analyze_tweets(tweets_df)
        
        # Print JSON summary
        print("\n" + "=" * 60)
        print("FPL SENTINEL ANALYSIS RESULTS")
        print("=" * 60)
        print(json.dumps(analysis_results, indent=2))
        print("=" * 60)
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

