#!/usr/bin/env python3
"""
Script to initialize TeamSearch and trigger database creation and data loading.
This will:
1. Create TeamSearch object
2. Create SQLite database from CSV (if needed)
3. Load all records into memory
"""
import sys
import os
sys.path.insert(0, 'src')

try:
    from team_search import TeamSearch
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    csv_path = r"C:\fpl-api\fpl_teams_full.csv"
    
    logger.info(f"Initializing TeamSearch with CSV: {csv_path}")
    logger.info(f"CSV file exists: {os.path.exists(csv_path)}")
    
    # Check if database already exists
    db_path = csv_path.replace('.csv', '.db')
    db_exists = os.path.exists(db_path)
    logger.info(f"Database file exists: {db_exists} at {db_path}")
    
    # Create TeamSearch instance
    ts = TeamSearch(csv_path)
    logger.info("TeamSearch object created successfully")
    
    # Check if database needs to be created
    if not db_exists:
        # Trigger database initialization by calling _ensure_database
        logger.info("Database does not exist. Creating SQLite database from CSV...")
        logger.info("This will take 5-10 minutes for 10M+ records...")
        ts._ensure_database()
        logger.info("✅ Database created successfully!")
    else:
        logger.info("Database already exists, will load from existing database...")
    
    # Trigger data loading by calling _load_teams_into_memory
    logger.info("Loading teams into memory (this will take 30-60 seconds for 10M+ records)...")
    logger.info("Waiting for database lock to be released (max 30 seconds)...")
    
    # Retry with timeout if database is locked
    max_retries = 30
    retry_count = 0
    loaded = False
    
    while retry_count < max_retries and not loaded:
        try:
            ts._load_teams_into_memory()
            logger.info(f"✅ Loaded {len(ts.teams_data):,} teams into memory")
            loaded = True
        except Exception as e:
            if "database is locked" in str(e) and retry_count < max_retries - 1:
                retry_count += 1
                logger.info(f"Database locked, waiting 1 second (attempt {retry_count}/{max_retries})...")
                import time
                time.sleep(1)
            else:
                raise
    
    if not loaded:
        raise Exception("Failed to load data after 30 retries - database may be locked by another process")
    
    # Test a search to verify everything works
    logger.info("Testing search with 'shaolin soccer xi'...")
    results = ts.search("shaolin soccer xi", limit=5)
    logger.info(f"Search returned {len(results)} results")
    for i, result in enumerate(results, 1):
        logger.info(f"  {i}. {result['team_name']} (ID: {result['team_id']}, similarity: {result['similarity']:.2f})")
    
    logger.info("✅ Initialization complete! TeamSearch is ready to use.")
    
except Exception as e:
    logger.error(f"❌ Error during initialization: {e}", exc_info=True)
    sys.exit(1)

