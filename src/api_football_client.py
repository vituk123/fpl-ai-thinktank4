"""
API-Football Client - Integration with API-Football.com v3
Provides detailed football statistics, fixtures, injuries, and predictions.
Documentation: https://www.api-football.com/documentation-v3
"""
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from collections import deque

logger = logging.getLogger(__name__)


class APIFootballClient:
    """Client for interacting with API-Football.com v3 API."""
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    # Premier League ID in API-Football
    PREMIER_LEAGUE_ID = 39
    
    def __init__(self, api_key: str, cache_dir: str = ".cache", cache_ttl: int = 3600,
                 requests_per_minute: int = 10, requests_per_day: int = 100):
        """
        Initialize API-Football client.
        
        Args:
            api_key: API key from api-football.com
            cache_dir: Directory for caching API responses
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            requests_per_minute: Rate limit for requests per minute (default: 10)
            requests_per_day: Rate limit for requests per day (default: 100)
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir) / "api_football"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        self.session = requests.Session()
        self.session.headers.update({
            'x-apisports-key': self.api_key,
            'User-Agent': 'FPL-Optimizer/1.0'
        })
        
        # Rate limiting
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        self.request_times = deque()  # Track request times for per-minute limit
        self.daily_request_count = 0
        self.daily_reset_date = datetime.now().date()
        self._load_daily_count()  # Load saved daily count
        
        # Calculate delay between requests (60 seconds / requests_per_minute)
        self.rate_limit_delay = max(6.0, 60.0 / requests_per_minute)  # At least 6 seconds between requests
    
    def _get_cache_path(self, endpoint: str, params: Dict = None) -> Path:
        """Get cache file path for an endpoint."""
        safe_name = endpoint.replace('/', '_').replace('?', '_').replace('&', '_')
        if params:
            param_str = '_'.join(f"{k}_{v}" for k, v in sorted(params.items()))
            safe_name = f"{safe_name}_{param_str}"
        return self.cache_dir / f"{safe_name}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid."""
        if not cache_path.exists():
            return False
        
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.total_seconds() < self.cache_ttl
    
    def _get_cached(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Get cached response if valid."""
        cache_path = self._get_cache_path(endpoint, params)
        
        if self._is_cache_valid(cache_path):
            logger.debug(f"Cache hit: {endpoint} (saved API request)")
            with open(cache_path, 'r') as f:
                return json.load(f)
        
        return None
    
    def _load_daily_count(self):
        """Load daily request count from file."""
        count_file = self.cache_dir / "daily_count.json"
        if count_file.exists():
            try:
                with open(count_file, 'r') as f:
                    data = json.load(f)
                    saved_date = datetime.fromisoformat(data['date']).date()
                    if saved_date == datetime.now().date():
                        self.daily_request_count = data.get('count', 0)
                        self.daily_reset_date = saved_date
                        logger.info(f"Loaded daily request count: {self.daily_request_count}/{self.requests_per_day}")
                    else:
                        # Reset if it's a new day
                        self.daily_request_count = 0
                        self.daily_reset_date = datetime.now().date()
            except:
                self.daily_request_count = 0
                self.daily_reset_date = datetime.now().date()
        else:
            self.daily_request_count = 0
            self.daily_reset_date = datetime.now().date()
    
    def _save_daily_count(self):
        """Save daily request count to file."""
        count_file = self.cache_dir / "daily_count.json"
        data = {
            'date': self.daily_reset_date.isoformat(),
            'count': self.daily_request_count
        }
        with open(count_file, 'w') as f:
            json.dump(data, f)
    
    def _check_rate_limits(self) -> bool:
        """
        Check if we can make a request based on rate limits.
        Returns True if request can be made, False otherwise.
        """
        now = datetime.now()
        
        # Check daily limit
        if now.date() != self.daily_reset_date:
            # New day, reset counter
            self.daily_request_count = 0
            self.daily_reset_date = now.date()
            logger.info("Daily request count reset")
        
        if self.daily_request_count >= self.requests_per_day:
            logger.warning(f"Daily request limit reached ({self.requests_per_day}/{self.requests_per_day}). "
                         f"Resets at midnight.")
            return False
        
        # Check per-minute limit
        # Remove requests older than 1 minute
        while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
            self.request_times.popleft()
        
        if len(self.request_times) >= self.requests_per_minute:
            # Need to wait
            oldest_request = self.request_times[0]
            wait_time = 60 - (now - oldest_request).total_seconds() + 1  # Add 1 second buffer
            if wait_time > 0:
                logger.warning(f"Rate limit: {len(self.request_times)}/{self.requests_per_minute} requests in last minute. "
                            f"Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                # Clean up old requests after waiting
                now = datetime.now()
                while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
                    self.request_times.popleft()
        
        return True
    
    def _record_request(self):
        """Record that a request was made."""
        now = datetime.now()
        self.request_times.append(now)
        self.daily_request_count += 1
        self._save_daily_count()
        
        # Log usage
        remaining_daily = self.requests_per_day - self.daily_request_count
        remaining_minute = self.requests_per_minute - len(self.request_times)
        
        if remaining_daily <= 10:
            logger.warning(f"⚠️  Daily requests: {self.daily_request_count}/{self.requests_per_day} "
                         f"({remaining_daily} remaining)")
        elif self.daily_request_count % 10 == 0:
            logger.info(f"API-Football requests: {self.daily_request_count}/{self.requests_per_day} "
                       f"({remaining_daily} remaining)")
        
        if remaining_minute <= 2:
            logger.warning(f"⚠️  Per-minute requests: {len(self.request_times)}/{self.requests_per_minute} "
                         f"({remaining_minute} remaining)")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics."""
        now = datetime.now()
        
        # Clean up old per-minute requests
        while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
            self.request_times.popleft()
        
        return {
            'daily_used': self.daily_request_count,
            'daily_limit': self.requests_per_day,
            'daily_remaining': self.requests_per_day - self.daily_request_count,
            'minute_used': len(self.request_times),
            'minute_limit': self.requests_per_minute,
            'minute_remaining': self.requests_per_minute - len(self.request_times),
            'reset_date': self.daily_reset_date.isoformat()
        }
    
    def _set_cache(self, endpoint: str, data: Dict, params: Dict = None):
        """Cache API response."""
        cache_path = self._get_cache_path(endpoint, params)
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        logger.debug(f"Cached: {endpoint}")
    
    def _request(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Dict:
        """
        Make API request with caching, rate limiting, and error handling.
        
        Args:
            endpoint: API endpoint (e.g., 'fixtures', 'players', 'injuries')
            params: Query parameters
            use_cache: Whether to use cache
            
        Returns:
            API response data
        """
        # Always check cache first to avoid API calls
        if use_cache:
            cached = self._get_cached(endpoint, params)
            if cached is not None:
                return cached
        
        # Check rate limits before making request
        if not self._check_rate_limits():
            raise Exception(f"Rate limit exceeded. Daily: {self.daily_request_count}/{self.requests_per_day}, "
                          f"Per-minute: {len(self.request_times)}/{self.requests_per_minute}")
        
        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"Fetching API-Football: {endpoint} with params {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Record the request
            self._record_request()
            
            # Check for API errors
            if data.get('errors'):
                error_msg = ', '.join(data['errors'])
                logger.warning(f"API-Football returned errors: {error_msg}")
            
            # Check rate limit from response headers (if available)
            if response.headers.get('x-ratelimit-requests-remaining'):
                remaining = int(response.headers['x-ratelimit-requests-remaining'])
                if remaining < 10:
                    logger.warning(f"API-Football rate limit low: {remaining} requests remaining")
            
            if use_cache:
                self._set_cache(endpoint, data, params)
            
            # Rate limiting delay (already handled by _check_rate_limits, but add small buffer)
            time.sleep(0.5)  # Small buffer between requests
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API-Football request failed for {url}: {e}")
            raise
    
    # ==================== FIXTURES ====================
    
    def get_fixtures(self, league_id: int = None, season: int = None, 
                     date: str = None, team_id: int = None, 
                     next_n: int = None, use_cache: bool = True) -> List[Dict]:
        """
        Get fixtures.
        
        Args:
            league_id: League ID (default: Premier League 39)
            season: Season year (e.g., 2024)
            date: Date in YYYY-MM-DD format
            team_id: Filter by team ID
            next_n: Get next N fixtures
            use_cache: Whether to use cache
            
        Returns:
            List of fixture dictionaries
        """
        params = {}
        if league_id:
            params['league'] = league_id
        else:
            params['league'] = self.PREMIER_LEAGUE_ID
        
        if season:
            params['season'] = season
        if date:
            params['date'] = date
        if team_id:
            params['team'] = team_id
        if next_n:
            params['next'] = next_n
        
        response = self._request('fixtures', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    def get_fixture_by_id(self, fixture_id: int, use_cache: bool = True) -> Optional[Dict]:
        """Get specific fixture by ID."""
        params = {'id': fixture_id}
        response = self._request('fixtures', params=params, use_cache=use_cache)
        fixtures = response.get('response', [])
        return fixtures[0] if fixtures else None
    
    def get_fixture_statistics(self, fixture_id: int, use_cache: bool = True) -> Dict:
        """Get detailed statistics for a fixture."""
        params = {'fixture': fixture_id}
        response = self._request('fixtures/statistics', params=params, use_cache=use_cache)
        return response.get('response', {})
    
    def get_fixture_events(self, fixture_id: int, use_cache: bool = True) -> List[Dict]:
        """Get match events (goals, cards, substitutions) for a fixture."""
        params = {'fixture': fixture_id}
        response = self._request('fixtures/events', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    def get_fixture_lineups(self, fixture_id: int, use_cache: bool = True) -> List[Dict]:
        """Get lineups for a fixture."""
        params = {'fixture': fixture_id}
        response = self._request('fixtures/lineups', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    # ==================== PLAYERS ====================
    
    def get_player(self, player_id: int = None, name: str = None, 
                   team_id: int = None, season: int = None, 
                   use_cache: bool = True) -> List[Dict]:
        """
        Get player information.
        
        Args:
            player_id: Player ID in API-Football
            name: Player name (search)
            team_id: Filter by team
            season: Season year
            use_cache: Whether to use cache
            
        Returns:
            List of player dictionaries
        """
        params = {}
        if player_id:
            params['id'] = player_id
        if name:
            params['search'] = name
        if team_id:
            params['team'] = team_id
        if season:
            params['season'] = season
        else:
            # Default to current season (2024-25 season)
            # API-Football uses the year the season starts
            current_year = datetime.now().year
            current_month = datetime.now().month
            # Premier League season typically starts in August
            if current_month >= 8:
                params['season'] = current_year
            else:
                params['season'] = current_year - 1
        
        if not params.get('league'):
            params['league'] = self.PREMIER_LEAGUE_ID
        
        response = self._request('players', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    def get_player_statistics(self, player_id: int, season: int = None, 
                             use_cache: bool = True) -> List[Dict]:
        """Get detailed player statistics."""
        params = {'id': player_id}
        if season:
            params['season'] = season
        else:
            # Default to current season
            current_year = datetime.now().year
            current_month = datetime.now().month
            if current_month >= 8:
                params['season'] = current_year
            else:
                params['season'] = current_year - 1
        params['league'] = self.PREMIER_LEAGUE_ID
        
        response = self._request('players', params=params, use_cache=use_cache)
        players = response.get('response', [])
        if players:
            return players[0].get('statistics', [])
        return []
    
    def get_player_squads(self, team_id: int, season: int = None, 
                         use_cache: bool = True) -> List[Dict]:
        """Get team squad/players."""
        params = {'team': team_id}
        if season:
            params['season'] = season
        else:
            # Default to current season
            current_year = datetime.now().year
            current_month = datetime.now().month
            if current_month >= 8:
                params['season'] = current_year
            else:
                params['season'] = current_year - 1
        
        response = self._request('players/squads', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    # ==================== TEAMS ====================
    
    def get_teams(self, team_id: int = None, league_id: int = None, 
                  season: int = None, use_cache: bool = True) -> List[Dict]:
        """Get team information."""
        params = {}
        if team_id:
            params['id'] = team_id
        if league_id:
            params['league'] = league_id
        else:
            params['league'] = self.PREMIER_LEAGUE_ID
        if season:
            params['season'] = season
        else:
            # Default to current season
            current_year = datetime.now().year
            current_month = datetime.now().month
            if current_month >= 8:
                params['season'] = current_year
            else:
                params['season'] = current_year - 1
        
        response = self._request('teams', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    def get_team_statistics(self, team_id: int, season: int = None, 
                           use_cache: bool = True) -> Dict:
        """Get team statistics."""
        params = {'team': team_id, 'league': self.PREMIER_LEAGUE_ID}
        if season:
            params['season'] = season
        else:
            # Default to current season
            current_year = datetime.now().year
            current_month = datetime.now().month
            if current_month >= 8:
                params['season'] = current_year
            else:
                params['season'] = current_year - 1
        
        response = self._request('teams/statistics', params=params, use_cache=use_cache)
        return response.get('response', {})
    
    # ==================== INJURIES ====================
    
    def get_injuries(self, fixture_id: int = None, team_id: int = None, 
                    player_id: int = None, date: str = None,
                    use_cache: bool = True) -> List[Dict]:
        """
        Get injury information.
        
        Args:
            fixture_id: Filter by fixture
            team_id: Filter by team
            player_id: Filter by player
            date: Date in YYYY-MM-DD format
            use_cache: Whether to use cache
            
        Returns:
            List of injury dictionaries
        """
        params = {}
        if fixture_id:
            params['fixture'] = fixture_id
        if team_id:
            params['team'] = team_id
        if player_id:
            params['player'] = player_id
        if date:
            params['date'] = date
        
        response = self._request('injuries', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    # ==================== PREDICTIONS ====================
    
    def get_predictions(self, fixture_id: int = None, use_cache: bool = True) -> List[Dict]:
        """Get match predictions."""
        params = {}
        if fixture_id:
            params['fixture'] = fixture_id
        
        response = self._request('predictions', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    # ==================== STANDINGS ====================
    
    def get_standings(self, league_id: int = None, season: int = None,
                     use_cache: bool = True) -> List[Dict]:
        """Get league standings."""
        params = {}
        if league_id:
            params['league'] = league_id
        else:
            params['league'] = self.PREMIER_LEAGUE_ID
        if season:
            params['season'] = season
        else:
            # Default to current season
            current_year = datetime.now().year
            current_month = datetime.now().month
            if current_month >= 8:
                params['season'] = current_year
            else:
                params['season'] = current_year - 1
        
        response = self._request('standings', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    # ==================== TRANSFERS ====================
    
    def get_transfers(self, team_id: int = None, player_id: int = None,
                     use_cache: bool = True) -> List[Dict]:
        """Get transfer information."""
        params = {}
        if team_id:
            params['team'] = team_id
        if player_id:
            params['player'] = player_id
        
        response = self._request('transfers', params=params, use_cache=use_cache)
        return response.get('response', [])
    
    # ==================== UTILITY METHODS ====================
    
    def map_fpl_team_to_api_football(self, fpl_team_id: int) -> Optional[int]:
        """
        Map FPL team ID to API-Football team ID.
        This is a basic mapping - may need to be enhanced with actual mapping data.
        """
        # Basic mapping (you may need to enhance this with actual data)
        # FPL team IDs: 1=Arsenal, 2=Aston Villa, 3=Bournemouth, etc.
        # API-Football uses different IDs, so we'd need to query and map them
        # For now, return None and let the caller handle it
        logger.warning("Team ID mapping not implemented - need to query teams endpoint")
        return None
    
    def get_team_id_by_name(self, team_name: str, use_cache: bool = True) -> Optional[int]:
        """Get API-Football team ID by team name."""
        teams = self.get_teams(use_cache=use_cache)
        for team in teams:
            if team_name.lower() in team.get('team', {}).get('name', '').lower():
                return team.get('team', {}).get('id')
        return None
    
    def clear_cache(self):
        """Clear all cached API responses."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("API-Football cache cleared")

