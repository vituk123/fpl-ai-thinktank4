"""
Simplified ML Report Generator - Rewritten from scratch
This version uses a direct, simple approach to avoid any caching or data flow issues.
"""
import pandas as pd
import requests
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# CRITICAL: Blocked players that should NEVER appear
BLOCKED_PLAYER_IDS = {5, 241}  # Gabriel, Caicedo

def get_fpl_picks_direct(entry_id: int, gameweek: int) -> List[Dict]:
    """Direct FPL API call to get picks - no caching, no wrapper"""
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gameweek}/picks/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            picks = data.get('picks', [])
            player_ids = [p['element'] for p in picks]
            
            # IMMEDIATELY filter blocked players
            filtered_ids = [pid for pid in player_ids if pid not in BLOCKED_PLAYER_IDS]
            
            if len(filtered_ids) < len(player_ids):
                blocked_found = set(player_ids).intersection(BLOCKED_PLAYER_IDS)
                logger.error(f"ML Report V2: FPL API returned blocked players {blocked_found} for GW{gameweek}!")
                logger.error(f"ML Report V2: Original IDs: {sorted(player_ids)}")
                logger.error(f"ML Report V2: Filtered IDs: {sorted(filtered_ids)}")
            
            # Return filtered picks
            filtered_picks = [p for p in picks if p['element'] in filtered_ids]
            return filtered_picks
        else:
            logger.error(f"ML Report V2: FPL API error {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"ML Report V2: Error fetching picks: {e}")
        return []

def determine_gameweek() -> int:
    """Determine current gameweek from FPL API"""
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            
            # Find current event
            current_event = next((e for e in events if e.get('is_current', False)), None)
            if current_event:
                return current_event.get('id', 1)
            
            # Fallback to latest finished
            finished = [e for e in events if e.get('finished', False)]
            if finished:
                return max(finished, key=lambda x: x.get('id', 0)).get('id', 1)
            
            # Last resort
            if events:
                return max(events, key=lambda x: x.get('id', 0)).get('id', 1)
    except Exception as e:
        logger.error(f"ML Report V2: Error determining gameweek: {e}")
    
    return 16  # Fallback

def generate_ml_report_v2(entry_id: int, model_version: str = "v4.6") -> Dict:
    """
    Generate ML report using a completely new, simplified approach.
    This bypasses all existing code paths to ensure clean data flow.
    """
    logger.info(f"ML Report V2: Starting report generation for entry {entry_id}")
    
    # Step 1: Determine gameweek
    gameweek = determine_gameweek()
    logger.info(f"ML Report V2: Using gameweek {gameweek}")
    
    # Step 2: Get picks DIRECTLY from FPL API
    picks = get_fpl_picks_direct(entry_id, gameweek)
    if not picks:
        logger.error(f"ML Report V2: No picks retrieved for entry {entry_id}, GW{gameweek}")
        return {"error": "No picks data available"}
    
    player_ids = [p['element'] for p in picks]
    logger.info(f"ML Report V2: Retrieved {len(player_ids)} players: {sorted(player_ids)}")
    
    # Verify no blocked players
    blocked_found = set(player_ids).intersection(BLOCKED_PLAYER_IDS)
    if blocked_found:
        logger.error(f"ML Report V2: ❌❌❌ BLOCKED PLAYERS STILL PRESENT: {blocked_found} ❌❌❌")
        # Force remove
        picks = [p for p in picks if p['element'] not in BLOCKED_PLAYER_IDS]
        player_ids = [p['element'] for p in picks]
        logger.error(f"ML Report V2: Force-removed. New player IDs: {sorted(player_ids)}")
    else:
        logger.info(f"ML Report V2: ✅ No blocked players in picks")
    
    # Step 3: Get bootstrap data
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if response.status_code == 200:
            bootstrap = response.json()
        else:
            return {"error": "Failed to get bootstrap data"}
    except Exception as e:
        logger.error(f"ML Report V2: Error getting bootstrap: {e}")
        return {"error": str(e)}
    
    # Step 4: Build current squad DataFrame
    players_df = pd.DataFrame(bootstrap['elements'])
    teams_df = pd.DataFrame(bootstrap['teams'])
    team_map = {t['id']: t['name'] for t in teams_df.to_dict('records')}
    players_df['team_name'] = players_df['team'].map(team_map)
    
    # Filter to only players in picks (already filtered for blocked players)
    current_squad = players_df[players_df['id'].isin(player_ids)].copy()
    
    # FINAL CHECK: Ensure no blocked players
    squad_ids = set(current_squad['id'].tolist())
    blocked_in_squad = squad_ids.intersection(BLOCKED_PLAYER_IDS)
    if blocked_in_squad:
        logger.error(f"ML Report V2: ❌❌❌ BLOCKED PLAYERS IN SQUAD DF: {blocked_in_squad} ❌❌❌")
        current_squad = current_squad[~current_squad['id'].isin(BLOCKED_PLAYER_IDS)].copy()
        logger.error(f"ML Report V2: Force-removed from DataFrame. New size: {len(current_squad)}")
    
    logger.info(f"ML Report V2: Current squad size: {len(current_squad)}, IDs: {sorted(current_squad['id'].tolist())}")
    
        # Step 5: Import and use optimizer (but with our clean squad)
        try:
            from src.optimizer_v2 import TransferOptimizerV2
            from src.report import ReportGenerator
            from src.chip_evaluator import ChipEvaluator
        
        # Create optimizer
        config = {"optimizer": {"points_hit_per_transfer": -4}}
        optimizer = TransferOptimizerV2(config)
        
        # Get available players (all players except current squad)
        available_players = players_df[~players_df['id'].isin(player_ids)].copy()
        
        # Get entry info for bank and free transfers
        entry_response = requests.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/", timeout=10)
        if entry_response.status_code == 200:
            entry_info = entry_response.json()
            bank = entry_info.get('last_deadline_bank', 0) / 10.0  # Convert to millions
            free_transfers = 1  # Default
        else:
            bank = 0.0
            free_transfers = 1
        
        # Generate recommendations with CLEAN squad
        logger.info(f"ML Report V2: Generating recommendations with clean squad...")
        smart_recs = optimizer.generate_smart_recommendations(
            current_squad, available_players, bank, free_transfers, max_transfers=4
        )
        
        # CRITICAL: Filter recommendations IMMEDIATELY
        recommendations = smart_recs.get('recommendations', [])
        filtered_recommendations = []
        
        for rec in recommendations:
            players_out = rec.get('players_out', [])
            players_in = rec.get('players_in', [])
            
            # Filter blocked players
            filtered_out = [p for p in players_out if p.get('id') not in BLOCKED_PLAYER_IDS]
            filtered_in = [p for p in players_in if p.get('id') not in BLOCKED_PLAYER_IDS]
            
            if len(filtered_out) < len(players_out) or len(filtered_in) < len(players_in):
                logger.error(f"ML Report V2: ❌❌❌ REMOVED BLOCKED PLAYERS FROM RECOMMENDATION! ❌❌❌")
                logger.error(f"ML Report V2: Original OUT IDs: {[p.get('id') for p in players_out]}")
                logger.error(f"ML Report V2: Filtered OUT IDs: {[p.get('id') for p in filtered_out]}")
            
            rec['players_out'] = filtered_out
            rec['players_in'] = filtered_in
            rec['num_transfers'] = len(filtered_out)
            filtered_recommendations.append(rec)
        
        smart_recs['recommendations'] = filtered_recommendations
        
        # Generate chip evaluations
        chip_eval = ChipEvaluator(config)
        avail_chips = ['bboost', '3xc', 'freehit', 'wildcard']  # Simplified
        chip_evals = chip_eval.evaluate_all_chips(
            current_squad, players_df, gameweek, avail_chips, bank, filtered_recommendations
        )
        
        # Generate report data
        report_gen = ReportGenerator(config)
        report_data = report_gen.generate_report_data(
            entry_info, gameweek, current_squad, filtered_recommendations,
            chip_evals, players_df, None, team_map, bootstrap
        )
        
        # FINAL FILTER: Remove blocked players from report_data
        if 'transfer_recommendations' in report_data:
            top_sug = report_data['transfer_recommendations'].get('top_suggestion', {})
            if top_sug and 'players_out' in top_sug:
                players_out = top_sug['players_out']
                filtered_players_out = [p for p in players_out if p.get('id') not in BLOCKED_PLAYER_IDS]
                if len(filtered_players_out) < len(players_out):
                    logger.error(f"ML Report V2: ❌❌❌ FINAL FILTER - Removed {len(players_out) - len(filtered_players_out)} blocked players from report_data! ❌❌❌")
                    report_data['transfer_recommendations']['top_suggestion']['players_out'] = filtered_players_out
                    report_data['transfer_recommendations']['top_suggestion']['num_transfers'] = len(filtered_players_out)
        
        logger.info(f"ML Report V2: ✅ Report generated successfully")
        return report_data
        
    except Exception as e:
        logger.error(f"ML Report V2: Error generating report: {e}", exc_info=True)
        return {"error": str(e)}

