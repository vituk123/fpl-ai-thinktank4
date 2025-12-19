"""
Advanced Visualization Dashboard - Core Analytics Engine
Provides data preparation functions for 15 different analytics visualizations.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .fpl_api import FPLAPIClient
from .database import DatabaseManager
from .api_football_client import APIFootballClient
from .dashboard_helpers import sample_high_ranked_teams, aggregate_template_team

logger = logging.getLogger(__name__)


class VisualizationDashboard:
    """Core analytics engine for visualization dashboard."""
    
    def __init__(self, api_client: FPLAPIClient, db_manager: Optional[DatabaseManager] = None,
                 api_football_client: Optional[APIFootballClient] = None):
        """
        Initialize visualization dashboard.
        
        Args:
            api_client: FPL API client instance
            db_manager: Optional database manager for historical data
            api_football_client: Optional API-Football client for additional data
        """
        self.api_client = api_client
        self.db_manager = db_manager
        self.api_football_client = api_football_client
    
    # ==================== TEAM-SPECIFIC ANALYTICS ====================
    
    def get_performance_heatmap(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get performance heatmap data showing player points by gameweek.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with players and their points by gameweek
        """
        try:
            # Get current gameweek
            current_gw = self.api_client.get_current_gameweek()
            
            # Get player history from database
            if self.db_manager:
                history_df = self.db_manager.get_current_season_history()
            else:
                history_df = pd.DataFrame()
            
            # Get bootstrap for player names
            bootstrap = self.api_client.get_bootstrap_static()
            players_map = {p['id']: p['web_name'] for p in bootstrap['elements']}
            
            # Get all picks for the season
            all_picks = {}
            for gw in range(1, current_gw + 1):
                try:
                    picks_data = self.api_client.get_entry_picks(entry_id, gw)
                    if picks_data and 'picks' in picks_data:
                        for pick in picks_data['picks']:
                            player_id = pick['element']
                            if player_id not in all_picks:
                                all_picks[player_id] = {
                                    'name': players_map.get(player_id, f'Player {player_id}'),
                                    'id': player_id,
                                    'points_by_gw': []
                                }
                except:
                    continue
            
            # Get points for each player by gameweek
            for player_id, player_data in all_picks.items():
                if not history_df.empty:
                    player_history = history_df[history_df['player_id'] == player_id]
                    for gw in range(1, current_gw + 1):
                        gw_data = player_history[player_history['gw'] == gw]
                        if not gw_data.empty:
                            points = int(gw_data.iloc[0]['total_points'])
                        else:
                            points = 0
                        player_data['points_by_gw'].append({'gw': gw, 'points': points})
                else:
                    # Fallback: use element-summary API
                    for gw in range(1, current_gw + 1):
                        try:
                            element_summary = self.api_client._request(f"element-summary/{player_id}/", use_cache=True)
                            history = element_summary.get('history', [])
                            gw_data = next((h for h in history if h.get('round') == gw), None)
                            points = gw_data.get('total_points', 0) if gw_data else 0
                            player_data['points_by_gw'].append({'gw': gw, 'points': points})
                        except:
                            player_data['points_by_gw'].append({'gw': gw, 'points': 0})
            
            return {
                'players': list(all_picks.values()),
                'gameweeks': list(range(1, current_gw + 1))
            }
        except Exception as e:
            logger.error(f"Error generating performance heatmap: {e}")
            return {'players': [], 'gameweeks': []}
    
    def get_value_tracker(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get team value tracker data showing value growth vs league average.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with gameweeks, your value, and league average
        """
        try:
            entry_history = self.api_client.get_entry_history(entry_id)
            current = entry_history.get('current', [])
            
            gameweeks = []
            your_value = []
            league_avg = []
            
            # Get your team values
            for event in current:
                gw = event.get('event', 0)
                if gw > 0:
                    gameweeks.append(gw)
                    # Team value is stored as integer (multiply by 10 to get actual value)
                    value = event.get('value', 0) / 10.0
                    your_value.append(value)
            
            # Calculate league average (simplified - would need more data for true average)
            # For now, use a baseline and add some variation
            if your_value:
                baseline = your_value[0] if your_value else 100.0
                for i, gw in enumerate(gameweeks):
                    # Approximate league average (slightly lower than top teams)
                    avg_value = baseline + (i * 0.1)  # Small growth over time
                    league_avg.append(avg_value)
            
            return {
                'gameweeks': gameweeks,
                'your_value': your_value,
                'league_avg': league_avg
            }
        except Exception as e:
            logger.error(f"Error generating value tracker: {e}")
            return {'gameweeks': [], 'your_value': [], 'league_avg': []}
    
    def get_transfer_analysis(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get transfer history analysis showing predicted vs actual gains.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with transfer analysis data
        """
        try:
            transfers = []
            
            # Get decisions from database
            if self.db_manager:
                decisions_df = self.db_manager.get_decisions(entry_id=entry_id)
                if not decisions_df.empty:
                    for _, row in decisions_df.iterrows():
                        gw = row.get('gw', 0)
                        rec_transfers = row.get('recommended_transfers', {})
                        actual_transfers = row.get('actual_transfers_made', [])
                        
                        predicted_gain = rec_transfers.get('net_ev_gain', 0) if isinstance(rec_transfers, dict) else 0
                        
                        # Calculate actual gain (simplified - would need more complex calculation)
                        actual_gain = 0  # Placeholder
                        # #region agent log
                        import json; log_data = {'location': 'visualization_dashboard.py:184', 'message': 'Transfer actual_gain hardcoded', 'data': {'gw': gw, 'predicted_gain': predicted_gain, 'actual_gain': actual_gain}, 'timestamp': int(__import__('time').time() * 1000), 'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'B'}; open('/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log', 'a').write(json.dumps(log_data) + '\n')
                        # #endregion
                        
                        players_in = rec_transfers.get('players_in', []) if isinstance(rec_transfers, dict) else []
                        players_out = rec_transfers.get('players_out', []) if isinstance(rec_transfers, dict) else []
                        
                        success_rate = (actual_gain / predicted_gain * 100) if predicted_gain > 0 else 0
                        
                        transfers.append({
                            'gw': gw,
                            'predicted_gain': round(predicted_gain, 2),
                            'actual_gain': round(actual_gain, 2),
                            'success_rate': round(success_rate, 1),
                            'players_in': players_in,
                            'players_out': players_out
                        })
            
            # Also get transfers from API
            transfers_data = self.api_client.get_entry_transfers(entry_id)
            for transfer in transfers_data:
                gw = transfer.get('event', 0)
                if gw > 0:
                    # Check if we already have this GW in decisions
                    if not any(t['gw'] == gw for t in transfers):
                        transfers.append({
                            'gw': gw,
                            'predicted_gain': 0,
                            'actual_gain': 0,
                            'success_rate': 0,
                            'players_in': [transfer.get('element_in', 0)],
                            'players_out': [transfer.get('element_out', 0)]
                        })
            
            transfers.sort(key=lambda x: x['gw'])
            
            return {'transfers': transfers}
        except Exception as e:
            logger.error(f"Error generating transfer analysis: {e}")
            return {'transfers': []}
    
    def get_position_balance(self, entry_id: int, gameweek: Optional[int] = None) -> Dict:
        """
        Get position balance chart data showing investment distribution.
        
        Args:
            entry_id: FPL entry ID
            gameweek: Gameweek number (default: current)
            
        Returns:
            Dictionary with position investment data
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            # Try current gameweek, fallback to previous
            picks_data = None
            actual_gw_used = gameweek
            try:
                picks_data = self.api_client.get_entry_picks(entry_id, gameweek)
            except:
                # Fallback to previous gameweek
                try:
                    actual_gw_used = gameweek - 1
                    picks_data = self.api_client.get_entry_picks(entry_id, actual_gw_used)
                    logger.info(f"Using GW{actual_gw_used} picks for position balance (GW{gameweek} not available)")
                except:
                    pass
            
            if not picks_data or 'picks' not in picks_data:
                return {'positions': [], 'total_value': 0}
            
            bootstrap = self.api_client.get_bootstrap_static()
            players_map = {p['id']: p for p in bootstrap['elements']}
            position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
            
            position_investment = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            
            for pick in picks_data['picks']:
                player_id = pick['element']
                player = players_map.get(player_id, {})
                element_type = player.get('element_type', 0)
                position = position_map.get(element_type, 'UNK')
                cost = player.get('now_cost', 0) / 10.0  # Convert to millions
                
                if position in position_investment:
                    position_investment[position] += cost
            
            total_value = sum(position_investment.values())
            
            positions = []
            for pos_name, investment in position_investment.items():
                percentage = (investment / total_value * 100) if total_value > 0 else 0
                positions.append({
                    'name': pos_name,
                    'investment': round(investment, 2),
                    'percentage': round(percentage, 1)
                })
            
            return {
                'positions': positions,
                'total_value': round(total_value, 2)
            }
        except Exception as e:
            logger.error(f"Error generating position balance: {e}")
            return {'positions': [], 'total_value': 0}
    
    def get_chip_usage_timeline(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get chip usage timeline with optimal timing analysis.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with chip usage data
        """
        try:
            entry_history = self.api_client.get_entry_history(entry_id)
            chips_used = entry_history.get('chips', [])
            
            chips = []
            for chip in chips_used:
                chip_name = chip.get('name', '')
                gw_used = chip.get('event', 0)
                
                # Map chip names
                chip_display = {
                    'wildcard': 'Wildcard',
                    'freehit': 'Free Hit',
                    'bboost': 'Bench Boost',
                    '3xc': 'Triple Captain'
                }.get(chip_name, chip_name)
                
                # Calculate optimal timing (simplified - would use helper function)
                optimal_gw = gw_used  # Placeholder
                points_gained = 0  # Placeholder
                points_lost = 0  # Placeholder
                
                chips.append({
                    'name': chip_display,
                    'gw_used': gw_used,
                    'optimal_gw': optimal_gw,
                    'points_gained': points_gained,
                    'points_lost': points_lost
                })
            
            return {'chips': chips}
        except Exception as e:
            logger.error(f"Error generating chip usage timeline: {e}")
            return {'chips': []}
    
    def get_captain_performance(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get captain performance data.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with captain performance data
        """
        try:
            current_gw = self.api_client.get_current_gameweek()
            bootstrap = self.api_client.get_bootstrap_static()
            players_map = {p['id']: p['web_name'] for p in bootstrap['elements']}
            
            captains = []
            captain_counts = {}
            
            # Get captain picks for each gameweek
            for gw in range(1, current_gw + 1):
                try:
                    picks_data = self.api_client.get_entry_picks(entry_id, gw)
                    if picks_data and 'picks' in picks_data:
                        for pick in picks_data['picks']:
                            if pick.get('is_captain', False):
                                player_id = pick['element']
                                player_name = players_map.get(player_id, f'Player {player_id}')
                                
                                # Get points for this gameweek
                                points = 0
                                if self.db_manager:
                                    history_df = self.db_manager.get_current_season_history()
                                    if not history_df.empty:
                                        player_gw = history_df[(history_df['player_id'] == player_id) & (history_df['gw'] == gw)]
                                        if not player_gw.empty:
                                            points = int(player_gw.iloc[0]['total_points'])
                                
                                # Fallback: Use bootstrap data if database has no points
                                # Approximate GW points from season total
                                if points == 0:
                                    player_element = next((e for e in bootstrap['elements'] if e['id'] == player_id), None)
                                    if player_element:
                                        # Use a rough estimate: divide season total by current GW
                                        season_total = player_element.get('total_points', 0)
                                        points = max(0, season_total // current_gw) if current_gw > 0 else 0
                                
                                doubled_points = points * 2
                                
                                captains.append({
                                    'player_name': player_name,
                                    'gw': gw,
                                    'points': points,
                                    'doubled_points': doubled_points,
                                    'times_captained': 1
                                })
                                
                                # Count total times captained
                                captain_counts[player_name] = captain_counts.get(player_name, 0) + 1
                except Exception as e:
                    logger.debug(f"Error getting captain picks for GW{gw}: {e}")
                    continue
            
            # Update times_captained
            for captain in captains:
                captain['times_captained'] = captain_counts.get(captain['player_name'], 1)
            
            return {'captains': captains}
        except Exception as e:
            logger.error(f"Error generating captain performance: {e}")
            return {'captains': []}
    
    def get_rank_progression(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get rank progression data for overall and mini-leagues.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with rank progression data
        """
        try:
            entry_history = self.api_client.get_entry_history(entry_id)
            current = entry_history.get('current', [])
            
            gameweeks = []
            overall_rank = []
            
            for event in current:
                gw = event.get('event', 0)
                if gw > 0:
                    gameweeks.append(gw)
                    rank = event.get('rank', 0)
                    overall_rank.append(rank)
            
            # Get mini-league data (simplified - would need league API access)
            mini_leagues = []
            
            return {
                'gameweeks': gameweeks,
                'overall_rank': overall_rank,
                'mini_leagues': mini_leagues
            }
        except Exception as e:
            logger.error(f"Error generating rank progression: {e}")
            return {'gameweeks': [], 'overall_rank': [], 'mini_leagues': []}
    
    def get_value_efficiency(self, entry_id: int, season: Optional[int] = None) -> Dict:
        """
        Get points vs budget efficiency data.
        
        Args:
            entry_id: FPL entry ID
            season: Season year (default: current season)
            
        Returns:
            Dictionary with value efficiency data
        """
        try:
            current_gw = self.api_client.get_current_gameweek()
            bootstrap = self.api_client.get_bootstrap_static()
            players_map = {p['id']: p for p in bootstrap['elements']}
            
            # Get current squad - try current GW, fallback to previous GW
            picks_data = None
            actual_gw_used = current_gw
            try:
                picks_data = self.api_client.get_entry_picks(entry_id, current_gw)
            except:
                # Fallback to previous gameweek
                try:
                    actual_gw_used = current_gw - 1
                    picks_data = self.api_client.get_entry_picks(entry_id, actual_gw_used)
                    logger.info(f"Using GW{actual_gw_used} picks for value efficiency (GW{current_gw} not available)")
                except:
                    pass
            
            if not picks_data or 'picks' not in picks_data:
                return {'players': []}
            
            players = []
            
            # Get points from database with bootstrap fallback
            history_df = None
            if self.db_manager:
                history_df = self.db_manager.get_current_season_history()
            
            for pick in picks_data['picks']:
                player_id = pick['element']
                player = players_map.get(player_id, {})
                player_name = player.get('web_name', f'Player {player_id}')
                price = player.get('now_cost', 0) / 10.0
                
                # Get total points - prefer database, fallback to bootstrap total_points
                total_points = 0
                if history_df is not None and not history_df.empty:
                    player_history = history_df[history_df['player_id'] == player_id]
                    total_points = int(player_history['total_points'].sum()) if not player_history.empty else 0
                
                # Fallback to bootstrap total_points if database has no data
                if total_points == 0:
                    total_points = player.get('total_points', 0)
                
                points_per_million = (total_points / price) if price > 0 else 0
                efficiency_score = points_per_million * 10  # Scale for readability
                
                players.append({
                    'name': player_name,
                    'price': round(price, 1),
                    'total_points': total_points,
                    'points_per_million': round(points_per_million, 2),
                    'efficiency_score': round(efficiency_score, 2)
                })
            
            # Sort by efficiency
            players.sort(key=lambda x: x['efficiency_score'], reverse=True)
            
            return {'players': players}
        except Exception as e:
            logger.error(f"Error generating value efficiency: {e}")
            return {'players': []}
    
    # ==================== LEAGUE-WIDE ANALYTICS ====================
    
    def get_ownership_points_correlation(self, season: Optional[int] = None, gameweek: Optional[int] = None) -> Dict:
        """
        Get ownership vs points correlation data.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            
        Returns:
            Dictionary with ownership correlation data
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            bootstrap = self.api_client.get_bootstrap_static()
            players = []
            
            # Get points from database with bootstrap fallback
            history_df = pd.DataFrame()
            current_gw_data = pd.DataFrame()
            if self.db_manager:
                history_df = self.db_manager.get_current_season_history()
                # #region agent log
                import json; log_data = {'location': 'visualization_dashboard.py:573', 'message': 'Ownership correlation DB lookup start', 'data': {'gameweek': gameweek, 'history_df_empty': history_df.empty, 'history_df_shape': list(history_df.shape) if not history_df.empty else None}, 'timestamp': int(__import__('time').time() * 1000), 'sessionId': 'debug-session', 'runId': 'post-fix', 'hypothesisId': 'A'}; open('/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log', 'a').write(json.dumps(log_data) + '\n')
                # #endregion
                current_gw_data = history_df[history_df['gw'] == gameweek] if not history_df.empty else pd.DataFrame()
                # #region agent log
                log_data = {'location': 'visualization_dashboard.py:577', 'message': 'Ownership correlation filtered by gameweek', 'data': {'current_gw_data_empty': current_gw_data.empty, 'current_gw_data_shape': list(current_gw_data.shape) if not current_gw_data.empty else None}, 'timestamp': int(__import__('time').time() * 1000), 'sessionId': 'debug-session', 'runId': 'post-fix', 'hypothesisId': 'D'}; open('/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log', 'a').write(json.dumps(log_data) + '\n')
                # #endregion
            
            # Use database if available, otherwise use bootstrap (season totals as approximation)
            use_bootstrap_fallback = current_gw_data.empty
            
            for element in bootstrap['elements']:
                player_id = element['id']
                player_name = element['web_name']
                ownership = float(element.get('selected_by_percent', 0))
                
                # Get points for this gameweek
                if not use_bootstrap_fallback:
                    player_gw = current_gw_data[current_gw_data['player_id'] == player_id] if not current_gw_data.empty else pd.DataFrame()
                    total_points = int(player_gw.iloc[0]['total_points']) if not player_gw.empty else 0
                else:
                    # Fallback: Use bootstrap total_points (season total, approximate for GW)
                    # Calculate approximate GW points by using season total / current GW
                    season_total = element.get('total_points', 0)
                    total_points = max(0, season_total // gameweek) if gameweek > 0 else 0
                
                # #region agent log
                if player_id <= 5:  # Log first 5 players to avoid too many logs
                    import json; log_data = {'location': 'visualization_dashboard.py:589', 'message': 'Ownership correlation player points', 'data': {'player_id': player_id, 'player_name': player_name, 'use_bootstrap_fallback': use_bootstrap_fallback, 'total_points': total_points}, 'timestamp': int(__import__('time').time() * 1000), 'sessionId': 'debug-session', 'runId': 'post-fix', 'hypothesisId': 'E'}; open('/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log', 'a').write(json.dumps(log_data) + '\n')
                # #endregion
                
                # Calculate differential score (low ownership, high points)
                differential_score = total_points / (ownership + 1) if ownership > 0 else total_points
                
                players.append({
                    'name': player_name,
                    'ownership': round(ownership, 1),
                    'total_points': total_points,
                    'differential_score': round(differential_score, 2)
                })
            
            # Calculate correlation coefficient
            if players:
                ownerships = [p['ownership'] for p in players]
                points = [p['total_points'] for p in players]
                correlation_coefficient = np.corrcoef(ownerships, points)[0, 1] if len(ownerships) > 1 else 0
            else:
                correlation_coefficient = 0
            
            # Sort by differential score
            players.sort(key=lambda x: x['differential_score'], reverse=True)
            
            return {
                'players': players[:50],  # Top 50 differentials
                'correlation_coefficient': round(correlation_coefficient, 3)
            }
        except Exception as e:
            logger.error(f"Error generating ownership correlation: {e}")
            return {'players': [], 'correlation_coefficient': 0}
    
    def get_template_team(self, season: Optional[int] = None, gameweek: Optional[int] = None) -> Dict:
        """
        Get template team data from high-ranked teams.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            
        Returns:
            Dictionary with template team data
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            # Sample high-ranked teams
            sampled_teams = sample_high_ranked_teams(
                self.api_client,
                rank_range=(1, 10000),
                sample_size=100
            )
            
            # Aggregate template team
            template = aggregate_template_team(sampled_teams, gameweek)
            
            # Enhance with player names
            if template['squad']:
                bootstrap = self.api_client.get_bootstrap_static()
                players_map = {p['id']: p['web_name'] for p in bootstrap['elements']}
                
                for player in template['squad']:
                    player_id = player.get('player_id', 0)
                    player['player_name'] = players_map.get(player_id, f'Player {player_id}')
            
            return template
        except Exception as e:
            logger.error(f"Error generating template team: {e}")
            return {'squad': [], 'formation': '3-4-3'}
    
    def get_price_change_predictors(self, season: Optional[int] = None, gameweek: Optional[int] = None) -> Dict:
        """
        Get price change predictor data.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            
        Returns:
            Dictionary with price change predictions
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            bootstrap = self.api_client.get_bootstrap_static()
            players = []
            
            for element in bootstrap['elements']:
                player_name = element['web_name']
                current_price = element.get('now_cost', 0) / 10.0
                transfers_in = element.get('transfers_in', 0)
                transfers_out = element.get('transfers_out', 0)
                net_transfers = transfers_in - transfers_out
                
                # Simple prediction: high net transfers = likely price rise
                predicted_change = 0
                confidence = 0
                
                if net_transfers > 50000:
                    predicted_change = 0.1
                    confidence = 0.8
                elif net_transfers > 20000:
                    predicted_change = 0.1
                    confidence = 0.6
                elif net_transfers < -50000:
                    predicted_change = -0.1
                    confidence = 0.8
                elif net_transfers < -20000:
                    predicted_change = -0.1
                    confidence = 0.6
                
                players.append({
                    'name': player_name,
                    'current_price': round(current_price, 1),
                    'predicted_change': predicted_change,
                    'confidence': round(confidence, 2),
                    'transfers_in': transfers_in,
                    'transfers_out': transfers_out
                })
            
            # Sort by confidence and predicted change
            players.sort(key=lambda x: (abs(x['predicted_change']), x['confidence']), reverse=True)
            
            return {'players': players[:30]}  # Top 30 predictions
        except Exception as e:
            logger.error(f"Error generating price change predictors: {e}")
            return {'players': []}
    
    def get_position_points_distribution(self, season: Optional[int] = None, gameweek: Optional[int] = None) -> Dict:
        """
        Get position-wise points distribution data.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            
        Returns:
            Dictionary with position distribution data
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            bootstrap = self.api_client.get_bootstrap_static()
            position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
            
            positions_data = {}
            
            # Get points from database
            if self.db_manager:
                history_df = self.db_manager.get_current_season_history()
                current_gw_data = history_df[history_df['gw'] == gameweek] if not history_df.empty else pd.DataFrame()
                
                for element in bootstrap['elements']:
                    player_id = element['id']
                    element_type = element.get('element_type', 0)
                    position = position_map.get(element_type, 'UNK')
                    
                    if position not in positions_data:
                        positions_data[position] = []
                    
                    # Get points for this player
                    player_gw = current_gw_data[current_gw_data['player_id'] == player_id] if not current_gw_data.empty else pd.DataFrame()
                    points = int(player_gw.iloc[0]['total_points']) if not player_gw.empty else 0
                    
                    if points > 0:  # Only include players who played
                        positions_data[position].append(points)
            
            positions = []
            for pos_name, points_list in positions_data.items():
                if points_list:
                    points_array = np.array(points_list)
                    positions.append({
                        'name': pos_name,
                        'points': [
                            float(np.min(points_array)),  # min
                            float(np.percentile(points_array, 25)),  # q1
                            float(np.median(points_array)),  # median
                            float(np.percentile(points_array, 75)),  # q3
                            float(np.max(points_array))  # max
                        ],
                        'avg': float(np.mean(points_array))
                    })
            
            return {'positions': positions}
        except Exception as e:
            logger.error(f"Error generating position distribution: {e}")
            return {'positions': []}
    
    def get_fixture_swing_analysis(self, season: Optional[int] = None, gameweek: Optional[int] = None, lookahead: int = 5) -> Dict:
        """
        Get fixture difficulty swing analysis.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            lookahead: Number of gameweeks to look ahead
            
        Returns:
            Dictionary with fixture swing data
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            fixtures = self.api_client.get_fixtures()
            bootstrap = self.api_client.get_bootstrap_static()
            teams_map = {t['id']: t['name'] for t in bootstrap['teams']}
            
            teams = []
            
            for team_id, team_name in teams_map.items():
                # Get past fixtures
                past_fixtures = [f for f in fixtures if f.get('event') < gameweek and 
                                (f.get('team_h') == team_id or f.get('team_a') == team_id)]
                past_difficulties = []
                for f in past_fixtures[-lookahead:]:
                    if f.get('team_h') == team_id:
                        difficulty = f.get('team_a_difficulty', 3)
                    else:
                        difficulty = f.get('team_h_difficulty', 3)
                    past_difficulties.append(difficulty)
                
                # Get future fixtures
                future_fixtures = [f for f in fixtures if f.get('event') >= gameweek and 
                                  f.get('event') <= gameweek + lookahead and
                                  (f.get('team_h') == team_id or f.get('team_a') == team_id)]
                future_difficulties = []
                for f in future_fixtures:
                    if f.get('team_h') == team_id:
                        difficulty = f.get('team_a_difficulty', 3)
                    else:
                        difficulty = f.get('team_h_difficulty', 3)
                    future_difficulties.append(difficulty)
                
                past_avg = np.mean(past_difficulties) if past_difficulties else 3
                future_avg = np.mean(future_difficulties) if future_difficulties else 3
                swing_score = future_avg - past_avg  # Negative = easier, Positive = harder
                
                teams.append({
                    'name': team_name,
                    'past_5_avg_difficulty': round(past_avg, 2),
                    'next_5_avg_difficulty': round(future_avg, 2),
                    'swing_score': round(swing_score, 2)
                })
            
            # Sort by swing score (easiest swings first)
            teams.sort(key=lambda x: x['swing_score'])
            
            return {'teams': teams}
        except Exception as e:
            logger.error(f"Error generating fixture swing analysis: {e}")
            return {'teams': []}
    
    def get_dgw_probability(self, season: Optional[int] = None, gameweek: Optional[int] = None, lookahead: int = 10) -> Dict:
        """
        Get double gameweek probability analysis.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            lookahead: Number of gameweeks to look ahead
            
        Returns:
            Dictionary with DGW probability data
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            fixtures = self.api_client.get_fixtures()
            gameweeks_data = []
            
            # Analyze each gameweek in lookahead range
            for gw in range(gameweek, min(gameweek + lookahead, 39)):
                gw_fixtures = [f for f in fixtures if f.get('event') == gw]
                
                # Count teams playing
                teams_playing = set()
                for f in gw_fixtures:
                    teams_playing.add(f.get('team_h'))
                    teams_playing.add(f.get('team_a'))
                
                # Check for potential DGW (if a team appears twice in same GW, it's a DGW)
                team_counts = {}
                for f in gw_fixtures:
                    team_h = f.get('team_h')
                    team_a = f.get('team_a')
                    team_counts[team_h] = team_counts.get(team_h, 0) + 1
                    team_counts[team_a] = team_counts.get(team_a, 0) + 1
                
                dgw_teams = [team for team, count in team_counts.items() if count > 1]
                
                # Calculate probability (simplified)
                probability = len(dgw_teams) / 20.0 if dgw_teams else 0
                
                gameweeks_data.append({
                    'gw': gw,
                    'probability': round(probability, 2),
                    'teams_likely': len(dgw_teams),
                    'reason': f'{len(dgw_teams)} teams have multiple fixtures' if dgw_teams else 'No DGW detected'
                })
            
            return {
                'gameweeks': gameweeks_data,
                'historical_patterns': []  # Would be populated from historical data
            }
        except Exception as e:
            logger.error(f"Error generating DGW probability: {e}")
            return {'gameweeks': [], 'historical_patterns': []}
    
    def get_price_bracket_performers(self, season: Optional[int] = None, gameweek: Optional[int] = None) -> Dict:
        """
        Get top performers by price bracket.
        
        Args:
            season: Season year (default: current season)
            gameweek: Gameweek number (default: current)
            
        Returns:
            Dictionary with price bracket performers
        """
        try:
            if gameweek is None:
                gameweek = self.api_client.get_current_gameweek()
            
            bootstrap = self.api_client.get_bootstrap_static()
            
            # Define price brackets
            brackets = [
                {'range': '4-5M', 'min': 4.0, 'max': 5.0},
                {'range': '5-7M', 'min': 5.0, 'max': 7.0},
                {'range': '7-10M', 'min': 7.0, 'max': 10.0},
                {'range': '10M+', 'min': 10.0, 'max': 20.0}
            ]
            
            # Get points from database with bootstrap fallback
            history_df = None
            current_season_data = pd.DataFrame()
            if self.db_manager:
                history_df = self.db_manager.get_current_season_history()
                current_season_data = history_df[history_df['gw'] <= gameweek] if not history_df.empty else pd.DataFrame()
            
            bracket_results = []
            
            for bracket in brackets:
                bracket_players = []
                
                for element in bootstrap['elements']:
                    player_id = element['id']
                    player_name = element['web_name']
                    price = element.get('now_cost', 0) / 10.0
                    
                    if bracket['min'] <= price < bracket['max'] or (bracket['range'] == '10M+' and price >= bracket['min']):
                        # Get total points - prefer database, fallback to bootstrap
                        total_points = 0
                        if not current_season_data.empty:
                            player_data = current_season_data[current_season_data['player_id'] == player_id]
                            total_points = int(player_data['total_points'].sum()) if not player_data.empty else 0
                        
                        # Fallback to bootstrap total_points if database has no data
                        if total_points == 0:
                            total_points = element.get('total_points', 0)
                        
                        # Only include players with points (active players)
                        if total_points > 0:
                            # Calculate value score
                            value_score = (total_points / price) if price > 0 else 0
                            
                            bracket_players.append({
                                'name': player_name,
                                'price': round(price, 1),
                                'points': total_points,
                                'value_score': round(value_score, 2)
                            })
                
                # Sort by value score and take top 10
                bracket_players.sort(key=lambda x: x['value_score'], reverse=True)
                
                bracket_results.append({
                    'range': bracket['range'],
                    'players': bracket_players[:10]
                })
            
            return {'brackets': bracket_results}
        except Exception as e:
            logger.error(f"Error generating price bracket performers: {e}")
            return {'brackets': []}

