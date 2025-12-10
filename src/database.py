"""
Database layer for FPL Optimizer.
v4.3: Added Robust Network Retries & Timeout Handling
"""
import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text, Column, Integer, String, Float, Boolean, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

logger = logging.getLogger(__name__)
load_dotenv()
Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.db_connection_string = os.getenv('DB_CONNECTION_STRING')
        
        if not all([self.supabase_url, self.supabase_key, self.db_connection_string]):
            raise ValueError("Missing environment variables.")
        
        # INCREASE TIMEOUT: Set timeout to 60 seconds for slow connections
        try:
            options = ClientOptions(post_timeout=60)
            self.supabase_client: Client = create_client(self.supabase_url, self.supabase_key, options=options)
        except:
            # Fallback for older supabase versions
            self.supabase_client: Client = create_client(self.supabase_url, self.supabase_key)

        # Improved connection pool settings for better reliability
        # Reduced pool_size to 1 to avoid exhausting Supabase session mode pooler
        try:
            # Try with pool_pre_ping (available in SQLAlchemy 1.2+)
            self.engine = create_engine(
                self.db_connection_string,
                pool_size=1,  # Minimal pool to avoid "MaxClientsInSessionMode" errors
                max_overflow=0,  # No overflow connections
                pool_recycle=3600,
                pool_pre_ping=True,  # Verify connections before using
                connect_args={
                    'connect_timeout': 10  # Shorter timeout
                }
            )
        except TypeError:
            # Fallback for older SQLAlchemy versions
            self.engine = create_engine(
                self.db_connection_string,
                pool_size=1,
                max_overflow=0,
                pool_recycle=3600
            )
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_user_credentials_table(self):
        """
        Create user_credentials table for password authentication.
        Prepared for future use - table will be created but not used until password feature is enabled.
        """
        try:
            # Check if table exists
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'user_credentials'
                    )
                """))
                exists = result.scalar()
                
                if not exists:
                    conn.execute(text("""
                        CREATE TABLE user_credentials (
                            team_id INTEGER PRIMARY KEY NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()
                    logger.info("Created user_credentials table")
                else:
                    logger.debug("user_credentials table already exists")
        except Exception as e:
            logger.warning(f"Could not create user_credentials table: {e}")
            # Don't fail if table creation fails - it's optional for now

    def create_tables(self):
        """
        Verify/create database tables. Uses REST API first to check if tables exist,
        avoiding PostgreSQL connection pool exhaustion. Only tries PostgreSQL if REST API fails.
        """
        # PRIMARY: Check if tables are accessible via REST API (no connection pool needed)
        # If REST API works, tables exist and we can skip PostgreSQL table creation
        try:
            # Try to access a key table via REST API
            result = self.supabase_client.table('current_season_history').select('player_id').limit(1).execute()
            # If we can query the table, it exists - no need to create via PostgreSQL
            logger.info("Database tables verified via REST API (tables exist).")
            return True
        except Exception as rest_error:
            # REST API failed - table might not exist, try PostgreSQL as fallback
            logger.debug(f"REST API table check failed: {rest_error}, trying PostgreSQL...")
        
        # FALLBACK: Try PostgreSQL table creation (only if REST API suggests tables don't exist)
        # But use minimal retries to avoid connection pool exhaustion
        max_retries = 1  # Only 1 retry to avoid exhausting pool
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.debug(f"Retrying PostgreSQL table creation (attempt {attempt + 1})...")
                    self.engine.dispose()
                    time.sleep(2)
                
                # Try to create tables via PostgreSQL
                Base.metadata.create_all(bind=self.engine)
                # Create user_credentials table (prepared for future password auth)
                self.create_user_credentials_table()
                logger.info("Database tables created/verified via PostgreSQL.")
                return True
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"PostgreSQL table creation failed: {e}")
                else:
                    # Don't fail completely - tables might exist but connection is temporary
                    logger.debug(f"Could not create/verify tables via PostgreSQL: {e}")
                    logger.debug("Assuming tables exist (REST API will be used for operations)")
                    return False
        
        return False

    def create_image_tables(self):
        """
        Create image mapping and team logo tables.
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Create player_image_mappings table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS player_image_mappings (
                            id SERIAL PRIMARY KEY,
                            fpl_player_id INTEGER UNIQUE NOT NULL,
                            api_football_player_id INTEGER,
                            image_url TEXT,
                            uploaded_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                    
                    # Create team_logos table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS team_logos (
                            id SERIAL PRIMARY KEY,
                            team_id INTEGER UNIQUE NOT NULL,
                            logo_url TEXT,
                            uploaded_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                    
                    logger.info("Image tables created successfully")
                    return True
        except Exception as e:
            logger.error(f"Error creating image tables: {e}")
            return False
    
    def create_news_summaries_table(self):
        """
        Create news summaries table for storing AI-summarized FPL news.
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
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
                        )
                    """))
                    
                    # Create indexes
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_news_summaries_article_id 
                        ON fpl_news_summaries(article_id)
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_news_summaries_published_date 
                        ON fpl_news_summaries(published_date DESC)
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_news_summaries_relevance 
                        ON fpl_news_summaries(fpl_relevance_score DESC)
                    """))
                    
                    logger.info("News summaries table created successfully")
                    return True
        except Exception as e:
            logger.error(f"Error creating news summaries table: {e}")
            return False
    
    def create_raw_articles_table(self):
        """
        Create raw news articles table for storing FPL news without AI summarization.
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
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
                        )
                    """))
                    
                    # Create indexes
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_news_articles_article_id 
                        ON fpl_news_articles(article_id)
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_news_articles_published_date 
                        ON fpl_news_articles(published_date DESC)
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_news_articles_source 
                        ON fpl_news_articles(source)
                    """))
                    
                    logger.info("Raw news articles table created successfully")
                    return True
        except Exception as e:
            logger.error(f"Error creating raw news articles table: {e}")
            return False
    
    def get_existing_article_ids(self) -> set:
        """
        Get set of existing article IDs for deduplication.
        
        Returns:
            Set of article_id strings
        """
        try:
            result = self._execute_with_retry(
                self.supabase_client.table('fpl_news_summaries').select('article_id')
            )
            if result.data:
                return {row['article_id'] for row in result.data if row.get('article_id')}
            return set()
        except Exception as e:
            logger.warning(f"Error fetching existing article IDs: {e}")
            return set()
    
    def save_news_summary(self, summary_data: Dict) -> bool:
        """
        Save or update a news summary in Supabase.
        
        Args:
            summary_data: Dictionary with article data and AI summary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for insertion
            data = {
                'article_id': summary_data.get('article_id'),
                'title': summary_data.get('title', ''),
                'summary_text': summary_data.get('summary_text', ''),
                'article_url': summary_data.get('article_url', ''),
                'source': summary_data.get('source'),
                'published_date': summary_data.get('published_date'),
                'article_type': summary_data.get('article_type', 'general'),
                'fpl_relevance_score': float(summary_data.get('fpl_relevance_score', 0.0)),
                'key_points': summary_data.get('key_points', []),
                'player_names': summary_data.get('player_names', []),
                'teams': summary_data.get('teams', []),
                'updated_at': datetime.now().isoformat()
            }
            
            # Upsert (insert or update on conflict)
            self._execute_with_retry(
                self.supabase_client.table('fpl_news_summaries').upsert(
                    data, 
                    on_conflict='article_id'
                )
            )
            
            return True
        except Exception as e:
            logger.error(f"Error saving news summary: {e}")
            return False
    
    def get_recent_summaries(self, limit: int = 50, min_relevance: float = 0.3) -> pd.DataFrame:
        """
        Get recent news summaries from database.
        
        Args:
            limit: Maximum number of summaries to return
            min_relevance: Minimum relevance score to include
            
        Returns:
            DataFrame with summaries
        """
        try:
            result = self._execute_with_retry(
                self.supabase_client.table('fpl_news_summaries')
                .select('*')
                .gte('fpl_relevance_score', min_relevance)
                .order('published_date', desc=True)
                .limit(limit)
            )
            
            if result.data:
                return pd.DataFrame(result.data)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching recent summaries: {e}")
            return pd.DataFrame()
    
    def get_news_articles(self, limit: int = 50, offset: int = 0, days_back: Optional[int] = None) -> Tuple[pd.DataFrame, int]:
        """
        Get news articles from database with pagination.
        
        Args:
            limit: Maximum number of articles to return
            offset: Number of articles to skip
            days_back: Optional number of days to look back
            
        Returns:
            Tuple of (DataFrame with articles, total count)
        """
        try:
            query = self.supabase_client.table('fpl_news_articles').select('*', count='exact')
            
            if days_back:
                from datetime import datetime, timedelta
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                query = query.gte('published_date', cutoff_date)
            
            query = query.order('published_date', desc=True).range(offset, offset + limit - 1)
            
            result = self._execute_with_retry(query)
            
            if result.data:
                df = pd.DataFrame(result.data)
                total_count = result.count if hasattr(result, 'count') and result.count is not None else len(df)
                return df, total_count
            return pd.DataFrame(), 0
        except Exception as e:
            logger.error(f"Error fetching news articles: {e}")
            return pd.DataFrame(), 0
    
    def get_news_article_by_id(self, article_id: str) -> Optional[Dict]:
        """
        Get a single news article by ID.
        
        Args:
            article_id: Article ID
            
        Returns:
            Dictionary with article data or None
        """
        try:
            result = self._execute_with_retry(
                self.supabase_client.table('fpl_news_articles')
                .select('*')
                .eq('article_id', article_id)
                .single()
            )
            
            if result.data:
                return result.data
            return None
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {e}")
            return None
    
    def get_player_image_url(self, player_id: int) -> Optional[str]:
        """
        Get player image URL from database.
        
        Args:
            player_id: FPL player ID
            
        Returns:
            Image URL or None
        """
        try:
            result = self._execute_with_retry(
                self.supabase_client.table('player_image_mappings')
                .select('image_url')
                .eq('fpl_player_id', player_id)
                .single()
            )
            
            if result.data and result.data.get('image_url'):
                return result.data['image_url']
            return None
        except Exception as e:
            logger.debug(f"Error fetching player image for {player_id}: {e}")
            return None
    
    def get_player_image_urls(self, player_ids: List[int]) -> Dict[int, Optional[str]]:
        """
        Get multiple player image URLs.
        
        Args:
            player_ids: List of FPL player IDs
            
        Returns:
            Dictionary mapping player_id -> image_url
        """
        results = {}
        for player_id in player_ids:
            results[player_id] = self.get_player_image_url(player_id)
        return results
    
    def get_team_logo_url(self, team_id: int) -> Optional[str]:
        """
        Get team logo URL from database.
        
        Args:
            team_id: FPL team ID
            
        Returns:
            Logo URL or None
        """
        try:
            result = self._execute_with_retry(
                self.supabase_client.table('team_logos')
                .select('logo_url')
                .eq('team_id', team_id)
                .single()
            )
            
            if result.data and result.data.get('logo_url'):
                return result.data['logo_url']
            return None
        except Exception as e:
            logger.debug(f"Error fetching team logo for {team_id}: {e}")
            return None
    
    def get_all_team_logos(self) -> Dict[int, Optional[str]]:
        """
        Get all team logo URLs.
        
        Returns:
            Dictionary mapping team_id -> logo_url
        """
        try:
            result = self._execute_with_retry(
                self.supabase_client.table('team_logos')
                .select('team_id, logo_url')
            )
            
            if result.data:
                return {item['team_id']: item.get('logo_url') for item in result.data}
            return {}
        except Exception as e:
            logger.error(f"Error fetching all team logos: {e}")
            return {}
    
    def reset_history_tables(self):
        """Drops history tables to allow schema reconstruction."""
        try:
            # Use context manager with transaction for proper connection management
            with self.engine.connect() as conn:
                with conn.begin():  # Use transaction for atomicity
                    conn.execute(text("DROP TABLE IF EXISTS player_history CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS current_season_history CASCADE"))
            logger.info("History tables dropped. Recreating with new schema...")
            self.create_tables()
        except Exception as e:
            logger.error(f"Error resetting tables: {e}")

    # --- HELPER FOR RETRIES ---
    def _execute_with_retry(self, operation, max_retries=3):
        """Executes a Supabase operation with exponential backoff."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return operation.execute()
            except Exception as e:
                last_error = e
                wait_time = 2 * (attempt + 1)
                logger.warning(f"   ⚠️ Database timeout/error. Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
        
        raise last_error

    # --- SAVING METHODS ---
    def save_player_history(self, data: List[Dict]) -> bool:
        """
        Save player history with proper connection management.
        """
        try:
            if not data: return True
            df = pd.DataFrame(data)
            # Use context manager to ensure connection is properly closed
            with self.engine.connect() as conn:
                with conn.begin():  # Use transaction for atomicity
                    df.to_sql('player_history', conn, if_exists='append', index=False, method='multi', chunksize=1000)
            logger.info(f"Saved {len(data)} archived records.")
            return True
        except Exception as e:
            logger.error(f"Error saving archive: {e}")
            return False

    def save_current_season_history(self, data: List[Dict]) -> bool:
        try:
            if not data: return True
            batch_size = 500
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                # Use retry logic for heavy writes
                self._execute_with_retry(
                    self.supabase_client.table('current_season_history').upsert(batch, on_conflict='player_id, gw')
                )
            logger.info(f"Saved {len(data)} live records.")
            return True
        except Exception as e:
            logger.error(f"Error saving live history: {e}")
            return False
            
    # --- FETCHING METHODS ---
    def get_player_history(self) -> pd.DataFrame:
        """
        Get player history with minimal retries to avoid connection pool exhaustion.
        Uses proper connection management to ensure connections are closed.
        """
        max_retries = 1  # Minimal retries to avoid pool exhaustion
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.debug(f"Retrying PostgreSQL connection (attempt {attempt + 1})...")
                    self.engine.dispose()
                    time.sleep(2)
                
                # Use context manager to ensure connection is properly closed
                with self.engine.connect() as conn:
                    result = pd.read_sql("SELECT * FROM player_history", conn)
                    return result
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"PostgreSQL connection error: {e}")
                else:
                    logger.error(f"Error fetching archive: {e}")
        
        return pd.DataFrame()

    def get_current_season_history(self) -> pd.DataFrame:
        """
        Get current season history using Supabase REST API (primary) with PostgreSQL fallback.
        This avoids connection pool exhaustion issues.
        """
        # PRIMARY: Try Supabase REST API first (no connection pool issues)
        try:
            logger.debug("Fetching current_season_history via Supabase REST API...")
            result = self._execute_with_retry(
                self.supabase_client.table('current_season_history').select('*')
            )
            
            if result.data:
                df = pd.DataFrame(result.data)
                logger.debug(f"Loaded {len(df)} records via REST API")
                return df
        except Exception as e:
            logger.debug(f"Supabase REST API failed, trying PostgreSQL: {e}")
        
        # FALLBACK: Try PostgreSQL (with minimal retries to avoid pool exhaustion)
        max_retries = 1  # Only 1 retry to avoid exhausting pool
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.debug(f"Retrying PostgreSQL connection (attempt {attempt + 1})...")
                    self.engine.dispose()
                    time.sleep(2)
                
                # Use context manager to ensure connection is properly closed
                with self.engine.connect() as conn:
                    result = pd.read_sql("SELECT * FROM current_season_history", conn)
                    logger.debug(f"Loaded {len(result)} records via PostgreSQL")
                    return result
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"PostgreSQL connection error: {e}")
                    logger.warning("Falling back to empty DataFrame to avoid pool exhaustion")
                else:
                    logger.error(f"Error fetching live history: {e}")
        
        # Return empty DataFrame if both methods fail (non-destructive)
        logger.warning("Could not fetch current_season_history, returning empty DataFrame")
        return pd.DataFrame()

    def health_check(self):
        """
        Health check using Supabase REST API (no connection pool needed).
        This avoids exhausting the PostgreSQL connection pool during initialization.
        """
        try:
            # Use REST API to check if Supabase is accessible
            # Try a simple query that doesn't require tables to exist
            result = self.supabase_client.table('current_season_history').select('player_id').limit(1).execute()
            return {'status': 'healthy', 'method': 'rest_api'}
        except Exception as e:
            # If REST API fails, try PostgreSQL as fallback (but don't fail initialization)
            try:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return {'status': 'healthy', 'method': 'postgresql'}
            except Exception as pg_error:
                logger.debug(f"Health check failed (REST API: {e}, PostgreSQL: {pg_error})")
                return {'status': 'unhealthy'}
    
    def save_decision(self, gw: int, recommended_transfers: Dict, actual_transfers: List = None, entry_id: int = None) -> bool:
        try:
            data = {
                'gw': gw,
                'recommended_transfers': str(recommended_transfers),
                'actual_transfers_made': str(actual_transfers or []),
                'created_at': datetime.utcnow().isoformat()
            }
            if entry_id is not None:
                data['entry_id'] = entry_id
            self._execute_with_retry(self.supabase_client.table('decisions').insert(data))
            logger.info("Transfer decision recorded successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving decision: {e}")
            return False
    
    def save_predictions(self, predictions: List[Dict]) -> bool:
        try:
            if not predictions: return True
            
            timestamp = datetime.utcnow().isoformat()
            clean_predictions = []
            
            for p in predictions:
                clean_record = {
                    'player_id': p.get('player_id'),
                    'gw': p.get('gw'),
                    'predicted_ev': p.get('predicted_ev'),
                    'confidence_score': p.get('confidence_score'),
                    'model_version': p.get('model_version'),
                    'created_at': timestamp
                }
                clean_predictions.append(clean_record)
            
            # Batch saving to prevent timeouts (chunks of 200)
            batch_size = 200
            total = len(clean_predictions)
            
            for i in range(0, total, batch_size):
                batch = clean_predictions[i:i+batch_size]
                try:
                    self._execute_with_retry(self.supabase_client.table('predictions').upsert(batch))
                except Exception as e:
                    logger.error(f"Failed to save batch {i}-{i+batch_size}: {e}")
            
            logger.info(f"Saved {total} predictions to DB.")
            return True
        except Exception as e:
            logger.error(f"Error saving predictions (Non-fatal): {e}")
            return True
    
    # --- LEARNING SYSTEM: Retrieve past decisions ---
    def get_decisions(self, entry_id: int = None, min_gw: int = None, max_gw: int = None) -> pd.DataFrame:
        """
        Retrieve past transfer decisions from the database.
        
        Args:
            entry_id: Optional entry ID to filter by
            min_gw: Optional minimum gameweek
            max_gw: Optional maximum gameweek
        
        Returns:
            DataFrame with decision records
        """
        try:
            query = self.supabase_client.table('decisions').select('*')
            
            if entry_id is not None:
                query = query.eq('entry_id', entry_id)
            if min_gw is not None:
                query = query.gte('gw', min_gw)
            if max_gw is not None:
                query = query.lte('gw', max_gw)
            
            result = query.order('gw', desc=True).execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                # Parse string representations back to dicts/lists
                if 'recommended_transfers' in df.columns:
                    df['recommended_transfers'] = df['recommended_transfers'].apply(
                        lambda x: eval(x) if isinstance(x, str) else x
                    )
                if 'actual_transfers_made' in df.columns:
                    df['actual_transfers_made'] = df['actual_transfers_made'].apply(
                        lambda x: eval(x) if isinstance(x, str) and x else []
                    )
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"Error retrieving decisions: {e}")
            return pd.DataFrame()
    
    def get_predictions_for_gw(self, gw: int, model_version: str = None) -> pd.DataFrame:
        """
        Retrieve predictions for a specific gameweek.
        
        Args:
            gw: Gameweek number
            model_version: Optional model version filter
        
        Returns:
            DataFrame with predictions
        """
        try:
            query = self.supabase_client.table('predictions').select('*').eq('gw', gw)
            if model_version:
                query = query.eq('model_version', model_version)
            
            result = query.execute()
            if result.data:
                return pd.DataFrame(result.data)
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"Error retrieving predictions for GW{gw}: {e}")
            return pd.DataFrame()

# --- SCHEMA DEFINITIONS (Unchanged) ---

class PlayerHistory(Base):
    __tablename__ = 'player_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String)
    season = Column(String)
    gw = Column(Integer)
    element_type = Column(Integer, default=0)
    minutes = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    bonus = Column(Integer, default=0)
    bps = Column(Integer, default=0)
    xg = Column(Float, default=0.0)
    xa = Column(Float, default=0.0)
    influence = Column(Float, default=0.0)
    creativity = Column(Float, default=0.0)
    threat = Column(Float, default=0.0)
    ict_index = Column(Float, default=0.0)
    goals_scored = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    clean_sheets = Column(Integer, default=0)
    goals_conceded = Column(Integer, default=0)
    own_goals = Column(Integer, default=0)
    penalties_saved = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    penalties_missed = Column(Integer, default=0)
    value = Column(Integer, default=0)
    transfers_balance = Column(Integer, default=0)
    selected = Column(Integer, default=0)
    transfers_in = Column(Integer, default=0)
    transfers_out = Column(Integer, default=0)
    opponent_team = Column(Integer, default=0)
    was_home = Column(Boolean, default=False)

class CurrentSeasonHistory(Base):
    __tablename__ = 'current_season_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String)
    gw = Column(Integer)
    element_type = Column(Integer, default=0)
    minutes = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    bonus = Column(Integer, default=0)
    bps = Column(Integer, default=0)
    xg = Column(Float, default=0.0)
    xa = Column(Float, default=0.0)
    influence = Column(Float, default=0.0)
    creativity = Column(Float, default=0.0)
    threat = Column(Float, default=0.0)
    ict_index = Column(Float, default=0.0)
    goals_scored = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    clean_sheets = Column(Integer, default=0)
    goals_conceded = Column(Integer, default=0)
    own_goals = Column(Integer, default=0)
    penalties_saved = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    penalties_missed = Column(Integer, default=0)
    value = Column(Integer, default=0)
    transfers_balance = Column(Integer, default=0)
    selected = Column(Integer, default=0)
    transfers_in = Column(Integer, default=0)
    transfers_out = Column(Integer, default=0)
    opponent_team = Column(Integer, default=0)
    was_home = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('player_id', 'gw', name='uix_player_gw'),)

class Predictions(Base):
    __tablename__ = 'predictions'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer)
    gw = Column(Integer)
    predicted_ev = Column(Float)
    model_version = Column(String)
    confidence_score = Column(Float)
    created_at = Column(DateTime)

class UserCredentials(Base):
    """
    User credentials table for password authentication.
    Prepared for future use - not currently enforced.
    """
    __tablename__ = 'user_credentials'
    
    team_id = Column(Integer, primary_key=True, nullable=False, comment='FPL entry/team ID')
    password_hash = Column(String(255), nullable=False, comment='Bcrypt hashed password')
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    def __repr__(self):
        return f"<UserCredentials(team_id={self.team_id})>"


class Decisions(Base):
    __tablename__ = 'decisions'
    id = Column(Integer, primary_key=True)
    gw = Column(Integer)
    recommended_transfers = Column(String)
    actual_transfers_made = Column(String)
    created_at = Column(DateTime)