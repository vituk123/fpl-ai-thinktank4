"""
Simple ML Engine Diagnostic Tool for FPL Optimizer
Direct database access to identify data quality issues
"""
import pandas as pd
import numpy as np
import logging
import os
from sqlalchemy import create_engine, text
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def run_sql_query(query):
    """Execute SQL query and return DataFrame"""
    db_connection_string = os.getenv('DB_CONNECTION_STRING')
    engine = create_engine(db_connection_string)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def diagnose_basic_data():
    """Basic diagnostic without complex imports"""
    logger.info("=== ML DATA DIAGNOSTIC TOOL ===")
    
    try:
        # Check if we can access the database
        result = run_sql_query("SELECT COUNT(*) as total_records FROM player_history")
        archive_count = result['total_records'].iloc[0] if len(result) > 0 else 0
        
        result = run_sql_query("SELECT COUNT(*) as total_records FROM current_season_history")
        current_count = result['total_records'].iloc[0] if len(result) > 0 else 0
        
        total_records = archive_count + current_count
        logger.info(f"Total records available: {total_records} (Archive: {archive_count}, Current: {current_count})")
        
        # 1. Check minutes distribution
        logger.info("\n1. MINUTES DISTRIBUTION:")
        minutes_query = """
        SELECT 
            SUM(CASE WHEN minutes = 0 THEN 1 ELSE 0 END) as zero_minutes,
            SUM(CASE WHEN minutes > 0 THEN 1 ELSE 0 END) as played_minutes,
            AVG(CASE WHEN minutes > 0 THEN minutes END) as avg_minutes_when_played,
            MAX(minutes) as max_minutes
        FROM (
            SELECT minutes FROM player_history 
            UNION ALL 
            SELECT minutes FROM current_season_history
        ) combined_data
        """
        
        minutes_stats = run_sql_query(minutes_query)
        if len(minutes_stats) > 0:
            row = minutes_stats.iloc[0]
            logger.info(f"   Zero minutes (DNPs): {row['zero_minutes']}")
            logger.info(f"   Played minutes: {row['played_minutes']}")
            logger.info(f"   Average minutes when played: {row['avg_minutes_when_played']:.1f}")
            logger.info(f"   Max minutes: {row['max_minutes']}")
        
        # 2. Check element_type distribution
        logger.info("\n2. ELEMENT_TYPE DISTRIBUTION:")
        element_query = """
        SELECT 
            element_type,
            COUNT(*) as count
        FROM (
            SELECT element_type FROM player_history WHERE element_type IS NOT NULL
            UNION ALL 
            SELECT element_type FROM current_season_history WHERE element_type IS NOT NULL
        ) combined_data
        GROUP BY element_type
        ORDER BY element_type
        """
        
        element_stats = run_sql_query(element_query)
        if len(element_stats) > 0:
            for _, row in element_stats.iterrows():
                logger.info(f"   Type {row['element_type']}: {row['count']}")
        else:
            logger.warning("   No element_type data found")
        
        # 3. Check for missing critical columns
        logger.info("\n3. CRITICAL COLUMNS CHECK:")
        critical_columns = ['minutes', 'total_points', 'xg', 'xa', 'ict_index', 'value', 'selected']
        
        for col in critical_columns:
            archive_check = run_sql_query(f"SELECT COUNT(*) as count FROM player_history WHERE {col} IS NOT NULL")
            current_check = run_sql_query(f"SELECT COUNT(*) as count FROM current_season_history WHERE {col} IS NOT NULL")
            
            archive_count = archive_check['count'].iloc[0] if len(archive_check) > 0 else 0
            current_count = current_check['count'].iloc[0] if len(current_check) > 0 else 0
            
            total_available = archive_count + current_count
            logger.info(f"   {col}: {total_available} records have non-null values")
        
        # 4. Check points distribution
        logger.info("\n4. TOTAL_POINTS DISTRIBUTION:")
        points_query = """
        SELECT 
            AVG(total_points) as avg_points,
            MAX(total_points) as max_points,
            SUM(CASE WHEN total_points = 0 THEN 1 ELSE 0 END) as zero_points,
            SUM(CASE WHEN total_points > 10 THEN 1 ELSE 0 END) as high_points
        FROM (
            SELECT total_points FROM player_history 
            UNION ALL 
            SELECT total_points FROM current_season_history
        ) combined_data
        WHERE total_points IS NOT NULL
        """
        
        points_stats = run_sql_query(points_query)
        if len(points_stats) > 0:
            row = points_stats.iloc[0]
            logger.info(f"   Average total_points: {row['avg_points']:.2f}")
            logger.info(f"   Max total_points: {row['max_points']}")
            logger.info(f"   Zero points: {row['zero_points']}")
            logger.info(f"   High points (>10): {row['high_points']}")
        
        # 5. Check data freshness
        logger.info("\n5. DATA FRESHNESS:")
        freshness_query = """
        SELECT 
            MIN(gw) as earliest_gw,
            MAX(gw) as latest_gw,
            COUNT(DISTINCT season) as seasons
        FROM player_history
        """
        
        freshness_stats = run_sql_query(freshness_query)
        if len(freshness_stats) > 0:
            row = freshness_stats.iloc[0]
            logger.info(f"   Archive data: GW {row['earliest_gw']} to {row['latest_gw']}")
            logger.info(f"   Seasons in archive: {row['seasons']}")
        
        current_season_stats = run_sql_query("SELECT MIN(gw) as min_gw, MAX(gw) as max_gw, COUNT(*) as records FROM current_season_history")
        if len(current_season_stats) > 0:
            row = current_season_stats.iloc[0]
            logger.info(f"   Current season data: GW {row['min_gw']} to {row['max_gw']} ({row['records']} records)")
        
        # 6. Test a simple prediction sample
        logger.info("\n6. SAMPLE DATA TEST:")
        sample_query = """
        SELECT 
            player_id, 
            gw, 
            minutes, 
            total_points,
            CASE WHEN minutes > 0 THEN (total_points * 90.0 / minutes) ELSE NULL END as points_per_90
        FROM current_season_history 
        WHERE player_id IN (
            SELECT player_id FROM current_season_history 
            WHERE minutes > 10 
            LIMIT 5
        )
        ORDER BY player_id, gw
        LIMIT 20
        """
        
        sample_data = run_sql_query(sample_query)
        if len(sample_data) > 0:
            logger.info("   Sample player data (first 5 rows):")
            for _, row in sample_data.head(5).iterrows():
                logger.info(f"   Player {row['player_id']}, GW{row['gw']}: {row['minutes']} mins, {row['total_points']} pts, {row['points_per_90']:.2f} p/90")
        
        logger.info("\n=== DIAGNOSTIC COMPLETE ===")
        return True
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        return False

if __name__ == "__main__":
    diagnose_basic_data()