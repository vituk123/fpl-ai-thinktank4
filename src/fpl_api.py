"""
FPL API Client with caching and comprehensive endpoint coverage.
"""
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FPLAPIClient:
    """Client for interacting with the Fantasy Premier League API."""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    def __init__(self, cache_dir: str = ".cache", cache_ttl: int = 3600):
        """
        Initialize FPL API client.
        
        Args:
            cache_dir: Directory for caching API responses
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_ttl = cache_ttl
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Optimizer/1.0'
        })
    
    def _get_cache_path(self, endpoint: str) -> Path:
        """Get cache file path for an endpoint."""
        safe_name = endpoint.replace('/', '_').replace('?', '_').replace('&', '_')
        return self.cache_dir / f"{safe_name}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid."""
        if not cache_path.exists():
            return False
        
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.total_seconds() < self.cache_ttl
    
    def _get_cached(self, endpoint: str) -> Optional[Dict]:
        """Get cached response if valid."""
        cache_path = self._get_cache_path(endpoint)
        
        if self._is_cache_valid(cache_path):
            logger.debug(f"Cache hit: {endpoint}")
            with open(cache_path, 'r') as f:
                return json.load(f)
        
        return None
    
    def _set_cache(self, endpoint: str, data: Dict):
        """Cache API response."""
        cache_path = self._get_cache_path(endpoint)
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        logger.debug(f"Cached: {endpoint}")
    
    def _request(self, endpoint: str, use_cache: bool = True) -> Dict:
        """
        Make API request with caching.
        """
        if use_cache:
            cached = self._get_cached(endpoint)
            if cached is not None:
                return cached
        
        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"Fetching: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if use_cache:
                self._set_cache(endpoint, data)
            
            # Reduced sleep delay for performance (only for non-cached requests)
            time.sleep(0.1)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {url}: {e}")
            raise
    
    def get_bootstrap_static(self, use_cache: bool = True) -> Dict:
        """
        Get bootstrap-static data (main FPL data).
        """
        return self._request("bootstrap-static/", use_cache=use_cache)
    
    def get_entry_info(self, entry_id: int, use_cache: bool = True) -> Dict:
        """
        Get manager entry information.
        """
        return self._request(f"entry/{entry_id}/", use_cache=use_cache)
    
    def get_entry_history(self, entry_id: int, use_cache: bool = True) -> Dict:
        """
        Get manager's historical performance.
        """
        return self._request(f"entry/{entry_id}/history/", use_cache=use_cache)
    
    def get_entry_picks(self, entry_id: int, gameweek: int, use_cache: bool = True) -> Dict:
        """
        Get manager's picks for a specific gameweek.
        """
        return self._request(f"entry/{entry_id}/event/{gameweek}/picks/", use_cache=use_cache)
    
    def get_entry_transfers(self, entry_id: int, use_cache: bool = True) -> List[Dict]:
        """
        Get manager's transfer history.
        """
        return self._request(f"entry/{entry_id}/transfers/", use_cache=use_cache)
    
    def get_fixtures(self, use_cache: bool = True) -> List[Dict]:
        """
        Get all fixtures.
        """
        return self._request("fixtures/", use_cache=use_cache)
    
    def get_fixtures_for_gameweek(self, gameweek: int, use_cache: bool = True) -> List[Dict]:
        """
        Get fixtures for a specific gameweek.
        """
        all_fixtures = self.get_fixtures(use_cache=use_cache)
        return [f for f in all_fixtures if f.get('event') == gameweek]
    
    def clear_cache(self):
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("Cache cleared")
    
    def get_current_gameweek(self) -> int:
        """
        Auto-detect current/next gameweek.
        """
        data = self.get_bootstrap_static(use_cache=False)
        
        for event in data['events']:
            if not event['is_next']:
                continue
            return event['id']
        
        # Fallback if no 'is_next' found
        for event in data['events']:
            if not event['finished']:
                return event['id']
        
        return data['events'][-1]['id']

