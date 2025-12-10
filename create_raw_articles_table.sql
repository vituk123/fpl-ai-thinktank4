-- Create table for raw FPL news articles (without AI summarization)
CREATE TABLE IF NOT EXISTS fpl_news_articles (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    content TEXT,
    article_url TEXT NOT NULL,
    source VARCHAR(255),
    source_id VARCHAR(255),
    published_date TIMESTAMP,
    image_url TEXT,
    category JSONB,
    language VARCHAR(10) DEFAULT 'en',
    country VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_news_articles_article_id ON fpl_news_articles(article_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_published_date ON fpl_news_articles(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON fpl_news_articles(source);

