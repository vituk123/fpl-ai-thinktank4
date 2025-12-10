-- Create FPL News Summaries Table
-- Run this in your Supabase SQL Editor

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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_news_summaries_article_id ON fpl_news_summaries(article_id);
CREATE INDEX IF NOT EXISTS idx_news_summaries_published_date ON fpl_news_summaries(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_summaries_relevance ON fpl_news_summaries(fpl_relevance_score DESC);

