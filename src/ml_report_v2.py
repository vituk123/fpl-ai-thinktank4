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

# Create a session with proper SSL configuration
def create_requests_session():
    """Create a requests session with proper SSL configuration"""
    session = requests.Session()
    # On Windows, use system certificate store (verify=True uses Windows cert store)
    # This avoids the certifi path issue on Windows
    session.verify = True
    return session

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
        # Use session with proper SSL configuration
        session = create_requests_session()
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            picks = data.get('picks', [])
            player_ids = [p['element'] for p in picks]
            
            # #region agent log
            # Check if picks include selling_price
            sample_pick = picks[0] if picks else {}
            has_selling_price = 'selling_price' in sample_pick
            selling_prices_sample = []
            if has_selling_price:
                for p in picks[:5]:  # Sample first 5
                    selling_prices_sample.append({
                        'id': p.get('element'),
                        'selling_price': p.get('selling_price'),
                        'purchase_price': p.get('purchase_price'),
                        'now_cost': p.get('now_cost')
                    })
            debug_log("ml_report_v2.py:get_fpl_picks_direct", f"FPL API returned picks", {
                "player_ids": sorted(player_ids), 
                "count": len(player_ids),
                "has_selling_price": has_selling_price,
                "sample_pick_keys": list(sample_pick.keys()) if sample_pick else [],
                "selling_prices_sample": selling_prices_sample
            }, "C")
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
    """Determine current gameweek from FPL API - prioritize latest finished gameweek"""
    try:
        # Use session with proper SSL configuration
        session = create_requests_session()
        response = session.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            
            # Priority 1: Latest finished gameweek (most recent completed)
            finished = [e for e in events if e.get('finished', False)]
            if finished:
                latest_finished = max(finished, key=lambda x: x.get('id', 0))
                initial_gw = latest_finished.get('id', 1)
                debug_log("ml_report_v2.py:determine_gameweek", f"Using latest finished gameweek", {"gameweek": initial_gw, "finished": latest_finished.get('finished', False)}, "H1")
            else:
                # Priority 2: Current event (if no finished events)
                current_event = next((e for e in events if e.get('is_current', False)), None)
                if current_event:
                    initial_gw = current_event.get('id', 1)
                    debug_log("ml_report_v2.py:determine_gameweek", f"Using current event", {"gameweek": initial_gw}, "H1")
                else:
                    # Priority 3: Next event
                    next_event = next((e for e in events if e.get('is_next', False)), None)
                    if next_event:
                        initial_gw = next_event.get('id', 1)
                        debug_log("ml_report_v2.py:determine_gameweek", f"Using next event", {"gameweek": initial_gw}, "H1")
                    else:
                        # Fallback: max event ID
                        initial_gw = max((e.get('id', 1) for e in events), default=16)
                        debug_log("ml_report_v2.py:determine_gameweek", f"Using max event ID", {"gameweek": initial_gw}, "H1")
            
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
    debug_log("ml_report_v2.py:generate_ml_report_v2:step1", f"Using gameweek", {"gameweek": gameweek, "entry_id": entry_id}, "H2")
    # #endregion
    
    # CRITICAL: Log the gameweek that will be used in the report
    logger.info(f"ML Report V2: Determined gameweek {gameweek} for entry {entry_id}")
    
    # Step 2: Get picks DIRECTLY from FPL API
    picks = get_fpl_picks_direct(entry_id, gameweek)
    if not picks:
        return {"error": "No picks data available"}
    
    # Store picks_data for optimizer (contains selling_price information)
    picks_data = {'picks': picks}
    
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
        session = create_requests_session()
        response = session.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
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
    
    # Step 4.5: Calculate FDR (Fixture Difficulty Rating) for upcoming gameweek with league position adjustment
    try:
        fixtures_response = requests.get("https://fantasy.premierleague.com/api/fixtures/", timeout=10)
        if fixtures_response.status_code == 200:
            fixtures = fixtures_response.json()
            # Get upcoming fixtures for the next gameweek
            next_gw = gameweek + 1
            upcoming_fixtures = [f for f in fixtures if f.get('event') == next_gw]
            
            # Build team FDR map from fixtures
            team_fdr_map = {}
            team_opponent_map = {}  # Map team_id -> opponent_team_id for next gameweek
            for fixture in upcoming_fixtures:
                home_team = fixture.get('team_h')
                away_team = fixture.get('team_a')
                home_difficulty = fixture.get('team_h_difficulty', 3)
                away_difficulty = fixture.get('team_a_difficulty', 3)
                
                if home_team:
                    team_fdr_map[home_team] = home_difficulty
                    team_opponent_map[home_team] = away_team
                if away_team:
                    team_fdr_map[away_team] = away_difficulty
                    team_opponent_map[away_team] = home_team
            
            # Get league table positions for tie-breaking
            try:
                # Use the bootstrap data we already have (from Step 3)
                team_position_map = {}
                teams_df = pd.DataFrame(bootstrap.get('teams', []))
                # Sort by overall points (descending) to get league positions
                # Teams with more points = higher in table = lower position number (1 = top)
                if 'points' in teams_df.columns:
                    teams_df_sorted = teams_df.sort_values('points', ascending=False).reset_index(drop=True)
                    # Create map: team_id -> league_position (1 = top team, 20 = bottom team)
                    for idx, row in teams_df_sorted.iterrows():
                        team_position_map[row['id']] = idx + 1
                    debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"League positions calculated", {"teams_with_position": len(team_position_map), "top_team": teams_df_sorted.iloc[0]['name'] if len(teams_df_sorted) > 0 else 'N/A'}, "H2")
                else:
                    debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"No 'points' column in teams data", {}, "H2")
            except Exception as e:
                debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"Failed to calculate league positions", {"error": str(e)}, "H2")
                team_position_map = {}
            
            # Apply base FDR to players DataFrame
            players_df['fdr'] = players_df['team'].map(lambda t: team_fdr_map.get(int(t), 3.0) if pd.notna(t) else 3.0)
            
            # Calculate adjusted FDR with league position weighting for tie-breaking
            # This adjustment only applies when FDR values are similar (within 0.5)
            players_df['fdr_adjusted'] = players_df['fdr'].copy()
            
            if team_position_map:
                def adjust_fdr_with_league_position(row):
                    """
                    Adjust FDR based on opponent's league position.
                    Higher league position (1-10) = harder opponent = increase FDR
                    Lower league position (11-20) = easier opponent = decrease FDR
                    This acts as a tie-breaker when base FDR values are similar.
                    """
                    base_fdr = row['fdr']
                    team_id = int(row['team']) if pd.notna(row['team']) else None
                    
                    if team_id and team_id in team_opponent_map:
                        opponent_id = team_opponent_map[team_id]
                        if opponent_id and opponent_id in team_position_map:
                            opponent_position = team_position_map[opponent_id]
                            # League position adjustment:
                            # Position 1 (top team) = hardest = +0.3 FDR adjustment
                            # Position 20 (bottom team) = easiest = -0.3 FDR adjustment
                            # Linear scaling: (21 - position) / 20 * 0.6 - 0.3
                            # This gives range: -0.3 (position 20) to +0.3 (position 1)
                            position_adjustment = ((21 - opponent_position) / 20.0 * 0.6) - 0.3
                            # Apply adjustment (acts as tie-breaker when FDR values are similar)
                            adjusted_fdr = base_fdr + position_adjustment
                            # Clamp to valid FDR range (1-5)
                            return max(1.0, min(5.0, adjusted_fdr))
                    
                    return base_fdr
                
                players_df['fdr_adjusted'] = players_df.apply(adjust_fdr_with_league_position, axis=1)
            else:
                players_df['fdr_adjusted'] = players_df['fdr']
            
            debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"FDR calculated with league position adjustment", {"teams_with_fdr": len(team_fdr_map), "next_gw": next_gw, "teams_with_position": len(team_position_map)}, "H2")
        else:
            players_df['fdr'] = 3.0  # Default FDR
            players_df['fdr_adjusted'] = 3.0
    except Exception as e:
        debug_log("ml_report_v2.py:generate_ml_report_v2:step4.5", f"FDR calculation failed", {"error": str(e)}, "H2")
        players_df['fdr'] = 3.0  # Default FDR
        players_df['fdr_adjusted'] = 3.0
    
    # Step 4.6: REFRESH PLAYER PRICES - Critical to use latest prices for budget constraint
    # This ensures we use the most current prices right before optimization
    try:
        session = create_requests_session()
        bootstrap_response = session.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if bootstrap_response.status_code == 200:
            fresh_bootstrap = bootstrap_response.json()
            fresh_elements = pd.DataFrame(fresh_bootstrap.get('elements', []))
            
            if not fresh_elements.empty and 'id' in fresh_elements.columns and 'now_cost' in fresh_elements.columns:
                # Create a price map from fresh data
                price_map = dict(zip(fresh_elements['id'], fresh_elements['now_cost']))
                
                # Store old prices for comparison (for first 5 squad players)
                old_prices = {}
                for pid in player_ids[:5]:
                    if len(players_df[players_df['id'] == pid]) > 0:
                        old_prices[pid] = players_df.loc[players_df['id'] == pid, 'now_cost'].iloc[0]
                
                # Update prices in players_df with fresh data
                players_df['now_cost'] = players_df['id'].map(price_map).fillna(players_df['now_cost'])
                
                # Log price updates for debugging
                price_changes = []
                for pid, old_price in old_prices.items():
                    new_price = price_map.get(pid)
                    if new_price is not None and old_price != new_price:
                        price_changes.append({"id": pid, "old": old_price, "new": new_price})
                
                if price_changes:
                    debug_log("ml_report_v2.py:generate_ml_report_v2:step4.6", f"Price updates detected", {"changes": price_changes}, "H2")
                else:
                    debug_log("ml_report_v2.py:generate_ml_report_v2:step4.6", f"Prices refreshed (no changes detected)", {"players_refreshed": len(players_df)}, "H2")
            else:
                debug_log("ml_report_v2.py:generate_ml_report_v2:step4.6", f"Price refresh failed - invalid data", {}, "H2")
        else:
            debug_log("ml_report_v2.py:generate_ml_report_v2:step4.6", f"Price refresh failed - API error", {"status": bootstrap_response.status_code}, "H2")
    except Exception as e:
        debug_log("ml_report_v2.py:generate_ml_report_v2:step4.6", f"Price refresh exception", {"error": str(e)}, "H2")
        # Continue with existing prices if refresh fails
    
    # Filter to only players in picks (AFTER price refresh)
    current_squad = players_df[players_df['id'].isin(player_ids)].copy()
    
    # #region agent log
    debug_log("ml_report_v2.py:generate_ml_report_v2:step4", f"Built squad DataFrame", {"squad_ids": sorted(current_squad['id'].tolist()), "count": len(current_squad)}, "H2")
    # #endregion
    
    # #region agent log
    # Log bank balance and entry info before optimization
    try:
        entry_response = session.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/", timeout=10)
        if entry_response.status_code == 200:
            entry_data = entry_response.json()
            bank_balance = entry_data.get('last_deadline_bank', 0) / 10.0
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Bank balance from FPL API", {
                "bank_balance": bank_balance,
                "last_deadline_bank_raw": entry_data.get('last_deadline_bank', 0),
                "entry_id": entry_id
            }, "B")
    except Exception as e:
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Failed to get bank balance", {"error": str(e)}, "B")
    # #endregion
    
    # Step 5: Import and use optimizer
    try:
        from .optimizer_v2 import TransferOptimizerV2
        from .report import ReportGenerator
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"About to import ChipEvaluator", {}, "H1")
        # #endregion
        
        try:
            from .chips import ChipEvaluator
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"ChipEvaluator import successful", {}, "H1")
            # #endregion
        except ImportError as e:
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"ChipEvaluator import failed", {"error": str(e), "error_type": type(e).__name__}, "H1")
            # #endregion
            raise
        except SyntaxError as e:
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"ChipEvaluator syntax error", {"error": str(e), "error_type": type(e).__name__}, "H1")
            # #endregion
            raise
        except Exception as e:
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"ChipEvaluator import exception", {"error": str(e), "error_type": type(e).__name__}, "H1")
            # #endregion
            raise
        
        # Create optimizer
        config = {
            "optimizer": {"points_hit_per_transfer": -4},
            "chips": {
                "min_ev_delta": 15.0,  # V5.0: Bench Boost threshold
                "min_ev_delta_freehit": 20.0  # V5.0: Free Hit threshold
            }
        }
        optimizer = TransferOptimizerV2(config)
        
        # Get available players
        available_players = players_df[~players_df['id'].isin(player_ids)].copy()
        
        # Get entry info
        session = create_requests_session()
        entry_response = session.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/", timeout=10)
        if entry_response.status_code == 200:
            entry_info = entry_response.json()
            bank = entry_info.get('last_deadline_bank', 0) / 10.0
            
            # Calculate free transfers using the same logic as main.py
            # Counts consecutive gameweeks with no transfers working backwards from last event
            free_transfers = 1  # Default
            try:
                session = create_requests_session()
                # Get entry history
                history_response = session.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/", timeout=10)
                if history_response.status_code == 200:
                    entry_history = history_response.json()
                    current_event = entry_history.get('current', [])[-1] if entry_history.get('current') else None
                    last_event = current_event.get('event', gameweek - 1) if current_event else (gameweek - 1)
                    
                    # Get transfer data
                    transfers_response = session.get(f"https://fantasy.premierleague.com/api/entry/{entry_id}/transfers/", timeout=10)
                    transfers_data = transfers_response.json() if transfers_response.status_code == 200 else []
                    
                    # Group transfers by gameweek
                    transfers_by_gw = {}
                    for t in transfers_data:
                        gw = t.get('event', 0)
                        transfers_by_gw[gw] = transfers_by_gw.get(gw, 0) + 1
                    
                    # Calculate free transfers by checking consecutive gameweeks with no transfers
                    # Start from last_event - 1 (exclude current gameweek we're planning for) and work backwards
                    consecutive_no_transfers = 0
                    start_gw = max(1, last_event - 1)  # Don't count current gameweek
                    
                    # Check gameweeks from start_gw down to 1 (or reasonable limit)
                    for gw in range(start_gw, max(1, start_gw - 10), -1):
                        has_transfers = gw in transfers_by_gw and transfers_by_gw[gw] > 0
                        if not has_transfers:
                            consecutive_no_transfers += 1
                            # Update free transfers as we count consecutive weeks with no transfers
                            free_transfers = min(consecutive_no_transfers + 1, 5)  # Cap at 5
                        else:
                            # Transfers were made this gameweek, stop counting
                            break
            except Exception as e:
                debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Error calculating free transfers", {"error": str(e), "gameweek": gameweek}, "H2")
                # Fallback
                free_transfers = 1
            
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Calculated free transfers", {"free_transfers": free_transfers, "gameweek": gameweek}, "H2")
        else:
            entry_info = {}
            bank = 0.0
            free_transfers = 1
        
        # #region agent log
        # Log bank balance and squad value before optimization
        squad_value_market = current_squad['now_cost'].sum() / 10.0 if not current_squad.empty else 0.0
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"Before optimization", {
            "squad_ids": sorted(current_squad['id'].tolist()), 
            "bank": bank, 
            "free_transfers": free_transfers,
            "squad_value_market": squad_value_market,
            "total_budget_market": bank + squad_value_market
        }, "B")
        # #endregion
        
        # Generate recommendations with CLEAN squad
        # Pass picks_data so optimizer can use selling_price for budget calculations
        smart_recs = optimizer.generate_smart_recommendations(
            current_squad, available_players, bank, free_transfers, max_transfers=4, picks_data=picks_data
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
        
        # Get fixtures for chip evaluation and updated squad display
        fixtures = []
        try:
            session = create_requests_session()
            fixtures_response = session.get("https://fantasy.premierleague.com/api/fixtures/", timeout=10)
            if fixtures_response.status_code == 200:
                fixtures = fixtures_response.json()
                debug_log("ml_report_v2.py:generate_ml_report_v2:step7", f"Fetched fixtures", {"count": len(fixtures)}, "H2")
        except Exception as e:
            debug_log("ml_report_v2.py:generate_ml_report_v2:step7", f"Failed to fetch fixtures", {"error": str(e)}, "H2")
        
        # Generate chip recommendations (v5.0 with LP solver)
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"About to instantiate ChipEvaluator", {"config_chips": config.get("chips", {})}, "H2")
        # #endregion
        
        try:
            chip_eval = ChipEvaluator(config)
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"ChipEvaluator instantiated successfully", {"bb_threshold": getattr(chip_eval, 'bb_threshold', 'N/A'), "tc_threshold": getattr(chip_eval, 'tc_threshold', 'N/A')}, "H2")
            # #endregion
        except Exception as e:
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"ChipEvaluator instantiation failed", {"error": str(e), "error_type": type(e).__name__}, "H2")
            # #endregion
            raise
        
        # #region agent log
        debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"About to call evaluate_all_chips", {
            "current_squad_size": len(current_squad),
            "players_df_size": len(players_df),
            "gameweek": gameweek,
            "avail_chips": avail_chips,
            "bank": bank,
            "has_transfer_recommendations": bool(filtered_recommendations),
            "has_fixtures": bool(fixtures)
        }, "H3")
        # #endregion
        
        try:
            chip_evals = chip_eval.evaluate_all_chips(
                current_squad, players_df, gameweek, avail_chips, bank, 
                transfer_recommendations=filtered_recommendations,
                fixtures=fixtures
            )
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"evaluate_all_chips returned successfully", {
                "has_best_chip": "best_chip" in chip_evals,
                "has_evaluations": "evaluations" in chip_evals,
                "best_chip": chip_evals.get("best_chip", "N/A")
            }, "H3")
            # #endregion
        except Exception as e:
            # #region agent log
            debug_log("ml_report_v2.py:generate_ml_report_v2:step5", f"evaluate_all_chips failed", {
                "error": str(e),
                "error_type": type(e).__name__,
                "error_args": str(e.args) if hasattr(e, 'args') else 'N/A'
            }, "H3")
            # #endregion
            raise
        
        # Generate report data
        report_gen = ReportGenerator(config)
        logger.info(f"ML Report V2: Generating report data with gameweek {gameweek}")
        report_data = report_gen.generate_report_data(
            entry_info, gameweek, current_squad, filtered_recommendations,
            chip_evals, players_df, fixtures, team_map, bootstrap
        )
        
        # CRITICAL: Verify gameweek in report_data
        if 'header' in report_data and 'gameweek' in report_data['header']:
            logger.info(f"ML Report V2: Report data header gameweek = {report_data['header']['gameweek']}")
        else:
            logger.warning(f"ML Report V2: Report data missing header.gameweek! Keys: {list(report_data.keys())}")
        
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
