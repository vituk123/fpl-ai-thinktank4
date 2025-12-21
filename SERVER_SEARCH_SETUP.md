# Server-Side Team Search Setup

## Overview

The team search functionality now queries the server directly instead of Supabase. The CSV file containing all FPL teams is stored on the ByteHosty server and searched using SQLite for fast performance.

## Architecture

1. **CSV File**: `C:\fpl-api\fpl_teams_full.csv` (on Windows server)
2. **SQLite Database**: Automatically created from CSV (`fpl_teams_full.csv.db`)
3. **Search Endpoint**: `/api/v1/search/teams?q=<query>&limit=20`
4. **Frontend**: Calls ByteHosty server endpoint instead of Supabase

## Files Changed

### Backend (`src/`)
- **`team_search.py`**: New module for searching teams from CSV using SQLite
- **`dashboard_api.py`**: Added team search initialization and endpoint

### Frontend (`frontend/src/services/api.ts`)
- Updated `teamSearchApi.searchTeams()` to call server endpoint instead of Supabase

## How It Works

1. On server startup, `TeamSearch` class checks if SQLite database exists
2. If CSV is newer than database, it loads CSV into SQLite
3. SQLite has indexes on `team_name` and `manager_name` for fast searching
4. Search endpoint queries SQLite and returns results
5. Frontend calls server endpoint via proxy (HTTPS) or direct (HTTP)

## Configuration

The CSV file path is determined automatically:
- **Windows**: `C:\fpl-api\fpl_teams_full.csv`
- **Linux**: `/opt/fpl-api/fpl_teams_full.csv`

## Performance

- **Initial Load**: First search triggers CSV→SQLite conversion (one-time, takes ~30-60 seconds for 12M rows)
- **Subsequent Searches**: Fast SQLite queries with indexes (~10-50ms)
- **Memory Usage**: SQLite database is typically 2-3x larger than CSV file

## Deployment

1. Ensure `fpl_teams_full.csv` exists on the server
2. Deploy updated code to server
3. Restart the API server
4. First search will automatically create SQLite database
5. Search is now available at `/api/v1/search/teams`

## Testing

```bash
# Test search endpoint
curl "http://198.23.185.233:8080/api/v1/search/teams?q=test&limit=10"

# Response format:
{
  "data": {
    "matches": [
      {
        "team_id": 12345,
        "team_name": "Test Team",
        "manager_name": "John Doe",
        "similarity": 0.9
      }
    ]
  },
  "meta": {
    "query": "test",
    "count": 1,
    "limit": 10
  }
}
```

## Benefits

1. ✅ **No Supabase dependency** for search
2. ✅ **Fast searches** using SQLite indexes
3. ✅ **Large dataset support** (12M+ teams)
4. ✅ **Automatic database creation** from CSV
5. ✅ **Resumable** - database persists across restarts

## Notes

- SQLite database is created automatically on first search
- Database is recreated if CSV file is updated (based on file modification time)
- Search uses LIKE queries with similarity scoring
- Results are sorted by similarity (exact match > starts with > contains)

