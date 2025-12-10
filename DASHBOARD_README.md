# Advanced Visualization Dashboard

## Overview

The Advanced Visualization Dashboard provides comprehensive analytics and visualization data for FPL teams through a REST API. It includes 15 different analytics covering both team-specific and league-wide metrics.

## Features

### Team-Specific Analytics (8 visualizations)
1. **Performance Heatmap** - Player points by gameweek with color coding
2. **Value Tracker** - Team value growth vs league average
3. **Transfer History Analysis** - Success rate of past transfers
4. **Position Balance Chart** - Investment distribution across positions
5. **Chip Usage Timeline** - Chip usage vs optimal timing
6. **Captain Performance** - Captain choices and their returns
7. **Rank Progression** - Overall and mini-league rank over time
8. **Points vs Budget Efficiency** - Value analysis of squad players

### League-Wide Analytics (7 visualizations)
1. **Ownership vs Points Correlation** - Identify differential picks
2. **Template Team Tracker** - Most common squad from top managers
3. **Price Change Predictors** - Players likely to rise/fall in price
4. **Position-wise Points Distribution** - Box plots by position
5. **Fixture Difficulty Swing Analysis** - Teams with easiest/hardest runs
6. **Double Gameweek Probability** - Historical DGW patterns
7. **Top Performers by Price Bracket** - Best value by price range

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your `config.yml` has dashboard settings:
```yaml
dashboard:
  api_port: 8000
  cache_enabled: true
  cache_ttl_seconds: 300
  template_team_sample_size: 100
  high_rank_range: [1, 10000]
```

## Running the API Server

### Option 1: Using the startup script
```bash
python3 run_dashboard_api.py
```

### Option 2: Using uvicorn directly
```bash
cd src
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## API Endpoints

### Team-Specific Endpoints

All team endpoints require `entry_id` parameter:

- `GET /api/v1/dashboard/team/heatmap?entry_id=2568103`
- `GET /api/v1/dashboard/team/value-tracker?entry_id=2568103`
- `GET /api/v1/dashboard/team/transfers?entry_id=2568103`
- `GET /api/v1/dashboard/team/position-balance?entry_id=2568103&gameweek=16`
- `GET /api/v1/dashboard/team/chips?entry_id=2568103`
- `GET /api/v1/dashboard/team/captain?entry_id=2568103`
- `GET /api/v1/dashboard/team/rank-progression?entry_id=2568103`
- `GET /api/v1/dashboard/team/value-efficiency?entry_id=2568103`

### League-Wide Endpoints

- `GET /api/v1/dashboard/league/ownership-correlation?gameweek=16`
- `GET /api/v1/dashboard/league/template-team?gameweek=16`
- `GET /api/v1/dashboard/league/price-predictors?gameweek=16`
- `GET /api/v1/dashboard/league/position-distribution?gameweek=16`
- `GET /api/v1/dashboard/league/fixture-swing?gameweek=16&lookahead=5`
- `GET /api/v1/dashboard/league/dgw-probability?gameweek=16&lookahead=10`
- `GET /api/v1/dashboard/league/price-brackets?gameweek=16`

### Utility Endpoints

- `GET /api/v1/health` - Health check
- `GET /` - API information

## Example Usage

### Using curl
```bash
# Get performance heatmap
curl "http://localhost:8000/api/v1/dashboard/team/heatmap?entry_id=2568103"

# Get value tracker
curl "http://localhost:8000/api/v1/dashboard/team/value-tracker?entry_id=2568103"

# Get ownership correlation
curl "http://localhost:8000/api/v1/dashboard/league/ownership-correlation?gameweek=16"
```

### Using Python
```python
import requests

# Get performance heatmap
response = requests.get(
    "http://localhost:8000/api/v1/dashboard/team/heatmap",
    params={"entry_id": 2568103}
)
data = response.json()
print(data)
```

### Using JavaScript/Frontend
```javascript
// Fetch performance heatmap
fetch('http://localhost:8000/api/v1/dashboard/team/heatmap?entry_id=2568103')
  .then(response => response.json())
  .then(data => {
    console.log(data);
    // Use data for visualization
  });
```

## Response Format

All endpoints return JSON data structures ready for frontend consumption. Example:

```json
{
  "players": [
    {
      "name": "Haaland",
      "id": 355,
      "points_by_gw": [
        {"gw": 1, "points": 8},
        {"gw": 2, "points": 6}
      ]
    }
  ],
  "gameweeks": [1, 2, 3, ...]
}
```

## Data Sources

The dashboard integrates with:
- **FPL API** - Official Fantasy Premier League API for live data
- **Database** - Historical player data and transfer decisions
- **API-Football** - Additional statistics and fixture data (optional)

## Testing

Run unit tests:
```bash
pytest tests/test_dashboard.py -v
```

## Architecture

```
src/
  visualization_dashboard.py  # Core analytics functions (15 functions)
  dashboard_api.py            # FastAPI REST endpoints (15 endpoints)
  dashboard_helpers.py        # Helper functions for aggregations
```

## Frontend Integration

The API is designed to be consumed by any frontend framework:
- **React/Vue/Angular** - Use fetch or axios
- **Chart.js/D3.js** - Direct JSON consumption
- **Python Dash/Streamlit** - HTTP requests

Example Chart.js integration:
```javascript
// Fetch data
const response = await fetch('/api/v1/dashboard/team/heatmap?entry_id=2568103');
const data = await response.json();

// Create heatmap
const ctx = document.getElementById('heatmap').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: data.gameweeks,
    datasets: data.players.map(player => ({
      label: player.name,
      data: player.points_by_gw.map(p => p.points)
    }))
  }
});
```

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200` - Success
- `400` - Bad request (missing parameters)
- `500` - Server error
- `503` - Service unavailable (dashboard not initialized)

Error response format:
```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Performance

- Responses are cached for 5 minutes (configurable)
- Database queries are optimized
- API rate limiting respects FPL API constraints
- Graceful degradation if optional services unavailable

## Future Enhancements

- Real-time WebSocket updates for live gameweeks
- Caching layer for frequently accessed data
- Batch endpoints for multiple analytics at once
- Authentication for multi-user support
- Historical season comparisons

