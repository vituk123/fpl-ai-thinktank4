"""
Live Data Updater. Fetches ALL stats for the current season, including Position.
"""
import logging
import requests
from database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_update_season_history():
    db = DatabaseManager()
    
    # 1. Fetch bootstrap to get Player Info (Position, Name)
    logger.info("Fetching bootstrap-static...")
    bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
    elements = bootstrap['elements']
    
    # Create lookup map: ID -> {web_name, element_type}
    player_map = {
        p['id']: {
            'web_name': p['web_name'],
            'element_type': p['element_type']
        } for p in elements
    }
    
    logger.info(f"Updating granular history for {len(elements)} players...")
    all_history = []
    
    for i, player in enumerate(elements):
        p_id = player['id']
        p_info = player_map.get(p_id)
        
        try:
            # 2. Fetch specific player history
            resp = requests.get(f"https://fantasy.premierleague.com/api/element-summary/{p_id}/")
            if resp.status_code != 200: continue
            
            history = resp.json().get('history', [])
            
            for h in history:
                all_history.append({
                    'player_id': p_id,
                    'player_name': p_info['web_name'],
                    'element_type': p_info['element_type'], # Now included!
                    'gw': h['round'],
                    # ALL STATS
                    'total_points': h['total_points'],
                    'minutes': h['minutes'],
                    'bonus': h['bonus'],
                    'bps': h['bps'],
                    'xg': float(h.get('expected_goals', 0)),
                    'xa': float(h.get('expected_assists', 0)),
                    'influence': float(h.get('influence', 0)),
                    'creativity': float(h.get('creativity', 0)),
                    'threat': float(h.get('threat', 0)),
                    'ict_index': float(h.get('ict_index', 0)),
                    'goals_scored': h['goals_scored'],
                    'assists': h['assists'],
                    'clean_sheets': h['clean_sheets'],
                    'goals_conceded': h['goals_conceded'],
                    'own_goals': h['own_goals'],
                    'penalties_saved': h['penalties_saved'],
                    'penalties_missed': h['penalties_missed'],
                    'saves': h['saves'],
                    'yellow_cards': h['yellow_cards'],
                    'red_cards': h['red_cards'],
                    'value': h['value'],
                    'transfers_balance': h['transfers_balance'],
                    'selected': h['selected'],
                    'transfers_in': h['transfers_in'],
                    'transfers_out': h['transfers_out'],
                    'opponent_team': h['opponent_team'],
                    'was_home': h['was_home']
                })
        except Exception as e:
            logger.warning(f"Error fetching {p_id}: {e}")
            continue
        
        if i % 100 == 0: logger.info(f"Processed {i} players...")

    if all_history:
        db.save_current_season_history(all_history)
        logger.info(f"✓ Live history updated with {len(all_history)} records.")

if __name__ == "__main__":
    fetch_and_update_season_history()