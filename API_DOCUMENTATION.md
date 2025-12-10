# FPL Visualization Dashboard API Documentation

## Overview

The FPL Visualization Dashboard API provides comprehensive REST endpoints for Fantasy Premier League analytics, news, images, live tracking, and transfer recommendations.

**Base URL**: `http://localhost:8000`  
**API Version**: `v1`  
**API Prefix**: `/api/v1`

## Response Format

All endpoints return JSON responses in a standardized format:

### Standard Response
```json
{
  "data": { ... },
  "meta": { ... },
  "errors": null
}
```

### Paginated Response
```json
{
  "data": [ ... ],
  "meta": {
    "total": 100,
    "limit": 50,
    "offset": 0,
    "returned": 50
  },
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  }
}
```

### Error Response
```json
{
  "error": "Error message",
  "status_code": 400,
  "path": "/api/v1/endpoint"
}
```

## Endpoints

### Dashboard Analytics

#### Team-Specific Analytics

##### GET `/api/v1/dashboard/team/heatmap`
Get performance heatmap data for a team.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

**Response:** StandardResponse with heatmap data

##### GET `/api/v1/dashboard/team/value-tracker`
Get value tracker data showing team value over time.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

##### GET `/api/v1/dashboard/team/transfers`
Get transfer analysis data.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

##### GET `/api/v1/dashboard/team/position-balance`
Get position balance analysis.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `gameweek` (optional): Gameweek number

##### GET `/api/v1/dashboard/team/chips`
Get chip usage timeline.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

##### GET `/api/v1/dashboard/team/captain`
Get captain performance analysis.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

##### GET `/api/v1/dashboard/team/rank-progression`
Get rank progression over time.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

##### GET `/api/v1/dashboard/team/value-efficiency`
Get value efficiency metrics.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `season` (optional): Season year

#### League-Wide Analytics

##### GET `/api/v1/dashboard/league/ownership-correlation`
Get ownership vs points correlation data.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number

##### GET `/api/v1/dashboard/league/template-team`
Get template team data from high-ranked teams.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number

##### GET `/api/v1/dashboard/league/price-predictors`
Get price change predictor data.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number

##### GET `/api/v1/dashboard/league/position-distribution`
Get position-wise points distribution.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number

##### GET `/api/v1/dashboard/league/fixture-swing`
Get fixture difficulty swing analysis.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number
- `lookahead` (default: 5): Number of gameweeks to look ahead

##### GET `/api/v1/dashboard/league/dgw-probability`
Get double gameweek probability data.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number
- `lookahead` (default: 10): Number of gameweeks to look ahead

##### GET `/api/v1/dashboard/league/price-brackets`
Get top performers by price bracket.

**Parameters:**
- `season` (optional): Season year
- `gameweek` (optional): Gameweek number

### News Articles

##### GET `/api/v1/news/articles`
Get recent news articles with pagination.

**Parameters:**
- `limit` (default: 50, max: 100): Number of articles to return
- `offset` (default: 0): Number of articles to skip
- `days_back` (optional, max: 365): Number of days to look back

**Response:** PaginatedResponse

##### GET `/api/v1/news/articles/{article_id}`
Get a single news article by ID.

**Parameters:**
- `article_id` (path): Article ID

**Response:** StandardResponse

##### GET `/api/v1/news/summaries`
Get AI-summarized news articles.

**Parameters:**
- `limit` (default: 50, max: 100): Number of summaries to return
- `min_relevance` (default: 0.3, range: 0.0-1.0): Minimum relevance score

**Response:** StandardResponse

### Images

##### GET `/api/v1/images/players/{player_id}`
Get player image URL.

**Parameters:**
- `player_id` (path): FPL player ID

**Response:** StandardResponse with `image_url`

##### GET `/api/v1/images/players`
Get batch player image URLs.

**Parameters:**
- `player_ids` (required): Comma-separated list of player IDs (max 100)

**Response:** StandardResponse with `images` dictionary

##### GET `/api/v1/images/teams/{team_id}`
Get team logo URL.

**Parameters:**
- `team_id` (path): FPL team ID

**Response:** StandardResponse with `logo_url`

##### GET `/api/v1/images/teams`
Get all team logo URLs.

