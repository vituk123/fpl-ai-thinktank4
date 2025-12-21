#!/usr/bin/env python3
"""Check how much data has been ingested"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager

db = DatabaseManager()

try:
    history = db.get_player_history()
    print("="*70)
    print("CURRENT DATA COUNT")
    print("="*70)
    print(f"Total records: {len(history):,}")
    
    if not history.empty:
        print(f"\nBy Season:")
        season_counts = history['season'].value_counts().sort_index()
        for season, count in season_counts.items():
            print(f"  {season}: {count:,} records")
        
        print(f"\nBy Position (element_type):")
        pos_counts = history['element_type'].value_counts().sort_index()
        pos_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD', 0: 'Unknown'}
        for pos, count in pos_counts.items():
            pos_name = pos_map.get(pos, f'Type {pos}')
            print(f"  {pos_name}: {count:,} records")
        
        print(f"\nDate Range:")
        if 'created_at' in history.columns:
            dates = pd.to_datetime(history['created_at'], errors='coerce')
            print(f"  Earliest: {dates.min()}")
            print(f"  Latest: {dates.max()}")
        else:
            print("  (No date column found)")
    else:
        print("No data found in database")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

