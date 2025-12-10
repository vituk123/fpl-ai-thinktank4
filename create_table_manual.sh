#!/bin/bash
# Manual table creation script using psql
# Run this if the Python script fails due to connection pooler limits

echo "======================================================================"
echo "Creating fpl_news_summaries table via psql"
echo "======================================================================"
echo ""
echo "This will prompt you for the database password."
echo "You can find it in your .env file (DB_CONNECTION_STRING)"
echo ""

psql -h aws-1-ap-south-1.pooler.supabase.com -p 5432 -d postgres -U postgres.sdezcbesdubplacfxibc << 'SQL'
CREATE TABLE IF NOT EXISTS fpl_news_summaries (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    article_url TEXT NOT NULL,
    source VARCHAR(255),
    published_date TIMESTAMP,
    article_type VARCHAR(50),
    fpl_relevance_score DECIMAL(3,2) DEFAULT 0.0,
    key_points JSONB,
    player_names JSONB,
    teams JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_summaries_article_id ON fpl_news_summaries(article_id);
CREATE INDEX IF NOT EXISTS idx_news_summaries_published_date ON fpl_news_summaries(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_summaries_relevance ON fpl_news_summaries(fpl_relevance_score DESC);

\q
SQL

echo ""
echo "✓ Table creation complete!"
