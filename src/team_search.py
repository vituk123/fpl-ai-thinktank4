"""
Team Search Module - Searches FPL teams from CSV file stored on server.
Uses SQLite for fast searching of large datasets.
"""
import csv
import sqlite3
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import threading

logger = logging.getLogger(__name__)

class TeamSearch:
    """Handles searching FPL teams from CSV file using SQLite for performance."""
    
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
        
    def _ensure_database(self):
        """Load CSV into SQLite database if not already loaded."""
        if self._db_initialized and self.db_path.exists():
            # Check if database is newer than CSV
            if self.csv_path.exists() and self.db_path.stat().st_mtime >= self.csv_path.stat().st_mtime:
                return
        
        with self._lock:
            # Double-check after acquiring lock
            if self._db_initialized and self.db_path.exists():
                if self.csv_path.exists() and self.db_path.stat().st_mtime >= self.csv_path.stat().st_mtime:
                    return
            
            logger.info(f"Loading CSV into SQLite database: {self.csv_path}")
            
            if not self.csv_path.exists():
                logger.warning(f"CSV file not found: {self.csv_path}")
                self._db_initialized = True
                return
            
            # Create or recreate database
            if self.db_path.exists():
                self.db_path.unlink()
            
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
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search teams by team name or manager name.
        
        Args:
            query: Search query (team name or manager name)
            limit: Maximum number of results to return
            
        Returns:
            List of matching teams with similarity score
        """
        if not query or not query.strip():
            return []
        
        try:
            self._ensure_database()
            
            if not self.db_path.exists():
                logger.warning("Database not available, returning empty results")
                return []
            
            query_lower = query.strip().lower()
            search_pattern = f"%{query_lower}%"
            
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Search both team_name and manager_name using LIKE
            # Calculate simple similarity score based on match position
            results = []
            
            # Search team names
            cursor.execute("""
                SELECT team_id, team_name, manager_name, 
                       CASE 
                           WHEN LOWER(team_name) = ? THEN 1.0
                           WHEN LOWER(team_name) LIKE ? THEN 0.9
                           WHEN LOWER(team_name) LIKE ? THEN 0.8
                           ELSE 0.7
                       END as similarity
                FROM teams
                WHERE LOWER(team_name) LIKE ?
                ORDER BY similarity DESC, team_name
                LIMIT ?
            """, (query_lower, f"{query_lower}%", f"%{query_lower}%", search_pattern, limit))
            
            for row in cursor.fetchall():
                results.append({
                    'team_id': row['team_id'],
                    'team_name': row['team_name'],
                    'manager_name': row['manager_name'],
                    'similarity': row['similarity']
                })
            
            # Get team IDs already found to avoid duplicates
            found_team_ids = {r['team_id'] for r in results}
            placeholders = ','.join(['?' for _ in found_team_ids]) if found_team_ids else '0'
            
            # Search manager names (excluding already found teams)
            if found_team_ids:
                cursor.execute(f"""
                    SELECT team_id, team_name, manager_name,
                           CASE 
                               WHEN LOWER(manager_name) = ? THEN 1.0
                               WHEN LOWER(manager_name) LIKE ? THEN 0.9
                               WHEN LOWER(manager_name) LIKE ? THEN 0.8
                               ELSE 0.7
                           END as similarity
                    FROM teams
                    WHERE LOWER(manager_name) LIKE ?
                      AND team_id NOT IN ({placeholders})
                    ORDER BY similarity DESC, manager_name
                    LIMIT ?
                """, (query_lower, f"{query_lower}%", f"%{query_lower}%", search_pattern, *found_team_ids, limit))
            else:
                cursor.execute("""
                    SELECT team_id, team_name, manager_name,
                           CASE 
                               WHEN LOWER(manager_name) = ? THEN 1.0
                               WHEN LOWER(manager_name) LIKE ? THEN 0.9
                               WHEN LOWER(manager_name) LIKE ? THEN 0.8
                               ELSE 0.7
                           END as similarity
                    FROM teams
                    WHERE LOWER(manager_name) LIKE ?
                    ORDER BY similarity DESC, manager_name
                    LIMIT ?
                """, (query_lower, f"{query_lower}%", f"%{query_lower}%", search_pattern, limit))
            
            for row in cursor.fetchall():
                results.append({
                    'team_id': row['team_id'],
                    'team_name': row['team_name'],
                    'manager_name': row['manager_name'],
                    'similarity': row['similarity']
                })
            
            conn.close()
            
            # Deduplicate and sort by similarity
            seen = {}
            for result in results:
                team_id = result['team_id']
                if team_id not in seen or result['similarity'] > seen[team_id]['similarity']:
                    seen[team_id] = result
            
            # Sort by similarity (highest first) and return top results
            sorted_results = sorted(seen.values(), key=lambda x: x['similarity'], reverse=True)
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching teams: {e}", exc_info=True)
            return []

