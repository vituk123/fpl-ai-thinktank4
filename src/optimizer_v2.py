"""
Transfer optimizer with PuLP linear programming - REWRITTEN FROM SCRATCH.
v4.0: Clean implementation with explicit blocked player prevention.
"""
import pandas as pd
import pulp
from typing import Dict, List, Tuple, Optional, Set
import logging
from .utils import price_from_api

logger = logging.getLogger(__name__)

# CRITICAL: Global set of players that should NEVER appear in recommendations
BLOCKED_PLAYER_IDS: Set[int] = {5, 241}  # Gabriel, Caicedo


class TransferOptimizerV2:
    """
    Clean rewrite of transfer optimizer with explicit blocked player prevention.
    """
    
    def __init__(self, config: Dict):
        self.config = config.get('optimizer', {})
        self.pulp_solver = pulp.PULP_CBC_CMD(msg=False)
        self.points_hit_per_transfer = self.config.get('points_hit_per_transfer', -4)
        self.squad_size = 15
        self.position_requirements = {1: 2, 2: 5, 3: 5, 4: 3}
        self.max_players_per_team = 3
        self.free_transfers = 1
    
    def get_current_squad(self, entry_id: int, gameweek: int, api_client, players_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get current squad for the specified gameweek.
        
        CRITICAL: This function MUST return a squad without blocked players.
        Uses direct FPL API call to bypass any caching issues.
        
        Returns:
            pd.DataFrame: Squad DataFrame with blocked players removed
        """
        logger.info(f"OptimizerV2: [get_current_squad] Entry {entry_id}, Gameweek {gameweek}")
        
        # CRITICAL: Use direct HTTP request to bypass any caching
        import requests
        url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gameweek}/picks/"
        logger.info(f"OptimizerV2: [get_current_squad] Making DIRECT FPL API call: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                picks_data = response.json()
                logger.info(f"OptimizerV2: [get_current_squad] Direct API call successful")
            else:
                logger.warning(f"OptimizerV2: [get_current_squad] Direct API call failed: {response.status_code}")
                # Fallback to api_client
                api_client.clear_cache()
                picks_data = api_client.get_entry_picks(entry_id, gameweek, use_cache=False)
        except Exception as e:
            logger.warning(f"OptimizerV2: [get_current_squad] Direct API call error: {e}, using api_client")
            api_client.clear_cache()
            picks_data = api_client.get_entry_picks(entry_id, gameweek, use_cache=False)
        
        if not picks_data or 'picks' not in picks_data:
            logger.warning(f"OptimizerV2: [get_current_squad] No picks data for entry {entry_id}, gameweek {gameweek}")
            return pd.DataFrame()
        
        # #region agent log
        # Log picks data structure to check for selling_price
        import json
        sample_pick = picks_data['picks'][0] if picks_data['picks'] else {}
        log_data = {
            'location': 'optimizer_v2.py:get_current_squad:picks_structure',
            'message': 'FPL API picks data structure',
            'data': {
                'sample_pick_keys': list(sample_pick.keys()),
                'has_selling_price': 'selling_price' in sample_pick,
                'sample_pick': {k: v for k, v in sample_pick.items() if k in ['element', 'selling_price', 'purchase_price', 'now_cost']} if sample_pick else {},
                'total_picks': len(picks_data['picks'])
            },
            'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'C'
        }
        try:
            import os
            # Use server-accessible path (Windows: C:\fpl-api\debug.log, Linux/Mac: workspace/.cursor/debug.log)
            if os.name == 'nt':  # Windows
                debug_log_path = r'C:\fpl-api\debug.log'
            else:
                debug_log_path = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        # Extract player IDs from picks
        player_ids = [p['element'] for p in picks_data['picks']]
        logger.info(f"OptimizerV2: [get_current_squad] Raw picks from FPL API - Player IDs: {sorted(player_ids)}")
        
        # CRITICAL: Remove blocked players immediately
        original_count = len(player_ids)
        player_ids = [pid for pid in player_ids if pid not in BLOCKED_PLAYER_IDS]
        removed_count = original_count - len(player_ids)
        
        if removed_count > 0:
            logger.error(f"OptimizerV2: [get_current_squad] ❌❌❌ CRITICAL - FPL API RETURNED {removed_count} BLOCKED PLAYERS! ❌❌❌")
            logger.error(f"OptimizerV2: [get_current_squad] Original IDs: {sorted([p['element'] for p in picks_data['picks']])}")
            logger.error(f"OptimizerV2: [get_current_squad] Filtered IDs: {sorted(player_ids)}")
        else:
            logger.info(f"OptimizerV2: [get_current_squad] ✅ FPL API returned clean picks (no blocked players)")
        
        # Create squad DataFrame
        if not player_ids:
            logger.warning(f"OptimizerV2: [get_current_squad] No valid players after filtering")
            return pd.DataFrame()
        
        squad_df = players_df[players_df['id'].isin(player_ids)].copy()
        
        # #region agent log
        # Add selling_price from picks data to squad_df if available
        if not squad_df.empty and 'picks' in picks_data:
            picks_dict = {p['element']: p for p in picks_data['picks']}
            selling_prices = []
            for _, row in squad_df.iterrows():
                pid = row['id']
                pick_data = picks_dict.get(pid, {})
                selling_price = pick_data.get('selling_price', None)
                selling_prices.append(selling_price)
            squad_df['selling_price'] = selling_prices
            
            # Log selling prices vs now_cost
            price_comparison = []
            for _, row in squad_df.iterrows():
                price_comparison.append({
                    'id': int(row['id']),
                    'name': str(row.get('web_name', 'Unknown')),
                    'now_cost': int(row.get('now_cost', 0)),
                    'selling_price': int(row.get('selling_price', 0)) if pd.notna(row.get('selling_price')) else None,
                    'difference': int(row.get('now_cost', 0)) - (int(row.get('selling_price', 0)) if pd.notna(row.get('selling_price')) else 0)
                })
            log_data = {
                'location': 'optimizer_v2.py:get_current_squad:selling_prices',
                'message': 'Selling prices vs market prices',
                'data': {
                    'price_comparison': price_comparison,
                    'total_squad_value_market': float(squad_df['now_cost'].sum() / 10.0),
                    'total_squad_value_selling': float(squad_df['selling_price'].sum() / 10.0) if 'selling_price' in squad_df.columns else None
                },
                'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'A'
            }
            try:
                with open('/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps(log_data) + '\n')
            except Exception as e:
                logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        # FINAL VERIFICATION: Ensure no blocked players in DataFrame
        squad_ids = set(squad_df['id'].tolist()) if not squad_df.empty else set()
        blocked_found = squad_ids.intersection(BLOCKED_PLAYER_IDS)
        
        if blocked_found:
            logger.error(f"OptimizerV2: [get_current_squad] ❌❌❌ CRITICAL - Blocked players {blocked_found} found in squad_df! ❌❌❌")
            squad_df = squad_df[~squad_df['id'].isin(BLOCKED_PLAYER_IDS)].copy()
            logger.error(f"OptimizerV2: [get_current_squad] Force-removed from DataFrame. New size: {len(squad_df)}")
        
        if not squad_df.empty:
            final_ids = sorted(squad_df['id'].tolist())
            logger.info(f"OptimizerV2: [get_current_squad] ✓ SUCCESS - Squad with {len(squad_df)} players")
            logger.info(f"OptimizerV2: [get_current_squad] Final Player IDs: {final_ids}")
            logger.info(f"OptimizerV2: [get_current_squad] Verified: No blocked players in squad")
        else:
            logger.warning(f"OptimizerV2: [get_current_squad] Empty squad returned")
        
        return squad_df
    
    def create_pulp_model(self, current_squad: pd.DataFrame, available_players: pd.DataFrame, 
                         bank: float, free_transfers: int, num_transfers: int, 
                         forced_out_ids: List[int] = None, picks_data: Dict = None) -> Tuple[pulp.LpProblem, Dict]:
        """
        Create PuLP optimization model.
        
        CRITICAL: Blocked players are NEVER included in the model variables.
        """
        logger.info(f"OptimizerV2: [create_pulp_model] Creating model for {num_transfers} transfers")
        
        # CRITICAL: Remove blocked players from current_squad BEFORE creating variables
        original_squad_size = len(current_squad)
        current_squad = current_squad[~current_squad['id'].isin(BLOCKED_PLAYER_IDS)].copy()
        if len(current_squad) < original_squad_size:
            logger.error(f"OptimizerV2: [create_pulp_model] Removed {original_squad_size - len(current_squad)} blocked players from current_squad!")
        
        # CRITICAL: Remove blocked players from available_players
        original_avail_size = len(available_players)
        available_players = available_players[~available_players['id'].isin(BLOCKED_PLAYER_IDS)].copy()
        if len(available_players) < original_avail_size:
            logger.warning(f"OptimizerV2: [create_pulp_model] Removed {original_avail_size - len(available_players)} blocked players from available_players")
        
        # Verify no blocked players
        current_squad_ids = set(current_squad['id'].tolist())
        available_player_ids = set(available_players['id'].tolist())
        
        blocked_in_squad = current_squad_ids.intersection(BLOCKED_PLAYER_IDS)
        blocked_in_avail = available_player_ids.intersection(BLOCKED_PLAYER_IDS)
        
        if blocked_in_squad or blocked_in_avail:
            logger.error(f"OptimizerV2: [create_pulp_model] CRITICAL - Blocked players found after filtering!")
            logger.error(f"OptimizerV2: [create_pulp_model] In squad: {blocked_in_squad}, In available: {blocked_in_avail}")
            raise ValueError(f"Blocked players found in DataFrames: squad={blocked_in_squad}, available={blocked_in_avail}")
        
        logger.info(f"OptimizerV2: [create_pulp_model] Squad size: {len(current_squad)}, Available: {len(available_players)}")
        logger.info(f"OptimizerV2: [create_pulp_model] Squad IDs: {sorted(current_squad_ids)}")
        
        # Create optimization problem
        prob = pulp.LpProblem("FPL_Transfer_Optimization", pulp.LpMaximize)
        
        # Variables - ONLY for non-blocked players
        final_squad_vars = {}
        transfer_out_vars = {}
        transfer_in_vars = {}
        
        # Create variables for current squad (already filtered)
        for pid in current_squad_ids:
            if pid in BLOCKED_PLAYER_IDS:
                logger.error(f"OptimizerV2: [create_pulp_model] CRITICAL - Attempted to create variable for blocked player {pid}!")
                continue
            final_squad_vars[pid] = pulp.LpVariable(f"in_squad_{pid}", cat='Binary')
            transfer_out_vars[pid] = pulp.LpVariable(f"trans_out_{pid}", cat='Binary')
        
        # Create variables for available players (already filtered)
        for pid in available_player_ids:
            if pid in BLOCKED_PLAYER_IDS:
                logger.error(f"OptimizerV2: [create_pulp_model] CRITICAL - Attempted to create variable for blocked player {pid}!")
                continue
            final_squad_vars[pid] = pulp.LpVariable(f"in_squad_{pid}", cat='Binary')
            transfer_in_vars[pid] = pulp.LpVariable(f"trans_in_{pid}", cat='Binary')
        
        logger.info(f"OptimizerV2: [create_pulp_model] Created {len(transfer_out_vars)} transfer_out vars, {len(transfer_in_vars)} transfer_in vars")
        
        # Constraints: Relationship between final squad and transfers
        for pid in current_squad_ids:
            if pid in final_squad_vars and pid in transfer_out_vars:
                prob += final_squad_vars[pid] == 1 - transfer_out_vars[pid]
        
        for pid in available_player_ids:
            if pid in final_squad_vars and pid in transfer_in_vars:
                prob += final_squad_vars[pid] == transfer_in_vars[pid]
        
        # CRITICAL: Enforce forced transfers (but verify they're not blocked)
        if forced_out_ids:
            for fid in forced_out_ids:
                if fid in BLOCKED_PLAYER_IDS:
                    logger.error(f"OptimizerV2: [create_pulp_model] CRITICAL - Forced transfer ID {fid} is blocked!")
                    continue
                if fid in transfer_out_vars:
                    prob += transfer_out_vars[fid] == 1, f"Force_Out_{fid}"
        
        # Objective: Maximize EV
        penalty_hits = max(0, num_transfers - free_transfers)
        transfer_penalty = penalty_hits * abs(self.points_hit_per_transfer)
        normalization_scale = 100.0
        tiebreaker_weight = 0.5
        
        total_ev = 0
        proven_bonus = 0
        
        for _, p in current_squad.iterrows():
            ev = p.get('EV', 0)
            pid = p['id']
            if pid in final_squad_vars:
                total_ev += final_squad_vars[pid] * ev
                if 'total_points' in p:
                    normalized_points = min(p['total_points'] / normalization_scale, 1.0)
                    proven_bonus += final_squad_vars[pid] * normalized_points * tiebreaker_weight
        
        for _, p in available_players.iterrows():
            ev = p.get('EV', 0)
            pid = p['id']
            if pid in final_squad_vars:
                total_ev += final_squad_vars[pid] * ev
                if 'total_points' in p:
                    normalized_points = min(p['total_points'] / normalization_scale, 1.0)
                    proven_bonus += final_squad_vars[pid] * normalized_points * tiebreaker_weight
        
        prob += total_ev + proven_bonus - transfer_penalty
        
        # Standard constraints
        prob += pulp.lpSum(final_squad_vars.values()) == self.squad_size
        prob += pulp.lpSum(transfer_out_vars.values()) == num_transfers
        prob += pulp.lpSum(transfer_in_vars.values()) == num_transfers
        
        # Budget constraint
        # #region agent log
        import json
        log_data = {
            'location': 'optimizer_v2.py:create_pulp_model:budget_constraint',
            'message': 'Budget constraint calculation - BEFORE',
            'data': {
                'bank': float(bank),
                'num_transfers': num_transfers,
                'current_squad_ids': sorted(current_squad['id'].tolist()) if not current_squad.empty else [],
                'available_players_count': len(available_players)
            },
            'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'A'
        }
        try:
            import os
            # Use server-accessible path (Windows: C:\fpl-api\debug.log, Linux/Mac: workspace/.cursor/debug.log)
            if os.name == 'nt':  # Windows
                debug_log_path = r'C:\fpl-api\debug.log'
            else:
                debug_log_path = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        cost_ins = pulp.lpSum([
            transfer_in_vars[p['id']] * price_from_api(p['now_cost']) 
            for _, p in available_players.iterrows() 
            if p['id'] in transfer_in_vars
        ])
        # Use selling_price from picks data if available, otherwise use now_cost
        # FPL API provides selling_price in picks data which is what you actually get when selling
        picks_dict = {}
        if picks_data and 'picks' in picks_data:
            picks_dict = {p['element']: p for p in picks_data['picks']}
        
        # #region agent log
        # Log which price source is being used
        price_source_log = []
        for _, p in current_squad.iterrows():
            if p['id'] in transfer_out_vars:
                pid = p['id']
                pick_data = picks_dict.get(pid, {})
                has_selling_price = 'selling_price' in pick_data
                selling_price = pick_data.get('selling_price', None)
                market_price = p.get('now_cost', 0)
                price_source_log.append({
                    'id': int(pid),
                    'name': str(p.get('web_name', 'Unknown')),
                    'market_price': int(market_price),
                    'has_selling_price': has_selling_price,
                    'selling_price': int(selling_price) if selling_price is not None else None,
                    'price_difference': int(market_price) - int(selling_price) if selling_price is not None else 0
                })
        log_data = {
            'location': 'optimizer_v2.py:create_pulp_model:selling_price_check',
            'message': 'Checking selling_price availability for budget constraint',
            'data': {
                'price_source_log': price_source_log,
                'picks_data_available': picks_data is not None,
                'picks_count': len(picks_dict) if picks_dict else 0
            },
            'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'A'
        }
        try:
            import os
            # Use server-accessible path (Windows: C:\fpl-api\debug.log, Linux/Mac: workspace/.cursor/debug.log)
            if os.name == 'nt':  # Windows
                debug_log_path = r'C:\fpl-api\debug.log'
            else:
                debug_log_path = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        # Calculate value_out using selling_price if available, otherwise now_cost
        val_outs_terms = []
        for _, p in current_squad.iterrows():
            if p['id'] in transfer_out_vars:
                pid = p['id']
                pick_data = picks_dict.get(pid, {})
                # Use selling_price from picks if available, otherwise calculate conservative estimate
                if 'selling_price' in pick_data and pick_data['selling_price'] is not None:
                    selling_price = price_from_api(pick_data['selling_price'])
                    val_outs_terms.append(transfer_out_vars[pid] * selling_price)
                else:
                    # FPL selling price: More accurate estimate
                    # FPL rule: Selling price = purchase_price + (market_increase / 2) if price increased
                    # Since we don't have purchase_price, estimate based on typical price rises
                    # Most players in active squads have risen 0.1-0.3m, so selling price is typically 0.05-0.15m less
                    # Use 0.15m reduction per player as conservative estimate (accounts for typical rises + safety margin)
                    market_price = price_from_api(p['now_cost'])
                    # Reduce by 0.15m or 3%, whichever is larger
                    # This accounts for typical price increases where you only get half the profit
                    # Increased from 0.1m/2% to 0.15m/3% to account for actual FPL selling price calculations
                    reduction = max(0.15, market_price * 0.03)  # At least 0.15m or 3%, whichever is larger
                    conservative_selling_price = max(4.0, market_price - reduction)  # Minimum 4.0m
                    val_outs_terms.append(transfer_out_vars[pid] * conservative_selling_price)
                    
                    # Log the price difference for debugging
                    logger.info(f"OptimizerV2: [create_pulp_model] Player {p.get('web_name', pid)} - Market: £{market_price:.2f}m, Selling (est): £{conservative_selling_price:.2f}m, Reduction: £{reduction:.2f}m")
        
        val_outs = pulp.lpSum(val_outs_terms) if val_outs_terms else pulp.lpSum([0])
        
        # #region agent log
        # Log individual player prices for debugging
        player_prices_log = []
        for _, p in current_squad.iterrows():
            if p['id'] in transfer_out_vars:
                player_prices_log.append({
                    'id': int(p['id']),
                    'name': str(p.get('web_name', 'Unknown')),
                    'now_cost': int(p.get('now_cost', 0)),
                    'price_from_api': price_from_api(p.get('now_cost', 0)),
                    'has_selling_price': 'selling_price' in p
                })
        # Calculate val_outs value safely (pulp.value() returns None before solving)
        val_outs_value = None
        try:
            if hasattr(pulp, 'value'):
                val_outs_value = pulp.value(val_outs)
                if val_outs_value is not None:
                    val_outs_value = float(val_outs_value)
        except (TypeError, ValueError):
            val_outs_value = None
        
        log_data = {
            'location': 'optimizer_v2.py:create_pulp_model:budget_constraint',
            'message': 'Player selling prices in budget constraint',
            'data': {
                'players_out_prices': player_prices_log,
                'total_val_outs_calculated': val_outs_value if val_outs_value is not None else 'N/A (not solved yet)',
                'bank': float(bank),
                'available_budget': float(bank) + (val_outs_value if val_outs_value is not None else 0)
            },
            'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'A'
        }
        try:
            import os
            # Use server-accessible path (Windows: C:\fpl-api\debug.log, Linux/Mac: workspace/.cursor/debug.log)
            if os.name == 'nt':  # Windows
                debug_log_path = r'C:\fpl-api\debug.log'
            else:
                debug_log_path = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        prob += cost_ins <= float(bank) + val_outs
        
        # Position constraints
        for pos, count in self.position_requirements.items():
            current_pos = [
                final_squad_vars[p['id']] 
                for _, p in current_squad.iterrows() 
                if p['element_type'] == pos and p['id'] in final_squad_vars
            ]
            avail_pos = [
                final_squad_vars[p['id']] 
                for _, p in available_players.iterrows() 
                if p['element_type'] == pos and p['id'] in final_squad_vars
            ]
            prob += pulp.lpSum(current_pos + avail_pos) == count
        
        # Team constraints
        all_teams = set(current_squad['team']).union(set(available_players['team']))
        for t in all_teams:
            current_team = [
                final_squad_vars[p['id']] 
                for _, p in current_squad.iterrows() 
                if p['team'] == t and p['id'] in final_squad_vars
            ]
            avail_team = [
                final_squad_vars[p['id']] 
                for _, p in available_players.iterrows() 
                if p['team'] == t and p['id'] in final_squad_vars
            ]
            prob += pulp.lpSum(current_team + avail_team) <= self.max_players_per_team
        
        # POSITION MATCHING CONSTRAINT: For each position, transfers out = transfers in
        # This ensures apples-to-apples comparisons (MID->MID, DEF->DEF, etc.)
        for pos in self.position_requirements.keys():
            out_pos = [
                transfer_out_vars[p['id']]
                for _, p in current_squad.iterrows()
                if p['element_type'] == pos and p['id'] in transfer_out_vars
            ]
            in_pos = [
                transfer_in_vars[p['id']]
                for _, p in available_players.iterrows()
                if p['element_type'] == pos and p['id'] in transfer_in_vars
            ]
            prob += pulp.lpSum(out_pos) == pulp.lpSum(in_pos), f"Position_Match_{pos}"
        
        logger.info(f"OptimizerV2: [create_pulp_model] ✓ Model created successfully with position matching")
        
        return prob, {
            'transfer_out_vars': transfer_out_vars,
            'transfer_in_vars': transfer_in_vars,
            'player_vars': final_squad_vars
        }
    
    def solve_transfer_optimization(self, current_squad, available_players, bank, free_transfers, 
                                   num_transfers, forced_out_ids=None, picks_data=None):
        """
        Solve transfer optimization problem.
        
        CRITICAL: Verifies no blocked players in results.
        """
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Solving for {num_transfers} transfers")
        
        prob, variables = self.create_pulp_model(
            current_squad, available_players, bank, free_transfers, num_transfers, forced_out_ids, picks_data
        )
        
        prob.solve(self.pulp_solver)
        
        if prob.status != pulp.LpStatusOptimal:
            logger.warning(f"OptimizerV2: [solve_transfer_optimization] Solver status: {prob.status}")
            return {'status': 'infeasible', 'net_ev_gain_adjusted': -999}
        
        # Extract results with explicit blocked player checks
        players_out = []
        for pid, var in variables['transfer_out_vars'].items():
            if var.varValue > 0.5:
                # CRITICAL: Check if this is a blocked player
                if pid in BLOCKED_PLAYER_IDS:
                    logger.error(f"OptimizerV2: [solve_transfer_optimization] CRITICAL - Solver selected blocked player {pid}!")
                    logger.error(f"OptimizerV2: [solve_transfer_optimization] This should NEVER happen!")
                    raise ValueError(f"PuLP solver selected blocked player {pid}")
                
                # Verify player exists in current_squad
                player_in_squad = current_squad[current_squad['id'] == pid]
                if player_in_squad.empty:
                    logger.error(f"OptimizerV2: [solve_transfer_optimization] CRITICAL - Solver selected player {pid} not in current_squad!")
                    raise ValueError(f"PuLP solver selected invalid player {pid}")
                
                p = player_in_squad.iloc[0]
                players_out.append({
                    'name': p['web_name'],
                    'team': p['team_name'],
                    'id': int(p['id']),
                    'EV': float(p.get('EV', 0)),
                    'element_type': int(p.get('element_type', 0)),
                    'form': float(p.get('form', 0)),
                    'selected_by_percent': float(p.get('selected_by_percent', 0)),
                    'points_per_game': float(p.get('points_per_game', 0)),
                    'now_cost': int(p.get('now_cost', 0)),
                    'total_points': int(p.get('total_points', 0)),
                    'photo': p.get('photo', ''),
                    'fdr': float(p.get('fdr', 3.0)),
                })
                logger.info(f"OptimizerV2: [solve_transfer_optimization] Selected {p['web_name']} (ID: {pid}) for transfer out")
        
        players_in = []
        for pid, var in variables['transfer_in_vars'].items():
            if var.varValue > 0.5:
                # CRITICAL: Check if this is a blocked player
                if pid in BLOCKED_PLAYER_IDS:
                    logger.error(f"OptimizerV2: [solve_transfer_optimization] CRITICAL - Solver selected blocked player {pid}!")
                    raise ValueError(f"PuLP solver selected blocked player {pid}")
                
                p = available_players[available_players['id'] == pid].iloc[0]
                players_in.append({
                    'name': p['web_name'],
                    'team': p['team_name'],
                    'id': int(p['id']),
                    'EV': float(p.get('EV', 0)),
                    'element_type': int(p.get('element_type', 0)),
                    'form': float(p.get('form', 0)),
                    'selected_by_percent': float(p.get('selected_by_percent', 0)),
                    'points_per_game': float(p.get('points_per_game', 0)),
                    'now_cost': int(p.get('now_cost', 0)),
                    'total_points': int(p.get('total_points', 0)),
                    'photo': p.get('photo', ''),
                    'fdr': float(p.get('fdr', 3.0)),
                })
                logger.info(f"OptimizerV2: [solve_transfer_optimization] Selected {p['web_name']} (ID: {pid}) for transfer in")
        
        # FINAL VERIFICATION: Check results for blocked players
        out_ids = {p['id'] for p in players_out}
        in_ids = {p['id'] for p in players_in}
        blocked_in_out = out_ids.intersection(BLOCKED_PLAYER_IDS)
        blocked_in_in = in_ids.intersection(BLOCKED_PLAYER_IDS)
        
        if blocked_in_out or blocked_in_in:
            logger.error(f"OptimizerV2: [solve_transfer_optimization] CRITICAL - Blocked players in results!")
            logger.error(f"OptimizerV2: [solve_transfer_optimization] In players_out: {blocked_in_out}, In players_in: {blocked_in_in}")
            raise ValueError(f"Blocked players found in results: out={blocked_in_out}, in={blocked_in_in}")
        
        logger.info(f"OptimizerV2: [solve_transfer_optimization] ✓ Results verified clean")
        
        # ENFORCE POSITION MATCHING: Sort by position and pair them
        # Group by position
        out_by_pos = {}
        in_by_pos = {}
        for p in players_out:
            pos = p.get('element_type', 0)
            if pos not in out_by_pos:
                out_by_pos[pos] = []
            out_by_pos[pos].append(p)
        for p in players_in:
            pos = p.get('element_type', 0)
            if pos not in in_by_pos:
                in_by_pos[pos] = []
            in_by_pos[pos].append(p)
        
        # Rebuild lists sorted by position, matching positions
        matched_out = []
        matched_in = []
        
        # First, handle positions that exist in both
        common_positions = set(out_by_pos.keys()) & set(in_by_pos.keys())
        for pos in sorted(common_positions):
            out_list = out_by_pos[pos]
            in_list = in_by_pos[pos]
            # Match them up (take minimum count)
            match_count = min(len(out_list), len(in_list))
            matched_out.extend(out_list[:match_count])
            matched_in.extend(in_list[:match_count])
        
        # If there are unmatched positions, log warning but still include them
        unmatched_out_pos = set(out_by_pos.keys()) - common_positions
        unmatched_in_pos = set(in_by_pos.keys()) - common_positions
        if unmatched_out_pos or unmatched_in_pos:
            logger.warning(f"OptimizerV2: [solve_transfer_optimization] Position mismatch detected!")
            logger.warning(f"OptimizerV2: [solve_transfer_optimization] Unmatched OUT positions: {unmatched_out_pos}")
            logger.warning(f"OptimizerV2: [solve_transfer_optimization] Unmatched IN positions: {unmatched_in_pos}")
            # Add unmatched players at the end (they won't be position-matched)
            for pos in sorted(unmatched_out_pos):
                matched_out.extend(out_by_pos[pos])
            for pos in sorted(unmatched_in_pos):
                matched_in.extend(in_by_pos[pos])
        
        players_out = matched_out
        players_in = matched_in
        
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Players OUT: {[p['name'] + '(' + str(p['id']) + ')' for p in players_out]}")
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Players IN: {[p['name'] + '(' + str(p['id']) + ')' for p in players_in]}")
        
        # CRITICAL: Validate budget constraint using fresh prices
        from .utils import price_from_api
        # #region agent log
        import json
        players_in_prices = [{'id': p.get('id'), 'name': p.get('name', 'Unknown'), 'now_cost': p.get('now_cost', 0), 'price': price_from_api(p.get('now_cost', 0))} for p in players_in]
        players_out_prices = [{'id': p.get('id'), 'name': p.get('name', 'Unknown'), 'now_cost': p.get('now_cost', 0), 'price': price_from_api(p.get('now_cost', 0)), 'has_selling_price': 'selling_price' in p} for p in players_out]
        log_data = {
            'location': 'optimizer_v2.py:solve_transfer_optimization:budget_validation',
            'message': 'Budget validation - BEFORE calculation',
            'data': {
                'bank': float(bank),
                'players_in': players_in_prices,
                'players_out': players_out_prices,
                'num_transfers': len(players_in)
            },
            'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'A'
        }
        try:
            import os
            # Use server-accessible path (Windows: C:\fpl-api\debug.log, Linux/Mac: workspace/.cursor/debug.log)
            if os.name == 'nt':  # Windows
                debug_log_path = r'C:\fpl-api\debug.log'
            else:
                debug_log_path = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        total_cost_in = sum(price_from_api(p['now_cost']) for p in players_in)
        
        # Calculate total_value_out using selling_price calculation
        # FPL selling price: Conservative estimate (95% of market price) since we don't have purchase_price
        picks_dict = {}
        if picks_data and 'picks' in picks_data:
            picks_dict = {p['element']: p for p in picks_data['picks']}
        
        total_value_out = 0.0
        for p in players_out:
            pid = p.get('id')
            pick_data = picks_dict.get(pid, {})
            market_price = price_from_api(p.get('now_cost', 0))
            
            if 'selling_price' in pick_data and pick_data['selling_price'] is not None:
                total_value_out += price_from_api(pick_data['selling_price'])
            else:
                # More accurate estimate: Reduce by 0.15m or 3%, whichever is larger
                # FPL rule: Selling price = purchase_price + (market_increase / 2)
                # Most players in active squads have risen 0.1-0.3m, so selling price is typically 0.05-0.15m less
                # Use 0.15m reduction per player as conservative estimate (increased from 0.1m to account for actual FPL calculations)
                reduction = max(0.15, market_price * 0.03)  # At least 0.15m or 3%, whichever is larger
                conservative_selling_price = max(4.0, market_price - reduction)  # Minimum 4.0m
                total_value_out += conservative_selling_price
                logger.info(f"OptimizerV2: [solve_transfer_optimization] Budget validation - Player {p.get('name', pid)} - Market: £{market_price:.2f}m, Selling (est): £{conservative_selling_price:.2f}m, Reduction: £{reduction:.2f}m")
        
        available_budget = float(bank) + total_value_out
        
        # #region agent log
        log_data = {
            'location': 'optimizer_v2.py:solve_transfer_optimization:budget_validation',
            'message': 'Budget validation - AFTER calculation',
            'data': {
                'total_cost_in': float(total_cost_in),
                'total_value_out': float(total_value_out),
                'bank': float(bank),
                'available_budget': float(available_budget),
                'budget_deficit': float(total_cost_in) - float(available_budget),
                'is_feasible': total_cost_in <= available_budget + 0.01
            },
            'timestamp': int(pd.Timestamp.now().timestamp() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'A'
        }
        try:
            import os
            # Use server-accessible path (Windows: C:\fpl-api\debug.log, Linux/Mac: workspace/.cursor/debug.log)
            if os.name == 'nt':  # Windows
                debug_log_path = r'C:\fpl-api\debug.log'
            else:
                debug_log_path = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        if total_cost_in > available_budget + 0.01:  # Allow 0.01 tolerance for floating point
            logger.error(f"OptimizerV2: [solve_transfer_optimization] BUDGET CONSTRAINT VIOLATION!")
            logger.error(f"OptimizerV2: [solve_transfer_optimization] Cost IN: {total_cost_in:.2f}, Available: {available_budget:.2f}, Bank: {bank:.2f}, Value OUT: {total_value_out:.2f}")
            logger.error(f"OptimizerV2: [solve_transfer_optimization] This indicates prices may have changed. Returning infeasible.")
            return {'status': 'infeasible', 'net_ev_gain_adjusted': -999, 'error': 'Budget constraint violation - prices may have changed'}
        
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Budget validation passed: Cost IN: {total_cost_in:.2f}, Available: {available_budget:.2f}")
        
        # Calculate net EV gain
        current_ev = current_squad['EV'].sum()
        final_ev = pulp.value(prob.objective) + (max(0, num_transfers - free_transfers) * abs(self.points_hit_per_transfer))
        net_gain = final_ev - current_ev
        
        return {
            'status': 'optimal',
            'num_transfers': num_transfers,
            'players_out': players_out,
            'players_in': players_in,
            'net_ev_gain': net_gain,
            'net_ev_gain_adjusted': net_gain - (max(0, num_transfers - free_transfers) * abs(self.points_hit_per_transfer)),
            'total_cost_in': total_cost_in,
            'total_value_out': total_value_out,
            'available_budget': available_budget
        }
    
    def generate_smart_recommendations(self, current_squad, available_players, bank, free_transfers, max_transfers: int = 4, picks_data: Dict = None):
        """
        Generate comprehensive transfer recommendations.
        
        CRITICAL: Final filter to remove any blocked players from recommendations.
        """
        logger.info(f"OptimizerV2: [generate_smart_recommendations] Starting with squad size: {len(current_squad)}")
        
        # CRITICAL: Final check - remove blocked players from current_squad
        original_size = len(current_squad)
        current_squad = current_squad[~current_squad['id'].isin(BLOCKED_PLAYER_IDS)].copy()
        if len(current_squad) < original_size:
            logger.error(f"OptimizerV2: [generate_smart_recommendations] Removed {original_size - len(current_squad)} blocked players from current_squad!")
        
        if current_squad.empty:
            logger.error("OptimizerV2: [generate_smart_recommendations] Current squad is empty after filtering!")
            return {
                'recommendations': [],
                'num_forced_transfers': 0,
                'forced_players': [],
                'error': 'Empty squad'
            }
        
        logger.info(f"OptimizerV2: [generate_smart_recommendations] Squad size: {len(current_squad)}, IDs: {sorted(current_squad['id'].tolist())}")
        
        # Identify forced transfers
        forced_mask = pd.Series(False, index=current_squad.index)
        forced_mask = forced_mask | current_squad['status'].isin(['i', 's', 'u'])
        
        if 'chance_of_playing_this_round' in current_squad.columns:
            chance = pd.to_numeric(current_squad['chance_of_playing_this_round'], errors='coerce').fillna(100)
        else:
            chance = pd.Series([100] * len(current_squad), index=current_squad.index)
        
        forced_mask = forced_mask | (chance == 0)
        forced_mask = forced_mask | ((current_squad['status'] == 'd') & (chance < 50))
        forced_mask = forced_mask | (current_squad.get('EV', pd.Series([999]*len(current_squad))) <= 0.1)
        
        forced_out = current_squad[forced_mask].copy()
        forced_ids = [pid for pid in forced_out['id'].tolist() if pid not in BLOCKED_PLAYER_IDS]  # Filter blocked players
        num_forced = len(forced_ids)
        
        recommendations = []
        
        # Generate scenarios
        if num_forced > 0:
            try:
                sol = self.solve_transfer_optimization(
                    current_squad, available_players, bank, free_transfers, num_forced, forced_out_ids=forced_ids, picks_data=picks_data
                )
                if sol.get('status') == 'optimal':
                    penalty_hits = max(0, num_forced-free_transfers)
                    hit_reason = None
                    if penalty_hits > 0:
                        hit_reason = f"Taking a -{penalty_hits * 4} point hit to fix {num_forced} injured/unavailable player(s). The expected value gain ({sol.get('net_ev_gain', 0):.2f} points) outweighs the penalty cost."
                    sol.update({
                        'strategy': 'FIX_FORCED',
                        'description': f'Fix {num_forced} injured player(s)',
                        'priority': 'HIGH',
                        'penalty_hits': penalty_hits,
                        'transfer_penalty': max(0, num_forced-free_transfers)*4,
                        'original_net_gain': sol['net_ev_gain'],
                        'hit_reason': hit_reason
                    })
                    recommendations.append(sol)
            except ValueError as e:
                logger.error(f"OptimizerV2: [generate_smart_recommendations] Forced transfer optimization failed: {e}")
        
        # Optional scenarios
        for tx in range(1, min(max_transfers + 1, 5)):
            if num_forced > 0 and tx == num_forced:
                continue
            try:
                sol = self.solve_transfer_optimization(
                    current_squad, available_players, bank, free_transfers, tx, picks_data=picks_data
                )
                if sol.get('status') == 'optimal' and sol.get('net_ev_gain_adjusted', -999) >= 0.1:
                    penalty_hits = max(0, tx-free_transfers)
                    hit_reason = None
                    if penalty_hits > 0:
                        net_gain = sol.get('net_ev_gain', 0)
                        hit_reason = f"Taking a -{penalty_hits * 4} point hit for {tx} transfer(s). The expected value gain ({net_gain:.2f} points) exceeds the penalty cost ({penalty_hits * 4} points), resulting in a net gain of {sol.get('net_ev_gain_adjusted', 0):.2f} points."
                    sol.update({
                        'strategy': 'OPTIMIZE',
                        'description': f'Optimize squad ({tx} transfer{"s" if tx > 1 else ""})',
                        'priority': 'LOW',
                        'penalty_hits': penalty_hits,
                        'transfer_penalty': max(0, tx-free_transfers)*4,
                        'original_net_gain': sol['net_ev_gain'],
                        'hit_reason': hit_reason
                    })
                    recommendations.append(sol)
            except ValueError as e:
                logger.error(f"OptimizerV2: [generate_smart_recommendations] Optimization for {tx} transfers failed: {e}")
                continue
        
        # Sort by net EV gain
        recommendations.sort(key=lambda x: x['net_ev_gain_adjusted'], reverse=True)
        
        # FINAL CRITICAL CHECK: Remove any recommendations with blocked players AND enforce position matching
        clean_recommendations = []
        for rec in recommendations:
            players_out_ids = {p.get('id') for p in rec.get('players_out', [])}
            players_in_ids = {p.get('id') for p in rec.get('players_in', [])}
            blocked_in_rec = players_out_ids.intersection(BLOCKED_PLAYER_IDS) | players_in_ids.intersection(BLOCKED_PLAYER_IDS)
            
            if blocked_in_rec:
                logger.error(f"OptimizerV2: [generate_smart_recommendations] CRITICAL - Recommendation contains blocked players {blocked_in_rec}!")
                logger.error(f"OptimizerV2: [generate_smart_recommendations] Removing this recommendation")
                continue
            
            # ENSURE POSITION MATCHING: Sort by position to ensure proper pairing
            # The PuLP constraint should already enforce this, but we sort here for display
            players_out = rec.get('players_out', [])
            players_in = rec.get('players_in', [])
            
            # Sort both lists by position to ensure proper pairing
            players_out_sorted = sorted(players_out, key=lambda p: (p.get('element_type', 0), p.get('id', 0)))
            players_in_sorted = sorted(players_in, key=lambda p: (p.get('element_type', 0), p.get('id', 0)))
            
            rec['players_out'] = players_out_sorted
            rec['players_in'] = players_in_sorted
            logger.info(f"OptimizerV2: [generate_smart_recommendations] ✓ Position-sorted recommendation")
            
            clean_recommendations.append(rec)
        
        logger.info(f"OptimizerV2: [generate_smart_recommendations] Returning {len(clean_recommendations)} clean recommendations")
        
        return {
            'recommendations': clean_recommendations,
            'num_forced_transfers': num_forced,
            'forced_players': forced_out.to_dict('records')
        }

