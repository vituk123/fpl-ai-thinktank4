"""
Historical Data Ingestion Script.
Downloads FULL FPL historical data and maps Positions.
"""
import logging
import requests
import pandas as pd
from pathlib import Path
from database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalDataIngester:
    BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
    SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24']
    
    # Position Map: String -> Integer
    POS_MAP = {'GK': 1, 'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        Path('.cache/history').mkdir(parents=True, exist_ok=True)
    
    def ingest_all_seasons(self):
        logger.info("Starting Full Ingestion...")
        # CRITICAL: We reset the tables to apply the new Schema (element_type)
        self.db.reset_history_tables()
        
        for season in self.SEASONS:
            logger.info(f"Processing {season}...")
            self._process_season(season)

    def _process_season(self, season):
        season_data = []
        for gw in range(1, 39):
            url = f"{self.BASE_URL}/{season}/gws/gw{gw}.csv"
            try:
                df = pd.read_csv(url, encoding='utf-8')
                df['gw'] = gw
                df['season'] = season
                season_data.append(df)
            except:
                continue
        
        if season_data:
            full_df = pd.concat(season_data, ignore_index=True)
            cleaned_df = self._clean_and_transform(full_df)
            self.db.save_player_history(cleaned_df.to_dict('records'))

    def _clean_and_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        mapping = {
            'name': 'player_name',
            'total_points': 'total_points',
            'minutes': 'minutes',
            'bonus': 'bonus',
            'bps': 'bps',
            'expected_goals': 'xg',
            'expected_assists': 'xa',
            'influence': 'influence',
            'creativity': 'creativity',
            'threat': 'threat',
            'ict_index': 'ict_index',
            'goals_scored': 'goals_scored',
            'assists': 'assists',
            'clean_sheets': 'clean_sheets',
            'goals_conceded': 'goals_conceded',
            'own_goals': 'own_goals',
            'penalties_saved': 'penalties_saved',
            'penalties_missed': 'penalties_missed',
            'saves': 'saves',
            'yellow_cards': 'yellow_cards',
            'red_cards': 'red_cards',
            'value': 'value',
            'transfers_balance': 'transfers_balance',
            'selected': 'selected',
            'transfers_in': 'transfers_in',
            'transfers_out': 'transfers_out',
            'opponent_team': 'opponent_team',
            'was_home': 'was_home',
            'position': 'element_type' # Map position column if exists
        }
        
        # 1. Map Position Strings to Integers
        if 'position' in df.columns:
            df['position'] = df['position'].map(self.POS_MAP).fillna(0)
        
        # Select available columns
        available = [c for c in mapping.keys() if c in df.columns]
        clean = df[available + ['gw', 'season']].copy()
        clean.rename(columns=mapping, inplace=True)
        
        # Fallback if position missing (Vaastav sometimes names it 'element_type' directly)
        if 'element_type' not in clean.columns and 'element_type' in df.columns:
             clean['element_type'] = df['element_type']

        clean = clean.fillna(0)
        
        # Ensure player name
        if 'player_name' not in clean.columns: clean['player_name'] = 'Unknown'
        
        # Ensure element_type exists
        if 'element_type' not in clean.columns: clean['element_type'] = 0
            
        return clean

if __name__ == "__main__":
    db = DatabaseManager()
    ingester = HistoricalDataIngester(db)
    ingester.ingest_all_seasons()