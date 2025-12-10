# API-Football Rate Limiting Guide

## Overview

The API-Football client has been configured with **intelligent rate limiting** to respect your plan limits:
- **100 requests per day**
- **10 requests per minute**

## Features

### 1. **Automatic Rate Limiting**
- The client automatically tracks and enforces both daily and per-minute limits
- Requests are queued and delayed if limits are approached
- Automatic waiting when per-minute limit is reached

### 2. **Request Tracking**
- Daily request count is saved to disk and persists across sessions
- Per-minute tracking uses a sliding window
- Counters reset automatically (daily at midnight, per-minute every 60 seconds)

### 3. **Smart Caching**
- **All responses are cached** to minimize API calls
- Cache TTL: 1 hour (configurable)
- Cache hits don't count toward rate limits
- This means repeated requests for the same data use **0 API calls**

### 4. **Usage Monitoring**
- Real-time usage statistics
- Warnings when approaching limits
- Daily and per-minute tracking

## Usage Statistics

You can check your current usage at any time:

```python
from src.api_football_client import APIFootballClient
import yaml

# Load config
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

api_key = config['api_football']['api_key']
client = APIFootballClient(
    api_key=api_key,
    requests_per_minute=10,
    requests_per_day=100
)

# Get usage stats
stats = client.get_usage_stats()
print(f"Daily: {stats['daily_used']}/{stats['daily_limit']} ({stats['daily_remaining']} remaining)")
print(f"Per-minute: {stats['minute_used']}/{stats['minute_limit']} ({stats['minute_remaining']} remaining)")
```

## How It Works

### Per-Minute Limit (10 requests)
1. Client tracks the timestamp of each API request
2. Before making a request, checks how many requests were made in the last 60 seconds
3. If 10 requests were made, automatically waits until the oldest request is >60 seconds old
4. Then proceeds with the new request

### Daily Limit (100 requests)
1. Daily count is stored in `.cache/api_football/daily_count.json`
2. Count persists across sessions
3. Automatically resets at midnight
4. If daily limit is reached, requests are blocked with an error

### Caching Strategy
- **Cache-first**: Always checks cache before making API request
- **Cache TTL**: 1 hour (configurable in `config.yml`)
- **Cache location**: `.cache/api_football/`
- **Cache benefits**: 
  - Repeated requests use 0 API calls
  - Faster response times
  - Reduces rate limit usage

## Example Scenarios

### Scenario 1: Making 5 Requests Quickly
```
Request 1: ✅ Made immediately (0/10 per-minute, 1/100 daily)
Request 2: ✅ Made immediately (1/10 per-minute, 2/100 daily)
...
Request 5: ✅ Made immediately (4/10 per-minute, 5/100 daily)
```

### Scenario 2: Making 12 Requests in 1 Minute
```
Request 1-10: ✅ Made immediately
Request 11: ⏳ Waits ~6 seconds (until oldest request is >60s old)
Request 12: ✅ Made after wait
```

### Scenario 3: Cached Requests
```
Request 1: 🌐 API call (1/100 daily)
Request 2 (same data, within 1 hour): 💾 Cache hit (1/100 daily - no change!)
Request 3 (same data, within 1 hour): 💾 Cache hit (1/100 daily - no change!)
```

## Best Practices

### 1. **Maximize Cache Usage**
- Use longer cache TTLs for data that doesn't change frequently
- Group related requests together to benefit from caching
- Don't clear cache unnecessarily

### 2. **Plan Your Requests**
- Batch requests when possible
- Use `use_cache=True` (default) to avoid redundant calls
- Check usage stats before making many requests

### 3. **Monitor Usage**
```python
# Before making many requests
stats = client.get_usage_stats()
if stats['daily_remaining'] < 20:
    print("⚠️  Low on daily requests!")
    # Consider using cached data or deferring requests
```

### 4. **Handle Rate Limit Errors**
```python
try:
    data = client.get_teams(season=2024)
except Exception as e:
    if "Rate limit exceeded" in str(e):
        print("Rate limit reached. Try again later or use cached data.")
    else:
        raise
```

## Configuration

Rate limits are configured in `config.yml`:

```yaml
api_football:
  api_key: "your-api-key"
  requests_per_minute: 10
  requests_per_day: 100
  cache_ttl_seconds: 3600  # 1 hour
```

## Cache Management

### Clear Cache
```python
client.clear_cache()  # Removes all cached responses
```

### Check Cache Status
```python
# Cache files are stored in:
# .cache/api_football/

# Daily count is stored in:
# .cache/api_football/daily_count.json
```

## Tips for Maximizing Your 100 Daily Requests

1. **Use caching effectively**: Set longer cache TTLs for static data
2. **Batch requests**: Get multiple pieces of data in one session
3. **Prioritize**: Use requests for data that changes frequently
4. **Monitor**: Check usage stats regularly
5. **Plan ahead**: Make requests during off-peak times if possible

## Example: Efficient Usage

```python
# Good: Uses cache, makes only 1 API call
teams = client.get_teams(season=2024)  # API call
teams_again = client.get_teams(season=2024)  # Cache hit (0 API calls)

# Good: Batches requests
teams = client.get_teams(season=2024)
fixtures = client.get_fixtures(season=2024, next_n=5)
injuries = client.get_injuries()

# Check usage
stats = client.get_usage_stats()
print(f"Used {stats['daily_used']} requests today")
```

## Troubleshooting

### "Rate limit exceeded" Error
- Check your daily usage: `client.get_usage_stats()`
- Wait until midnight for daily reset
- Use cached data if available
- Clear cache only if necessary (forces new API calls)

### Requests Taking Too Long
- This is normal when approaching per-minute limits
- Client automatically waits to respect limits
- Consider using cached data for faster responses

### Cache Not Working
- Check cache directory exists: `.cache/api_football/`
- Verify cache TTL hasn't expired
- Ensure `use_cache=True` (default)

## Summary

The rate limiting system ensures you:
- ✅ Never exceed your 100 daily requests
- ✅ Never exceed your 10 per-minute requests
- ✅ Maximize cache usage to minimize API calls
- ✅ Get warnings before hitting limits
- ✅ Have persistent tracking across sessions

With smart caching, you can make many "requests" while using very few actual API calls!

