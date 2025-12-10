# AI News Summarization System

## Overview

This system automatically fetches FPL-related news from NewsData.io, uses AI (aimlapi.com) to summarize articles and extract only FPL-relevant information, then stores the summaries in Supabase. The system runs daily at midnight via cron job.

## Features

- **Automated News Fetching**: Retrieves FPL news from NewsData.io API
- **AI-Powered Summarization**: Uses GPT-4o to extract only FPL-relevant information
- **Smart Filtering**: Automatically filters out low-relevance articles
- **Deduplication**: Prevents processing the same article multiple times
- **Database Storage**: Stores summaries in Supabase with full article links
- **Daily Automation**: Runs automatically at midnight via cron job

## Architecture

### Components

1. **`src/ai_summarizer.py`**: AI client for summarizing articles using aimlapi.com
2. **`src/news_processor.py`**: Orchestrates the news processing pipeline
3. **`process_news_daily.py`**: Main script for daily execution
4. **`cron_setup.sh`**: Helper script to set up cron job

### Database Schema

The system creates a `fpl_news_summaries` table in Supabase with:

- `id`: Primary key
- `article_id`: Unique identifier (for deduplication)
- `title`: Article title
- `summary_text`: AI-generated summary
- `article_url`: Link to full article
- `source`: News source name
- `published_date`: When article was published
- `article_type`: Category (injury, transfer, captain, etc.)
- `fpl_relevance_score`: AI-assigned relevance (0.0-1.0)
- `key_points`: JSON array of key FPL insights
- `player_names`: JSON array of mentioned players
- `teams`: JSON array of mentioned teams
- `created_at`: When summary was created
- `updated_at`: When summary was last updated

## Setup

### 1. Install Dependencies

```bash
pip install openai
```

### 2. Configure API Keys

Ensure your `config.yml` has:

```yaml
news:
  api_key: "your_newsdata_api_key"
  
ai_api:
  api_key: "your_aimlapi_key"
  base_url: "https://api.aimlapi.com/v1"
  model: "gpt-4o"
  fallback_model: "gpt-3.5-turbo"
  max_tokens: 500
  temperature: 0.3
```

### 3. Set Up Cron Job

Run the setup script:

```bash
./cron_setup.sh
```

Or manually add to crontab:

```bash
crontab -e
```

Add this line:

```
0 0 * * * cd /path/to/fpl-ai-thinktank4 && source venv/bin/activate && python3 process_news_daily.py >> logs/news_processing.log 2>&1
```

### 4. Test Manually

Test the system before setting up cron:

```bash
python3 process_news_daily.py
```

## Usage

### Daily Processing

The cron job runs automatically at midnight. Check logs:

```bash
tail -f logs/news_processing.log
```

### Manual Processing

Run manually anytime:

```bash
python3 process_news_daily.py
```

### Query Summaries

Use the database manager to retrieve summaries:

```python
from src.database import DatabaseManager

db = DatabaseManager()
summaries_df = db.get_recent_summaries(limit=50, min_relevance=0.5)
print(summaries_df)
```

## AI Summarization

The AI is prompted to extract only FPL-relevant information:

- Player injuries and fitness updates
- Transfer news affecting FPL
- Captaincy recommendations
- Price changes
- Fixture difficulty updates
- Team news and lineup changes
- Player form insights
- Chip usage recommendations

Articles with relevance score < 0.2 are automatically skipped.

## Rate Limiting

- **NewsData.io**: 200 requests/day (free tier)
- **aimlapi.com**: Check your plan limits
- The system includes delays between requests to respect limits

## Logging

Logs are written to:
- `logs/news_processing.log` (file)
- Console output (stdout)

## Error Handling

The system handles:
- API rate limits (with retries)
- Network failures
- Invalid article content
- Database connection issues
- Partial failures (continues processing other articles)

## Monitoring

Check processing statistics in logs:

```
Articles fetched: 50
New articles: 30
Summarized: 25
Saved to database: 25
Skipped (low relevance): 5
Failed: 0
```

## Troubleshooting

### Cron Job Not Running

1. Check cron service: `systemctl status cron` (Linux) or `sudo launchctl list | grep cron` (macOS)
2. Check cron logs: `grep CRON /var/log/syslog` (Linux)
3. Verify cron job: `crontab -l`
4. Check script permissions: `chmod +x process_news_daily.py`

### API Errors

- Verify API keys in `config.yml`
- Check API rate limits
- Review error messages in logs

### Database Errors

- Ensure Supabase credentials are correct in `.env`
- Check database connection
- Verify table exists: `db_manager.create_news_summaries_table()`

## Future Enhancements

- Email notifications for high-relevance articles
- Webhook integration for real-time updates
- Custom relevance thresholds per user
- Multi-language support
- Article clustering by topic

