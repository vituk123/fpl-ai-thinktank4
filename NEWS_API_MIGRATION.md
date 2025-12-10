# Twitter Scraper to NewsData.io Migration

## Summary

The Twitter scraper has been **disabled** and replaced with the **NewsData.io API** for fetching FPL-related news articles.

## Changes Made

### 1. New Module: `src/news_client.py`
- Created `NewsDataClient` class to interact with NewsData.io API
- Supports searching for FPL-related news articles
- Includes caching and rate limiting (200 requests/day for free tier)
- Categorizes articles (injury, transfer, captain, lineup, etc.)

### 2. Updated Files

#### `src/fpl_sentinel.py`
- Replaced `TwitterScraper` import with `NewsDataClient`
- Updated main function to fetch news instead of scraping tweets
- Maintains compatibility with existing sentiment analyzer

#### `run_twitter_scraper.py`
- Renamed functionality to "FPL News Collector"
- Now uses NewsData.io API instead of Twitter scraping
- Output format remains similar (CSV with articles)

#### `config.yml`
- Added `news` section with API key and configuration:
  ```yaml
  news:
    api_key: "pub_de403c9973ee41c3aff1442d3ba3e4"
    enabled: true
    cache_ttl_seconds: 3600
    days_back: 7
    max_results: 200
  ```

### 3. Disabled Components

- `src/twitter_scraper.py` - **No longer used** (kept for reference)
- Selenium/ChromeDriver dependencies - **No longer required**

## API Key Setup

### Current Status
The API key `pub_de403c9973ee41c3aff1442d3ba3e4` is currently returning 401 Unauthorized errors.

### Troubleshooting

1. **Verify API Key**
   - Check if the API key is correct at: https://newsdata.io/dashboard
   - Ensure the key is activated/verified

2. **Free Tier Limits**
   - 200 requests per day
   - Basic search functionality
   - May have restrictions on date filtering and categories

3. **Test API Key**
   ```bash
   python3 -c "
   import requests
   api_key = 'your_api_key_here'
   url = 'https://newsdata.io/api/1/news'
   params = {'apikey': api_key, 'q': 'Premier League', 'language': 'en', 'country': 'gb'}
   r = requests.get(url, params=params)
   print(f'Status: {r.status_code}')
   print(r.json())
   "
   ```

## Usage

### Run News Collector
```bash
python3 run_twitter_scraper.py
```

This will:
1. Fetch FPL-related news from NewsData.io
2. Categorize articles (injury, transfer, captain, etc.)
3. Save results to `fpl_news_articles.csv`

### Use in FPL Sentinel
```bash
python3 -m src.fpl_sentinel
```

The sentiment analyzer will process news articles instead of tweets.

## API Documentation

- NewsData.io Documentation: https://newsdata.io/documentation
- Free Tier: https://newsdata.io/pricing

## Benefits Over Twitter Scraper

1. **No Browser Automation** - No need for Selenium/ChromeDriver
2. **More Reliable** - API-based, no bot detection issues
3. **Better Coverage** - Multiple news sources, not just Twitter
4. **Structured Data** - Clean JSON responses
5. **Rate Limiting Built-in** - Respects API limits automatically

## Migration Notes

- The `sentiment_analyzer.py` works with both tweets and news articles
- Output format is compatible (DataFrame with 'content', 'date', 'source' columns)
- Article categorization helps identify relevant FPL information

