#!/usr/bin/env python3
"""
Test script for API-Football integration
"""
import sys
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_football_client import APIFootballClient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yml"""
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)

def main():
    """Test API-Football client"""
    logger.info("=" * 70)
    logger.info("API-FOOTBALL CLIENT TEST")
    logger.info("=" * 70)
    
    # Load config
    config = load_config()
    api_football_config = config.get('api_football', {})
    api_key = api_football_config.get('api_key')
    
    if not api_key:
        logger.error("API key not found in config.yml")
        return 1
    
    # Initialize client with rate limits from config
    requests_per_minute = api_football_config.get('requests_per_minute', 10)
    requests_per_day = api_football_config.get('requests_per_day', 100)
    
    client = APIFootballClient(
        api_key=api_key,
        requests_per_minute=requests_per_minute,
        requests_per_day=requests_per_day
    )
    
    # Show usage stats
    logger.info("\n📊 Current API Usage:")
    logger.info("-" * 70)
    stats = client.get_usage_stats()
    logger.info(f"Daily: {stats['daily_used']}/{stats['daily_limit']} ({stats['daily_remaining']} remaining)")
    logger.info(f"Per-minute: {stats['minute_used']}/{stats['minute_limit']} ({stats['minute_remaining']} remaining)")
    logger.info("")
    
    try:
        # Test 1: Get Premier League teams (2024 season)
        logger.info("\n1. Testing: Get Premier League Teams (2024 season)")
        logger.info("-" * 70)
        teams = client.get_teams(season=2024)
        logger.info(f"Found {len(teams)} teams")
        if teams:
            for team in teams[:5]:  # Show first 5
                team_info = team.get('team', {})
                logger.info(f"  - {team_info.get('name')} (ID: {team_info.get('id')})")
        else:
            logger.warning("  No teams found - API may have rate limits or plan restrictions")
        
        # Test 2: Get upcoming fixtures (2024 season)
        logger.info("\n2. Testing: Get Upcoming Fixtures (next 5, 2024 season)")
        logger.info("-" * 70)
        fixtures = client.get_fixtures(season=2024, next_n=5)
        logger.info(f"Found {len(fixtures)} fixtures")
        for fixture in fixtures[:5]:
            home = fixture.get('teams', {}).get('home', {}).get('name', 'Unknown')
            away = fixture.get('teams', {}).get('away', {}).get('name', 'Unknown')
            date = fixture.get('fixture', {}).get('date', 'Unknown')
            logger.info(f"  - {home} vs {away} on {date}")
        
        # Test 3: Get injuries
        logger.info("\n3. Testing: Get Current Injuries")
        logger.info("-" * 70)
        injuries = client.get_injuries()
        logger.info(f"Found {len(injuries)} injuries")
        for injury in injuries[:5]:  # Show first 5
            player = injury.get('player', {}).get('name', 'Unknown')
            team = injury.get('team', {}).get('name', 'Unknown')
            reason = injury.get('player', {}).get('reason', 'Unknown')
            logger.info(f"  - {player} ({team}): {reason}")
        
        # Test 4: Get standings (2024 season)
        logger.info("\n4. Testing: Get Premier League Standings (2024 season)")
        logger.info("-" * 70)
        standings = client.get_standings(season=2024)
        if standings:
            league_standings = standings[0].get('league', {}).get('standings', [])
            if league_standings:
                logger.info(f"Top 5 teams:")
                for team_standing in league_standings[:5]:
                    team_info = team_standing[0].get('team', {})
                    points = team_standing[0].get('points', 0)
                    position = team_standing[0].get('rank', 0)
                    logger.info(f"  {position}. {team_info.get('name')} - {points} pts")
        
        # Test 5: Get player statistics (example: search for a player)
        logger.info("\n5. Testing: Search for Player (Haaland, 2024 season)")
        logger.info("-" * 70)
        players = client.get_player(name="Haaland", season=2024)
        if players:
            for player in players[:3]:  # Show first 3 matches
                player_info = player.get('player', {})
                team = player.get('statistics', [{}])[0].get('team', {}).get('name', 'Unknown') if player.get('statistics') else 'Unknown'
                logger.info(f"  - {player_info.get('name')} ({team}) - ID: {player_info.get('id')}")
        else:
            logger.info("  No players found")
        
        # Show final usage stats
        logger.info("\n📊 Final API Usage:")
        logger.info("-" * 70)
        stats = client.get_usage_stats()
        logger.info(f"Daily: {stats['daily_used']}/{stats['daily_limit']} ({stats['daily_remaining']} remaining)")
        logger.info(f"Per-minute: {stats['minute_used']}/{stats['minute_limit']} ({stats['minute_remaining']} remaining)")
        
        if stats['daily_remaining'] < 20:
            logger.warning(f"⚠️  Low on daily requests! Only {stats['daily_remaining']} remaining.")
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ All tests completed successfully!")
        logger.info("=" * 70)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error testing API-Football client: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())

