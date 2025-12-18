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
        If blocked players are found, they are removed immediately.
        
        Returns:
            pd.DataFrame: Squad DataFrame with blocked players removed
        """
        logger.info(f"OptimizerV2: [get_current_squad] Entry {entry_id}, Gameweek {gameweek}")
        
        # Clear cache to ensure fresh data
        api_client.clear_cache()
        
        # Fetch picks for the specified gameweek
        picks_data = api_client.get_entry_picks(entry_id, gameweek, use_cache=False)
        
        if not picks_data or 'picks' not in picks_data:
            logger.warning(f"OptimizerV2: [get_current_squad] No picks data for entry {entry_id}, gameweek {gameweek}")
            return pd.DataFrame()
        
        # Extract player IDs from picks
        player_ids = [p['element'] for p in picks_data['picks']]
        logger.info(f"OptimizerV2: [get_current_squad] Raw picks - Player IDs: {sorted(player_ids)}")
        
        # CRITICAL: Remove blocked players immediately
        original_count = len(player_ids)
        player_ids = [pid for pid in player_ids if pid not in BLOCKED_PLAYER_IDS]
        removed_count = original_count - len(player_ids)
        
        if removed_count > 0:
            logger.error(f"OptimizerV2: [get_current_squad] CRITICAL - Removed {removed_count} blocked players from picks!")
            logger.error(f"OptimizerV2: [get_current_squad] Original IDs: {sorted([p['element'] for p in picks_data['picks']])}")
            logger.error(f"OptimizerV2: [get_current_squad] Filtered IDs: {sorted(player_ids)}")
        
        # Create squad DataFrame
        if not player_ids:
            logger.warning(f"OptimizerV2: [get_current_squad] No valid players after filtering")
            return pd.DataFrame()
        
        squad_df = players_df[players_df['id'].isin(player_ids)].copy()
        
        # FINAL VERIFICATION: Ensure no blocked players in DataFrame
        squad_ids = set(squad_df['id'].tolist()) if not squad_df.empty else set()
        blocked_found = squad_ids.intersection(BLOCKED_PLAYER_IDS)
        
        if blocked_found:
            logger.error(f"OptimizerV2: [get_current_squad] CRITICAL - Blocked players {blocked_found} found in squad_df!")
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
                         forced_out_ids: List[int] = None) -> Tuple[pulp.LpProblem, Dict]:
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
        cost_ins = pulp.lpSum([
            transfer_in_vars[p['id']] * price_from_api(p['now_cost']) 
            for _, p in available_players.iterrows() 
            if p['id'] in transfer_in_vars
        ])
        val_outs = pulp.lpSum([
            transfer_out_vars[p['id']] * price_from_api(p['now_cost']) 
            for _, p in current_squad.iterrows() 
            if p['id'] in transfer_out_vars
        ])
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
        
        logger.info(f"OptimizerV2: [create_pulp_model] ✓ Model created successfully")
        
        return prob, {
            'transfer_out_vars': transfer_out_vars,
            'transfer_in_vars': transfer_in_vars,
            'player_vars': final_squad_vars
        }
    
    def solve_transfer_optimization(self, current_squad, available_players, bank, free_transfers, 
                                   num_transfers, forced_out_ids=None):
        """
        Solve transfer optimization problem.
        
        CRITICAL: Verifies no blocked players in results.
        """
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Solving for {num_transfers} transfers")
        
        prob, variables = self.create_pulp_model(
            current_squad, available_players, bank, free_transfers, num_transfers, forced_out_ids
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
                    'id': p['id'],
                    'EV': p.get('EV', 0)
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
                    'id': p['id'],
                    'EV': p.get('EV', 0)
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
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Players OUT: {[p['name'] + '(' + str(p['id']) + ')' for p in players_out]}")
        logger.info(f"OptimizerV2: [solve_transfer_optimization] Players IN: {[p['name'] + '(' + str(p['id']) + ')' for p in players_in]}")
        
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
            'net_ev_gain_adjusted': net_gain - (max(0, num_transfers - free_transfers) * abs(self.points_hit_per_transfer))
        }
    
    def generate_smart_recommendations(self, current_squad, available_players, bank, free_transfers, max_transfers: int = 4):
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
                    current_squad, available_players, bank, free_transfers, num_forced, forced_out_ids=forced_ids
                )
                if sol.get('status') == 'optimal':
                    sol.update({
                        'strategy': 'FIX_FORCED',
                        'description': f'Fix {num_forced} injured player(s)',
                        'priority': 'HIGH',
                        'penalty_hits': max(0, num_forced-free_transfers),
                        'transfer_penalty': max(0, num_forced-free_transfers)*4,
                        'original_net_gain': sol['net_ev_gain']
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
                    current_squad, available_players, bank, free_transfers, tx
                )
                if sol.get('status') == 'optimal' and sol.get('net_ev_gain_adjusted', -999) >= 0.1:
                    sol.update({
                        'strategy': 'OPTIMIZE',
                        'description': f'Optimize squad ({tx} transfer{"s" if tx > 1 else ""})',
                        'priority': 'LOW',
                        'penalty_hits': max(0, tx-free_transfers),
                        'transfer_penalty': max(0, tx-free_transfers)*4,
                        'original_net_gain': sol['net_ev_gain']
                    })
                    recommendations.append(sol)
            except ValueError as e:
                logger.error(f"OptimizerV2: [generate_smart_recommendations] Optimization for {tx} transfers failed: {e}")
                continue
        
        # Sort by net EV gain
        recommendations.sort(key=lambda x: x['net_ev_gain_adjusted'], reverse=True)
        
        # FINAL CRITICAL CHECK: Remove any recommendations with blocked players
        clean_recommendations = []
        for rec in recommendations:
            players_out_ids = {p.get('id') for p in rec.get('players_out', [])}
            players_in_ids = {p.get('id') for p in rec.get('players_in', [])}
            blocked_in_rec = players_out_ids.intersection(BLOCKED_PLAYER_IDS) | players_in_ids.intersection(BLOCKED_PLAYER_IDS)
            
            if blocked_in_rec:
                logger.error(f"OptimizerV2: [generate_smart_recommendations] CRITICAL - Recommendation contains blocked players {blocked_in_rec}!")
                logger.error(f"OptimizerV2: [generate_smart_recommendations] Removing this recommendation")
                continue
            
            clean_recommendations.append(rec)
        
        logger.info(f"OptimizerV2: [generate_smart_recommendations] Returning {len(clean_recommendations)} clean recommendations")
        
        return {
            'recommendations': clean_recommendations,
            'num_forced_transfers': num_forced,
            'forced_players': forced_out.to_dict('records')
        }

