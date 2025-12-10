# FPL Sentinel - Expert Tweet Analysis System

## Overview

FPL Sentinel is a comprehensive system that scrapes tweets from top FPL experts, analyzes them for transfer and captaincy recommendations, and provides sentiment-based insights.

## Features

- **Twitter Scraping**: Uses Selenium with undetected-chromedriver to bypass X's bot detection
- **Expert Tracking**: Monitors 18 top FPL expert accounts across 3 tiers
- **Sentiment Analysis**: Detects buy/sell/captain recommendations using NLP
- **Player Recognition**: Handles player names, nicknames, and variations
- **JSON Output**: Provides structured recommendations

## Installation

The required dependencies are already in `requirements.txt`:

```bash
pip install selenium undetected-chromedriver textblob vaderSentiment
```

**Note**: VADER sentiment analyzer is optional. The system will use a simple fallback if VADER is not available.

## Usage

### Basic Usage

```bash
python src/fpl_sentinel.py
```

This will:
1. Scrape tweets from all 18 FPL expert accounts
2. Analyze them for transfer/captaincy recommendations
3. Output a JSON summary with top recommendations

### Programmatic Usage

```python
from src.twitter_scraper import TwitterScraper
from src.sentiment_analyzer import SentimentAnalyzer
from src.fpl_api import FPLAPIClient
import pandas as pd

# Initialize
api = FPLAPIClient()
bootstrap = api.get_bootstrap_static()
players_df = pd.DataFrame(bootstrap['elements'])

# Scrape tweets
scraper = TwitterScraper(headless=True)
tweets_df = scraper.scrape_all_experts()
scraper.close()

# Analyze
analyzer = SentimentAnalyzer(players_df)
results = analyzer.analyze_tweets(tweets_df)

print(results)
```

## Expert Accounts Tracked

### Tier 1: Official & Breaking News
- `OfficialFPL` - The source of truth
- `BenDinnery` - CRITICAL for injuries
- `FPLUpdates` - Lineups and news
- `FFScout` - Major analysis hub

### Tier 2: Elite Creators & Veterans
- `LetsTalk_FPL` - Andy (Huge following)
- `FPLGeneral` - Consistent elite ranker
- `PrasFPL` - Strategic expert
- `BigManBakar` - Stats & drafts
- `FPL_Heisenberg` - Team reveals
- `fplmate` - Dan (Community sentiment)

### Tier 3: High Frequency & Tactics
- `FPLFocal` - Price changes & news
- `FPL_JianBatra` - Detailed threads & tips
- `FPLMeerkat` - Data & predictions
- `FPLGuidance` - Stats based
- `FPL_Harry` - YouTube/Twitter hybrid
- `FPLMarcin` - Visuals & memes
- `FPL_Salah` - High volume tips
- `FPL_Banger` - Algorithms & models

## Output Format

```json
{
  "top_3_transfer_targets": [
    {"player": "Haaland", "score": 2.5},
    {"player": "Salah", "score": 2.1},
    {"player": "Saka", "score": 1.8}
  ],
  "top_3_sell_targets": [
    {"player": "Gabriel", "score": -1.5},
    {"player": "Pope", "score": -1.2},
    {"player": "Caicedo", "score": -0.9}
  ],
  "top_3_captain_picks": [
    {"player": "Haaland", "score": 2.3},
    {"player": "Salah", "score": 1.9},
    {"player": "Son", "score": 1.5}
  ]
}
```

## Configuration

### Twitter Scraper Options

```python
scraper = TwitterScraper(
    headless=True,              # Run browser in background
    delay_between_requests=3.0  # Seconds between requests (avoid IP bans)
)
```

### Sentiment Analyzer

The analyzer automatically:
- Maps player names and nicknames (e.g., "KDB" → "De Bruyne")
- Detects buy/sell/captain intent using regex patterns
- Calculates sentiment scores (-1 to 1)
- Forces sentiment based on detected intent

## Error Handling

The system includes comprehensive error handling:
- Network timeouts
- X blocking requests
- Missing player data
- Browser automation failures

All errors are logged and the system continues processing other accounts.

## Notes

- **Rate Limiting**: 3-second delay between requests to avoid IP bans
- **Browser Automation**: Uses undetected-chromedriver to bypass bot detection
- **Player Matching**: Handles common nicknames and variations
- **Sentiment Fallback**: Works even if VADER is not installed

## Testing

Run the test script to verify the sentiment analyzer:

```bash
python test_sentinel.py
```

## Integration with Main Optimizer

The FPL Sentinel can be integrated with the main optimizer to:
1. Provide additional signals for transfer recommendations
2. Validate optimizer suggestions against expert consensus
3. Add expert sentiment as a feature in ML models

