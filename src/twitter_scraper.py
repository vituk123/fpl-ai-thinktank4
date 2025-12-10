"""
Twitter Scraper Module for FPL Sentinel System
Scrapes tweets from FPL experts using Selenium with stealth options
to bypass X (Twitter) bot detection.
Collects all tweets from the last 3 days from each account.
"""
import time
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

# Try to use undetected_chromedriver if available, otherwise use regular selenium
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False

logger = logging.getLogger(__name__)


class TwitterScraper:
    """
    Scrapes tweets from FPL expert accounts on X (Twitter).
    Uses browser automation to bypass bot detection.
    """
    
    def __init__(self, headless: bool = True, delay_between_requests: float = 3.0, days_back: int = 7, max_retries: int = 2):
        """
        Initialize the Twitter scraper.
        
        Args:
            headless: Run browser in headless mode (default: True)
            delay_between_requests: Seconds to wait between requests (default: 3.0)
            days_back: Number of days to look back for tweets (default: 7)
            max_retries: Maximum number of retry attempts for failed requests (default: 2)
        """
        self.headless = headless
        self.delay_between_requests = delay_between_requests
        self.days_back = days_back
        self.max_retries = max_retries
        self.driver = None
        # Use timezone-naive datetime for cutoff (will normalize all dates to naive)
        self.cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(days=days_back)
        
        # Categorized list of FPL expert accounts
        self.fpl_experts = [
            # --- TIER 1: Official & Breaking News ---
            "OfficialFPL",       # The source of truth
            "BenDinnery",        # CRITICAL for injuries (Transfer Out logic)
            "FPLUpdates",        # Lineups and news
            "FFScout",           # Major analysis hub
            
            # --- TIER 2: Elite Creators & Veterans ---
            "LetsTalk_FPL",      # Andy (Huge following)
            "FPLGeneral",        # Consistent elite ranker
            "PrasFPL",           # Strategic expert
            "BigManBakar",       # Stats & drafts
            "FPL_Heisenberg",    # Team reveals
            "fplmate",           # Dan (Community sentiment)
            
            # --- TIER 3: High Frequency & Tactics ---
            "FPLFocal",          # Price changes & news
            "FPL_JianBatra",     # Detailed threads & tips
            "FPLMeerkat",        # Data & predictions
            "FPLGuidance",       # Stats based
            "FPL_Harry",         # YouTube/Twitter hybrid
            "FPLMarcin",         # Visuals & memes (high engagement)
            "FPL_Salah",         # High volume tips
            "FPL_Banger"         # Algorithms & models
        ]
        
        logger.info(f"Initialized TwitterScraper with {len(self.fpl_experts)} expert accounts (collecting tweets from last {days_back} days)")
    
    def _parse_tweet_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse X's relative time format to datetime.
        Handles formats like "2h", "1d ago", "Dec 3", "Just now", etc.
        
        Args:
            date_str: Date string from X (could be relative or absolute)
        
        Returns:
            Datetime object or None if parsing fails
        """
        if not date_str:
            return None
        
        date_str = date_str.strip().lower()
        now = datetime.now()
        
        # Handle "Just now" or "now"
        if 'just now' in date_str or date_str == 'now':
            return now.replace(tzinfo=None)  # Return timezone-naive
        
        # Handle relative time: "2h", "1d", "3d ago", etc.
        # Pattern: number + unit (h, m, d, w)
        relative_pattern = r'(\d+)\s*(h|m|d|w|hour|hours|minute|minutes|day|days|week|weeks)\s*(ago)?'
        match = re.search(relative_pattern, date_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            # Ensure now is timezone-naive for calculation
            now_naive = now.replace(tzinfo=None) if now.tzinfo else now
            
            if unit in ['m', 'minute', 'minutes']:
                return now_naive - timedelta(minutes=value)
            elif unit in ['h', 'hour', 'hours']:
                return now_naive - timedelta(hours=value)
            elif unit in ['d', 'day', 'days']:
                return now_naive - timedelta(days=value)
            elif unit in ['w', 'week', 'weeks']:
                return now_naive - timedelta(weeks=value)
        
        # Handle absolute dates: "Dec 3", "Dec 3, 2024", etc.
        # Try to parse common date formats
        date_formats = [
            '%b %d',  # "Dec 3"
            '%b %d, %Y',  # "Dec 3, 2024"
            '%d %b',  # "3 Dec"
            '%d %b %Y',  # "3 Dec 2024"
            '%Y-%m-%d',  # "2024-12-03"
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # If year not specified, assume current year
                if '%Y' not in fmt:
                    parsed = parsed.replace(year=now.year)
                return parsed
            except:
                continue
        
        # Fallback: return current time if we can't parse (timezone-naive)
        logger.warning(f"Could not parse date: {date_str}, using current time")
        return datetime.now().replace(tzinfo=None)
    
    def _is_tweet_within_date_range(self, tweet_date: Optional[datetime]) -> bool:
        """
        Check if tweet date is within the specified date range (last N days).
        
        Args:
            tweet_date: Datetime of the tweet
        
        Returns:
            True if tweet is within date range, False otherwise
        """
        if not tweet_date:
            return False
        return tweet_date >= self.cutoff_date
    
    def _scroll_and_wait(self, scroll_pause_time: float = 2.0, max_scrolls: int = 40):
        """
        Scroll down the page to load more tweets with dynamic detection.
        
        Args:
            scroll_pause_time: Seconds to wait after each scroll
            max_scrolls: Maximum number of scrolls to prevent infinite loops
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        no_change_count = 0  # Track consecutive scrolls with no new content
        
        while scrolls < max_scrolls:
            # Scroll down in smaller increments for better loading
            current_position = self.driver.execute_script("return window.pageYOffset;")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            
            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # If height hasn't changed, increment no_change_count
            if new_height == last_height:
                no_change_count += 1
                # If no new content for 3 consecutive scrolls, stop
                if no_change_count >= 3:
                    logger.debug(f"Stopped scrolling: no new content detected after {no_change_count} scrolls")
                    break
            else:
                no_change_count = 0  # Reset counter when new content is found
            
            last_height = new_height
            scrolls += 1
        
        logger.debug(f"Scrolled {scrolls} times to load more content")
    
    def _init_driver(self):
        """
        Initialize the Chrome driver with stealth options.
        Tries undetected_chromedriver first, falls back to regular selenium with stealth options.
        """
        try:
            if UC_AVAILABLE:
                # Use undetected_chromedriver if available
                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                self.driver = uc.Chrome(options=options)
                logger.info("Initialized undetected Chrome driver")
            else:
                # Fallback to regular selenium with stealth options
                options = Options()
                if self.headless:
                    options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                self.driver = webdriver.Chrome(options=options)
                # Execute stealth script to hide webdriver property
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
                logger.info("Initialized regular Chrome driver with stealth options")
            
            self.driver.set_page_load_timeout(30)
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def _extract_tweet_data(self, article_element) -> Optional[Dict]:
        """
        Extract tweet data from an article element, handling different tweet types.
        
        Args:
            article_element: Selenium WebElement representing a tweet article
        
        Returns:
            Dictionary with 'date', 'content', 'tweet_date' (datetime), 'tweet_type', 'engagement', or None if extraction fails
        """
        try:
            # Detect tweet type (regular, reply, retweet, quote)
            tweet_type = 'tweet'  # Default
            try:
                # Check for reply indicator
                reply_indicators = article_element.find_elements(By.CSS_SELECTOR, "[data-testid='reply']")
                if reply_indicators:
                    # Check if this is a reply (has "Replying to" text)
                    article_text = article_element.text.lower()
                    if 'replying to' in article_text:
                        tweet_type = 'reply'
                
                # Check for retweet indicator
                retweet_indicators = article_element.find_elements(By.CSS_SELECTOR, "[data-testid='retweet']")
                if retweet_indicators and tweet_type == 'tweet':
                    # Check if this is a retweet (has "Retweeted" text or retweet icon)
                    article_text = article_element.text.lower()
                    if 'retweeted' in article_text or len(retweet_indicators) > 0:
                        tweet_type = 'retweet'
                
                # Check for quote tweet
                quote_indicators = article_element.find_elements(By.CSS_SELECTOR, "[data-testid='quote']")
                if quote_indicators and tweet_type == 'tweet':
                    tweet_type = 'quote'
            except:
                pass  # If detection fails, default to 'tweet'
            
            # Extract tweet text
            content = None
            text_selectors = [
                "div[data-testid='tweetText']",
                "div[lang]",
                "span[lang]",
                "[data-testid='tweetText']",
                ".css-901oao"
            ]
            
            for selector in text_selectors:
                try:
                    text_elements = article_element.find_elements(By.CSS_SELECTOR, selector)
                    if text_elements:
                        content_parts = [elem.text for elem in text_elements if elem.text.strip()]
                        if content_parts:
                            content = " ".join(content_parts)
                            break
                except:
                    continue
            
            # Fallback: get all text from the article
            if not content:
                content = article_element.text
            
            # Accept all tweets (even if empty or short) - we want everything FPL-related
            # Only skip if completely empty
            if not content:
                content = ""  # Allow empty content (might have images only)
            
            # Extract images from the tweet
            images = []
            try:
                # Look for image elements in the tweet
                image_selectors = [
                    "img[src*='pbs.twimg.com']",  # Twitter image URLs
                    "img[alt]",  # Images with alt text
                    "img[src]",  # Any image with src
                    "[data-testid='tweet'] img",  # Images within tweet
                    "article img"  # Any image in article
                ]
                
                for selector in image_selectors:
                    try:
                        img_elements = article_element.find_elements(By.CSS_SELECTOR, selector)
                        for img in img_elements:
                            img_src = img.get_attribute('src')
                            img_alt = img.get_attribute('alt') or ''
                            
                            # Only include valid image URLs
                            if img_src and ('http' in img_src or 'data:' in img_src):
                                # Get full resolution image if available (Twitter uses :large, :orig suffixes)
                                if 'pbs.twimg.com' in img_src:
                                    # Try to get original size
                                    if ':large' in img_src:
                                        img_src = img_src.replace(':large', ':orig')
                                    elif ':small' in img_src:
                                        img_src = img_src.replace(':small', ':orig')
                                    elif ':medium' in img_src:
                                        img_src = img_src.replace(':medium', ':orig')
                                
                                images.append({
                                    'url': img_src,
                                    'alt': img_alt
                                })
                    except:
                        continue
                
                # Remove duplicates
                seen_urls = set()
                unique_images = []
                for img in images:
                    if img['url'] not in seen_urls:
                        seen_urls.add(img['url'])
                        unique_images.append(img)
                images = unique_images
            except Exception as e:
                logger.debug(f"Could not extract images: {e}")
            
            # Extract engagement metrics (likes, retweets, replies, quotes)
            engagement = {
                'likes': 0,
                'retweets': 0,
                'replies': 0,
                'quotes': 0
            }
            
            try:
                # Try to find engagement metrics
                # Note: X's structure changes frequently, so we use generic selectors
                engagement_selectors = {
                    'likes': ["[data-testid='like']", "[aria-label*='like']", "[aria-label*='Like']"],
                    'retweets': ["[data-testid='retweet']", "[aria-label*='retweet']", "[aria-label*='Retweet']"],
                    'replies': ["[data-testid='reply']", "[aria-label*='reply']", "[aria-label*='Reply']"],
                    'quotes': ["[data-testid='quote']", "[aria-label*='quote']", "[aria-label*='Quote']"]
                }
                
                for metric, selectors in engagement_selectors.items():
                    for selector in selectors:
                        try:
                            elements = article_element.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                # Try to extract the number from aria-label or text
                                for elem in elements:
                                    aria_label = elem.get_attribute('aria-label') or ''
                                    text = elem.text or ''
                                    # Look for numbers in aria-label or text
                                    numbers = re.findall(r'\d+', aria_label + ' ' + text)
                                    if numbers:
                                        try:
                                            engagement[metric] = int(numbers[0])
                                            break
                                        except:
                                            pass
                                if engagement[metric] > 0:
                                    break
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Could not extract engagement metrics: {e}")
            
            # Extract date/time
            date_str = None
            tweet_datetime = None
            
            # Try to find time element with datetime attribute
            try:
                time_elements = article_element.find_elements(By.CSS_SELECTOR, "time")
                if time_elements:
                    date_attr = time_elements[0].get_attribute("datetime")
                    if date_attr:
                        try:
                            # Parse ISO format datetime and convert to timezone-naive
                            tweet_datetime = datetime.fromisoformat(date_attr.replace('Z', '+00:00'))
                            # Convert to timezone-naive for comparison
                            if tweet_datetime.tzinfo:
                                tweet_datetime = tweet_datetime.replace(tzinfo=None)
                            date_str = date_attr
                        except:
                            # Try parsing the text content of time element
                            time_text = time_elements[0].text
                            if time_text:
                                tweet_datetime = self._parse_tweet_date(time_text)
                                date_str = time_text
            except:
                pass
            
            # If no time element found, try to find relative time in text
            if not tweet_datetime:
                # Look for relative time patterns in the article text
                article_text = article_element.text
                # Try to find patterns like "2h", "1d ago", etc. - look near the end where timestamps usually are
                # Split text and check last few parts
                text_parts = article_text.split()
                if len(text_parts) > 3:
                    # Check last 3-5 words for time patterns
                    last_words = " ".join(text_parts[-5:])
                    relative_pattern = r'(\d+\s*(?:h|m|d|w|hour|hours|minute|minutes|day|days|week|weeks)\s*(?:ago)?)'
                    match = re.search(relative_pattern, last_words, re.IGNORECASE)
                    if match:
                        tweet_datetime = self._parse_tweet_date(match.group(1))
                        date_str = match.group(1)
            
            # Default to current time if we can't parse (timezone-naive)
            if not tweet_datetime:
                tweet_datetime = datetime.now().replace(tzinfo=None)
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                'date': date_str,
                'tweet_date': tweet_datetime,
                'content': content.strip() if content else "",
                'tweet_type': tweet_type,
                'engagement': engagement,
                'images': images,
                'has_images': len(images) > 0
            }
        except Exception as e:
            logger.debug(f"Error extracting tweet data: {e}")
            return None
    
    def _scrape_user_tweets_with_retry(self, username: str) -> List[Dict]:
        """
        Scrape tweets with retry logic for handling timeouts and recoverable errors.
        
        Args:
            username: Twitter username (without @)
        
        Returns:
            List of dictionaries with tweet data
        """
        for attempt in range(self.max_retries + 1):
            try:
                return self._scrape_user_tweets(username)
            except (TimeoutException, Exception) as e:
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * self.delay_between_requests
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} for {username} after {wait_time:.1f}s (error: {type(e).__name__})")
                    time.sleep(wait_time)
                    # Try to recover driver if session expired
                    try:
                        if self.driver:
                            self.driver.current_url
                    except:
                        logger.info(f"Reinitializing driver for {username} retry...")
                        self._init_driver()
                else:
                    logger.error(f"Failed to scrape {username} after {self.max_retries} retries: {e}")
                    return []
        return []
    
    def _scrape_user_tweets(self, username: str) -> List[Dict]:
        """
        Scrape all tweets from the last N days from a user's profile.
        
        Args:
            username: Twitter username (without @)
        
        Returns:
            List of dictionaries with 'date', 'username', 'content', 'tweet_date'
        """
        if not self.driver:
            self._init_driver()
        
        url = f"https://x.com/{username}"
        tweets = []
        
        try:
            logger.info(f"Scraping {username} (collecting tweets from last {self.days_back} days)...")
            self.driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
            
            # Wait for content to render
            time.sleep(3)
            
            # Scroll to load more tweets (scroll more to get recent tweets)
            self._scroll_and_wait(scroll_pause_time=2.0, max_scrolls=40)
            
            # Scroll back to top to ensure we have the most recent tweets
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Find all article elements (tweets)
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            
            if not articles:
                logger.warning(f"No tweets found for {username}")
                return []
            
            logger.info(f"Found {len(articles)} tweet elements for {username}, extracting data...")
            
            # Extract data from each tweet
            seen_content = set()  # Deduplicate by content
            tweets_checked = 0
            tweets_in_range = 0
            tweets_out_of_range = 0
            
            for article in articles:
                tweet_data = self._extract_tweet_data(article)
                
                if not tweet_data:
                    continue
                
                tweets_checked += 1
                
                # Deduplicate
                content_hash = hash(tweet_data['content'])
                if content_hash in seen_content:
                    continue
                seen_content.add(content_hash)
                
                # Filter by date (only last N days)
                tweet_date = tweet_data.get('tweet_date')
                if tweet_date:
                    if self._is_tweet_within_date_range(tweet_date):
                        tweet_data['username'] = username
                        tweets.append(tweet_data)
                        tweets_in_range += 1
                    else:
                        tweets_out_of_range += 1
                        # Log first few out-of-range tweets for debugging
                        if tweets_out_of_range <= 2:
                            logger.debug(f"Tweet from {tweet_date} is older than {self.days_back} days (cutoff: {self.cutoff_date})")
                else:
                    # ALWAYS include tweets with unparseable dates (better to have data than miss it)
                    # This handles cases where X's date format isn't recognized
                    logger.debug(f"Including tweet with unparseable date for {username} (content: {tweet_data['content'][:50]}...)")
                    tweet_data['username'] = username
                    tweets.append(tweet_data)
                    tweets_in_range += 1
            
            if tweets_checked > 0:
                logger.info(f"Checked {tweets_checked} tweets for {username}: {tweets_in_range} in range, {tweets_out_of_range} out of range")
            
            logger.info(f"Successfully scraped {len(tweets)} tweets from {username} (last {self.days_back} days)")
            return tweets
            
        except TimeoutException:
            logger.warning(f"Timeout while scraping {username}")
            return []
        except NoSuchElementException as e:
            logger.warning(f"Element not found for {username}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scraping {username}: {e}")
            return []
    
    def scrape_all_experts(self) -> pd.DataFrame:
        """
        Scrape all tweets from the last N days from all FPL expert accounts.
        
        Returns:
            DataFrame with columns: date, username, content, tweet_date
        """
        if not self.driver:
            self._init_driver()
        
        all_tweets = []
        
        for i, username in enumerate(self.fpl_experts):
            try:
                # Check if driver is still valid
                if self.driver:
                    try:
                        # Quick check if session is still alive
                        self.driver.current_url
                    except:
                        logger.warning(f"Browser session expired, reinitializing...")
                        self._init_driver()
                
                # Use retry logic for scraping
                tweets = self._scrape_user_tweets_with_retry(username)
                if tweets:
                    all_tweets.extend(tweets)
                
                # Delay between requests to avoid IP bans
                if i < len(self.fpl_experts) - 1:  # Don't delay after last request
                    time.sleep(self.delay_between_requests)
                    
            except Exception as e:
                logger.error(f"Failed to scrape {username} after all retries: {e}")
                # Try to recover by reinitializing driver
                try:
                    if self.driver:
                        self.driver.quit()
                    self._init_driver()
                except:
                    pass
                continue
        
        if not all_tweets:
            logger.warning("No tweets scraped from any expert")
            return pd.DataFrame(columns=['date', 'username', 'content', 'tweet_type', 'engagement', 'images', 'has_images'])
        
        df = pd.DataFrame(all_tweets)
        # Remove tweet_date column for final output (keep only date string)
        if 'tweet_date' in df.columns:
            df = df.drop(columns=['tweet_date'])
        
        # Flatten engagement dict into separate columns for easier analysis
        if 'engagement' in df.columns:
            engagement_df = pd.json_normalize(df['engagement'])
            engagement_df.columns = [f'engagement_{col}' for col in engagement_df.columns]
            df = pd.concat([df.drop(columns=['engagement']), engagement_df], axis=1)
        
        # Keep images as list (don't flatten - preserve structure)
        # Images column will contain list of dicts with 'url' and 'alt'
        
        unique_accounts = df['username'].nunique()
        tweet_types = df.get('tweet_type', pd.Series()).value_counts().to_dict() if 'tweet_type' in df.columns else {}
        tweets_with_images = df.get('has_images', pd.Series()).sum() if 'has_images' in df.columns else 0
        logger.info(f"Successfully scraped {len(df)} tweets from {unique_accounts} experts (last {self.days_back} days)")
        if tweet_types:
            logger.info(f"Tweet types: {tweet_types}")
        if tweets_with_images > 0:
            logger.info(f"Tweets with images: {tweets_with_images}")
        return df
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures driver is closed."""
        self.close()

