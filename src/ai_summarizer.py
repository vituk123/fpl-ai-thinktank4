"""
AI Summarization Client for FPL News
Uses Supabase Edge Function with built-in AI API (Ollama/Llamafile).
"""
import logging
import time
from typing import Dict, Optional, List
import json
from supabase import Client

logger = logging.getLogger(__name__)


class AISummarizer:
    """
    Summarizes FPL news articles using Supabase Edge Function with built-in AI API.
    """
    
    def __init__(self, supabase_client: Client, function_name: str = "summarize-news"):
        """
        Initialize AI summarizer.
        
        Args:
            supabase_client: Supabase client instance
            function_name: Name of the Edge Function to call
        """
        self.supabase_client = supabase_client
        self.function_name = function_name
        
        logger.info(f"AISummarizer initialized with Supabase Edge Function: {function_name}")
    
    def summarize_article(self, title: str, content: str, url: str) -> Optional[Dict]:
        """
        Summarize an article using Supabase Edge Function.
        
        Args:
            title: Article title
            content: Article content/description
            url: Article URL
            
        Returns:
            Dictionary with summary, relevance_score, key_points, etc.
            Returns None if summarization fails
        """
        try:
            logger.debug(f"Summarizing article via Edge Function: {title[:50]}...")
            
            # Call Supabase Edge Function
            response = self.supabase_client.functions.invoke(
                self.function_name,
                invoke_options={
                    'body': {
                        'title': title,
                        'content': content or '',
                        'url': url or ''
                    }
                }
            )
            
            # Parse response
            if hasattr(response, 'data'):
                summary_data = response.data
            elif isinstance(response, dict):
                summary_data = response
            else:
                # Try to parse as JSON string
                try:
                    summary_data = json.loads(str(response))
                except:
                    logger.error(f"Unexpected response format: {type(response)}")
                    return None
            
            # Validate required fields
            required_fields = ['summary', 'relevance_score', 'key_points', 'article_type']
            if not all(field in summary_data for field in required_fields):
                logger.warning(f"Missing required fields in Edge Function response: {summary_data.keys()}")
                # Fill in missing fields with defaults
                summary_data.setdefault('summary', summary_data.get('summary', '')[:500])
                summary_data.setdefault('relevance_score', 0.5)
                summary_data.setdefault('key_points', [])
                summary_data.setdefault('article_type', 'general')
                summary_data.setdefault('player_names', [])
                summary_data.setdefault('teams', [])
            
            # Ensure relevance_score is a float
            if isinstance(summary_data.get('relevance_score'), str):
                try:
                    summary_data['relevance_score'] = float(summary_data['relevance_score'])
                except:
                    summary_data['relevance_score'] = 0.5
            
            logger.debug(f"Summary generated: relevance={summary_data.get('relevance_score', 0)}")
            return summary_data
        
        except Exception as e:
            logger.error(f"Error summarizing article '{title[:50]}...': {e}", exc_info=True)
            return None
    
    def batch_summarize(self, articles: List[Dict], delay: float = 1.0) -> List[Dict]:
        """
        Summarize multiple articles with rate limiting.
        
        Args:
            articles: List of article dicts with 'title', 'content', 'url' keys
            delay: Delay between requests (seconds)
            
        Returns:
            List of summary dicts (None entries for failed summaries)
        """
        summaries = []
        
        for idx, article in enumerate(articles, 1):
            if idx > 1:
                time.sleep(delay)  # Rate limiting
            
            title = article.get('title', '')
            content = article.get('content', '') or article.get('description', '')
            url = article.get('url', '') or article.get('link', '')
            
            if not title:
                logger.warning(f"Skipping article {idx}: missing title")
                summaries.append(None)
                continue
            
            summary = self.summarize_article(title, content, url)
            summaries.append(summary)
            
            if idx % 10 == 0:
                logger.info(f"Processed {idx}/{len(articles)} articles")
        
        successful = sum(1 for s in summaries if s is not None)
        logger.info(f"Summarized {successful}/{len(articles)} articles successfully")
        
        return summaries
