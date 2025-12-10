# API-Football Integration Guide

## Overview

The API-Football client has been successfully integrated into the FPL Optimizer system. This integration provides access to comprehensive football statistics, fixtures, injuries, predictions, and more from [API-Football.com](https://www.api-football.com/documentation-v3).

## Configuration

The API key has been added to `config.yml`:

```yaml
api_football:
  api_key: "08b18b2d60e1cfea7769c7276226d2d1"
  enabled: true
  cache_ttl_seconds: 3600
  premier_league_id: 39
```

## Features

The `APIFootballClient` class provides access to:

### 1. **Fixtures**
- Get fixtures by league, team, date
- Get fixture statistics and events
- Get lineups
- Get upcoming fixtures

### 2. **Players**
- Search players by name
- Get player statistics
- Get team squads
- Player performance data

### 3. **Teams**
- Get team information
- Get team statistics
- Team standings

### 4. **Injuries**
- Get current injuries
- Filter by team, player, or fixture
- Injury reasons and expected return dates

### 5. **Predictions**
- Match predictions
- Win probability
- Score predictions

### 6. **Standings**
- League tables
- Team positions
- Points, goals, form

### 7. **Transfers**
- Transfer information
- Filter by team or player

## Usage Example

```python
from src.api_football_client import APIFootballClient
import yaml

# Load config
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize client
api_key = config['api_football']['api_key']
client = APIFootballClient(api_key=api_key)

# Get Premier League teams
teams = client.get_teams(season=2024)
for team in teams:
    print(f"{team['team']['name']} (ID: {team['team']['id']})")

# Get upcoming fixtures
fixtures = client.get_fixtures(season=2024, next_n=5)
for fixture in fixtures:
    home = fixture['teams']['home']['name']
    away = fixture['teams']['away']['name']
    date = fixture['fixture']['date']
    print(f"{home} vs {away} on {date}")

# Get injuries
injuries = client.get_injuries()
for injury in injuries:
    player = injury['player']['name']
    team = injury['team']['name']
    reason = injury['player']['reason']
    print(f"{player} ({team}): {reason}")

# Get player statistics
players = client.get_player(name="Haaland", season=2024)
if players:
    player = players[0]
    stats = player.get('statistics', [])
    # Access detailed statistics
```

## Integration with FPL System

The API-Football client can enhance the FPL system in several ways:

### 1. **Enhanced Injury Tracking**
Replace or supplement FPL's basic injury status with detailed injury information:
- Injury reasons
- Expected return dates
- Injury severity

### 2. **Expected Lineups**
Get predicted lineups before matches to help with team selection.

### 3. **Advanced Statistics**
Access detailed player statistics not available in FPL API:
- xG (Expected Goals)
- xA (Expected Assists)
- Pass accuracy
- Dribbles, tackles, interceptions
- Heat maps and positioning data

### 4. **Match Predictions**
Use match predictions to inform captaincy and transfer decisions.

### 5. **Fixture Analysis**
Get more detailed fixture information:
- Head-to-head records
- Recent form
- Home/away performance

## API Rate Limits

The client includes:
- **Caching**: Responses are cached to reduce API calls
- **Rate limiting**: Built-in delays between requests
- **Error handling**: Graceful handling of API errors

**Note**: The API key may be on a free tier with limited requests per day. Check your API-Football dashboard for:
- Daily request limits
- Available endpoints
- Plan restrictions

## API Plan Restrictions

If you see "plan" errors, it means:
1. Your API key may be on a free tier
2. Certain endpoints may require a paid plan
3. Some features may be rate-limited

**Free Tier Limitations** (typical):
- Limited requests per day (e.g., 100 requests/day)
- Some endpoints may be restricted
- No access to certain premium features

**To Upgrade**:
1. Visit [API-Football.com](https://www.api-football.com/pricing)
2. Choose a plan that fits your needs
3. Update your API key in `config.yml`

## Testing

Run the test script to verify the integration:

```bash
python3 test_api_football.py
```

This will test:
- Team retrieval
- Fixture retrieval
- Injury information
- Standings
- Player search

## Next Steps

1. **Verify API Key**: Ensure your API key is active and has the necessary permissions
2. **Check Plan Limits**: Review your API-Football plan to understand available endpoints
3. **Integrate Features**: Add API-Football data to existing FPL analysis modules:
   - Enhance `fixture_analyzer.py` with detailed fixture stats
   - Improve `statistical_models.py` with xG/xA data
   - Update `live_tracker.py` with real-time match events
4. **Create Mappings**: Build mappings between FPL player/team IDs and API-Football IDs

## Documentation

- **API-Football Docs**: https://www.api-football.com/documentation-v3
- **Client Code**: `src/api_football_client.py`
- **Test Script**: `test_api_football.py`

## Support

For API-Football issues:
- Check API status: https://www.api-football.com/status
- Review documentation: https://www.api-football.com/documentation-v3
- Contact API-Football support for plan/access issues

