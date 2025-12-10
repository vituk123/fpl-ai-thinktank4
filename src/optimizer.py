"""
Transfer optimizer with PuLP linear programming.
v3.3: Strict enforcement of forced transfers.
"""
import pandas as pd
import pulp
from typing import Dict, List, Tuple, Optional
import logging
from utils import price_from_api

logger = logging.getLogger(__name__)

class TransferOptimizer:
    def __init__(self, config: Dict):
        self.config = config.get('optimizer', {})
        self.pulp_solver = pulp.PULP_CBC_CMD(msg=False)
        self.points_hit_per_transfer = self.config.get('points_hit_per_transfer', -4)
        self.squad_size = 15
        self.position_requirements = {1: 2, 2: 5, 3: 5, 4: 3}
        self.max_players_per_team = 3
        self.free_transfers = 1
        
    def get_current_squad(self, entry_id: int, gameweek: int, api_client, players_df: pd.DataFrame) -> pd.DataFrame:
        last_played_gw = max(1, gameweek - 1)
        history = api_client.get_entry_history(entry_id)
        chips_used = history.get('chips', [])
        
        free_hit_active = False
        for chip in chips_used:
            if chip['event'] == last_played_gw and chip['name'] == 'freehit':
                free_hit_active = True
                break
        
        target_picks_gw = max(1, last_played_gw - 1) if free_hit_active else last_played_gw
        picks_data = api_client.get_entry_picks(entry_id, target_picks_gw)
        
        if not picks_data or 'picks' not in picks_data:
             return pd.DataFrame()

        player_ids = [p['element'] for p in picks_data['picks']]
        squad_df = players_df[players_df['id'].isin(player_ids)].copy()
        return squad_df
    
    def create_pulp_model(self,
                         current_squad: pd.DataFrame,
                         available_players: pd.DataFrame,
                         bank: float,
                         free_transfers: int,
                         num_transfers: int,
                         forced_out_ids: List[int] = None) -> Tuple[pulp.LpProblem, Dict]:
        
        prob = pulp.LpProblem("FPL_Transfer_Optimization", pulp.LpMaximize)
        
        final_squad_vars = {}
        transfer_out_vars = {}
        transfer_in_vars = {}
        
        current_squad_ids = set(current_squad['id'])
        available_player_ids = set(available_players['id'])
        all_player_ids = current_squad_ids.union(available_player_ids)
        
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
        for pid, var in variables['transfer_out_vars'].items():
            if var.varValue > 0.5:
                p = current_squad[current_squad['id'] == pid].iloc[0]
                players_out.append({'name': p['web_name'], 'team': p['team_name'], 'id': p['id'], 'EV': p.get('EV', 0)})
                
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
        Generate comprehensive transfer recommendations including all scenarios.
        
        Args:
            current_squad: Current squad DataFrame
            available_players: Available players DataFrame
            bank: Available budget
            free_transfers: Number of free transfers
            max_transfers: Maximum number of transfers to consider (default 4)
        
        Returns:
            Dictionary with recommendations, forced transfer info
        """
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
            if self._is_scenario_beneficial(sol, min_gain=0.5):
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
        
        return {'recommendations': recommendations, 'num_forced_transfers': num_forced, 'forced_players': forced_out.to_dict('records')}
