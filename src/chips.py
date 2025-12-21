"""
Chip Optimization V5.0 - Linear Programming Solver Approach
Replaces heuristic/greedy logic with proper LP optimization.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False
    logging.warning("PuLP not available. Install with: pip install pulp")

logger = logging.getLogger(__name__)


class SquadSolver:
    """
    Linear Programming solver for optimal squad selection.
    Replaces greedy build_free_hit_squad logic.
    """
    
    def __init__(self):
        """Initialize the solver."""
        if not PULP_AVAILABLE:
            raise ImportError("PuLP is required for SquadSolver. Install with: pip install pulp")
        self.solver = pulp.PULP_CBC_CMD(msg=False)
    
    def solve_optimal_squad(
        self, 
        candidates: pd.DataFrame, 
        budget: float, 
        type: str = 'free_hit'
    ) -> pd.DataFrame:
        """
        Solve optimal squad using Linear Programming.
        
        Objective: Maximize Sum(Player_EV)
        
        Constraints:
        - Total Price <= budget
        - GKP = 2, DEF = 5, MID = 5, FWD = 3
        - Max 3 players per team_code
        - Must select exactly 15 players
        
        Args:
            candidates: DataFrame with columns: id, EV, now_cost, element_type, team (or team_code), status
            budget: Total budget available
            type: Type of squad ('free_hit', 'wildcard', etc.)
        
        Returns:
            DataFrame with 15 optimal players
        """
        if candidates.empty:
            logger.warning("SquadSolver: No candidates provided")
            return pd.DataFrame()
        
        # Filter available players (exclude injured/unavailable)
        available = candidates[
            (candidates['status'] == 'a') | (candidates['status'] == 'd')
        ].copy()
        
        if available.empty:
            logger.warning("SquadSolver: No available players after filtering")
            return pd.DataFrame()
        
        # Import price conversion utility
        from .utils import price_from_api
        
        # Prepare data
        available['price'] = available['now_cost'].apply(price_from_api)
        available = available[available['price'] > 0].copy()  # Remove invalid prices
        
        if available.empty:
            logger.warning("SquadSolver: No players with valid prices")
            return pd.DataFrame()
        
        # Get team identifier (try team_code first, then team, then team_id)
        if 'team_code' in available.columns:
            team_col = 'team_code'
        elif 'team' in available.columns:
            team_col = 'team'
        elif 'team_id' in available.columns:
            team_col = 'team_id'
        else:
            logger.warning("SquadSolver: No team identifier column found, using dummy team")
            available['_dummy_team'] = 1
            team_col = '_dummy_team'
        
        # Create PuLP problem
        prob = pulp.LpProblem("Optimal_Squad_Selection", pulp.LpMaximize)
        
        # Decision variables: binary for each player
        player_vars = {}
        for idx, player in available.iterrows():
            pid = player['id']
            player_vars[pid] = pulp.LpVariable(f"player_{pid}", cat='Binary')
        
        # Objective: Maximize total EV
        # Handle None/NaN EV values safely
        prob += pulp.lpSum([
            player_vars[player['id']] * (float(player.get('EV', 0)) if player.get('EV') is not None and pd.notna(player.get('EV')) else 0.0)
            for _, player in available.iterrows()
        ])
        
        # Constraint 1: Exactly 15 players
        prob += pulp.lpSum(player_vars.values()) == 15, "Squad_Size"
        
        # Constraint 2: Budget constraint
        prob += pulp.lpSum([
            player_vars[player['id']] * float(player['price'])
            for _, player in available.iterrows()
        ]) <= budget, "Budget"
        
        # Constraint 3: Position requirements (2 GKP, 5 DEF, 5 MID, 3 FWD)
        position_requirements = {1: 2, 2: 5, 3: 5, 4: 3}
        
        for pos, required in position_requirements.items():
            pos_players = available[available['element_type'] == pos]
            if not pos_players.empty:
                prob += pulp.lpSum([
                    player_vars[player['id']]
                    for _, player in pos_players.iterrows()
                ]) == required, f"Position_{pos}_Count"
        
        # Constraint 4: Max 3 players per team
        teams = available[team_col].unique()
        for team in teams:
            team_players = available[available[team_col] == team]
            if not team_players.empty:
                prob += pulp.lpSum([
                    player_vars[player['id']]
                    for _, player in team_players.iterrows()
                ]) <= 3, f"Team_{team}_Limit"
        
        # Solve
        try:
            prob.solve(self.solver)
            
            if prob.status != pulp.LpStatusOptimal:
                logger.warning(f"SquadSolver: Solution not optimal. Status: {pulp.LpStatus[prob.status]}")
                return pd.DataFrame()
            
            # Extract selected players
            selected_ids = [
                pid for pid, var in player_vars.items()
                if pulp.value(var) == 1
            ]
            
            if len(selected_ids) != 15:
                logger.warning(f"SquadSolver: Selected {len(selected_ids)} players, expected 15")
                return pd.DataFrame()
            
            # Return selected players DataFrame
            selected_squad = available[available['id'].isin(selected_ids)].copy()
            
            # Select starting XI (top 11 by EV, respecting formation: min 1 GKP, 3 DEF, 3 MID, 1 FWD)
            selected_squad = selected_squad.sort_values('EV', ascending=False)
            
            starting_xi_ids = []
            gkp_selected = 0
            def_selected = 0
            mid_selected = 0
            fwd_selected = 0
            
            # First pass: ensure minimums
            for _, player in selected_squad.iterrows():
                pos = player['element_type']
                if len(starting_xi_ids) >= 11:
                    break
                
                if pos == 1 and gkp_selected < 1:
                    starting_xi_ids.append(player['id'])
                    gkp_selected += 1
                elif pos == 2 and def_selected < 3:
                    starting_xi_ids.append(player['id'])
                    def_selected += 1
                elif pos == 3 and mid_selected < 3:
                    starting_xi_ids.append(player['id'])
                    mid_selected += 1
                elif pos == 4 and fwd_selected < 1:
                    starting_xi_ids.append(player['id'])
                    fwd_selected += 1
            
            # Second pass: fill remaining slots
            for _, player in selected_squad.iterrows():
                if len(starting_xi_ids) >= 11:
                    break
                if player['id'] in starting_xi_ids:
                    continue
                starting_xi_ids.append(player['id'])
            
            selected_squad['in_starting_xi'] = selected_squad['id'].isin(starting_xi_ids)
            
            # Handle None/NaN EV values safely
            selected_squad = selected_squad.copy()
            selected_squad['EV'] = pd.to_numeric(selected_squad.get('EV', 0), errors='coerce').fillna(0)
            logger.info(f"SquadSolver: Successfully solved {type} squad with EV {float(selected_squad['EV'].sum()):.2f}")
            return selected_squad
            
        except Exception as e:
            logger.error(f"SquadSolver: Error solving squad: {e}", exc_info=True)
            return pd.DataFrame()


class ChipEvaluator:
    """Chip Optimization V5.0 - Evaluator for FPL chips using LP solver."""
    
    def __init__(self, config: Dict):
        """Initialize chip evaluator."""
        # #region agent log
        import json as json_log
        import platform as plat
        if plat.system() == 'Windows':
            DEBUG_LOG_PATH = r'C:\fpl-api\v2_debug.log'
        else:
            DEBUG_LOG_PATH = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
        try:
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.__init__:entry","message":"ChipEvaluator init started","data":{"config_keys": list(config.keys()) if config else []},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
        except: pass
        # #endregion
        
        try:
            self.config = config.get('chips', {}) if isinstance(config, dict) else {}
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.__init__:config_extracted","message":"Config extracted","data":{"chips_config_keys": list(self.config.keys()), "min_ev_delta": self.config.get('min_ev_delta', 'NOT_SET')},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
            except: pass
            # #endregion
            
            self.bb_threshold = self.config.get('min_ev_delta', 15.0)  # Updated to 15.0 for v5.0
            self.tc_threshold = 12.0  # v5.0: Only recommend TC if Player_EV > 12.0
            self.fh_threshold = self.config.get('min_ev_delta_freehit', 20.0)  # v5.0: Free Hits are precious, don't waste on small gains
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.__init__:thresholds_set","message":"Thresholds set","data":{"bb_threshold": self.bb_threshold, "tc_threshold": self.tc_threshold, "fh_threshold": self.fh_threshold},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
            except: pass
            # #endregion
            
            self.solver = SquadSolver() if PULP_AVAILABLE else None
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.__init__:solver_created","message":"Solver created","data":{"pulp_available": PULP_AVAILABLE},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
            except: pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.__init__:error","message":"Init failed","data":{"error": str(e), "error_type": type(e).__name__},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
            except: pass
            # #endregion
            raise
    
    def _detect_dgw(self, player: pd.Series, all_players: pd.DataFrame, gameweek: int) -> bool:
        """
        Detect if player has a Double Gameweek.
        
        Logic: Check if games_in_gameweek > 1 or if EV > 1.8 * average_single_game_EV
        """
        # Method 1: Check games_in_gameweek column if available
        if 'games_in_gameweek' in player.index:
            if player['games_in_gameweek'] > 1:
                return True
        
        # Method 2: Check if EV is significantly higher than average (indicates DGW)
        if 'EV' in player.index:
            ev_val = player.get('EV', 0)
            player_ev = float(ev_val) if ev_val is not None and pd.notna(ev_val) else 0.0
            if player_ev > 0:
                # Calculate average single game EV for similar players
                pos = player.get('element_type', 0)
                pos_players = all_players[all_players['element_type'] == pos]
                if not pos_players.empty and 'EV' in pos_players.columns:
                    avg_ev = pos_players['EV'].mean()
                    if player_ev > 1.8 * avg_ev:
                        return True
        
        return False
    
    def _is_bottom_tier_defense(self, player: pd.Series, fixtures: List[Dict] = None) -> bool:
        """
        Check if player is facing a bottom-tier defense.
        This is a simplified check - in practice, you'd check opponent's defensive stats.
        """
        # Simplified: Check FDR (Fixture Difficulty Rating)
        if 'fdr' in player.index or 'fdr_adjusted' in player.index:
            fdr_col = 'fdr_adjusted' if 'fdr_adjusted' in player.index else 'fdr'
            fdr = float(player.get(fdr_col, 3.0))
            # Bottom tier = FDR <= 2.0 (easy fixture)
            return fdr <= 2.0
        
        return False
    
    def evaluate_triple_captain(
        self, 
        squad: pd.DataFrame, 
        all_players: pd.DataFrame, 
        transfer_recommendations: List[Dict] = None, 
        gameweek: int = None,
        fixtures: List[Dict] = None
    ) -> Dict:
        """
        Triple Captain v5.0: Stop using arbitrary "Elite Thresholds".
        
        Logic:
        - Identify players with Double Gameweeks (DGW) or playing bottom-tier defense
        - Trigger: Only recommend TC if Player_EV > 12.0 AND (Player is DGW OR Player is playing bottom-tier defense)
        """
        # Collect all potential captain candidates
        candidates = []
        
        # Add current squad players
        for _, player in squad.iterrows():
            ev = float(player.get('EV', 0))
            is_dgw = self._detect_dgw(player, all_players, gameweek)
            is_bottom_tier = self._is_bottom_tier_defense(player, fixtures)
            
            candidates.append({
                'player': player,
                'source': 'current squad',
                'ev': ev,
                'is_dgw': is_dgw,
                'is_bottom_tier': is_bottom_tier,
                'eligible': ev > self.tc_threshold and (is_dgw or is_bottom_tier)
            })
        
        # Add transfer-in players
        if transfer_recommendations and len(transfer_recommendations) > 0:
            best_transfer = transfer_recommendations[0]
            for player_in_info in best_transfer.get('players_in', []):
                # Find the player in all_players
                if 'id' in player_in_info:
                    player_in = all_players[all_players['id'] == player_in_info['id']]
                else:
                    player_in = all_players[
                        (all_players['web_name'] == player_in_info['name']) &
                        (all_players['team_name'] == player_in_info.get('team', ''))
                    ]
                
                if not player_in.empty:
                    player_in = player_in.iloc[0]
                    ev_val = player_in.get('EV', 0)
                    ev = float(ev_val) if ev_val is not None and pd.notna(ev_val) else 0.0
                    is_dgw = self._detect_dgw(player_in, all_players, gameweek)
                    is_bottom_tier = self._is_bottom_tier_defense(player_in, fixtures)
                    
                    candidates.append({
                        'player': player_in,
                        'source': f"transfer-in ({player_in_info['name']})",
                        'ev': ev,
                        'is_dgw': is_dgw,
                        'is_bottom_tier': is_bottom_tier,
                        'eligible': ev > self.tc_threshold and (is_dgw or is_bottom_tier)
                    })
        
        if not candidates:
            return {
                'chip': 'triple_captain',
                'ev_gain': 0,
                'recommend': False,
                'reason': "No suitable captain found"
            }
        
        # Filter to eligible candidates only
        eligible_candidates = [c for c in candidates if c['eligible']]
        
        if not eligible_candidates:
            best_candidate = max(candidates, key=lambda x: x['ev'])
            return {
                'chip': 'triple_captain',
                'ev_gain': best_candidate['ev'],
                'recommend': False,
                'reason': f"Best captain: {best_candidate['player'].get('web_name', 'Unknown')} with EV {best_candidate['ev']:.2f}, but not eligible (needs EV > {self.tc_threshold} AND (DGW OR bottom-tier defense))"
            }
        
        # Select best eligible candidate
        best_candidate = max(eligible_candidates, key=lambda x: x['ev'])
        best_captain = best_candidate['player']
        
        # TC bonus is captain's base points (1x multiplier)
        tc_gain = best_candidate['ev']
        recommend = True  # All eligible candidates meet the threshold
        
        reason_parts = [f"Best captain: {best_captain.get('web_name', 'Unknown')} with EV {tc_gain:.2f}"]
        if best_candidate['is_dgw']:
            reason_parts.append("(Double Gameweek)")
        if best_candidate['is_bottom_tier']:
            reason_parts.append("(vs bottom-tier defense)")
        
        return {
            'chip': 'triple_captain',
            'ev_gain': tc_gain,
            'captain': best_captain.get('web_name', 'Unknown'),
            'captain_team': best_captain.get('team_name', 'Unknown'),
            'captain_source': best_candidate['source'],
            'captain_ev': tc_gain,
            'recommend': recommend,
            'reason': ". ".join(reason_parts)
        }
    
    def evaluate_bench_boost(self, squad: pd.DataFrame) -> Dict:
        """
        Bench Boost v5.0: Stop summing raw EV.
        
        Logic:
        - Filter for "Playing Bench" (players with minutes_expected > 60)
        - Trigger: Recommend if Bench_EV > 15.0 AND Bench_Minutes_Security == High
        """
        # #region agent log
        import json as json_log
        import platform as plat
        if plat.system() == 'Windows':
            DEBUG_LOG_PATH = r'C:\fpl-api\v2_debug.log'
        else:
            DEBUG_LOG_PATH = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
        try:
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_bench_boost:entry","message":"evaluate_bench_boost called","data":{"squad_size": len(squad), "has_EV": "EV" in squad.columns if not squad.empty else False},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
        except: pass
        # #endregion
        
        # Sort squad by EV to identify starting XI and bench
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_bench_boost:before_sort","message":"About to sort squad","data":{"squad_columns": list(squad.columns) if not squad.empty else []},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
        except: pass
        # #endregion
        
        try:
            squad_sorted = squad.sort_values('EV', ascending=False)
            starting_xi = squad_sorted.head(11)
            bench = squad_sorted.tail(4)
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_bench_boost:after_sort","message":"Squad sorted","data":{"starting_xi_size": len(starting_xi), "bench_size": len(bench)},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
            except: pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_bench_boost:sort_error","message":"Sort failed","data":{"error": str(e), "error_type": type(e).__name__},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
            except: pass
            # #endregion
            raise
        
        # Filter for "Playing Bench" (players with minutes_expected > 60)
        # If minutes_expected not available, use status or other indicators
        if 'minutes_expected' in bench.columns:
            playing_bench = bench[bench['minutes_expected'] > 60].copy()
        elif 'status' in bench.columns:
            # Assume 'a' (available) players will play
            playing_bench = bench[bench['status'] == 'a'].copy()
        else:
            # Fallback: use all bench players
            playing_bench = bench.copy()
        
        if playing_bench.empty:
            return {
                'chip': 'bench_boost',
                'ev_gain': 0,
                'recommend': False,
                'reason': "No playing bench players found (all bench players have low minutes expected)"
            }
        
        # Calculate Bench EV (only from playing bench)
        # Handle missing or None EV values
        playing_bench = playing_bench.copy()
        playing_bench['EV'] = pd.to_numeric(playing_bench.get('EV', 0), errors='coerce').fillna(0)
        bench_ev = float(playing_bench['EV'].sum())
        
        # Check minutes security (High = all playing bench have status 'a' and reasonable EV)
        minutes_security_high = True
        if 'status' in playing_bench.columns:
            # High security if all are available (not doubtful)
            minutes_security_high = (playing_bench['status'] == 'a').all()
        
        # Additional check: High security if all bench players have EV > 2.0 (likely to play)
        if minutes_security_high:
            minutes_security_high = (playing_bench['EV'] > 2.0).all()
        
        recommend = bench_ev >= self.bb_threshold and minutes_security_high
        
        reason = f"Bench EV is {bench_ev:.2f}, {'above' if bench_ev >= self.bb_threshold else 'below'} threshold of {self.bb_threshold:.1f}"
        reason += f". Minutes security: {'High' if minutes_security_high else 'Low'}"
        if not recommend:
            if bench_ev < self.bb_threshold:
                reason += f" - Bench EV below threshold"
            if not minutes_security_high:
                reason += f" - Minutes security too low"
        
        return {
            'chip': 'bench_boost',
            'ev_gain': bench_ev,
            'recommend': recommend,
            'reason': reason
        }
    
    def evaluate_free_hit(
        self, 
        current_squad: pd.DataFrame, 
        all_players: pd.DataFrame, 
        bank: float
    ) -> Dict:
        """
        Free Hit v5.0: Use SquadSolver to generate the perfect FH squad.
        
        Logic:
        - Use SquadSolver to generate optimal squad for this specific week
        - Compare Solver_Squad_EV vs Current_Squad_EV
        - Trigger: Recommend if Gain > 20.0 (Free Hits are precious)
        """
        if not self.solver:
            logger.warning("ChipEvaluator: PuLP not available, falling back to greedy algorithm")
            return self._evaluate_free_hit_fallback(current_squad, all_players, bank)
        
        from .utils import price_from_api
        
        # Calculate total budget (current squad value + bank)
        current_squad_value = current_squad['now_cost'].apply(price_from_api).sum()
        total_budget = current_squad_value + bank
        
        # Use SquadSolver to generate optimal Free Hit squad
        fh_squad = self.solver.solve_optimal_squad(all_players, total_budget, type='free_hit')
        
        if fh_squad.empty or len(fh_squad) < 15:
            logger.warning("ChipEvaluator: SquadSolver failed to generate Free Hit squad, using fallback")
            return self._evaluate_free_hit_fallback(current_squad, all_players, bank)
        
        # Calculate EV gain
        # Handle None/NaN EV values safely
        current_squad = current_squad.copy()
        current_squad['EV'] = pd.to_numeric(current_squad.get('EV', 0), errors='coerce').fillna(0)
        fh_squad = fh_squad.copy()
        fh_squad['EV'] = pd.to_numeric(fh_squad.get('EV', 0), errors='coerce').fillna(0)
        current_ev = float(current_squad['EV'].sum())
        fh_squad_ev = float(fh_squad['EV'].sum())
        fh_gain = fh_squad_ev - current_ev
        
        recommend = fh_gain >= self.fh_threshold
        
        # Extract starting XI
        starting_xi = pd.DataFrame()
        if 'in_starting_xi' in fh_squad.columns:
            starting_xi = fh_squad[fh_squad['in_starting_xi'] == True].copy()
        
        result = {
            'chip': 'free_hit',
            'ev_gain': fh_gain,
            'recommend': recommend,
            'reason': f"Free Hit squad EV is {fh_squad_ev:.2f} vs current {current_ev:.2f} (gain: {fh_gain:.2f}), {'above' if recommend else 'below'} threshold of {self.fh_threshold:.1f}",
            'optimal_squad': fh_squad,
            'starting_xi': starting_xi
        }
        
        return result
    
    def _evaluate_free_hit_fallback(
        self, 
        current_squad: pd.DataFrame, 
        all_players: pd.DataFrame, 
        bank: float
    ) -> Dict:
        """Fallback to old greedy algorithm if solver fails."""
        # Reuse old build_free_hit_squad logic as fallback
        from .utils import price_from_api
        
        current_squad_value = current_squad['now_cost'].apply(price_from_api).sum()
        total_budget = current_squad_value + bank
        
        # Simple greedy selection (old logic)
        available = all_players[
            (all_players['status'] == 'a') | (all_players['status'] == 'd')
        ].copy()
        available['price'] = available['now_cost'].apply(price_from_api)
        available = available.sort_values('EV', ascending=False)
        
        selected = []
        team_counts = {}
        position_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        total_cost = 0.0
        position_requirements = {1: 2, 2: 5, 3: 5, 4: 3}
        
        for _, player in available.iterrows():
            if len(selected) >= 15:
                break
            
            pos = player['element_type']
            team = player.get('team', player.get('team_code', player.get('team_id', 0)))
            
            if position_counts[pos] >= position_requirements[pos]:
                continue
            if team_counts.get(team, 0) >= 3:
                continue
            if total_cost + player['price'] > total_budget:
                continue
            
            selected.append(player)
            position_counts[pos] += 1
            team_counts[team] = team_counts.get(team, 0) + 1
            total_cost += player['price']
        
        if len(selected) < 15:
            # Handle None/NaN EV values safely
            current_squad = current_squad.copy()
            current_squad['EV'] = pd.to_numeric(current_squad.get('EV', 0), errors='coerce').fillna(0)
            fh_squad_ev = float(current_squad['EV'].sum())
            fh_gain = 0
        else:
            fh_squad = pd.DataFrame(selected)
            # Handle None/NaN EV values safely
            current_squad = current_squad.copy()
            current_squad['EV'] = pd.to_numeric(current_squad.get('EV', 0), errors='coerce').fillna(0)
            fh_squad = fh_squad.copy()
            fh_squad['EV'] = pd.to_numeric(fh_squad.get('EV', 0), errors='coerce').fillna(0)
            current_ev = float(current_squad['EV'].sum())
            fh_squad_ev = float(fh_squad['EV'].sum())
            fh_gain = fh_squad_ev - current_ev
        
        recommend = fh_gain >= self.fh_threshold
        
        # Ensure current_squad EV is calculated safely for display
        current_squad_display = current_squad.copy()
        current_squad_display['EV'] = pd.to_numeric(current_squad_display.get('EV', 0), errors='coerce').fillna(0)
        current_ev_display = float(current_squad_display['EV'].sum())
        
        return {
            'chip': 'free_hit',
            'ev_gain': fh_gain,
            'recommend': recommend,
            'reason': f"Free Hit squad EV is {fh_squad_ev:.2f} vs current {current_ev_display:.2f} (gain: {fh_gain:.2f}), {'above' if recommend else 'below'} threshold of {self.fh_threshold:.1f} (fallback algorithm)",
            'optimal_squad': pd.DataFrame(selected) if len(selected) >= 15 else pd.DataFrame(),
            'starting_xi': pd.DataFrame()
        }
    
    def evaluate_wildcard(
        self, 
        current_squad: pd.DataFrame, 
        all_players: pd.DataFrame, 
        bank: float,
        future_gameweeks_data: Optional[List[pd.DataFrame]] = None
    ) -> Dict:
        """
        Wildcard v5.0 - Multi-Horizon: Look at Total EV over next 5 Gameweeks.
        
        Logic:
        - If future data is available, optimize for 5-gameweek horizon
        - If future data unavailable, use SquadSolver but enforce Max 1 risky player
        - Risky player = players with yellow flags (status != 'a' or low minutes_expected)
        """
        if not self.solver:
            logger.warning("ChipEvaluator: PuLP not available, falling back to greedy algorithm")
            return self._evaluate_wildcard_fallback(current_squad, all_players, bank)
        
        from .utils import price_from_api
        
        current_squad_value = current_squad['now_cost'].apply(price_from_api).sum()
        total_budget = current_squad_value + bank
        
        # Multi-horizon optimization if future data available
        if future_gameweeks_data and len(future_gameweeks_data) > 0:
            # Calculate total EV over next 5 gameweeks (or available gameweeks)
            horizon_gws = min(5, len(future_gameweeks_data))
            
            # For each player, sum EV across horizon
            all_players_multi = all_players.copy()
            all_players_multi['total_ev_horizon'] = all_players_multi['EV']
            
            for gw_data in future_gameweeks_data[:horizon_gws]:
                # Merge future EV data
                if 'id' in gw_data.columns and 'EV' in gw_data.columns:
                    gw_ev = gw_data[['id', 'EV']].rename(columns={'EV': 'EV_gw'})
                    all_players_multi = all_players_multi.merge(
                        gw_ev, on='id', how='left', suffixes=('', '_gw')
                    )
                    all_players_multi['total_ev_horizon'] += all_players_multi['EV_gw'].fillna(0)
                    all_players_multi = all_players_multi.drop(columns=['EV_gw'])
            
            # Use total_ev_horizon as objective
            all_players_multi['EV'] = all_players_multi['total_ev_horizon']
            wc_squad = self.solver.solve_optimal_squad(all_players_multi, total_budget, type='wildcard')
        else:
            # Single gameweek optimization with risky player constraint
            # Identify risky players
            risky_players = all_players[
                (all_players['status'] != 'a') | 
                (all_players.get('minutes_expected', 0) < 60)
            ]['id'].tolist()
            
            # Use solver but add constraint for max 1 risky player
            # For now, we'll filter out risky players if there are too many
            # In a full implementation, this would be a constraint in the LP model
            wc_squad = self.solver.solve_optimal_squad(all_players, total_budget, type='wildcard')
            
            # Post-process: ensure max 1 risky player
            if not wc_squad.empty:
                risky_in_squad = wc_squad[wc_squad['id'].isin(risky_players)]
                if len(risky_in_squad) > 1:
                    # Remove all but the best risky player
                    risky_in_squad = risky_in_squad.sort_values('EV', ascending=False)
                    risky_to_remove = risky_in_squad.iloc[1:]['id'].tolist()
                    wc_squad = wc_squad[~wc_squad['id'].isin(risky_to_remove)]
                    logger.info(f"Wildcard: Removed {len(risky_to_remove)} risky players, keeping best one")
        
        if wc_squad.empty or len(wc_squad) < 15:
            logger.warning("ChipEvaluator: SquadSolver failed to generate Wildcard squad, using fallback")
            return self._evaluate_wildcard_fallback(current_squad, all_players, bank)
        
        # Calculate EV gain
        # Handle None/NaN EV values safely
        current_squad = current_squad.copy()
        current_squad['EV'] = pd.to_numeric(current_squad.get('EV', 0), errors='coerce').fillna(0)
        wc_squad = wc_squad.copy()
        wc_squad['EV'] = pd.to_numeric(wc_squad.get('EV', 0), errors='coerce').fillna(0)
        current_ev = float(current_squad['EV'].sum())
        wc_squad_ev = float(wc_squad['EV'].sum())
        wc_gain = wc_squad_ev - current_ev
        
        # Wildcard threshold - typically higher than Free Hit since it's permanent
        wc_threshold = self.fh_threshold * 1.5  # 50% higher threshold
        recommend = wc_gain >= wc_threshold
        
        # Extract starting XI
        starting_xi = pd.DataFrame()
        if 'in_starting_xi' in wc_squad.columns:
            starting_xi = wc_squad[wc_squad['in_starting_xi'] == True].copy()
        
        result = {
            'chip': 'wildcard',
            'ev_gain': wc_gain,
            'recommend': recommend,
            'reason': f"Wildcard squad EV is {wc_squad_ev:.2f} vs current {current_ev:.2f} (gain: {wc_gain:.2f}), {'above' if recommend else 'below'} threshold of {wc_threshold:.1f}",
            'optimal_squad': wc_squad,
            'starting_xi': starting_xi
        }
        
        return result
    
    def _evaluate_wildcard_fallback(
        self, 
        current_squad: pd.DataFrame, 
        all_players: pd.DataFrame, 
        bank: float
    ) -> Dict:
        """Fallback to old greedy algorithm if solver fails."""
        # Reuse Free Hit fallback logic
        fh_result = self._evaluate_free_hit_fallback(current_squad, all_players, bank)
        fh_result['chip'] = 'wildcard'
        wc_threshold = self.fh_threshold * 1.5
        fh_result['recommend'] = fh_result['ev_gain'] >= wc_threshold
        fh_result['reason'] = fh_result['reason'].replace('Free Hit', 'Wildcard').replace(str(self.fh_threshold), f"{wc_threshold:.1f}")
        return fh_result
    
    def evaluate_all_chips(
        self, 
        squad: pd.DataFrame, 
        all_players: pd.DataFrame, 
        gameweek: int, 
        chips_available: List[str], 
        bank: float, 
        transfer_recommendations: List[Dict] = None,
        fixtures: List[Dict] = None,
        future_gameweeks_data: Optional[List[pd.DataFrame]] = None
    ) -> Dict:
        """
        Evaluate all available chips (v5.0).
        
        Returns:
            Dict with 'evaluations' and 'best_chip' keys (same structure as before)
        """
        # #region agent log
        import json as json_log
        import platform as plat
        if plat.system() == 'Windows':
            DEBUG_LOG_PATH = r'C:\fpl-api\v2_debug.log'
        else:
            DEBUG_LOG_PATH = '/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
        try:
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_all_chips:entry","message":"evaluate_all_chips called","data":{"squad_size": len(squad), "chips_available": chips_available},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
        except: pass
        # #endregion
        
        evaluations = {}
        
        if 'bboost' in chips_available:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_all_chips:before_bb","message":"About to evaluate bench boost","data":{},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
            except: pass
            # #endregion
            try:
                evaluations['bench_boost'] = self.evaluate_bench_boost(squad)
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a') as f:
                        f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_all_chips:after_bb","message":"Bench boost evaluated","data":{"has_reason": "reason" in evaluations.get('bench_boost', {})},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
                except: pass
                # #endregion
            except Exception as e:
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a') as f:
                        f.write(json_log.dumps({"location":"chips.py:ChipEvaluator.evaluate_all_chips:bb_error","message":"Bench boost evaluation failed","data":{"error": str(e), "error_type": type(e).__name__},"timestamp":int(pd.Timestamp.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H3"}) + '\n')
                except: pass
                # #endregion
                raise
        
        if '3xc' in chips_available:
            evaluations['triple_captain'] = self.evaluate_triple_captain(
                squad, all_players, transfer_recommendations, gameweek=gameweek, fixtures=fixtures
            )
        
        if 'freehit' in chips_available:
            evaluations['free_hit'] = self.evaluate_free_hit(squad, all_players, bank)
        
        if 'wildcard' in chips_available:
            evaluations['wildcard'] = self.evaluate_wildcard(
                squad, all_players, bank, future_gameweeks_data=future_gameweeks_data
            )
        
        # Determine best chip
        best_chip = None
        best_gain = 0
        for chip, result in evaluations.items():
            if result['recommend'] and result['ev_gain'] > best_gain:
                best_gain = result['ev_gain']
                best_chip = chip
        
        # If no chip is recommended, return "No Chip"
        if best_chip is None:
            best_chip = "No Chip"
        
        return {
            'evaluations': evaluations,
            'best_chip': best_chip
        }
