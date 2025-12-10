# Instructions: Push 10 Most Recent Articles to Supabase

## Step 1: Create the Table

The table needs to be created manually in Supabase first.

### Option A: Via Supabase SQL Editor (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the contents of `create_raw_articles_table.sql`
4. Click **Run** to execute

### Option B: Via Command Line (if you have direct DB access)

```bash
psql "YOUR_DB_CONNECTION_STRING" -f create_raw_articles_table.sql
```

## Step 2: Run the Script

Once the table is created:

```bash
python3 push_recent_articles.py
```

This will:
- Fetch the 10 most recent FPL news articles
- Save them to the `fpl_news_articles` table in Supabase
- Skip duplicates if any exist

## What Gets Saved

Each article includes:
- `article_id` - Unique identifier
- `title` - Article title
- `description` - Article description/summary
- `content` - Full article content (if available)
- `article_url` - Link to original article
- `source` - News source name
- `published_date` - When article was published
- `image_url` - Article image (if available)
- `category` - Article categories
- `language` - Language code (default: 'en')
- `country` - Country code

## Troubleshooting

### Table Not Found Error
- Make sure you've created the table using Step 1 above
- Wait a few seconds after creating the table for Supabase to update its schema cache

### Connection Timeout
- Check your `.env` file has correct `SUPABASE_URL` and `SUPABASE_KEY`
- Verify your database connection string is correct

### No Articles Found
- Check your NewsData.io API key in `config.yml`
- Verify you have API credits remaining

