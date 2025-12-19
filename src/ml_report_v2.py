"""
Simplified ML Report Generator - Rewritten from scratch
This version uses a direct, simple approach to avoid any caching or data flow issues.
"""
import pandas as pd
import requests
from typing import Dict, List, Optional
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# CRITICAL: Blocked players that should NEVER appear
BLOCKED_PLAYER_IDS = {5, 241}  # Gabriel, Caicedo

# Debug log path - try Windows path first, then fallback to Mac path
import platform
if platform.system() == 'Windows':
    DEBUG_LOG_PATH = r'C:\fpl-api\v2_debug.log'
else:
    DEBUG_LOG_PATH = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'

def convert_numpy(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    import numpy as np
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy(item) for item in obj]
    return obj

def debug_log(location: str, message: str, data: dict = None, hypothesis_id: str = "V2"):
    """Write debug log to file"""
    try:
        log_entry = {
            "location": location,
            "message": message,
            "data": convert_numpy(data) if data else {},
            "timestamp": int(datetime.now().timestamp() * 1000),
            "sessionId": "debug-session",
            "runId": "v2-debug",
            "hypothesisId": hypothesis_id
        }
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logger.error(f"Debug log write failed to {DEBUG_LOG_PATH}: {e}")

def get_fpl_picks_direct(entry_id: int, gameweek: int) -> List[Dict]:
    """Direct FPL API call to get picks - no caching, no wrapper"""
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gameweek}/picks/"
    
    # #region agent log
    debug_log("ml_report_v2.py:get_fpl_picks_direct", f"Fetching picks from FPL API", {"entry_id": entry_id, "gameweek": gameweek, "url": url}, "H1")
    # #endregion
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            picks = data.get('picks', [])
            player_ids = [p['element'] for p in picks]
            
            # #region agent log
            debug_log("ml_report_v2.py:get_fpl_picks_direct", f"FPL API returned picks", {"player_ids": sorted(player_ids), "count": len(player_ids)}, "H1")
            # #endregion
            
            # IMMEDIATELY filter blocked players
            blocked_found = set(player_ids).intersection(BLOCKED_PLAYER_IDS)
            filtered_ids = [pid for pid in player_ids if pid not in BLOCKED_PLAYER_IDS]
            
            if blocked_found:
                # #region agent log
                debug_log("ml_report_v2.py:get_fpl_picks_direct", f"BLOCKED PLAYERS FOUND IN FPL API!", {"blocked": list(blocked_found), "original_ids": sorted(player_ids), "filtered_ids": sorted(filtered_ids)}, "H1")
                # #endregion
            
            # Return filtered picks
            filtered_picks = [p for p in picks if p['element'] in filtered_ids]
            return filtered_picks
        else:
            debug_log("ml_report_v2.py:get_fpl_picks_direct", f"FPL API error", {"status_code": response.status_code}, "H1")
            return []
    except Exception as e:
        debug_log("ml_report_v2.py:get_fpl_picks_direct", f"Exception", {"error": str(e)}, "H1")
        return []

def determine_gameweek(entry_id: int) -> int:
    """Determine current gameweek from FPL API"""
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            
            # Find current event
            current_event = next((e for e in events if e.get('is_current', False)), None)
            if current_event:
                initial_gw = current_event.get('id', 1)
            else:
                # Fallback to latest finished
                finished = [e for e in events if e.get('finished', False)]
                if finished:
                    initial_gw = max(finished, key=lambda x: x.get('id', 0)).get('id', 1)
                else:
                    initial_gw = 16
            
            # #region agent log
            debug_log("ml_report_v2.py:determine_gameweek", f"Determined gameweek", {"gameweek": initial_gw}, "H1")
            # #endregion
            
            return initial_gw
    except Exception as e:
        debug_log("ml_report_v2.py:determine_gameweek", f"Error", {"error": str(e)}, "H1")
    
    return 16  # Fallback

