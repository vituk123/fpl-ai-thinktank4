"""
NewsData.io Client for FPL News Collection
Replaces Twitter scraper with news API for FPL-related news articles.
Documentation: https://newsdata.io/documentation
"""
import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import time
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class NewsDataClient:
    """
    Client for fetching FPL-related news from NewsData.io API.
    """
    
    BASE_URL = "https://newsdata.io/api/1"
    
    # FPL-related keywords for news search
    FPL_KEYWORDS = [
        "Fantasy Premier League",
        "FPL",
        "Premier League",
        "Premier League football",
        "EPL",
        "English Premier League",
        "Fantasy football",
        "FPL tips",
        "FPL transfers",
        "FPL captain",
        "FPL team",
        "FPL gameweek",
        "FPL wildcard",
        "FPL free hit"
    ]
    
    # Premier League team names for better filtering
    PREMIER_LEAGUE_TEAMS = [
        "Arsenal", "Manchester City", "Manchester United", "Liverpool", 
        "Chelsea", "Tottenham", "Newcastle", "Brighton", "Aston Villa",
        "West Ham", "Crystal Palace", "Brentford", "Fulham", "Wolves",
        "Everton", "Nottingham Forest", "Bournemouth", "Burnley",
        "Sheffield United", "Luton Town"
    ]
    
    def __init__(self, api_key: str, cache_dir: str = ".cache", cache_ttl: int = 3600):
        """
        Initialize NewsData.io client.
        
        Args:
            api_key: NewsData.io API key
            cache_dir: Directory for caching responses
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir) / "news"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Optimizer/1.0'
        })
        
        logger.info("NewsData.io client initialized")
    
    def _get_cache_path(self, query: str) -> Path:
        """Get cache file path for a query."""
        # Use hash to avoid filename length issues
        import hashlib
        hash_obj = hashlib.md5(query.encode())
        hash_hex = hash_obj.hexdigest()
        return self.cache_dir / f"{hash_hex}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid."""
        if not cache_path.exists():
            return False
        
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.total_seconds() < self.cache_ttl
    
    def _get_cached(self, query: str) -> Optional[Dict]:
        """Get cached response if valid."""
        cache_path = self._get_cache_path(query)
        
        if self._is_cache_valid(cache_path):
            logger.debug(f"Cache hit: {query}")
            with open(cache_path, 'r') as f:
                return json.load(f)
        
        return None
    
    def _set_cache(self, query: str, data: Dict):
        """Cache API response."""
        cache_path = self._get_cache_path(query)
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        logger.debug(f"Cached: {query}")
    
    def _request(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Dict:
        """
        Make API request with caching and error handling.
        
        Args:
            endpoint: API endpoint (e.g., 'news')
            params: Query parameters
            use_cache: Whether to use cache
            
        Returns:
            API response data
        """
        if params is None:
            params = {}
        
        # Add API key as query parameter (NewsData.io format)
        params['apikey'] = self.api_key
        
        # Create cache key from endpoint and params
        cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"Fetching NewsData.io: {endpoint} with params {params.get('q', 'N/A')}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if data.get('status') == 'error':
                error_results = data.get('results', {})
                if isinstance(error_results, dict):
                    error_msg = error_results.get('message', data.get('message', 'Unknown error'))
                    error_code = error_results.get('code', 'Unknown')
                else:
                    error_msg = data.get('message', 'Unknown error')
                    error_code = 'Unknown'
                
                logger.error(f"NewsData.io API error ({error_code}): {error_msg}")
                
                # Provide helpful message for common errors
                if '401' in str(response.status_code) or 'Unauthorized' in error_msg:
                    logger.error("API key may be invalid. Please verify your API key at https://newsdata.io/register")
                
                return {'status': 'error', 'results': [], 'totalResults': 0}
            
            if use_cache:
                self._set_cache(cache_key, data)
            
            # Rate limiting - free tier allows 200 requests/day
            time.sleep(0.5)  # Small delay between requests
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsData.io request failed for {url}: {e}")
            return {'status': 'error', 'results': [], 'totalResults': 0}
    
    def search_news(self, query: str, language: str = "en", 
                   country: str = "gb", category: str = None,
                   days_back: int = 7, max_results: int = 100) -> List[Dict]:
        """
        Search for news articles.
        
        Args:
            query: Search query
            language: Language code (default: "en")
            country: Country code (default: "gb" for UK)
            category: News category (optional, free tier may not support all categories)
            days_back: Number of days to look back (filtered client-side for free tier)
            max_results: Maximum number of results to return
            
        Returns:
            List of news article dictionaries
        """
        # Free tier has limited parameters - use minimal set
        params = {
            'q': query,
            'language': language,
            'country': country,
        }
        
        # Only add category if provided (free tier may have restrictions)
        if category:
            params['category'] = category
        
        # Note: Free tier may not support date filtering via API
        # We'll filter by date client-side after fetching
        
        all_results = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Free tier may not support pagination, so try without page parameter first
        response = self._request('news', params=params)
        
        if response.get('status') == 'error':
            error_msg = response.get('message', 'Unknown error')
            logger.warning(f"API error: {error_msg}")
            return []
        
        results = response.get('results', [])
        
        # Filter by date client-side (free tier may not support date params)
        filtered_results = []
        for article in results:
            pub_date_str = article.get('pubDate', '')
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    # Convert to naive datetime for comparison
                    pub_date_naive = pub_date.replace(tzinfo=None)
                    if pub_date_naive >= cutoff_date:
                        filtered_results.append(article)
                except:
                    # If date parsing fails, include the article
                    filtered_results.append(article)
            else:
                # If no date, include it (better to have it than miss it)
                filtered_results.append(article)
        
        all_results.extend(filtered_results)
        
        # Try pagination if nextPage is available and we haven't reached max_results
        # Note: Free tier may not support pagination
        if len(all_results) < max_results:
            next_page = response.get('nextPage')
            if next_page:
                # Try to get next page (may fail for free tier)
                try:
                    params_with_page = params.copy()
                    params_with_page['page'] = next_page
                    next_response = self._request('news', params=params_with_page, use_cache=False)
                    
                    if next_response.get('status') != 'error':
                        next_results = next_response.get('results', [])
                        # Filter by date
                        for article in next_results:
                            pub_date_str = article.get('pubDate', '')
                            if pub_date_str:
                                try:
                                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                                    pub_date_naive = pub_date.replace(tzinfo=None)
                                    if pub_date_naive >= cutoff_date:
                                        filtered_results.append(article)
                                except:
                                    filtered_results.append(article)
                            else:
                                filtered_results.append(article)
                except:
                    logger.debug("Pagination not supported or failed (free tier limitation)")
        
        return filtered_results[:max_results]
    
    def get_fpl_news(self, days_back: int = 7, max_results: int = 200) -> pd.DataFrame:
        """
        Get FPL-related news articles.
        
        Args:
            days_back: Number of days to look back
            max_results: Maximum number of results
            
        Returns:
            DataFrame with news articles
        """
        all_articles = []
        
        # Search with main FPL keywords
        logger.info(f"Searching for FPL news from last {days_back} days...")
        
        # Use simpler queries (free tier may not support complex OR queries)
        queries = [
            "Fantasy Premier League",
            "FPL",
            "Premier League"
        ]
        
        for query in queries:
            articles = self.search_news(
                query=query,
                category=None,  # Don't use category filter for free tier
                days_back=days_back,
                max_results=max_results // len(queries)  # Split max_results across queries
            )
            all_articles.extend(articles)
        
        logger.info(f"Found {len(articles)} articles")
        all_articles.extend(articles)
        
        # Remove duplicates based on article_id or link
        seen_ids = set()
        unique_articles = []
        for article in all_articles:
            article_id = article.get('article_id') or article.get('link', '')
            if article_id and article_id not in seen_ids:
                seen_ids.add(article_id)
                unique_articles.append(article)
        
        # Convert to DataFrame
        if not unique_articles:
            return pd.DataFrame()
        
        df = pd.DataFrame(unique_articles)
        
        # Add standardized columns similar to Twitter scraper output
        df['source'] = df.get('source_id', 'Unknown')
        df['date'] = pd.to_datetime(df.get('pubDate', ''), errors='coerce')
        df['content'] = df.get('description', '') + ' ' + df.get('content', '')
        df['title'] = df.get('title', '')
        df['url'] = df.get('link', '')
        df['has_images'] = df.get('image_url', '').notna()
        
        # Categorize articles
        df['article_type'] = df.apply(self._categorize_article, axis=1)
        
        # Select relevant columns
        columns_to_keep = [
            'title', 'content', 'source', 'date', 'url', 
            'article_type', 'has_images', 'image_url', 'category'
        ]
        available_columns = [col for col in columns_to_keep if col in df.columns]
        df = df[available_columns].copy()
        
        # Sort by date (newest first)
        if 'date' in df.columns:
            df = df.sort_values('date', ascending=False).reset_index(drop=True)
        
        logger.info(f"Processed {len(df)} unique FPL news articles")
        
        return df
    
    def _categorize_article(self, row: pd.Series) -> str:
        """
        Categorize article based on content.
        
        Args:
            row: DataFrame row with article data
            
        Returns:
            Article category string
        """
        title = str(row.get('title', '')).lower()
        content = str(row.get('content', '')).lower()
        text = title + ' ' + content
        
        # Injury-related
        if any(word in text for word in ['injury', 'injured', 'doubt', 'fitness', 'knock', 'hamstring', 'knee']):
            return 'injury'
        
        # Transfer-related
        if any(word in text for word in ['transfer', 'signing', 'deal', 'move', 'loan']):
            return 'transfer'
        
        # Captain-related
        if any(word in text for word in ['captain', 'captaincy', 'armband']):
            return 'captain'
        
        # Team news / lineup
        if any(word in text for word in ['lineup', 'line-up', 'team news', 'starting xi', 'squad']):
            return 'lineup'
        
        # Price changes
        if any(word in text for word in ['price', 'rise', 'fall', 'cost']):
            return 'price_change'
        
        # Gameweek / fixture
        if any(word in text for word in ['gameweek', 'game week', 'gw', 'fixture', 'match']):
            return 'fixture'
        
        # Chip-related
        if any(word in text for word in ['wildcard', 'free hit', 'triple captain', 'bench boost', 'chip']):
            return 'chip'
        
        # General tips
        if any(word in text for word in ['tip', 'advice', 'recommend', 'pick', 'selection']):
            return 'tips'
        
        return 'general'
    
    def get_usage_stats(self) -> Dict:
        """
        Get API usage statistics (if available from response headers).
        
        Returns:
            Dictionary with usage stats
        """
        # NewsData.io free tier: 200 requests/day
        # This is a placeholder - actual usage tracking would need to be implemented
        return {
            'daily_limit': 200,
            'note': 'Free tier allows 200 requests per day'
        }

