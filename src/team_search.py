"""
Team Search Module - Searches FPL teams from CSV file stored on server.
Uses SQLite for data storage and rapidfuzz for fuzzy matching in memory.
"""
import csv
import sqlite3
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import threading

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    fuzz = None

logger = logging.getLogger(__name__)

class TeamSearch:
    """Handles searching FPL teams from CSV file using SQLite for storage and rapidfuzz for fuzzy matching."""
    
    def __init__(self, csv_path: str, db_path: Optional[str] = None):
        """
        Initialize team search.
        
        Args:
            csv_path: Path to the CSV file with team data
            db_path: Path to SQLite database (default: csv_path + '.db')
        """
        self.csv_path = Path(csv_path)
        self.db_path = Path(db_path) if db_path else self.csv_path.with_suffix('.db')
        self._lock = threading.Lock()
        self._db_initialized = False
        self.teams_data: List[Dict] = []  # Store all teams in memory for fast fuzzy matching
        self._data_loaded = False
        
    def _ensure_database(self):
        """Load CSV into SQLite database if not already loaded."""
        # Check if database already exists (even if not yet initialized in this instance)
        if self.db_path.exists():
            # Check if database is newer than CSV (or CSV doesn't exist)
            if not self.csv_path.exists() or (self.csv_path.exists() and self.db_path.stat().st_mtime >= self.csv_path.stat().st_mtime):
                # Database exists and is up to date, just load data into memory
                self._db_initialized = True
                self._load_teams_into_memory()
                return
        
        with self._lock:
            # Double-check after acquiring lock
            if self.db_path.exists():
                if not self.csv_path.exists() or (self.csv_path.exists() and self.db_path.stat().st_mtime >= self.csv_path.stat().st_mtime):
                    # Database exists and is up to date
                    self._db_initialized = True
                    self._load_teams_into_memory()
                    return
            
            logger.info(f"Loading CSV into SQLite database: {self.csv_path}")
            
            if not self.csv_path.exists():
                logger.warning(f"CSV file not found: {self.csv_path}")
                self._db_initialized = True
                return
            
            # Only delete database if we need to recreate it (database is older than CSV)
            # Don't delete if database exists and CSV is newer (might be locked by another process)
            if self.db_path.exists():
                try:
                    # Only delete if database is older than CSV
                    if self.csv_path.exists() and self.db_path.stat().st_mtime < self.csv_path.stat().st_mtime:
                        self.db_path.unlink()
                except (PermissionError, OSError) as e:
                    # Database is locked or can't be deleted - use existing database
                    logger.warning(f"Cannot delete existing database (may be in use): {e}. Using existing database.")
                    self._db_initialized = True
                    self._load_teams_into_memory()
                    return
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create table
            cursor.execute("""
                CREATE TABLE teams (
                    team_id INTEGER PRIMARY KEY,
                    team_name TEXT NOT NULL,
                    manager_name TEXT NOT NULL,
                    region TEXT,
                    overall_points INTEGER,
                    overall_rank INTEGER
                )
            """)
            
            # Create indexes for fast searching
            cursor.execute("CREATE INDEX idx_team_name ON teams(team_name)")
            cursor.execute("CREATE INDEX idx_manager_name ON teams(manager_name)")
            cursor.execute("CREATE INDEX idx_team_name_lower ON teams(LOWER(team_name))")
            cursor.execute("CREATE INDEX idx_manager_name_lower ON teams(LOWER(manager_name))")
            
            # Load CSV data
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                batch = []
                for row in reader:
                    batch.append((
                        int(row['id']),
                        row['team_name'],
                        row['manager_name'],
                        row.get('region', ''),
                        int(row.get('overall_points', 0)) if row.get('overall_points') else 0,
                        int(row.get('overall_rank', 0)) if row.get('overall_rank') else 0
                    ))
                    
                    if len(batch) >= 10000:  # Insert in batches
                        cursor.executemany(
                            "INSERT INTO teams VALUES (?, ?, ?, ?, ?, ?)",
                            batch
                        )
                        batch = []
                
                # Insert remaining
                if batch:
                    cursor.executemany(
                        "INSERT INTO teams VALUES (?, ?, ?, ?, ?, ?)",
                        batch
                    )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database created successfully: {self.db_path}")
            self._db_initialized = True
            
            # Load all records into memory for fast fuzzy matching
            self._load_teams_into_memory()
    
    def _load_teams_into_memory(self):
        """Load all team records from SQLite database into memory."""
        if self._data_loaded and self.teams_data:
            return
        
        with self._lock:
            # Double-check after acquiring lock
            if self._data_loaded and self.teams_data:
                return
            
            if not self.db_path.exists():
                logger.warning("Database not available, cannot load teams into memory")
                return
            
            if not RAPIDFUZZ_AVAILABLE:
                error_msg = "[TeamSearch] rapidfuzz library is not available. Please install it with: pip install rapidfuzz>=3.0.0"
                logger.error(error_msg)
                print(error_msg)
                # Don't return - try to load data anyway and see what happens
                # return
            
            logger.info(f"[TeamSearch] Loading teams from database into memory: {self.db_path}")
            print(f"[TeamSearch] Loading teams from database into memory: {self.db_path}")
            
            try:
                conn = sqlite3.connect(str(self.db_path), timeout=30)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Load all teams from database
                logger.info("[TeamSearch] Executing SELECT query to load teams...")
                print("[TeamSearch] Executing SELECT query to load teams...")
                cursor.execute("SELECT team_id, team_name, manager_name FROM teams")
                rows = cursor.fetchall()
                logger.info(f"[TeamSearch] Fetched {len(rows)} rows from database")
                print(f"[TeamSearch] Fetched {len(rows)} rows from database")
                
                self.teams_data = []
                for row in rows:
                    self.teams_data.append({
                        'team_id': row['team_id'],
                        'team_name': row['team_name'],
                        'manager_name': row['manager_name']
                    })
                
                conn.close()
                
                logger.info(f"[TeamSearch] Loaded {len(self.teams_data):,} teams into memory")
                print(f"[TeamSearch] Loaded {len(self.teams_data):,} teams into memory")
                self._data_loaded = True
            except Exception as e:
                error_msg = f"[TeamSearch] Error loading teams into memory: {e}"
                logger.error(error_msg, exc_info=True)
                print(error_msg)
                import traceback
                traceback_str = traceback.format_exc()
                logger.error(f"[TeamSearch] Traceback: {traceback_str}")
                print(f"[TeamSearch] Traceback: {traceback_str}")
                raise
    
    def search(self, query: str, limit: int = 20, similarity_threshold: int = 60) -> List[Dict]:
        """
        Search teams by team name or manager name using fuzzy matching.
        
        Args:
            query: Search query (team name or manager name)
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-100) to include in results
            
        Returns:
            List of matching teams with similarity score (0-100)
        """
        if not query or not query.strip():
            return []
        
        if not RAPIDFUZZ_AVAILABLE:
            logger.error("rapidfuzz library is not available. Please install it with: pip install rapidfuzz>=3.0.0")
            return []
        
        try:
            # Ensure database exists and data is loaded into memory
            logger.info(f"search() called with query='{query}', limit={limit}. _data_loaded={self._data_loaded}, teams_data length={len(self.teams_data) if self.teams_data else 0}")
            self._ensure_database()
            logger.info(f"After _ensure_database(): _data_loaded={self._data_loaded}, teams_data length={len(self.teams_data) if self.teams_data else 0}")
            self._load_teams_into_memory()
            logger.info(f"After _load_teams_into_memory(): _data_loaded={self._data_loaded}, teams_data length={len(self.teams_data) if self.teams_data else 0}")
            
            if not self.teams_data:
                error_msg = f"[TeamSearch] No team data loaded in memory. _data_loaded={self._data_loaded}, teams_data length={len(self.teams_data) if self.teams_data else 0}. Returning empty results."
                logger.error(error_msg)
                print(error_msg)
                return []
            
            # Normalize query to lowercase for case-insensitive matching
            query_normalized = query.strip().lower()
            
            if not query_normalized:
                return []
            
            # Calculate similarity scores for all teams
            results = []
            for team in self.teams_data:
                team_name = team['team_name'].lower()
                manager_name = team['manager_name'].lower()
                
                # Calculate similarity scores using rapidfuzz
                team_score = fuzz.ratio(query_normalized, team_name)
                manager_score = fuzz.ratio(query_normalized, manager_name)
                
                # Take the maximum similarity score (best match)
                similarity = max(team_score, manager_score)
                
                # Filter by threshold
                if similarity >= similarity_threshold:
                    results.append({
                        'team_id': team['team_id'],
                        'team_name': team['team_name'],  # Keep original case
                        'manager_name': team['manager_name'],  # Keep original case
                        'similarity': float(similarity) / 100.0  # Convert to 0-1 range for compatibility
                    })
            
            # Sort by similarity (highest first) and return top results
            sorted_results = sorted(results, key=lambda x: x['similarity'], reverse=True)
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching teams: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

