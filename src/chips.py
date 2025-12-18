"""
Chip evaluation and recommendation engine.
"""
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ChipEvaluator:
    """Evaluator for FPL chips."""
    
    def __init__(self, config: Dict):
        """
        Initialize chip evaluator.
        """
        self.config = config.get('chips', {})
        self.bb_threshold = self.config.get('min_ev_delta', 10.0)
        self.tc_threshold = self.config.get('min_ev_delta', 10.0) # Can be different
        self.fh_threshold = self.config.get('min_ev_delta_freehit', 10.0)
    
    def evaluate_bench_boost(self, squad: pd.DataFrame) -> Dict:
        """
        Evaluate Bench Boost chip.
        """
        # A simple heuristic for starting XI is to pick the top EV players
        # respecting formation rules, but for simplicity, we'll take top 11 EV.
        squad_sorted = squad.sort_values('EV', ascending=False)
        starting_xi = squad_sorted.head(11)
        bench = squad_sorted.tail(4)
        
        bench_ev = bench['EV'].sum()
        recommend = bench_ev >= self.bb_threshold
        
        return {
            'chip': 'bench_boost',
            'ev_gain': bench_ev,
            'recommend': recommend,
            'reason': f"Bench EV is {bench_ev:.2f}, {'above' if recommend else 'below'} threshold of {self.bb_threshold}"
        }

    def evaluate_triple_captain(self, squad: pd.DataFrame, all_players: pd.DataFrame, transfer_recommendations: List[Dict] = None, gameweek: int = None) -> Dict:
        """
        Evaluate Triple Captain chip.
        Considers both current squad and potential transfer-ins.
        Uses smart captaincy selection: prefers elite players and forwards when EV is similar.
        Elite thresholds are dynamic based on gameweek to maintain selectivity as season progresses.
        """
        # Calculate dynamic elite thresholds based on gameweek
        # Thresholds scale with season progress to maintain selectivity
        if gameweek is None:
            # Fallback: use percentile-based thresholds
            elite_threshold = all_players['total_points'].quantile(0.90)  # Top 10%
            very_elite_threshold = all_players['total_points'].quantile(0.95)  # Top 5%
        else:
            # Dynamic thresholds: scale with gameweek (GW1-38)
            # Elite: ~5 pts/GW (top performers)
            # Very elite: ~7 pts/GW (exceptional performers)
            elite_threshold = max(50, gameweek * 5)  # Minimum 50, scales with GW
            very_elite_threshold = max(70, gameweek * 7)  # Minimum 70, scales with GW
        
        # Collect all potential captain candidates
        candidates = []
        
        # Add current squad players
        for _, player in squad.iterrows():
            total_pts = player.get('total_points', 0)
            # Handle NaN values
            if pd.isna(total_pts):
                total_pts = 0
            candidates.append({
                'player': player,
                'source': 'current squad',
                'ev': player.get('EV', 0),
                'total_points': total_pts,
                'is_forward': player.get('element_type', 0) == 4,
                'is_elite': total_pts >= elite_threshold,
                'is_very_elite': total_pts >= very_elite_threshold
            })
        
        # Add transfer-in players
        if transfer_recommendations and len(transfer_recommendations) > 0:
            best_transfer = transfer_recommendations[0]
            for player_in_info in best_transfer.get('players_in', []):
                # Find the player in all_players (use ID if available for precise matching)
                if 'id' in player_in_info:
                    player_in = all_players[all_players['id'] == player_in_info['id']]
                else:
                    # Fallback to name + team matching
                    player_in = all_players[
                        (all_players['web_name'] == player_in_info['name']) &
                        (all_players['team_name'] == player_in_info.get('team', ''))
                    ]
                
                if not player_in.empty:
                    player_in = player_in.iloc[0]
                    total_pts = player_in.get('total_points', 0)
                    # Handle NaN values
                    if pd.isna(total_pts):
                        total_pts = 0
                    candidates.append({
                        'player': player_in,
                        'source': f"transfer-in ({player_in_info['name']})",
                        'ev': player_in.get('EV', 0),
                        'total_points': total_pts,
                        'is_forward': player_in.get('element_type', 0) == 4,
                        'is_elite': total_pts >= elite_threshold,
                        'is_very_elite': total_pts >= very_elite_threshold
                    })
        
        if not candidates:
            return {
                'chip': 'triple_captain',
                'ev_gain': 0,
                'recommend': False,
                'reason': "No suitable captain found"
            }
        
        # Smart captaincy selection: prioritize elite players and forwards when EV is similar
        # Score = EV + bonus for elite status + bonus for forward position
        # Elite forwards get the highest priority (best captaincy options)
        for candidate in candidates:
            score = candidate['ev']
            # Elite players get +2 bonus (proven reliability)
            # Very elite players get additional +1 bonus
            if candidate['is_elite']:
                score += 2.0
                if candidate['is_very_elite']:
                    score += 1.0  # Extra bonus for very elite players
            # Forwards get +1.5 bonus (better captaincy option historically)
            # Elite forwards are the best captaincy options
            if candidate['is_forward']:
                score += 1.5
            candidate['captain_score'] = score
        
        # Select best captain by score
        best_candidate = max(candidates, key=lambda x: x['captain_score'])
        best_captain = best_candidate['player']
        best_captain_source = best_candidate['source']
        
        # TC bonus is captain's base points (1x multiplier)
        tc_gain = best_captain['EV']
        recommend = tc_gain >= self.tc_threshold
        
        return {
            'chip': 'triple_captain',
            'ev_gain': tc_gain,
            'captain': best_captain['web_name'],
            'captain_team': best_captain.get('team_name', 'Unknown'),
            'captain_source': best_captain_source,
            'captain_ev': tc_gain,
            'recommend': recommend,
            'reason': f"Best captain: {best_captain['web_name']} ({best_captain_source}) with EV {tc_gain:.2f}, {'above' if recommend else 'below'} threshold of {self.tc_threshold}"
        }

    def build_free_hit_squad(self, all_players: pd.DataFrame, budget: float) -> pd.DataFrame:
        """
        Build optimal Free Hit squad using greedy algorithm.
        
        Returns: DataFrame with 15 players (11 starters + 4 bench)
        """
        from .utils import price_from_api
        
        # Filter available players (exclude injured/unavailable)
        available = all_players[
            (all_players['status'] == 'a') | (all_players['status'] == 'd')  # Available or doubtful
        ].copy()
        
        # Calculate price in millions
        available['price'] = available['now_cost'].apply(price_from_api)
        
        # Position requirements: 2 GKP, 5 DEF, 5 MID, 3 FWD
        position_requirements = {1: 2, 2: 5, 3: 5, 4: 3}  # GKP, DEF, MID, FWD
        
        selected = []
        team_counts = {}
        position_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        total_cost = 0.0
        
        # Sort by EV/price ratio for value
        available['value_ratio'] = available['EV'] / available['price']
        
        # Select players by position, prioritizing high EV/price ratio
        for pos, required in position_requirements.items():
            pos_players = available[available['element_type'] == pos].copy()
            pos_players = pos_players.sort_values(['EV', 'value_ratio'], ascending=[False, False])
            
            for _, player in pos_players.iterrows():
                if position_counts[pos] >= required:
                    break
                
                player_team = player['team']
                player_price = player['price']
                
                # Check team constraint (max 3 per team)
                if team_counts.get(player_team, 0) >= 3:
                    continue
                
                # Check budget
                if total_cost + player_price > budget:
                    continue
                
                # Add player
                selected.append(player)
                position_counts[pos] += 1
                team_counts[player_team] = team_counts.get(player_team, 0) + 1
                total_cost += player_price
        
        if len(selected) < 15:
            logger.warning(f"Could only select {len(selected)} players for Free Hit squad (need 15)")
            # Fill remaining slots with cheapest available players
            remaining_needed = 15 - len(selected)
            for pos, required in position_requirements.items():
                if position_counts[pos] < required:
                    needed = required - position_counts[pos]
                    selected_ids = [p['id'] for p in selected] if selected else []
                    pos_players = available[
                        (available['element_type'] == pos) & 
                        (~available['id'].isin(selected_ids))
                    ].copy()
                    pos_players = pos_players.sort_values('price')
                    
                    for _, player in pos_players.iterrows():
                        if needed <= 0:
                            break
                        if len(selected) >= 15:
                            break
                        
                        player_team = player['team']
                        player_price = player['price']
                        
                        if team_counts.get(player_team, 0) >= 3:
                            continue
                        if total_cost + player_price > budget:
                            continue
                        
                        selected.append(player)
                        position_counts[pos] += 1
                        team_counts[player_team] = team_counts.get(player_team, 0) + 1
                        total_cost += player_price
                        needed -= 1
        
        squad_df = pd.DataFrame(selected)
        
        # Select starting XI (top 11 by EV, respecting formation: min 1 GKP, 3 DEF, 3 MID, 1 FWD)
        if len(squad_df) >= 11:
            squad_sorted = squad_df.sort_values('EV', ascending=False).copy()
            
            # Ensure minimum formation requirements
            starting_xi_ids = []
            gkp_selected = 0
            def_selected = 0
            mid_selected = 0
            fwd_selected = 0
            
            # First pass: ensure minimums
            for _, player in squad_sorted.iterrows():
                pos = player['element_type']
                if len(starting_xi_ids) >= 11:
                    break
                
                if pos == 1 and gkp_selected < 1:  # Need at least 1 GKP
                    starting_xi_ids.append(player['id'])
                    gkp_selected += 1
                elif pos == 2 and def_selected < 3:  # Need at least 3 DEF
                    starting_xi_ids.append(player['id'])
                    def_selected += 1
                elif pos == 3 and mid_selected < 3:  # Need at least 3 MID
                    starting_xi_ids.append(player['id'])
                    mid_selected += 1
                elif pos == 4 and fwd_selected < 1:  # Need at least 1 FWD
                    starting_xi_ids.append(player['id'])
                    fwd_selected += 1
            
            # Second pass: fill remaining slots with best players
            for _, player in squad_sorted.iterrows():
                if len(starting_xi_ids) >= 11:
                    break
                if player['id'] in starting_xi_ids:
                    continue
                starting_xi_ids.append(player['id'])
            
            squad_df['in_starting_xi'] = squad_df['id'].isin(starting_xi_ids)
        else:
            squad_df['in_starting_xi'] = False
        
        return squad_df
    
    def evaluate_free_hit(self, current_squad: pd.DataFrame, all_players: pd.DataFrame, bank: float) -> Dict:
        """
        Evaluate Free Hit chip and build optimal squad.
        """
        from .utils import price_from_api
        
        # Calculate total budget (current squad value + bank)
        current_squad_value = current_squad['now_cost'].apply(price_from_api).sum()
        total_budget = current_squad_value + bank
        
        # Build optimal Free Hit squad
        fh_squad = self.build_free_hit_squad(all_players, total_budget)
        
        if fh_squad.empty or len(fh_squad) < 15:
            # Fallback if squad building failed
            fh_squad_ev = current_squad['EV'].sum()
            fh_gain = 0
        else:
            # Calculate EV gain
            current_ev = current_squad['EV'].sum()
            fh_squad_ev = fh_squad['EV'].sum()
            fh_gain = fh_squad_ev - current_ev
        
        recommend = fh_gain >= self.fh_threshold
        
        # Extract starting XI
        starting_xi = pd.DataFrame()
        if not fh_squad.empty and 'in_starting_xi' in fh_squad.columns:
            starting_xi = fh_squad[fh_squad['in_starting_xi'] == True].copy()
        
        result = {
            'chip': 'free_hit',
            'ev_gain': fh_gain,
            'recommend': recommend,
            'reason': f"Free Hit squad EV is {fh_squad_ev:.2f} vs current {current_squad['EV'].sum():.2f} (gain: {fh_gain:.2f}), {'above' if recommend else 'below'} threshold of {self.fh_threshold}",
            'optimal_squad': fh_squad,
            'starting_xi': starting_xi
        }
        
        return result

    def evaluate_wildcard(self, current_squad: pd.DataFrame, all_players: pd.DataFrame, bank: float) -> Dict:
        """
        Evaluate Wildcard chip and build optimal squad.
        Similar to Free Hit but for permanent squad changes.
        """
        from .utils import price_from_api
        
        # Calculate total budget (current squad value + bank)
        current_squad_value = current_squad['now_cost'].apply(price_from_api).sum()
        total_budget = current_squad_value + bank
        
        # Build optimal Wildcard squad (reuse Free Hit squad builder logic)
        wc_squad = self.build_free_hit_squad(all_players, total_budget)
        
        if wc_squad.empty or len(wc_squad) < 15:
            # Fallback if squad building failed
            wc_squad_ev = current_squad['EV'].sum()
            wc_gain = 0
        else:
            # Calculate EV gain
            current_ev = current_squad['EV'].sum()
            wc_squad_ev = wc_squad['EV'].sum()
            wc_gain = wc_squad_ev - current_ev
        
        # Wildcard threshold - typically higher than Free Hit since it's permanent
        wc_threshold = self.fh_threshold * 1.5  # 50% higher threshold
        recommend = wc_gain >= wc_threshold
        
        # Extract starting XI
        starting_xi = pd.DataFrame()
        if not wc_squad.empty and 'in_starting_xi' in wc_squad.columns:
            starting_xi = wc_squad[wc_squad['in_starting_xi'] == True].copy()
        
        result = {
            'chip': 'wildcard',
            'ev_gain': wc_gain,
            'recommend': recommend,
            'reason': f"Wildcard squad EV is {wc_squad_ev:.2f} vs current {current_squad['EV'].sum():.2f} (gain: {wc_gain:.2f}), {'above' if recommend else 'below'} threshold of {wc_threshold:.1f}",
            'optimal_squad': wc_squad,
            'starting_xi': starting_xi
        }
        
        return result

    def evaluate_all_chips(self, squad: pd.DataFrame, all_players: pd.DataFrame, gameweek: int, chips_available: List[str], bank: float, transfer_recommendations: List[Dict] = None) -> Dict:
        """
        Evaluate all available chips.
        """
        evaluations = {}
        
        if 'bboost' in chips_available:
            evaluations['bench_boost'] = self.evaluate_bench_boost(squad)
        
        if '3xc' in chips_available:
            evaluations['triple_captain'] = self.evaluate_triple_captain(squad, all_players, transfer_recommendations, gameweek=gameweek)
        
        if 'freehit' in chips_available:
            evaluations['free_hit'] = self.evaluate_free_hit(squad, all_players, bank)
        
        if 'wildcard' in chips_available:
            evaluations['wildcard'] = self.evaluate_wildcard(squad, all_players, bank)
            
        best_chip = None
        best_gain = 0
        for chip, result in evaluations.items():
            if result['recommend'] and result['ev_gain'] > best_gain:
                best_gain = result['ev_gain']
                best_chip = chip

        return {
            'evaluations': evaluations,
            'best_chip': best_chip
        }