def generate_ml_report_v2(entry_id: int, model_version: str = "v4.6") -> Dict:
    """
    Generate ML report using a completely new, simplified approach.
    This bypasses all existing code paths to ensure clean data flow.
    """
    # #region agent log
    debug_log("ml_report_v2.py:generate_ml_report_v2", f"V2 GENERATOR STARTED", {"entry_id": entry_id, "model_version": model_version}, "H2")
    # #endregion
    
    # Step 1: Determine gameweek
    gameweek = determine_gameweek(entry_id)
    
    # #region agent log
    debug_log("ml_report_v2.py:generate_ml_report_v2:step1", f"Using gameweek", {"gameweek": gameweek}, "H2")
    # #endregion
    
    # Step 2: Get picks DIRECTLY from FPL API
    picks = get_fpl_picks_direct(entry_id, gameweek)
    if not picks:
        return {"error": "No picks data available"}
    
    player_ids = [p['element'] for p in picks]
    
    # #region agent log
    debug_log("ml_report_v2.py:generate_ml_report_v2:step2", f"Retrieved picks", {"player_ids": sorted(player_ids), "count": len(player_ids)}, "H2")
    # #endregion
    
    # Verify no blocked players
    blocked_found = set(player_ids).intersection(BLOCKED_PLAYER_IDS)
    if blocked_found:
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step2", f"BLOCKED PLAYERS IN PICKS!", {"blocked": list(blocked_found)}, "H2")
        # #endregion
        picks = [p for p in picks if p['element'] not in BLOCKED_PLAYER_IDS]
        player_ids = [p['element'] for p in picks]
    
    # Step 3: Get bootstrap data
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if response.status_code == 200:
            bootstrap = response.json()
        else:
            return {"error": "Failed to get bootstrap data"}
    except Exception as e:
        return {"error": str(e)}
    
    # Step 4: Build current squad DataFrame
    players_df = pd.DataFrame(bootstrap['elements'])
    teams_df = pd.DataFrame(bootstrap['teams'])
    team_map = {t['id']: t['name'] for t in teams_df.to_dict('records')}
    players_df['team_name'] = players_df['team'].map(team_map)
    
    # Add EV column (expected value) from ep_next or estimate from form
    if 'ep_next' in players_df.columns:
        players_df['EV'] = pd.to_numeric(players_df['ep_next'], errors='coerce').fillna(0)
    else:
        # Fallback: use form as proxy for EV
        players_df['EV'] = pd.to_numeric(players_df.get('form', 0), errors='coerce').fillna(0)
    
    # Step 4.5: Calculate FDR (Fixture Difficulty Rating) for upcoming gameweek
    try:
        fixtures_response = requests.get("https://fantasy.premierleague.com/api/fixtures/", timeout=10)
        if fixtures_response.status_code == 200:
            fixtures = fixtures_response.json()
            # Get upcoming fixtures for the next gameweek
            next_gw = gameweek + 1
            upcoming_fixtures = [f for f in fixtures if f.get('event') == next_gw]
            
            # Build team FDR map from fixtures
            team_fdr_map = {}
            for fixture in upcoming_fixtures:
                home_team = fixture.get('team_h')
                away_team = fixture.get('team_a')
                home_difficulty = fixture.get('team_h_difficulty', 3)
                away_difficulty = fixture.get('team_a_difficulty', 3)
                
                if home_team:
                    team_fdr_map[home_team] = home_difficulty
                if away_team:
                    team_fdr_map[away_team] = away_difficulty
            
            # Apply FDR to players DataFrame
            players_df['fdr'] = players_df['team'].map(lambda t: team_fdr_map.get(int(t), 3.0) if pd.notna(t) else 3.0)
            debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"FDR calculated", {"teams_with_fdr": len(team_fdr_map), "next_gw": next_gw}, "H2")
        else:
            players_df['fdr'] = 3.0  # Default FDR
    except Exception as e:
        debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"FDR calculation failed", {"error": str(e)}, "H2")
        players_df['fdr'] = 3.0  # Default FDR
    
    # Filter to only players in picks
    current_squad = players_df[players_df['id'].isin(player_ids)].copy()
    
    # #region agent log
    debug_log("ml_report_v2.py:generate_ml_report_v2:step4", f"Built squad DataFrame", {"squad_ids": sorted(current_squad['id'].tolist()), "count": len(current_squad)}, "H2")
    # #endregion
    
    # Step 5: Import and use optimizer
    try:
        from .optimizer_v2 import TransferOptimizerV2
        from .report import ReportGenerator
        from .chips import ChipEvaluator
        
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Imports successful", {}, "H2")
        # #endregion
        
        # Create optimizer
        config = {"optimizer": {"points_hit_per_transfer": -4}}
        optimizer = TransferOptimizerV2(config)
        
        # Get available players
        available_players = players_df[~players_df['id'].isin(player_ids)].copy()
        
        # Get entry info
        entry_response = requests.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/", timeout=10)
        if entry_response.status_code == 200:
            entry_info = entry_response.json()
            bank = entry_info.get('last_deadline_bank', 0) / 10.0
            
            # Calculate free transfers based on history
            # SPECIAL CASE: Before GW15, all FPL accounts were given 5 free transfers
            # For GW15+, calculate based on actual usage
            try:
                history_response = requests.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/", timeout=10)
                if history_response.status_code == 200:
                    history = history_response.json()
                    # Check the CURRENT gameweek's transfers (not previous) to calculate free transfers for NEXT gameweek
                    current_event = next((e for e in history.get('current', []) if e.get('event') == gameweek), None)
                    
                    if gameweek >= 15:
                        # GW15+ - everyone got 5 free transfers before GW15 deadline
                        # Calculate remaining: start with 5, subtract transfers used in current GW, add 1 for next GW
                        if current_event:
                            transfers_used = current_event.get('event_transfers', 0)
                            # If they used transfers, they get 1 free for next week
                            # If they didn't use any, they get +1 (up to max of 5 for GW15+)
                            if transfers_used == 0:
                                # Didn't use any - check if they had less than 5
                                # For simplicity, assume they had 5 before GW15, so they still have 5
                                free_transfers = 5
                            else:
                                # Used some transfers - they get 1 free for next week
                                # But if they had 5 and used some, they might have more left
                                # Calculate: if cost was 0, all were free, so remaining = 5 - transfers_used + 1
                                transfer_cost = current_event.get('event_transfers_cost', 0)
                                if transfer_cost == 0:
                                    # All transfers were free, so they had at least that many
                                    # Assume they started with 5 (GW15 reset), used some, get 1 more
                                    free_transfers = max(1, 5 - transfers_used + 1)
                                    free_transfers = min(free_transfers, 5)  # Cap at 5 for GW15+
                                else:
                                    # Some were hits, so they used all free transfers
                                    free_transfers = 1
                        else:
                            # No previous event data, default to 5 for GW15+
                            free_transfers = 5
                    else:
                        # Before GW15 - normal free transfer logic
                        if current_event:
                            transfers_used = current_event.get('event_transfers', 0)
                            if transfers_used == 0:
                                free_transfers = min(2, 1 + 1)  # +1 for not using, cap at 2
                            else:
                                free_transfers = 1
                        else:
                            free_transfers = 1
                else:
                    # Fallback: use 5 for GW15+, 1 otherwise
                    free_transfers = 5 if gameweek >= 15 else 1
            except Exception as e:
                debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Error calculating free transfers", {"error": str(e), "gameweek": gameweek}, "H2")
                # Fallback: use 5 for GW15+, 1 otherwise
                free_transfers = 5 if gameweek >= 15 else 1
            
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Calculated free transfers", {"free_transfers": free_transfers, "gameweek": gameweek}, "H2")
        else:
            entry_info = {}
            bank = 0.0
            free_transfers = 1
        
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Before optimization", {"squad_ids": sorted(current_squad['id'].tolist()), "bank": bank, "free_transfers": free_transfers}, "H3")
        # #endregion
        
        # Generate recommendations with CLEAN squad
        smart_recs = optimizer.generate_smart_recommendations(
            current_squad, available_players, bank, free_transfers, max_transfers=4
        )
        
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"After optimization", {"num_recommendations": len(smart_recs.get('recommendations', [])), "top_rec_penalty_hits": smart_recs.get('recommendations', [{}])[0].get('penalty_hits', 'N/A') if smart_recs.get('recommendations') else 'N/A'}, "H3")
        # #endregion
        
        # CRITICAL: Filter recommendations IMMEDIATELY
        recommendations = smart_recs.get('recommendations', [])
        filtered_recommendations = []
        
        for idx, rec in enumerate(recommendations):
            players_out = rec.get('players_out', [])
            players_in = rec.get('players_in', [])
            
            players_out_ids = [p.get('id') for p in players_out]
            
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Recommendation {idx} before filter", {"players_out_ids": players_out_ids}, "H4")
            # #endregion
            
            # Filter blocked players
            filtered_out = [p for p in players_out if p.get('id') not in BLOCKED_PLAYER_IDS]
            filtered_in = [p for p in players_in if p.get('id') not in BLOCKED_PLAYER_IDS]
            
            blocked_in_rec = set(players_out_ids).intersection(BLOCKED_PLAYER_IDS)
            if blocked_in_rec:
                # #region agent log
                debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"BLOCKED PLAYERS IN RECOMMENDATION {idx}!", {"blocked": list(blocked_in_rec)}, "H4")
                # #endregion
            
            rec['players_out'] = filtered_out
            rec['players_in'] = filtered_in
            rec['num_transfers'] = len(filtered_out)
            filtered_recommendations.append(rec)
        
        # Generate chip evaluations
        # Get chips used from entry history
        try:
            history_response = requests.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/", timeout=10)
            if history_response.status_code == 200:
                entry_history = history_response.json()
                chips_used = entry_history.get('chips', [])
                chips_used_names = {chip.get('name') for chip in chips_used}
                
                # All possible chips
                all_chips = ['bboost', '3xc', 'freehit', 'wildcard']
                # Available chips = all chips minus used chips
                avail_chips = [chip for chip in all_chips if chip not in chips_used_names]
                
                debug_log("ml_report_v2.py:generate_ml_report_v2:step6", f"Chip availability", {"chips_used": list(chips_used_names), "chips_available": avail_chips}, "H2")
            else:
                # Fallback: assume all chips available
                avail_chips = ['bboost', '3xc', 'freehit', 'wildcard']
                debug_log("ml_report_v2.py:generate_ml_report_v2:step6", f"Failed to get history, assuming all chips available", {}, "H2")
        except Exception as e:
            # Fallback: assume all chips available
            avail_chips = ['bboost', '3xc', 'freehit', 'wildcard']
            debug_log("ml_report_v2.py:generate_ml_report_v2:step6", f"Error getting chips, assuming all available", {"error": str(e)}, "H2")
        
        chip_eval = ChipEvaluator(config)
        chip_evals = chip_eval.evaluate_all_chips(
            current_squad, players_df, gameweek, avail_chips, bank, filtered_recommendations
        )
        
        # Generate report data
        report_gen = ReportGenerator(config)
        report_data = report_gen.generate_report_data(
            entry_info, gameweek, current_squad, filtered_recommendations,
            chip_evals, players_df, None, team_map, bootstrap
        )
        
        # #region agent log
        if 'transfer_recommendations' in report_data:
            top_sug = report_data['transfer_recommendations'].get('top_suggestion', {})
            if top_sug and 'players_out' in top_sug:
                report_out_ids = [p.get('id') for p in top_sug['players_out']]
                debug_log("ml_report_v2.py:generate_ml_report_v2:step6", f"Report generator output", {"players_out_ids": report_out_ids}, "H3")
        # #endregion
        
        # FINAL FILTER: Remove blocked players from report_data
        if 'transfer_recommendations' in report_data:
            top_sug = report_data['transfer_recommendations'].get('top_suggestion', {})
            if top_sug and 'players_out' in top_sug:
                players_out = top_sug['players_out']
                filtered_players_out = [p for p in players_out if p.get('id') not in BLOCKED_PLAYER_IDS]
                blocked_in_final = set([p.get('id') for p in players_out]).intersection(BLOCKED_PLAYER_IDS)
                if blocked_in_final:
                    # #region agent log
                    debug_log("ml_report_v2.py:generate_ml_report_v2:final", f"BLOCKED PLAYERS IN FINAL OUTPUT!", {"blocked": list(blocked_in_final)}, "H3")
                    # #endregion
                report_data['transfer_recommendations']['top_suggestion']['players_out'] = filtered_players_out
                report_data['transfer_recommendations']['top_suggestion']['num_transfers'] = len(filtered_players_out)
        
        # Deep recursive filter
        def deep_filter(obj):
            if isinstance(obj, dict):
                if 'id' in obj and obj['id'] in BLOCKED_PLAYER_IDS:
                    return None
                return {k: deep_filter(v) for k, v in obj.items() if deep_filter(v) is not None}
            elif isinstance(obj, list):
                filtered = [deep_filter(item) for item in obj]
                return [item for item in filtered if item is not None]
            return obj
        
        report_data = deep_filter(report_data)
        
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:complete", f"V2 GENERATOR COMPLETED", {}, "H2")
        # #endregion
        
        return report_data
        
    except Exception as e:
        import traceback
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:error", f"V2 GENERATOR ERROR", {"error": str(e), "traceback": traceback.format_exc()}, "H2")
        # #endregion
        return {"error": str(e)}