**Response:** StandardResponse with `logos` dictionary

### Live Gameweek Tracking

##### GET `/api/v1/live/gameweek/{gameweek}`
Get live gameweek status and summary.

**Parameters:**
- `gameweek` (path): Gameweek number
- `entry_id` (query, required): FPL entry ID

**Response:** StandardResponse with live points and player breakdown

##### GET `/api/v1/live/points/{gameweek}`
Get live points breakdown.

**Parameters:**
- `gameweek` (path): Gameweek number
- `entry_id` (query, required): FPL entry ID

**Response:** StandardResponse with points data

##### GET `/api/v1/live/breakdown/{gameweek}`
Get player-by-player live breakdown.

**Parameters:**
- `gameweek` (path): Gameweek number
- `entry_id` (query, required): FPL entry ID

**Response:** StandardResponse with player breakdown array

### Transfer Recommendations

##### GET `/api/v1/recommendations/transfers`
Get transfer recommendations.

**Parameters:**
- `entry_id` (required): FPL entry ID
- `gameweek` (optional): Gameweek number (defaults to current)
- `max_transfers` (default: 4, range: 1-15): Maximum number of transfers
- `forced_out_ids` (optional): Comma-separated list of player IDs to force out

**Response:** StandardResponse with recommendations array

##### POST `/api/v1/recommendations/transfers`
Generate custom transfer recommendations.

**Request Body:**
```json
{
  "entry_id": 2568103,
  "gameweek": 16,
  "max_transfers": 4,
  "forced_out_ids": [123, 456],
  "constraints": {}
}
```

**Response:** StandardResponse with recommendations array

### Utility Endpoints

##### GET `/api/v1/health`
Comprehensive health check endpoint.

**Response:** JSON with service statuses (dashboard, database, storage, FPL API)

##### GET `/api/v1/info`
Get API information and capabilities.

**Response:** JSON with API version, capabilities, and endpoint list

##### GET `/`
Root endpoint with API information.

**Response:** JSON with API name, version, and endpoint groups

## Error Codes

- `400`: Bad Request - Invalid parameters
- `404`: Not Found - Resource not found
- `422`: Validation Error - Request validation failed
- `500`: Internal Server Error - Server error
- `503`: Service Unavailable - Service not initialized

## Frontend Integration Examples

### React with Fetch

```javascript
// Fetch news articles
const fetchNews = async (limit = 50, offset = 0) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/news/articles?limit=${limit}&offset=${offset}`
  );
  const data = await response.json();
  return data;
};

// Fetch player image
const fetchPlayerImage = async (playerId) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/images/players/${playerId}`
  );
  const data = await response.json();
  return data.data.image_url;
};

// Get transfer recommendations
const fetchRecommendations = async (entryId, gameweek) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/recommendations/transfers?entry_id=${entryId}&gameweek=${gameweek}`
  );
  const data = await response.json();
  return data.data.recommendations;
};
```

### React with Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Fetch dashboard data
const getHeatmap = async (entryId, season) => {
  const response = await api.get('/dashboard/team/heatmap', {
    params: { entry_id: entryId, season },
  });
  return response.data;
};

// Post transfer request
const getTransferRecommendations = async (requestData) => {
  const response = await api.post('/recommendations/transfers', requestData);
  return response.data;
};
```

## CORS Configuration

CORS is configured via `config.yml`:

```yaml
dashboard:
  cors_origins:
    - "http://localhost:3000"  # React dev server
    - "http://localhost:5173"  # Vite dev server
    - "*"  # Allow all in development
```

For production, remove `"*"` and specify exact origins.

## Authentication

Authentication is currently disabled but prepared for future implementation. When enabled, endpoints will require authentication via:

- **API Key**: `X-API-Key` header
- **Bearer Token**: `Authorization: Bearer <token>` header (Supabase Auth)

See `src/auth.py` for authentication structure.

## Rate Limiting

Rate limiting is configured in `config.yml`:

```yaml
dashboard:
  rate_limit_per_minute: 60
```

## Notes

- All endpoints use the `/api/v1/` prefix
- Responses follow RESTful conventions
- All data is returned as JSON
- Timestamps are in ISO 8601 format
- Pagination uses `limit` and `offset` parameters
- Error responses include helpful error messages

