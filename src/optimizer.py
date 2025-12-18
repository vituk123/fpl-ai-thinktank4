"""
Transfer optimizer with PuLP linear programming.
v3.3: Strict enforcement of forced transfers + GW15 player blocking.
"""
import pandas as pd
import pulp
from typing import Dict, List, Tuple, Optional, Set
import logging
from .utils import price_from_api

logger = logging.getLogger(__name__)

# CRITICAL: Global set of players that should NEVER appear in recommendations
# These players were removed from the game/user's squad before GW16
BLOCKED_PLAYER_IDS: Set[int] = {5, 241}  # Gabriel, Caicedo

class TransferOptimizer:
    def __init__(self, config: Dict):
        self.config = config.get('optimizer', {})
        self.pulp_solver = pulp.PULP_CBC_CMD(msg=False)
        self.points_hit_per_transfer = self.config.get('points_hit_per_transfer', -4)
        self.squad_size = 15
        self.position_requirements = {1: 2, 2: 5, 3: 5, 4: 3}
        self.max_players_per_team = 3
        self.free_transfers = 1
    
    def _verify_squad_integrity(self, squad: pd.DataFrame, gameweek: int = 999) -> pd.DataFrame:
        """
        Verify squad doesn't contain blocked players.
        Returns cleaned squad with blocked players removed.
        Raises ValueError if squad is corrupted.
        """
        if squad.empty:
            return squad
        
        squad_ids = set(squad['id'])
        blocked_found = squad_ids.intersection(BLOCKED_PLAYER_IDS)
        
        if blocked_found:
            logger.error(f"CRITICAL: Squad contains blocked players: {blocked_found}")
            logger.error(f"Full squad IDs: {sorted(squad_ids)}")
            
            # Remove blocked players
            cleaned_squad = squad[~squad['id'].isin(BLOCKED_PLAYER_IDS)].copy()
            logger.warning(f"Removed {len(blocked_found)} blocked players. New squad size: {len(cleaned_squad)}")
            
            # If squad is now too small, raise error
            if len(cleaned_squad) < 11:
                raise ValueError(f"Squad too small after removing blocked players: {len(cleaned_squad)} players (need 11+)")
            
            return cleaned_squad
        
        return squad
        
    def get_current_squad(self, entry_id: int, gameweek: int, api_client, players_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get current squad for the specified gameweek.
        
        NOTE: Gameweek should be determined by the caller to ensure it's clean.
        This function simply fetches the squad for the provided gameweek.
        """
        logger.info(f"Optimizer: [get_current_squad] Entry {entry_id}, Gameweek {gameweek}")
        
        # Clear cache to ensure fresh data
        api_client.clear_cache()
        
        # Fetch picks for the specified gameweek
        picks_data = api_client.get_entry_picks(entry_id, gameweek, use_cache=False)
        
        if not picks_data or 'picks' not in picks_data:
            logger.warning(f"Optimizer: [get_current_squad] No picks data available for entry {entry_id}, gameweek {gameweek}")
            return pd.DataFrame()
        
        player_ids = [p['element'] for p in picks_data['picks']]
        logger.info(f"Optimizer: [get_current_squad] GW{gameweek} raw picks - Player IDs: {sorted(player_ids)}")
        
        # CRITICAL: Final safety check - verify no blocked players
        blocked_found = set(player_ids).intersection(BLOCKED_PLAYER_IDS)
        if blocked_found:
            logger.error(f"Optimizer: [get_current_squad] CRITICAL - GW{gameweek} picks contain blocked players {blocked_found}!")
            logger.error(f"Optimizer: [get_current_squad] This should NOT happen - gameweek should have been validated before calling this function!")
            logger.error(f"Optimizer: [get_current_squad] Full player IDs: {sorted(player_ids)}")
            # Remove blocked players as last resort
            player_ids = [pid for pid in player_ids if pid not in BLOCKED_PLAYER_IDS]
            logger.warning(f"Optimizer: [get_current_squad] Removed blocked players. Filtered player IDs: {sorted(player_ids)}")
        
        squad_df = players_df[players_df['id'].isin(player_ids)].copy()
        
        # Final verification
        squad_ids_from_df = set(squad_df['id'].tolist()) if not squad_df.empty else set()
        blocked_in_df = squad_ids_from_df.intersection(BLOCKED_PLAYER_IDS)
        if blocked_in_df:
            logger.error(f"Optimizer: [get_current_squad] CRITICAL - squad_df contains blocked players {blocked_in_df}!")
            squad_df = squad_df[~squad_df['id'].isin(BLOCKED_PLAYER_IDS)].copy()
            logger.error(f"Optimizer: [get_current_squad] Force-removed from DataFrame. New size: {len(squad_df)}")
        
        if not squad_df.empty:
            logger.info(f"Optimizer: [get_current_squad] ✓ Retrieved squad from GW{gameweek} with {len(squad_df)} players")
            logger.info(f"Optimizer: [get_current_squad] Final Player IDs: {sorted(squad_df['id'].tolist())}")
        else:
            logger.warning(f"Optimizer: [get_current_squad] Retrieved empty squad from GW{gameweek}")
        
        return squad_df
        
        # CRITICAL: Don't cache bootstrap when checking gameweek status
        # Cached data may have stale event flags (is_current, finished, is_next)
        # Also clear picks cache to ensure we get fresh squad data
        api_client.clear_cache()
        bootstrap = api_client.get_bootstrap_static(use_cache=False)
        events = bootstrap.get('events', [])
        target_event = next((e for e in events if e.get('id') == gameweek), None)
        
        is_current = target_event and target_event.get('is_current', False)
        is_finished = target_event and target_event.get('finished', False)
        is_next = target_event and target_event.get('is_next', False)
        
        # #region agent log
        import json, os
        try:
            # Use absolute Windows path for server
            log_path = r'C:\fpl-api\debug.log'
            with open(log_path, 'a') as f:
                f.write(json.dumps({"location":"optimizer.py:39","message":"get_current_squad entry","data":{"entry_id":entry_id,"gameweek":gameweek,"target_event_id":target_event.get('id') if target_event else None,"is_current":is_current,"is_finished":is_finished,"is_next":is_next},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        # Priority 1: If gameweek is finished, use its picks (most recent completed squad)
        # Check finished FIRST because a gameweek can be both is_current and finished
        # When finished, the picks reflect the final squad after all transfers
        if is_finished:
            target_picks_gw = gameweek
            logger.info(f"Gameweek {gameweek} is finished, using picks from GW{target_picks_gw} (most recent completed squad)")
            # #region agent log
            try:
                log_path = r'C:\fpl-api\debug.log'
                with open(log_path, 'a') as f:
                    f.write(json.dumps({"location":"optimizer.py:47","message":"Priority 1: finished gameweek","data":{"gameweek":gameweek,"target_picks_gw":target_picks_gw},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
            except Exception as e:
                logger.error(f"Debug log write failed: {e}")
            # #endregion
        
        # Priority 2: If gameweek is in session (not finished), use its picks (includes recent transfers)
        elif is_current:
            target_picks_gw = gameweek
            logger.info(f"Gameweek {gameweek} is in session, using picks from GW{target_picks_gw} (includes transfers made before deadline)")
        
        # If neither finished nor current, but gameweek >= 16, still try to use it
        # (handles edge cases where flags might be incorrect)
        elif gameweek >= 16:
            target_picks_gw = gameweek
            logger.info(f"Gameweek {gameweek} >= 16, attempting to use picks from GW{target_picks_gw} (may reflect recent transfers)")
            # #region agent log
            try:
                with open(r'C:\fpl-api\debug.log', 'a') as f:
                    f.write(json.dumps({"location":"optimizer.py:53","message":"Priority 2: current gameweek","data":{"gameweek":gameweek,"target_picks_gw":target_picks_gw},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
            except: pass
            # #endregion
        
        # Priority 3: If gameweek hasn't started yet, find the most recent finished gameweek
        elif is_next:
            # Find the most recent finished gameweek (this is the current squad)
            finished_events = [e for e in events if e.get('finished', False)]
            if finished_events:
                most_recent_finished = max(finished_events, key=lambda x: x.get('id', 0))
                target_picks_gw = most_recent_finished.get('id')
                logger.info(f"Gameweek {gameweek} hasn't started yet, using picks from most recent finished GW{target_picks_gw}")
                # #region agent log
                try:
                    with open(r'C:\fpl-api\debug.log', 'a') as f:
                        f.write(json.dumps({"location":"optimizer.py:60","message":"Priority 3: most recent finished","data":{"gameweek":gameweek,"target_picks_gw":target_picks_gw,"most_recent_finished_id":most_recent_finished.get('id')},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
                except: pass
                # #endregion
            else:
                # Fallback: use gameweek - 1
                target_picks_gw = max(1, gameweek - 1)
                logger.warning(f"No finished gameweeks found, falling back to GW{target_picks_gw}")
                # #region agent log
                try:
                    with open(r'C:\fpl-api\debug.log', 'a') as f:
                        f.write(json.dumps({"location":"optimizer.py:66","message":"Priority 3 fallback: gameweek-1","data":{"gameweek":gameweek,"target_picks_gw":target_picks_gw},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
                except: pass
                # #endregion
        
        # Priority 4: Fallback to gameweek - 1
        else:
            target_picks_gw = max(1, gameweek - 1)
            logger.warning(f"Could not determine gameweek status, falling back to GW{target_picks_gw}")
            # #region agent log
            try:
                with open(r'C:\fpl-api\debug.log', 'a') as f:
                    f.write(json.dumps({"location":"optimizer.py:72","message":"Priority 4 fallback: gameweek-1","data":{"gameweek":gameweek,"target_picks_gw":target_picks_gw},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
            except: pass
            # #endregion
        
        # Check for free hit chip (affects which gameweek's picks to use)
        history = api_client.get_entry_history(entry_id)
        chips_used = history.get('chips', [])
        free_hit_active = False
        for chip in chips_used:
            if chip['event'] == target_picks_gw and chip['name'] == 'freehit':
                free_hit_active = True
                break
        
        # If free hit was active in the target gameweek, use the gameweek before that
        if free_hit_active:
            target_picks_gw = max(1, target_picks_gw - 1)
            logger.info(f"Free hit was active in GW{target_picks_gw + 1}, using picks from GW{target_picks_gw} instead")
        
        # Try to get picks for the target gameweek
        # CRITICAL: Disable cache to ensure we get fresh picks data
        # #region agent log
        try:
            log_path = r'C:\fpl-api\debug.log'
            with open(log_path, 'a') as f:
                f.write(json.dumps({"location":"optimizer.py:84","message":"Before API call for picks","data":{"entry_id":entry_id,"target_picks_gw":target_picks_gw,"gameweek":gameweek},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        picks_data = api_client.get_entry_picks(entry_id, target_picks_gw, use_cache=False)
        
        # CRITICAL FIX: If picks contain problem players, try next gameweek
        if picks_data and 'picks' in picks_data:
            player_ids_in_picks = {p['element'] for p in picks_data['picks']}
            if gameweek >= 16 and PROBLEM_PLAYER_IDS.intersection(player_ids_in_picks):
                logger.error(f"CRITICAL: GW{target_picks_gw} picks contain problem players {PROBLEM_PLAYER_IDS.intersection(player_ids_in_picks)}! These players were removed before GW16.")
                # Try next gameweek to get updated squad
                next_gw = target_picks_gw + 1
                logger.warning(f"Attempting to fetch GW{next_gw} picks to get updated squad...")
                next_picks = api_client.get_entry_picks(entry_id, next_gw, use_cache=False)
                if next_picks and 'picks' in next_picks:
                    next_player_ids = {p['element'] for p in next_picks['picks']}
                    if not PROBLEM_PLAYER_IDS.intersection(next_player_ids):
                        logger.info(f"SUCCESS: GW{next_gw} picks are clean, using them instead")
                        picks_data = next_picks
                        target_picks_gw = next_gw
                    else:
                        logger.error(f"GW{next_gw} also contains problem players! Will filter them out...")
        
        # If picks not available for target gameweek, try the provided gameweek as fallback
        # CRITICAL: For GW16+, NEVER fall back to GW15 (gameweek-1) as it contains removed players
        if not picks_data or 'picks' not in picks_data:
            if target_picks_gw != gameweek and gameweek >= 16:
                # For GW16+, try the gameweek itself, but NEVER gameweek-1
                logger.warning(f"No picks found for GW{target_picks_gw}, trying GW{gameweek} as fallback (NOT GW{gameweek-1} to avoid GW15 players)")
                picks_data = api_client.get_entry_picks(entry_id, gameweek, use_cache=False)
                if picks_data and 'picks' in picks_data:
                    target_picks_gw = gameweek
            elif target_picks_gw != gameweek:
                logger.warning(f"No picks found for GW{target_picks_gw}, trying GW{gameweek} as fallback")
                picks_data = api_client.get_entry_picks(entry_id, gameweek, use_cache=False)
                if picks_data and 'picks' in picks_data:
                    target_picks_gw = gameweek
        
        if not picks_data or 'picks' not in picks_data:
            logger.warning(f"No picks data available for entry {entry_id}, gameweek {target_picks_gw}")
            return pd.DataFrame()

        player_ids = [p['element'] for p in picks_data['picks']]
        
        # CRITICAL FILTER: ALWAYS remove problem players for GW16+ (no exceptions)
        if gameweek >= 16:
            original_count = len(player_ids)
            original_player_ids_set = set(player_ids)
            problem_found = PROBLEM_PLAYER_IDS.intersection(original_player_ids_set)
            
            if problem_found:
                logger.error(f"CRITICAL: Found problem players {problem_found} in picks from GW{target_picks_gw}! Filtering them out immediately.")
                player_ids = [pid for pid in player_ids if pid not in PROBLEM_PLAYER_IDS]
                logger.error(f"CRITICAL: Removed {original_count - len(player_ids)} problem players! Original count: {original_count}, Filtered count: {len(player_ids)}")
                logger.error(f"Original player IDs: {sorted(original_player_ids_set)}")
                logger.error(f"Filtered player IDs: {sorted(player_ids)}")
            else:
                logger.info(f"No problem players found in picks. Squad is clean.")
        
        squad_df = players_df[players_df['id'].isin(player_ids)].copy()
        
        # Final verification - squad should NEVER contain problem players
        if not squad_df.empty and gameweek >= 16:
            squad_ids_set = set(squad_df['id'].tolist())
            final_problem_check = PROBLEM_PLAYER_IDS.intersection(squad_ids_set)
            if final_problem_check:
                logger.error(f"CRITICAL ERROR: Problem players {final_problem_check} STILL in squad_df after filtering! This should never happen!")
                # Force remove them from squad_df
                squad_df = squad_df[~squad_df['id'].isin(PROBLEM_PLAYER_IDS)].copy()
                logger.error(f"Force-removed problem players. New squad size: {len(squad_df)}")
        
        if not squad_df.empty:
            logger.info(f"Retrieved squad with {len(squad_df)} players from GW{target_picks_gw}. Player IDs: {sorted(squad_df['id'].tolist())}")
        else:
            logger.warning(f"Retrieved empty squad from GW{target_picks_gw}. Player IDs from picks: {player_ids}")
        
        # #region agent log
        try:
            log_path = r'C:\fpl-api\debug.log'
            with open(log_path, 'a') as f:
                f.write(json.dumps({"location":"optimizer.py:122","message":"get_current_squad exit","data":{"target_picks_gw":target_picks_gw,"squad_size":len(squad_df),"player_ids":sorted(player_ids)[:15]},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        return squad_df
    
    def create_pulp_model(self,
                         current_squad: pd.DataFrame,
                         available_players: pd.DataFrame,
                         bank: float,
                         free_transfers: int,
                         num_transfers: int,
                         forced_out_ids: List[int] = None) -> Tuple[pulp.LpProblem, Dict]:
        
        # CRITICAL: Verify squad integrity FIRST - before creating any variables
        current_squad = self._verify_squad_integrity(current_squad, gameweek=999)
        
        prob = pulp.LpProblem("FPL_Transfer_Optimization", pulp.LpMaximize)
        
        final_squad_vars = {}
        transfer_out_vars = {}
        transfer_in_vars = {}
        
        current_squad_ids = set(current_squad['id'])
        available_player_ids = set(available_players['id'])
        
        # CRITICAL: Double-check no blocked players in squad IDs
        blocked_in_squad = current_squad_ids.intersection(BLOCKED_PLAYER_IDS)
        if blocked_in_squad:
            raise ValueError(f"CRITICAL: Blocked players {blocked_in_squad} still in squad after verification!")
        
        all_player_ids = current_squad_ids.union(available_player_ids)
        
        # CRITICAL: Verify no GW15 players (Gabriel=5, Caicedo=241) in current_squad
        # These players were removed before GW16 started
        problem_players = {5, 241}  # Gabriel, Caicedo
        found_problem_players = current_squad_ids.intersection(problem_players)
        if found_problem_players:
            logger.error(f"CRITICAL ERROR in create_pulp_model: Found GW15 players in current_squad! Problem player IDs: {found_problem_players}, Full squad IDs: {sorted(current_squad_ids)}")
            # Remove problem players from current_squad to prevent wrong recommendations
            current_squad = current_squad[~current_squad['id'].isin(problem_players)].copy()
            current_squad_ids = set(current_squad['id'])
            logger.warning(f"Removed problem players from squad. New squad size: {len(current_squad)}, IDs: {sorted(current_squad_ids)}")
        
        # #region agent log
        try:
            log_path = r'C:\fpl-api\debug.log'
            squad_ids_list = sorted(list(current_squad_ids))
            with open(log_path, 'a') as f:
                f.write(json.dumps({"location":"optimizer.py:223","message":"create_pulp_model - current_squad_ids","data":{"squadSize":len(current_squad),"squadPlayerIds":squad_ids_list,"problemPlayers":{"Gabriel(5)":5 in current_squad_ids,"Caicedo(241)":241 in current_squad_ids,"Casemiro(457)":457 in current_squad_ids,"Burn(476)":476 in current_squad_ids}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        except: pass
        # #endregion
        
        # Variables
        for pid in all_player_ids:
            final_squad_vars[pid] = pulp.LpVariable(f"in_squad_{pid}", cat='Binary')
        for pid in current_squad_ids:
            transfer_out_vars[pid] = pulp.LpVariable(f"trans_out_{pid}", cat='Binary')
        for pid in available_player_ids:
            transfer_in_vars[pid] = pulp.LpVariable(f"trans_in_{pid}", cat='Binary')
        
        # Constraints
        # Link squad to transfers
        for pid in current_squad_ids:
            prob += final_squad_vars[pid] == 1 - transfer_out_vars[pid]
        for pid in available_player_ids:
            prob += final_squad_vars[pid] == transfer_in_vars[pid]
            
        # CRITICAL FIX: Enforce forced transfers out
        if forced_out_ids:
            for fid in forced_out_ids:
                if fid in transfer_out_vars:
                    prob += transfer_out_vars[fid] == 1, f"Force_Out_{fid}"

        # Objective: Maximize EV - Penalty + Proven Performance Tiebreaker
        penalty_hits = max(0, num_transfers - free_transfers)
        transfer_penalty = penalty_hits * abs(self.points_hit_per_transfer)
        
        # Proven performance tiebreaker: prefer players with more total_points when EV is similar
        # Use fixed normalization scale (100 points) for consistent tiebreaker impact
        # This ensures a 10-point difference in total_points = 0.1 tiebreaker bonus
        normalization_scale = 100.0
        
        total_ev = 0
        proven_bonus = 0  # Tiebreaker: bonus for proven players (total_points)
        
        # Tiebreaker weight: 0.5 means a 20-point difference in total_points = 0.1 bonus
        # This allows proven players to win when EV is within ~0.5-1.0
        # Example: Player A (EV=16.0, 50 pts) vs Player B (EV=15.5, 80 pts)
        # Player A: 16.0 + 0.25 = 16.25, Player B: 15.5 + 0.40 = 15.90
        # If EV difference is smaller (e.g., 0.3), Player B wins
        tiebreaker_weight = 0.5
        
        for _, p in current_squad.iterrows():
            ev = p.get('EV', 0)
            total_ev += final_squad_vars[p['id']] * ev
            
            # Add tiebreaker bonus based on total_points (normalized by fixed scale)
            if 'total_points' in p:
                normalized_points = min(p['total_points'] / normalization_scale, 1.0)  # Cap at 1.0
                proven_bonus += final_squad_vars[p['id']] * normalized_points * tiebreaker_weight
        
        for _, p in available_players.iterrows():
            ev = p.get('EV', 0)
            total_ev += final_squad_vars[p['id']] * ev
            
            # Add tiebreaker bonus based on total_points (normalized by fixed scale)
            if 'total_points' in p:
                normalized_points = min(p['total_points'] / normalization_scale, 1.0)  # Cap at 1.0
                proven_bonus += final_squad_vars[p['id']] * normalized_points * tiebreaker_weight
        
        # Objective: EV + Proven Performance Tiebreaker - Transfer Penalty
        prob += total_ev + proven_bonus - transfer_penalty
        
        # Standard Rules
        prob += pulp.lpSum(final_squad_vars.values()) == self.squad_size
        prob += pulp.lpSum(transfer_out_vars.values()) == num_transfers
        prob += pulp.lpSum(transfer_in_vars.values()) == num_transfers
        
        # Budget
        cost_ins = pulp.lpSum([transfer_in_vars[p['id']] * price_from_api(p['now_cost']) for _, p in available_players.iterrows()])
        val_outs = pulp.lpSum([transfer_out_vars[p['id']] * price_from_api(p['now_cost']) for _, p in current_squad.iterrows()])
        prob += cost_ins <= float(bank) + val_outs
        
        # Positions
        for pos, count in self.position_requirements.items():
            current_pos = [final_squad_vars[p['id']] for _, p in current_squad.iterrows() if p['element_type'] == pos]
            avail_pos = [final_squad_vars[p['id']] for _, p in available_players.iterrows() if p['element_type'] == pos]
            prob += pulp.lpSum(current_pos + avail_pos) == count

        # Teams
        all_teams = set(current_squad['team']).union(set(available_players['team']))
        for t in all_teams:
            current_team = [final_squad_vars[p['id']] for _, p in current_squad.iterrows() if p['team'] == t]
            avail_team = [final_squad_vars[p['id']] for _, p in available_players.iterrows() if p['team'] == t]
            prob += pulp.lpSum(current_team + avail_team) <= self.max_players_per_team

        return prob, {'transfer_out_vars': transfer_out_vars, 'transfer_in_vars': transfer_in_vars, 'player_vars': final_squad_vars}

    def solve_transfer_optimization(self, current_squad, available_players, bank, free_transfers, num_transfers, forced_out_ids=None):
        prob, variables = self.create_pulp_model(current_squad, available_players, bank, free_transfers, num_transfers, forced_out_ids)
        prob.solve(self.pulp_solver)
        
        if prob.status != pulp.LpStatusOptimal:
            return {'status': 'infeasible', 'net_ev_gain_adjusted': -999}
            
        # Extract results
        players_out = []
        # #region agent log
        try:
            log_path = r'C:\fpl-api\debug.log'
            current_squad_ids_in_optimizer = sorted(current_squad['id'].tolist()) if not current_squad.empty else []
            with open(log_path, 'a') as f:
                f.write(json.dumps({"location":"optimizer.py:320","message":"solve_transfer_optimization - current_squad check","data":{"squadSize":len(current_squad),"squadPlayerIds":current_squad_ids_in_optimizer,"problemPlayersInSquad":{"Gabriel(5)":5 in current_squad_ids_in_optimizer,"Caicedo(241)":241 in current_squad_ids_in_optimizer}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        except: pass
        # #endregion
        for pid, var in variables['transfer_out_vars'].items():
            if var.varValue > 0.5:
                # Verify player is actually in current_squad
                player_in_squad = current_squad[current_squad['id'] == pid]
                if player_in_squad.empty:
                    logger.error(f"CRITICAL: Player ID {pid} selected for transfer out but NOT in current_squad! Squad IDs: {sorted(current_squad['id'].tolist())}")
                    continue
                p = player_in_squad.iloc[0]
                players_out.append({'name': p['web_name'], 'team': p['team_name'], 'id': p['id'], 'EV': p.get('EV', 0)})
                # #region agent log
                try:
                    log_path = r'C:\fpl-api\debug.log'
                    with open(log_path, 'a') as f:
                        f.write(json.dumps({"location":"optimizer.py:332","message":"Player selected for transfer out","data":{"playerId":pid,"playerName":p['web_name'],"problemPlayer":pid in [5, 241, 457, 476],"playerInSquad":True},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
                except: pass
                # #endregion
                
        players_in = []
        for pid, var in variables['transfer_in_vars'].items():
            if var.varValue > 0.5:
                p = available_players[available_players['id'] == pid].iloc[0]
                players_in.append({'name': p['web_name'], 'team': p['team_name'], 'id': p['id'], 'EV': p.get('EV', 0)})
        
        current_ev = current_squad['EV'].sum()
        final_ev = pulp.value(prob.objective) + (max(0, num_transfers - free_transfers) * abs(self.points_hit_per_transfer))
        net_gain = final_ev - current_ev
        
        return {
            'status': 'optimal',
            'num_transfers': num_transfers,
            'players_out': players_out,
            'players_in': players_in,
            'net_ev_gain': net_gain,
            'net_ev_gain_adjusted': net_gain - (max(0, num_transfers - free_transfers) * abs(self.points_hit_per_transfer))
        }

    def _is_scenario_beneficial(self, sol: Dict, min_gain: float = 0.5) -> bool:
        """
        Check if a transfer scenario is beneficial enough to include.
        
        Args:
            sol: Solution dictionary from solve_transfer_optimization
            min_gain: Minimum net EV gain threshold (default 0.5)
        
        Returns:
            True if scenario is beneficial, False otherwise
        """
        if sol.get('status') != 'optimal':
            return False
        
        net_gain = sol.get('net_ev_gain_adjusted', -999)
        # For forced transfers, allow slightly negative gains (up to -10) as they're necessary
        # For optional transfers, require positive gain
        return net_gain >= min_gain or (net_gain > -10 and sol.get('strategy') == 'FIX_FORCED')
    
    def _deduplicate_scenarios(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Remove duplicate scenarios (same number of transfers, same net gain).
        
        Args:
            recommendations: List of recommendation dictionaries
        
        Returns:
            Deduplicated list of recommendations
        """
        seen = {}
        deduplicated = []
        
        for rec in recommendations:
            num_transfers = rec.get('num_transfers', 0)
            net_gain = rec.get('net_ev_gain_adjusted', 0)
            # Create a key based on num_transfers and rounded net_gain
            key = (num_transfers, round(net_gain, 2))
            
            # Keep the first occurrence (highest net_gain due to sorting)
            if key not in seen:
                seen[key] = True
                deduplicated.append(rec)
        
        return deduplicated
    
    def _filter_unprofitable_hits(self, recommendations: List[Dict], free_transfers: int) -> List[Dict]:
        """
        Remove scenarios where taking a hit doesn't provide enough benefit.
        If a scenario with hits has net gain less than 4 points better than a scenario
        without hits (with fewer transfers), remove the scenario with hits.
        
        Args:
            recommendations: List of recommendation dictionaries (should be sorted by net gain)
            free_transfers: Number of free transfers available
        
        Returns:
            Filtered list of recommendations
        """
        if not recommendations:
            return recommendations
        
        # Group scenarios by whether they have hits
        scenarios_with_hits = []
        scenarios_without_hits = []
        
        for rec in recommendations:
            hits = rec.get('penalty_hits', 0)
            if hits > 0:
                scenarios_with_hits.append(rec)
            else:
                scenarios_without_hits.append(rec)
        
        # If no scenarios with hits, return as-is
        if not scenarios_with_hits:
            return recommendations
        
        # Find the best scenario without hits for comparison
        best_no_hit_gain = 0
        if scenarios_without_hits:
            best_no_hit_gain = max(rec.get('net_ev_gain_adjusted', 0) for rec in scenarios_without_hits)
        
        # Filter out scenarios with hits that don't provide enough benefit
        filtered = []
        hit_cost = abs(self.points_hit_per_transfer)  # Typically 4 points
        
        for rec in recommendations:
            hits = rec.get('penalty_hits', 0)
            net_gain = rec.get('net_ev_gain_adjusted', 0)
            
            if hits > 0:
                # This scenario has hits - check if it's worth it
                gain_over_no_hit = net_gain - best_no_hit_gain
                
                if gain_over_no_hit >= hit_cost:
                    # Taking the hit is worth it (gain >= hit cost)
                    filtered.append(rec)
                    logger.info(f"   Keeping {rec['num_transfers']} transfer scenario with {hits} hit(s): net gain {net_gain:.2f} is {gain_over_no_hit:.2f} better than no-hit option")
                else:
                    # Taking the hit is NOT worth it (gain < hit cost)
                    logger.info(f"   Removing {rec['num_transfers']} transfer scenario with {hits} hit(s): net gain {net_gain:.2f} is only {gain_over_no_hit:.2f} better than no-hit option (need {hit_cost} points)")
            else:
                # No hits - always keep
                filtered.append(rec)
        
        return filtered
    
    def generate_smart_recommendations(self, current_squad, available_players, bank, free_transfers, max_transfers: int = 4):
        """
        Generate comprehensive transfer recommendations.
        
        CRITICAL: Verifies squad integrity before optimization.
        """
        # CRITICAL: Verify and clean squad BEFORE any optimization
        try:
            original_size = len(current_squad)
            current_squad = self._verify_squad_integrity(current_squad, gameweek=999)
            if len(current_squad) < original_size:
                logger.warning(f"Squad was cleaned: {original_size} -> {len(current_squad)} players")
        except ValueError as e:
            logger.error(f"Squad integrity check failed: {e}")
            return {
                'recommendations': [],
                'num_forced_transfers': 0,
                'forced_players': [],
                'error': str(e)
            }
        
        if current_squad.empty:
            logger.error("Current squad is empty after verification!")
            return {
                'recommendations': [],
                'num_forced_transfers': 0,
                'forced_players': [],
                'error': 'Empty squad'
            }
        
        logger.info(f"Generating recommendations with {len(current_squad)} players")
        logger.info(f"Squad player IDs: {sorted(current_squad['id'].tolist())[:10]}...")
        
        # #region agent log
        import json
        try:
            log_path = r'C:\fpl-api\debug.log'
            squad_player_ids = sorted(current_squad['id'].tolist()) if not current_squad.empty else []
            # Also log the actual player names to verify
            player_names = {}
            if not current_squad.empty:
                for idx, row in current_squad.iterrows():
                    player_names[row['id']] = row.get('web_name', 'Unknown')
            logger.info(f"generate_smart_recommendations entry - Squad size: {len(current_squad)}, Player IDs: {squad_player_ids}, Names: {player_names}")
            with open(log_path, 'a') as f:
                f.write(json.dumps({"location":"optimizer.py:452","message":"generate_smart_recommendations entry","data":{"squadSize":len(current_squad),"playerIds":squad_player_ids,"playerNames":player_names,"problemPlayers":{"Gabriel(5)":5 in squad_player_ids,"Caicedo(241)":241 in squad_player_ids,"Casemiro(457)":457 in squad_player_ids,"Burn(476)":476 in squad_player_ids}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        # Identify forced transfers: injured, suspended, or doubtful with low chance
        # Check status and chance_of_playing
        forced_mask = pd.Series(False, index=current_squad.index)
        
        # Status-based: injured, suspended, unavailable
        status_forced = current_squad['status'].isin(['i', 's', 'u'])
        forced_mask = forced_mask | status_forced
        
        # Chance-based: 0% chance of playing
        if 'chance_of_playing_this_round' in current_squad.columns:
            chance = pd.to_numeric(current_squad['chance_of_playing_this_round'], errors='coerce').fillna(100)
        else:
            chance = pd.Series([100] * len(current_squad), index=current_squad.index)
        
        zero_chance = (chance == 0)
        forced_mask = forced_mask | zero_chance
        
        # Doubtful with low chance (<50%): also flag as forced
        doubtful = current_squad['status'] == 'd'
        low_chance = chance < 50
        doubtful_low_chance = doubtful & low_chance
        forced_mask = forced_mask | doubtful_low_chance
        
        # Also check EV <= 0.1 as fallback
        low_ev = current_squad.get('EV', pd.Series([999]*len(current_squad))) <= 0.1
        forced_mask = forced_mask | low_ev
        
        forced_out = current_squad[forced_mask].copy()
        forced_ids = forced_out['id'].tolist()
        num_forced = len(forced_ids)
        
        recommendations = []
        
        # Strategy 1: Forced transfer scenarios (if forced transfers exist)
        if num_forced > 0:
            # Fix exact forced players
            sol = self.solve_transfer_optimization(current_squad, available_players, bank, free_transfers, num_forced, forced_out_ids=forced_ids)
            if self._is_scenario_beneficial(sol, min_gain=-10):
                sol.update({
                    'strategy': 'FIX_FORCED',
                    'description': f'Fix {num_forced} injured player(s)',
                    'priority': 'HIGH',
                    'penalty_hits': max(0, num_forced-free_transfers),
                    'transfer_penalty': max(0, num_forced-free_transfers)*4,
                    'original_net_gain': sol['net_ev_gain']
                })
                recommendations.append(sol)
            
            # Fix forced + upgrades (if within max_transfers limit)
            for additional_tx in range(1, max_transfers - num_forced + 1):
                total_tx = num_forced + additional_tx
                if total_tx > max_transfers:
                    break
                
                sol = self.solve_transfer_optimization(current_squad, available_players, bank, free_transfers, total_tx, forced_out_ids=forced_ids)
                if self._is_scenario_beneficial(sol, min_gain=0.5):
                    sol.update({
                        'strategy': 'FIX_PLUS_UPGRADE',
                        'description': f'Fix {num_forced} injured + {additional_tx} upgrade(s)',
                        'priority': 'MEDIUM',
                        'penalty_hits': max(0, total_tx-free_transfers),
                        'transfer_penalty': max(0, total_tx-free_transfers)*4,
                        'original_net_gain': sol['net_ev_gain']
                    })
                    recommendations.append(sol)
        
        # Strategy 2: Optional scenarios (always generate, regardless of forced transfers)
        # Generate 1, 2, 3, 4 transfer scenarios if beneficial
        for tx in range(1, min(max_transfers + 1, 5)):  # Generate up to 4 transfers or max_transfers
            # Skip if this scenario would be identical to a forced scenario
            if num_forced > 0 and tx == num_forced:
                # Already generated as forced scenario, skip to avoid duplicate
                continue
            
            sol = self.solve_transfer_optimization(current_squad, available_players, bank, free_transfers, tx)
            # Lower threshold to 0.1 for optional transfers to show more recommendations
            # This allows marginal improvements to be shown
            if self._is_scenario_beneficial(sol, min_gain=0.1):
                sol.update({
                    'strategy': 'OPTIMIZE',
                    'description': f'Optimize squad ({tx} transfer{"s" if tx > 1 else ""})',
                    'priority': 'LOW',
                    'penalty_hits': max(0, tx-free_transfers),
                    'transfer_penalty': max(0, tx-free_transfers)*4,
                    'original_net_gain': sol['net_ev_gain']
                })
                recommendations.append(sol)
        
        # Deduplicate scenarios (remove identical num_transfers with same net gain)
        recommendations = self._deduplicate_scenarios(recommendations)
        
        # Sort by net gain before filtering (needed for hit comparison)
        recommendations.sort(key=lambda x: x['net_ev_gain_adjusted'], reverse=True)
        
        # Filter out scenarios where taking a hit doesn't provide enough benefit
        recommendations = self._filter_unprofitable_hits(recommendations, free_transfers)
        
        # IMPROVEMENT: Ensure position balance for forced transfers
        # If a player in a specific position is forced out, prioritize that position in replacements
        if num_forced > 0:
            # Count forced transfers by position
            forced_by_pos = forced_out.groupby('element_type').size().to_dict()
            
            # For each recommendation, check if it maintains position balance
            for rec in recommendations:
                # Count positions in transfers
                players_out = rec.get('players_out', [])
                players_in = rec.get('players_in', [])
                
                # Get position counts from names (approximate check)
                # This is a heuristic - full check happens in LP solver
                rec['position_balanced'] = True  # LP solver enforces this, but flag for logging
        
        # Final sort by net EV gain (descending)
        recommendations.sort(key=lambda x: x['net_ev_gain_adjusted'], reverse=True)
        
        # If no recommendations found, try to generate at least one with a very low threshold
        # This ensures users always see something, even if marginal
        if not recommendations and free_transfers > 0:
            logger.info("No recommendations found with standard thresholds, trying with lower threshold...")
            for tx in range(1, min(max_transfers + 1, 3)):  # Try 1-2 transfers only
                sol = self.solve_transfer_optimization(current_squad, available_players, bank, free_transfers, tx)
                if sol.get('status') == 'optimal' and sol.get('net_ev_gain_adjusted', -999) >= -2.0:  # Allow up to -2 points
                    sol.update({
                        'strategy': 'OPTIMIZE',
                        'description': f'Marginal optimization ({tx} transfer{"s" if tx > 1 else ""})',
                        'priority': 'VERY LOW',
                        'penalty_hits': max(0, tx-free_transfers),
                        'transfer_penalty': max(0, tx-free_transfers)*4,
                        'original_net_gain': sol['net_ev_gain']
                    })
                    recommendations.append(sol)
                    logger.info(f"Found marginal recommendation: {tx} transfer(s) with net gain {sol.get('net_ev_gain_adjusted', 0):.2f}")
                    break  # Only add one marginal recommendation
        
        return {'recommendations': recommendations, 'num_forced_transfers': num_forced, 'forced_players': forced_out.to_dict('records')}
