"""
News Processing Pipeline
Orchestrates fetching news, AI summarization, and database storage.
"""
import logging
import hashlib
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

from news_client import NewsDataClient
from ai_summarizer import AISummarizer
from database import DatabaseManager

logger = logging.getLogger(__name__)


class NewsProcessor:
    """
    Processes FPL news articles: fetches, summarizes with AI, and saves to database.
    """
    
    def __init__(self, news_client: NewsDataClient, db_manager: DatabaseManager,
                 ai_summarizer: Optional[AISummarizer] = None):
        """
        Initialize news processor.
        
        Args:
            news_client: NewsData.io client instance
            db_manager: Database manager instance
            ai_summarizer: Optional AI summarization client (created from db_manager if not provided)
        """
        self.news_client = news_client
        self.db_manager = db_manager
        
        # Create AI summarizer from database manager if not provided
        if ai_summarizer is None:
            from ai_summarizer import AISummarizer
            ai_summarizer = AISummarizer(supabase_client=db_manager.supabase_client)
        
        self.ai_summarizer = ai_summarizer
        
        logger.info("NewsProcessor initialized")
    
    def _generate_article_id(self, article: Dict) -> str:
        """
        Generate unique article ID from article data.
        
        Args:
            article: Article dictionary
            
        Returns:
            Unique article ID string
        """
        # Use article_id from NewsData.io if available
        if article.get('article_id'):
            return str(article['article_id'])
        
        # Otherwise, hash the URL
        url = article.get('link') or article.get('url', '')
        if url:
            return hashlib.md5(url.encode()).hexdigest()
        
        # Fallback: hash title + source
        title = article.get('title', '')
        source = article.get('source_id', '')
        combined = f"{title}_{source}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove articles that already exist in database.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Filtered list of new articles
        """
        # Get existing article IDs
        existing_ids = self.db_manager.get_existing_article_ids()
        logger.info(f"Found {len(existing_ids)} existing articles in database")
        
        # Filter out duplicates
        new_articles = []
        for article in articles:
            article_id = self._generate_article_id(article)
            if article_id not in existing_ids:
                new_articles.append(article)
            else:
                logger.debug(f"Skipping duplicate article: {article.get('title', '')[:50]}")
        
        logger.info(f"Filtered to {len(new_articles)} new articles (removed {len(articles) - len(new_articles)} duplicates)")
        return new_articles
    
    def process_article(self, article: Dict) -> Optional[Dict]:
        """
        Process a single article: summarize with AI and prepare for database.
        
        Args:
            article: Article dictionary from NewsData.io
            
        Returns:
            Dictionary ready for database insertion, or None if processing failed
        """
        try:
            title = article.get('title', '')
            content = article.get('description', '') or article.get('content', '')
            url = article.get('link', '') or article.get('url', '')
            source = article.get('source_id', 'Unknown')
            
            if not title:
                logger.warning("Skipping article: missing title")
                return None
            
            # Summarize with AI
            logger.debug(f"Summarizing: {title[:60]}...")
            summary_result = self.ai_summarizer.summarize_article(title, content, url)
            
            if not summary_result:
                logger.warning(f"Failed to summarize article: {title[:50]}")
                return None
            
            # Check relevance score - skip if too low
            relevance = summary_result.get('relevance_score', 0.0)
            if relevance < 0.2:  # Very low relevance threshold
                logger.debug(f"Skipping low-relevance article (score={relevance:.2f}): {title[:50]}")
                return None
            
            # Parse published date
            published_date = None
            pub_date_str = article.get('pubDate', '')
            if pub_date_str:
                try:
                    published_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                except:
                    try:
                        published_date = datetime.strptime(pub_date_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        published_date = datetime.now()
            
            # Prepare data for database
            article_id = self._generate_article_id(article)
            
            summary_data = {
                'article_id': article_id,
                'title': title,
                'summary_text': summary_result.get('summary', ''),
                'article_url': url,
                'source': source,
                'published_date': published_date.isoformat() if published_date else None,
                'article_type': summary_result.get('article_type', 'general'),
                'fpl_relevance_score': relevance,
                'key_points': summary_result.get('key_points', []),
                'player_names': summary_result.get('player_names', []),
                'teams': summary_result.get('teams', [])
            }
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error processing article: {e}", exc_info=True)
            return None
    
    def fetch_and_summarize_news(self, days_back: int = 1, max_results: int = 100) -> Dict:
        """
        Main processing function: fetch news, summarize, and save to database.
        
        Args:
            days_back: Number of days to look back for news
            max_results: Maximum number of articles to process
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info("=" * 70)
        logger.info("FPL NEWS PROCESSING PIPELINE")
        logger.info("=" * 70)
        
        stats = {
            'articles_fetched': 0,
            'articles_new': 0,
            'articles_summarized': 0,
            'articles_saved': 0,
            'articles_skipped_low_relevance': 0,
            'articles_failed': 0,
            'errors': []
        }
        
        try:
            # Step 1: Fetch news articles
            logger.info(f"\n1. Fetching FPL news from last {days_back} day(s)...")
            news_df = self.news_client.get_fpl_news(days_back=days_back, max_results=max_results)
            
            if news_df.empty:
                logger.warning("No news articles found")
                return stats
            
            stats['articles_fetched'] = len(news_df)
            logger.info(f"   ✓ Fetched {stats['articles_fetched']} articles")
            
            # Convert DataFrame to list of dicts
            articles = news_df.to_dict('records')
            
            # Step 2: Deduplicate
            logger.info("\n2. Checking for duplicates...")
            new_articles = self.deduplicate_articles(articles)
            stats['articles_new'] = len(new_articles)
            
            if not new_articles:
                logger.info("   ✓ No new articles to process")
                return stats
            
            logger.info(f"   ✓ {stats['articles_new']} new articles to process")
            
            # Step 3: Process each article
            logger.info("\n3. Processing articles with AI summarization...")
            summaries = []
            
            for idx, article in enumerate(new_articles, 1):
                if idx % 10 == 0 or idx == len(new_articles):
                    logger.info(f"   Progress: {idx}/{len(new_articles)} ({idx*100//len(new_articles)}%)")
                
                summary_data = self.process_article(article)
                
                if summary_data:
                    if summary_data.get('fpl_relevance_score', 0) < 0.2:
                        stats['articles_skipped_low_relevance'] += 1
                    else:
                        summaries.append(summary_data)
                        stats['articles_summarized'] += 1
                else:
                    stats['articles_failed'] += 1
            
            logger.info(f"   ✓ Summarized {stats['articles_summarized']} articles")
            logger.info(f"   ⚠ Skipped {stats['articles_skipped_low_relevance']} low-relevance articles")
            
            # Step 4: Save to database
            if summaries:
                logger.info(f"\n4. Saving {len(summaries)} summaries to database...")
                saved_count = 0
                
                for summary in summaries:
                    if self.db_manager.save_news_summary(summary):
                        saved_count += 1
                    else:
                        stats['errors'].append(f"Failed to save: {summary.get('title', 'Unknown')[:50]}")
                
                stats['articles_saved'] = saved_count
                logger.info(f"   ✓ Saved {saved_count}/{len(summaries)} summaries")
            else:
                logger.info("\n4. No summaries to save")
            
            # Final summary
            logger.info("\n" + "=" * 70)
            logger.info("PROCESSING SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Articles fetched: {stats['articles_fetched']}")
            logger.info(f"New articles: {stats['articles_new']}")
            logger.info(f"Summarized: {stats['articles_summarized']}")
            logger.info(f"Saved to database: {stats['articles_saved']}")
            logger.info(f"Skipped (low relevance): {stats['articles_skipped_low_relevance']}")
            logger.info(f"Failed: {stats['articles_failed']}")
            if stats['errors']:
                logger.warning(f"Errors: {len(stats['errors'])}")
            logger.info("=" * 70)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in processing pipeline: {e}", exc_info=True)
            stats['errors'].append(str(e))
            return stats

