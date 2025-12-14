"""
Live Gameweek Tracker - Real-time tracking during live gameweeks.
Tracks live points, auto-substitutions, bonus points, rank projections, and alerts.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class LiveGameweekTracker:
    """
    Tracks live gameweek data and provides real-time updates.
    """
    
    def __init__(self, api_client, entry_id: int):
        """
        Initialize Live Gameweek Tracker.
        
        Args:
            api_client: FPL API client instance
            entry_id: User's FPL entry ID
        """
        self.api_client = api_client
        self.entry_id = entry_id
        self.last_update = None
        self.previous_points = {}
        self.previous_bps = {}
        logger.info(f"Live Gameweek Tracker initialized for entry {entry_id}")
    
    def get_live_points(self, gameweek: int, bootstrap: Dict = None, entry_history: Dict = None, picks_data: Dict = None) -> Dict:
        """
        Get live points for user's team.
        Uses bootstrap-static event_points for current gameweek data.
        
        Args:
            gameweek: Current gameweek number
        
        Returns:
            Dictionary with live points breakdown
        """
        try:
            # Use provided data or fetch if not provided (for backward compatibility)
            if bootstrap is None:
                bootstrap = self.api_client.get_bootstrap_static(use_cache=True)  # Enable cache
            elements = {e['id']: e for e in bootstrap['elements']}
            
            # Use provided picks_data or fetch if not provided
            if picks_data is None or 'picks' not in picks_data:
                try:
                    picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=gameweek, use_cache=True)
                except:
                    try:
                        picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=gameweek-1, use_cache=True)
                    except:
                        picks_data = None
            
            # If still no picks, try to get from entry info
            if not picks_data or 'picks' not in picks_data:
                # Fallback: use entry info to get current gameweek points
                if entry_history:
                    current_event = entry_history.get('current', [])
                else:
                    entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=True)
                    entry_history = self.api_client.get_entry_history(self.entry_id, use_cache=True)
                    current_event = entry_history.get('current', [])
                
                if current_event:
                    gw_data = next((e for e in current_event if e.get('event') == gameweek), None)
                    if gw_data:
                        total = gw_data.get('points', 0)
                        return {
                            'total': total,
                            'starting_xi': total,  # Approximate
                            'bench': 0,
                            'captain': 0,
                            'vice_captain': 0,
                            'bench_boost_active': False,
                            'live_elements': {}
                        }
                return {'total': 0, 'starting_xi': 0, 'bench': 0, 'captain': 0, 'vice_captain': 0, 'bench_boost_active': False}
            
            picks = picks_data['picks']
            
            # Check if Bench Boost chip is active for this gameweek
            if entry_history is None:
                entry_history = self.api_client.get_entry_history(self.entry_id, use_cache=True)
            chips_used = entry_history.get('chips', [])
            bench_boost_active = any(
                chip.get('event') == gameweek and chip.get('name') == 'bboost' 
                for chip in chips_used
            )
            
            total_points = 0
            starting_xi_points = 0
            bench_points = 0
            captain_points = 0
            vice_captain_points = 0
            
            # Get live element data from bootstrap (event_points field)
            live_elements = {}
            for pick in picks:
                player_id = pick['element']
                element = elements.get(player_id, {})
                
                # event_points contains current gameweek points
                points = element.get('event_points', 0)
                
                # Get additional stats from element (if available)
                live_elements[player_id] = {
                    'points': points,
                    'minutes': element.get('minutes', 0),
                    'bps': 0,  # BPS not in bootstrap, would need element-summary
                    'goals': element.get('goals_scored', 0),
                    'assists': element.get('assists', 0),
                    'xg': 0,  # Would need element-summary
                    'xa': 0   # Would need element-summary
                }
            
            # Calculate points
            for pick in picks:
                player_id = pick['element']
                position = pick['position']
                is_captain = pick.get('is_captain', False)
                is_vice = pick.get('is_vice_captain', False)
                
                player_data = live_elements.get(player_id, {})
                base_points = player_data.get('points', 0)
                
                # Apply captain multiplier
                if is_captain:
                    points = base_points * 2
                    captain_points = points
                elif is_vice:
                    points = base_points
                    vice_captain_points = points
                else:
                    points = base_points
                
                if position <= 11:  # Starting XI
                    starting_xi_points += points
                    total_points += points
                else:  # Bench
                    bench_points += base_points
                    # Include bench points in total only if Bench Boost is active
                    if bench_boost_active:
                        total_points += base_points
            
            return {
                'total': total_points,
                'starting_xi': starting_xi_points,
                'bench': bench_points,
                'captain': captain_points,
                'vice_captain': vice_captain_points,
                'bench_boost_active': bench_boost_active,
                'live_elements': live_elements
            }
        except Exception as e:
            logger.error(f"Error getting live points: {e}")
            # Final fallback: try entry info
            try:
                entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=False)
                current_event = entry_info.get('current', [])
                if current_event:
                    gw_data = next((e for e in current_event if e.get('event') == gameweek), None)
                    if gw_data:
                        total = gw_data.get('points', 0)
                return {
                    'total': total,
                    'starting_xi': total,
                    'bench': 0,
                    'captain': 0,
                    'vice_captain': 0,
                    'bench_boost_active': False,
                    'live_elements': {}
                }
            except:
                pass
            return {'total': 0, 'starting_xi': 0, 'bench': 0, 'captain': 0, 'vice_captain': 0, 'bench_boost_active': False}
    
    def calculate_auto_substitutions(self, gameweek: int) -> List[Dict]:
        """
        Calculate which bench players will auto-substitute in.
        
        Args:
            gameweek: Current gameweek number
        
        Returns:
            List of auto-substitution scenarios
        """
        try:
            picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=gameweek, use_cache=False)
            
            if not picks_data or 'picks' not in picks_data:
                return []
            
            picks = picks_data['picks']
            bootstrap = self.api_client.get_bootstrap_static(use_cache=False)
            elements = {e['id']: e for e in bootstrap['elements']}
            
            # Get live data for all picks
            live_elements = {}
            for pick in picks:
                player_id = pick['element']
                try:
                    element_summary = self.api_client._request(f"element-summary/{player_id}/", use_cache=False)
                    history = element_summary.get('history', [])
                    current_gw_data = next((h for h in history if h.get('round') == gameweek), None)
                    if current_gw_data:
                        live_elements[player_id] = {
                            'minutes': current_gw_data.get('minutes', 0),
                            'points': current_gw_data.get('total_points', 0)
                        }
                except:
                    live_elements[player_id] = {'minutes': 0, 'points': 0}
            
            # Identify players who didn't play (0 minutes)
            starting_xi = [p for p in picks if p['position'] <= 11]
            bench = [p for p in picks if p['position'] > 11]
            
            auto_subs = []
            
            # Check each starting XI player
            for starter in starting_xi:
                player_id = starter['element']
                minutes = live_elements.get(player_id, {}).get('minutes', 0)
                
                if minutes == 0:
                    # Find replacement from bench (same position or flexible)
                    element = elements.get(player_id, {})
                    position_type = element.get('element_type', 0)  # 1=GK, 2=DEF, 3=MID, 4=FWD
                    
                    # Find bench player of same position who played
                    for bench_player in bench:
                        bench_id = bench_player['element']
                        bench_minutes = live_elements.get(bench_id, {}).get('minutes', 0)
                        bench_element = elements.get(bench_id, {})
                        bench_position = bench_element.get('element_type', 0)
                        
                        if bench_minutes > 0 and bench_position == position_type:
                            auto_subs.append({
                                'out': {
                                    'id': player_id,
                                    'name': element.get('web_name', 'Unknown'),
                                    'position': starter['position']
                                },
                                'in': {
                                    'id': bench_id,
                                    'name': bench_element.get('web_name', 'Unknown'),
                                    'position': bench_player['position']
                                },
                                'points_gain': live_elements.get(bench_id, {}).get('points', 0)
                            })
                            break
            
            return auto_subs
        except Exception as e:
            logger.error(f"Error calculating auto-substitutions: {e}")
            return []
    
    def predict_bonus_points(self, gameweek: int) -> Dict:
        """
        Predict bonus points based on current BPS (Bonus Points System).
        
        Args:
            gameweek: Current gameweek number
        
        Returns:
            Dictionary with bonus point predictions
        """
        try:
            picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=gameweek, use_cache=False)
            
            if not picks_data or 'picks' not in picks_data:
                return {}
            
            picks = picks_data['picks']
            bootstrap = self.api_client.get_bootstrap_static(use_cache=False)
            elements = {e['id']: e for e in bootstrap['elements']}
            
            # Get all players' BPS for this gameweek
            all_bps = {}
            for pick in picks:
                player_id = pick['element']
                try:
                    element_summary = self.api_client._request(f"element-summary/{player_id}/", use_cache=False)
                    history = element_summary.get('history', [])
                    current_gw_data = next((h for h in history if h.get('round') == gameweek), None)
                    if current_gw_data:
                        all_bps[player_id] = {
                            'bps': current_gw_data.get('bps', 0),
                            'bonus': current_gw_data.get('bonus', 0),
                            'name': elements.get(player_id, {}).get('web_name', 'Unknown')
                        }
                except:
                    continue
            
            # Sort by BPS
            sorted_bps = sorted(all_bps.items(), key=lambda x: x[1]['bps'], reverse=True)
            
            # Predict bonus (top 3 get 3, 2, 1 points)
            predictions = {}
            for i, (player_id, data) in enumerate(sorted_bps[:10]):  # Top 10 for context
                if i < 3:
                    predicted_bonus = 3 - i
                else:
                    predicted_bonus = 0
                
                predictions[player_id] = {
                    'name': data['name'],
                    'current_bps': data['bps'],
                    'current_bonus': data['bonus'],
                    'predicted_bonus': predicted_bonus,
                    'rank': i + 1
                }
            
            return predictions
        except Exception as e:
            logger.error(f"Error predicting bonus points: {e}")
            return {}
    
    def project_rank_change(self, gameweek: int, current_points: int, league_id: int = None, league_analysis: Dict = None, entry_info: Dict = None, entry_history: Dict = None) -> Dict:
        """
        Project rank change based on current points.
        If league_id is provided, projects mini-league rank instead of overall rank.
        
        Args:
            gameweek: Current gameweek number
            current_points: Current total points for the gameweek
            league_id: Optional mini-league ID to project mini-league rank
            league_analysis: Optional pre-computed league analysis
        
        Returns:
            Dictionary with rank projection
        """
        try:
            # If mini-league specified, use mini-league rank
            if league_id and league_analysis:
                current_rank = league_analysis.get('user_rank', 0)
                user_total = league_analysis.get('user_total', 0)
                user_gw_points = league_analysis.get('user_gw_points', 0)
                
                # Calculate how many teams we might pass based on points difference
                points_diff = current_points - user_gw_points
                
                # Get competitors to estimate rank movement
                competitors_above = league_analysis.get('competitors_above', [])
                competitors_below = league_analysis.get('competitors_below', [])
                
                # Estimate rank improvement based on points vs competitors
                rank_improvement = 0
                
                # Count how many teams above us we might pass
                for comp in competitors_above:
                    if comp['gw_points'] < current_points:
                        rank_improvement += 1
                
                # Count how many teams below us might pass us
                rank_degradation = 0
                for comp in competitors_below:
                    if comp['gw_points'] > current_points:
                        rank_degradation += 1
                
                # Net rank change
                net_rank_change = rank_improvement - rank_degradation
                projected_rank = max(1, current_rank - net_rank_change)  # Lower rank number = better
                
                return {
                    'current_rank': current_rank,
                    'projected_rank': int(projected_rank),
                    'rank_change': -net_rank_change,  # Negative = improvement
                    'points': current_points,
                    'is_mini_league': True
                }
            
            # Default: overall rank projection
            if entry_info is None:
                entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=True)  # Enable cache
            current_rank = entry_info.get('summary_overall_rank', 0)
            
            # Get gameweek average (estimate)
            if entry_history is None:
                entry_history = self.api_client.get_entry_history(self.entry_id, use_cache=True)  # Enable cache
            current_event = entry_history.get('current', [])
            
            if current_event:
                gw_points = current_event[-1].get('points', 0) if current_event else 0
                gw_rank = current_event[-1].get('rank', 0) if current_event else 0
                
                # Estimate rank change (simplified)
                points_diff = current_points - gw_points
                
                # Rough estimate: ~1000 ranks per point difference (varies by gameweek)
                estimated_rank_change = -points_diff * 500  # Negative = better rank
                projected_rank = max(1, current_rank + estimated_rank_change)
                
                return {
                    'current_rank': current_rank,
                    'projected_rank': int(projected_rank),
                    'rank_change': int(estimated_rank_change),
                    'points': current_points,
                    'is_mini_league': False
                }
            
            return {'current_rank': current_rank, 'projected_rank': current_rank, 'rank_change': 0, 'is_mini_league': False}
        except Exception as e:
            logger.error(f"Error projecting rank: {e}")
            return {}
    
    def get_user_leagues(self) -> List[Dict]:
        """
        Get list of user's mini-leagues.
        
        Returns:
            List of league information
        """
        try:
            entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=False)
            leagues = entry_info.get('leagues', {}).get('classic', [])
            
            league_list = []
            for league in leagues:
                league_list.append({
                    'id': league.get('id'),
                    'name': league.get('name', 'Unknown'),
                    'rank': league.get('entry_rank', 0),
                    'total_teams': league.get('max_entries', 0)
                })
            
            return league_list
        except Exception as e:
            logger.error(f"Error getting user leagues: {e}")
            return []
    
    def get_mini_league_table(self, league_id: int = None) -> Tuple[List[Dict], str]:
        """
        Get mini-league live table.
        
        Args:
            league_id: Optional league ID (if None, uses user's primary league)
        
        Returns:
            Tuple of (list of league standings, league name)
        """
        try:
            # Get user's leagues
            entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=False)
            leagues = entry_info.get('leagues', {}).get('classic', [])
            
            if not leagues:
                return [], "No leagues found"
            
            # Use first league if league_id not specified
            if league_id is None:
                league_id = leagues[0].get('id')
                league_name = leagues[0].get('name', 'Unknown')
            else:
                # Find league name
                league_name = "Unknown"
                for league in leagues:
                    if league.get('id') == league_id:
                        league_name = league.get('name', 'Unknown')
                        break
            
            # Get league standings
            league_data = self.api_client._request(f"leagues-classic/{league_id}/standings/", use_cache=False)
            
            if not league_data or 'standings' not in league_data:
                return [], league_name
            
            standings = league_data['standings'].get('results', [])
            
            # Format standings
            table = []
            for standing in standings:
                table.append({
                    'rank': standing.get('rank', 0),
                    'entry_name': standing.get('entry_name', 'Unknown'),
                    'player_name': standing.get('player_name', 'Unknown'),
                    'total': standing.get('total', 0),
                    'event_total': standing.get('event_total', 0),  # Current GW points
                    'entry_id': standing.get('entry', 0)
                })
            
            return table, league_name
        except Exception as e:
            logger.error(f"Error getting mini-league table: {e}")
            return [], "Error"
    
    def analyze_mini_league_competitors(self, league_id: int, gameweek: int, user_gw_points: int = None, entry_info: Dict = None) -> Dict:
        """
        Analyze competitors in mini-league for intelligence.
        
        Args:
            league_id: Mini-league ID
            gameweek: Current gameweek number
        
        Returns:
            Dictionary with competitor analysis
        """
        try:
            # Get league standings
            mini_league_table, league_name = self.get_mini_league_table(league_id)
            if not mini_league_table:
                return {}
            
            # Get user's position
            if entry_info is None:
                entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=True)  # Enable cache
            user_total = entry_info.get('summary_overall_points', 0)
            
            # Use provided GW points or fetch from history
            if user_gw_points is None:
                user_gw_points = 0
                entry_history = self.api_client.get_entry_history(self.entry_id, use_cache=True)  # Enable cache
                current = entry_history.get('current', [])
                gw_data = next((e for e in current if e.get('event') == gameweek), None)
                if gw_data:
                    user_gw_points = gw_data.get('points', 0)
            
            # Find user's rank (from entry info if not in standings table)
            user_entry = next((t for t in mini_league_table if t.get('entry_id') == self.entry_id), None)
            if user_entry:
                user_rank = user_entry.get('rank', 0)
            else:
                # User not in top standings - get rank from entry info
                leagues = entry_info.get('leagues', {}).get('classic', [])
                user_league = next((l for l in leagues if l.get('id') == league_id), None)
                user_rank = user_league.get('entry_rank', 0) if user_league else 0
            
            # Get total teams in league from entry info
            leagues = entry_info.get('leagues', {}).get('classic', [])
            user_league = next((l for l in leagues if l.get('id') == league_id), None)
            total_teams_in_league = user_league.get('entry_set_overall_rank', 0) if user_league else len(mini_league_table)
            
            analysis = {
                'league_name': league_name,
                'user_rank': user_rank,
                'user_total': user_total,
                'user_gw_points': user_gw_points,
                'total_teams': total_teams_in_league if total_teams_in_league > 0 else len(mini_league_table),
                'competitors_above': [],
                'competitors_below': [],
                'points_gaps': {},
                'threats': [],
                'opportunities': []
            }
            
            # Analyze competitors above and below
            # If user is not in standings table, all teams in table are above them
            for team in mini_league_table:
                team_rank = team.get('rank', 0)
                team_total = team.get('total', 0)
                team_gw = team.get('event_total', 0)
                team_entry_id = team.get('entry_id', 0)
                
                if team_entry_id == self.entry_id:
                    continue
                
                points_gap = team_total - user_total
                
                # All teams in standings table are above user if user not in table
                if user_entry:
                    # User is in table - compare ranks normally
                    if team_rank < user_rank:  # Above user
                        analysis['competitors_above'].append({
                            'rank': team_rank,
                            'name': team.get('entry_name', 'Unknown'),
                            'total': team_total,
                            'gw_points': team_gw,
                            'points_gap': points_gap,
                            'entry_id': team_entry_id
                        })
                    else:  # Below user
                        analysis['competitors_below'].append({
                            'rank': team_rank,
                            'name': team.get('entry_name', 'Unknown'),
                            'total': team_total,
                            'gw_points': team_gw,
                            'points_gap': abs(points_gap),
                            'entry_id': team_entry_id
                        })
                else:
                    # User not in table - all teams shown are above
                    analysis['competitors_above'].append({
                        'rank': team_rank,
                        'name': team.get('entry_name', 'Unknown'),
                        'total': team_total,
                        'gw_points': team_gw,
                        'points_gap': points_gap,
                        'entry_id': team_entry_id
                    })
            
            # Sort competitors
            analysis['competitors_above'].sort(key=lambda x: x['rank'])
            analysis['competitors_below'].sort(key=lambda x: x['rank'])
            
            # Identify threats (teams below climbing fast)
            if analysis['competitors_below']:
                for team in analysis['competitors_below'][:10]:  # Top 10 below
                    if team['gw_points'] > user_gw_points + 5:  # Scored 5+ more this GW
                        analysis['threats'].append({
                            'name': team['name'],
                            'rank': team['rank'],
                            'gw_points': team['gw_points'],
                            'points_gap': team['points_gap'],
                            'threat_level': 'High' if team['gw_points'] > user_gw_points + 10 else 'Medium'
                        })
            
            # Identify opportunities (teams above struggling)
            if analysis['competitors_above']:
                for team in analysis['competitors_above'][:10]:  # Top 10 above
                    if team['gw_points'] < user_gw_points - 5:  # Scored 5+ less this GW
                        analysis['opportunities'].append({
                            'name': team['name'],
                            'rank': team['rank'],
                            'gw_points': team['gw_points'],
                            'points_gap': team['points_gap'],
                            'opportunity': 'High' if team['gw_points'] < user_gw_points - 10 else 'Medium'
                        })
            
            # Calculate points gaps
            if analysis['competitors_above']:
                # Get closest above (lowest rank number)
                next_above = min(analysis['competitors_above'], key=lambda x: x['rank'])
                analysis['points_gaps']['next_rank'] = next_above['points_gap']
                analysis['points_gaps']['next_rank_name'] = next_above['name']
            
            if analysis['competitors_below']:
                # Get closest below (highest rank number)
                next_below = min(analysis['competitors_below'], key=lambda x: x['rank'])
                analysis['points_gaps']['next_rank_below'] = next_below['points_gap']
                analysis['points_gaps']['next_rank_below_name'] = next_below['name']
            
            # Top of league
            if mini_league_table:
                top_team = mini_league_table[0]
                analysis['points_gaps']['top_team'] = top_team.get('total', 0) - user_total
                analysis['points_gaps']['top_team_name'] = top_team.get('entry_name', 'Unknown')
            
            # Last place in standings (if user not in table, show gap to last shown)
            if mini_league_table and not user_entry:
                last_team = mini_league_table[-1]
                analysis['points_gaps']['last_shown'] = last_team.get('total', 0) - user_total
                analysis['points_gaps']['last_shown_name'] = last_team.get('entry_name', 'Unknown')
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing mini-league competitors: {e}")
            return {}
    
    def check_alerts(self, gameweek: int, previous_data: Dict = None) -> List[Dict]:
        """
        Check for in-game alerts (goals, assists, cards, injuries, clean sheets).
        
        Args:
            gameweek: Current gameweek number
            previous_data: Previous state for comparison
        
        Returns:
            List of alerts
        """
        alerts = []
        
        try:
            picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=gameweek, use_cache=False)
            
            if not picks_data or 'picks' not in picks_data:
                return alerts
            
            picks = picks_data['picks']
            bootstrap = self.api_client.get_bootstrap_static(use_cache=False)
            elements = {e['id']: e for e in bootstrap['elements']}
            
            # Get current live data
            current_data = {}
            for pick in picks:
                player_id = pick['element']
                try:
                    element_summary = self.api_client._request(f"element-summary/{player_id}/", use_cache=False)
                    history = element_summary.get('history', [])
                    current_gw_data = next((h for h in history if h.get('round') == gameweek), None)
                    if current_gw_data:
                        current_data[player_id] = current_gw_data
                except:
                    continue
            
            # Compare with previous data
            if previous_data:
                prev_data = previous_data.get('live_elements', {})
            else:
                prev_data = {}
            
            # Check for goal alerts
            for player_id, current in current_data.items():
                player_name = elements.get(player_id, {}).get('web_name', 'Unknown')
                prev = prev_data.get(player_id, {})
                
                # Goal alert
                current_goals = current.get('goals_scored', 0)
                prev_goals = prev.get('goals_scored', 0)
                if current_goals > prev_goals:
                    xg = current.get('expected_goals', 0)
                    alerts.append({
                        'type': 'goal',
                        'player': player_name,
                        'player_id': player_id,
                        'goals': current_goals,
                        'xg': xg,
                        'message': f"⚽ GOAL! {player_name} scored! (xG: {xg:.2f})"
                    })
                
                # Assist alert
                current_assists = current.get('assists', 0)
                prev_assists = prev.get('assists', 0)
                if current_assists > prev_assists:
                    xa = current.get('expected_assists', 0)
                    alerts.append({
                        'type': 'assist',
                        'player': player_name,
                        'player_id': player_id,
                        'assists': current_assists,
                        'xa': xa,
                        'message': f"🎯 ASSIST! {player_name} assisted! (xA: {xa:.2f})"
                    })
                
                # Red card alert
                current_reds = current.get('red_cards', 0)
                prev_reds = prev.get('red_cards', 0)
                if current_reds > prev_reds:
                    alerts.append({
                        'type': 'red_card',
                        'player': player_name,
                        'player_id': player_id,
                        'message': f"🟥 RED CARD! {player_name} sent off!"
                    })
                
                # Injury/availability check
                element = elements.get(player_id, {})
                chance = element.get('chance_of_playing_this_round', 100)
                if chance and chance < 75:
                    alerts.append({
                        'type': 'injury',
                        'player': player_name,
                        'player_id': player_id,
                        'chance': chance,
                        'message': f"⚠️ INJURY WARNING! {player_name} only {chance}% chance of playing"
                    })
            
            # Check for clean sheet threats (defenders/goalkeepers)
            for pick in picks:
                player_id = pick['element']
                element = elements.get(player_id, {})
                position = element.get('element_type', 0)
                
                if position in [1, 2]:  # GK or DEF
                    current = current_data.get(player_id, {})
                    goals_conceded = current.get('goals_conceded', 0)
                    if goals_conceded > 0:
                        player_name = element.get('web_name', 'Unknown')
                        alerts.append({
                            'type': 'clean_sheet_lost',
                            'player': player_name,
                            'player_id': player_id,
                            'goals_conceded': goals_conceded,
                            'message': f"🚨 CLEAN SHEET LOST! {player_name}'s team conceded {goals_conceded} goal(s)"
                        })
            
            return alerts
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    def track_live(self, gameweek: int, update_interval: int = 60) -> None:
        """
        Continuously track live gameweek data.
        
        Args:
            gameweek: Current gameweek number
            update_interval: Update interval in seconds (default: 60)
        """
        logger.info(f"Starting live tracking for GW{gameweek} (updates every {update_interval}s)")
        
        previous_data = None
        
        try:
            while True:
                # Get live points
                live_points = self.get_live_points(gameweek)
                
                # Calculate auto-subs
                auto_subs = self.calculate_auto_substitutions(gameweek)
                
                # Predict bonus
                bonus_predictions = self.predict_bonus_points(gameweek)
                
                # Project rank
                rank_projection = self.project_rank_change(gameweek, live_points['total'])
                
                # Check alerts
                alerts = self.check_alerts(gameweek, previous_data)
                
                # Get additional data (pass league_id if tracking specific league)
                team_summary = self.get_team_summary(gameweek, league_id=None)  # Could be enhanced to pass league_id
                player_breakdown = self.get_player_breakdown(gameweek)
                league_analysis = None  # Will be set if league_id provided
                
                # Display update
                self._display_live_update(live_points, auto_subs, bonus_predictions, rank_projection, alerts,
                                         team_summary, player_breakdown, league_analysis)
                
                # Update previous data
                previous_data = {'live_elements': live_points.get('live_elements', {})}
                
                # Wait for next update
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            logger.info("Live tracking stopped by user")
        except Exception as e:
            logger.error(f"Error in live tracking: {e}")
    
    def get_team_summary(self, gameweek: int, league_id: int = None, entry_info: Dict = None, entry_history: Dict = None) -> Dict:
        """
        Get comprehensive team summary information.
        
        Args:
            gameweek: Current gameweek number
        
        Returns:
            Dictionary with team summary data
        """
        try:
            # Use provided data or fetch if not provided (for backward compatibility)
            if entry_info is None:
                entry_info = self.api_client.get_entry_info(self.entry_id, use_cache=True)  # Enable cache
            if entry_history is None:
                entry_history = self.api_client.get_entry_history(self.entry_id, use_cache=True)  # Enable cache
            
            # Manager info
            manager_name = entry_info.get('player_first_name', '') + ' ' + entry_info.get('player_last_name', '')
            manager_name = manager_name.strip() or 'Unknown'
            
            # FPL History
            current = entry_history.get('current', [])
            seasons_played = len([e for e in current if e.get('event') == 1])  # Count first gameweeks
            if current:
                ranks = [e.get('rank', 0) for e in current if e.get('rank', 0) > 0]
                avg_rank = sum(ranks) / len(ranks) if ranks else 0
            else:
                avg_rank = 0
            
            # Total points
            total_points = entry_info.get('summary_overall_points', 0)
            
            # GW points
            gw_data = next((e for e in current if e.get('event') == gameweek), None)
            gw_points = gw_data.get('points', 0) if gw_data else 0
            
            # Transfers
            transfers_data = self.api_client.get_entry_transfers(self.entry_id, use_cache=True)  # Enable cache
            gw_transfers = len([t for t in transfers_data if t.get('event') == gameweek])
            
            # Free transfers saved
            free_transfers = 1
            for gw in range(gameweek, max(1, gameweek - 10), -1):
                gw_transfers_count = len([t for t in transfers_data if t.get('event') == gw])
                if gw_transfers_count == 0:
                    free_transfers = min(free_transfers + 1, 3)
                else:
                    break
            
            # Chips used
            chips_used = entry_history.get('chips', [])
            chips_used_list = []
            for chip in chips_used:
                chip_name = chip.get('name', '')
                chip_gw = chip.get('event', 0)
                if chip_name == 'wildcard':
                    chips_used_list.append(f"WC{chip_gw}")
                elif chip_name == 'freehit':
                    chips_used_list.append(f"FH{chip_gw}")
                elif chip_name == 'bboost':
                    chips_used_list.append(f"BB{chip_gw}")
                elif chip_name == '3xc':
                    chips_used_list.append(f"TC{chip_gw}")
            
            # Current chip
            current_chip = None
            for chip in chips_used:
                if chip.get('event') == gameweek:
                    chip_name = chip.get('name', '')
                    if chip_name == 'wildcard':
                        current_chip = 'Wildcard'
                    elif chip_name == 'freehit':
                        current_chip = 'Free Hit'
                    elif chip_name == 'bboost':
                        current_chip = 'Bench Boost'
                    elif chip_name == '3xc':
                        current_chip = 'Triple Captain'
                    break
            
            # Team value
            bank = entry_info.get('last_deadline_bank', 0) / 10.0
            squad_value = entry_info.get('last_deadline_value', 0) / 10.0
            total_value = squad_value + bank
            
            # Live rank (overall rank should always be available from entry_info)
            live_rank = entry_info.get('summary_overall_rank')
            # Gameweek rank might not be available if gameweek hasn't finished yet
            gw_rank = None
            if gw_data:
                gw_rank = gw_data.get('rank')  # Don't default to 0, use None if missing
                if gw_rank is None:
                    logger.debug(f"GW{gameweek} rank not available in entry_history.current - gameweek may not be finished yet")
            else:
                logger.debug(f"GW{gameweek} data not found in entry_history.current")
            
            # Log what we found
            logger.debug(f"Team summary ranks - Overall: {live_rank}, GW{gameweek}: {gw_rank}")
            
            # Mini-league rank (if league_id provided)
            mini_league_rank = None
            mini_league_name = None
            if league_id:
                try:
                    # First try to get rank from entry info (more reliable, works for all ranks)
                    leagues = entry_info.get('leagues', {}).get('classic', [])
                    user_league = next((l for l in leagues if l.get('id') == league_id), None)
                    if user_league:
                        mini_league_rank = user_league.get('entry_rank', 0)
                        mini_league_name = user_league.get('name', 'Unknown')
                        logger.debug(f"Found mini-league rank from entry info: {mini_league_rank} in {mini_league_name}")
                    else:
                        # Fallback: try to find in standings table (only works if user is in top results)
                        mini_league_table, league_name = self.get_mini_league_table(league_id)
                        mini_league_name = league_name
                        user_entry = next(
                            (t for t in mini_league_table 
                             if int(t.get('entry_id', 0)) == self.entry_id or int(t.get('entry', 0)) == self.entry_id), 
                            None
                        )
                        if user_entry:
                            mini_league_rank = user_entry.get('rank', 0)
                            logger.debug(f"Found mini-league rank from standings: {mini_league_rank} in {league_name}")
                except Exception as e:
                    logger.debug(f"Error getting mini-league rank: {e}")
            
            return {
                'manager_name': manager_name,
                'seasons_played': seasons_played,
                'avg_rank': int(avg_rank) if avg_rank > 0 else 0,
                'total_points': total_points,
                'gw_points': gw_points,
                'gw_transfers': gw_transfers,
                'free_transfers': free_transfers,
                'chips_used': ', '.join(chips_used_list) if chips_used_list else 'None',
                'current_chip': current_chip,
                'bank': bank,
                'squad_value': squad_value,
                'total_value': total_value,
                'live_rank': live_rank,
                'gw_rank': gw_rank,
                'mini_league_rank': mini_league_rank,
                'mini_league_name': mini_league_name
            }
        except Exception as e:
            logger.error(f"Error getting team summary: {e}")
            return {}
    
    def get_player_breakdown(self, gameweek: int, bootstrap: Dict = None, picks_data: Dict = None, fixtures: List[Dict] = None) -> List[Dict]:
        """
        Get detailed player breakdown for the team.
        
        Args:
            gameweek: Current gameweek number
        
        Returns:
            List of player information
        """
        try:
            # Get picks - track which gameweek we actually got picks for
            picks_data = None
            actual_gameweek = gameweek  # Track which GW we're actually using
            try:
                picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=gameweek, use_cache=False)
            except:
                try:
                    # Fallback to previous gameweek if current GW picks not available
                    actual_gameweek = gameweek - 1
                    picks_data = self.api_client.get_entry_picks(entry_id=self.entry_id, gameweek=actual_gameweek, use_cache=False)
                    logger.debug(f"GW{gameweek} picks not available, using GW{actual_gameweek} picks instead")
                except:
                    return []
            
            if not picks_data or 'picks' not in picks_data:
                return []
            
            picks = picks_data['picks']
            
            if bootstrap is None:
                bootstrap = self.api_client.get_bootstrap_static(use_cache=True)  # Enable cache
            elements = {e['id']: e for e in bootstrap['elements']}
            teams = {t['id']: {'short_name': t.get('short_name', ''), 'name': t.get('name', '')} for t in bootstrap['teams']}
            
            # Get fixtures for status - use the actual gameweek we got picks for
            if fixtures is None:
                fixtures = self.api_client.get_fixtures(use_cache=True)  # Enable cache
            gw_fixtures = [f for f in fixtures if f.get('event') == actual_gameweek]
            
            player_breakdown = []
            
            for pick in picks:
                player_id = pick['element']
                element = elements.get(player_id, {})
                team_id = element.get('team', 0)
                team_data = teams.get(team_id, {})
                team_name = team_data.get('short_name') or team_data.get('name') or 'Unknown'
                
                # Get player points and status
                # Try to get current gameweek minutes from element-summary if available
                points = element.get('event_points', 0)
                minutes = 0
                
                # Try to get actual gameweek minutes from element-summary
                # Use actual_gameweek (the GW we got picks for) not the requested gameweek
                try:
                    element_summary = self.api_client._request(f"element-summary/{player_id}/", use_cache=False)
                    history = element_summary.get('history', [])
                    current_gw_data = next((h for h in history if h.get('round') == actual_gameweek), None)
                    if current_gw_data:
                        minutes = current_gw_data.get('minutes', 0)
                        # Also get points from history if event_points is 0
                        if points == 0:
                            points = current_gw_data.get('total_points', 0)
                except:
                    # Fallback: use total minutes (not ideal but better than nothing)
                    minutes = element.get('minutes', 0)
                
                position = pick['position']
                is_captain = pick.get('is_captain', False)
                is_vice = pick.get('is_vice_captain', False)
                
                # Determine status
                player_fixture = next((f for f in gw_fixtures if f.get('team_h') == team_id or f.get('team_a') == team_id), None)
                
                # Check if fixture is currently in play (started but not finished)
                fixture_in_play = False
                if player_fixture:
                    finished = player_fixture.get('finished', False)
                    kickoff = player_fixture.get('kickoff_time')
                    if not finished and kickoff:
                        try:
                            from datetime import datetime, timezone, timedelta
                            kickoff_dt = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                            now_utc = datetime.now(timezone.utc)
                            # Fixture is in play if kickoff has passed but match hasn't finished
                            # and we're within 3 hours of kickoff (typical match duration)
                            if kickoff_dt < now_utc and (now_utc - kickoff_dt) < timedelta(hours=3):
                                fixture_in_play = True
                        except Exception:
                            pass
                
                # If player has points or minutes, they've played
                if points > 0 or minutes > 0:
                    # Player has played
                    if fixture_in_play:
                        # Game is currently in play
                        if minutes >= 90:
                            # Player has played full match, but game might still be finishing
                            status = f"In Play ({minutes}')"
                        elif minutes > 0:
                            status = f"In Play ({minutes}')"
                        else:
                            # Has points but no minutes recorded yet (game just started)
                            status = "In Play"
                    else:
                        # Game is finished or not in play
                        if minutes >= 90:
                            status = f"Done ({minutes}')"
                        elif minutes > 0:
                            status = f"Done ({minutes}')"
                        else:
                            # Has points but no minutes recorded (unusual, but mark as done)
                            status = "Done"
                elif player_fixture:
                    # Check fixture status
                    finished = player_fixture.get('finished', False)
                    kickoff = player_fixture.get('kickoff_time')
                    
                    # If fixture is finished, player definitely didn't play (0 points/minutes)
                    if finished:
                        status = "Did not play"
                    elif kickoff:
                        try:
                            from datetime import datetime, timezone, timedelta
                            # Parse kickoff time (always UTC in FPL API)
                            kickoff_dt_utc = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                            # Convert to local timezone for display
                            kickoff_dt_local = kickoff_dt_utc.astimezone()
                            # Get current time in UTC for accurate comparison
                            now_utc = datetime.now(timezone.utc)
                            
                            # If kickoff has passed, check if enough time has elapsed for match to finish
                            # (matches typically last ~2 hours, so if kickoff was >3 hours ago, match is done)
                            if kickoff_dt_utc > now_utc:
                                # Match hasn't started yet - show local time
                                status = f"Playing {kickoff_dt_local.strftime('%a %H:%M')}"
                            elif (now_utc - kickoff_dt_utc) > timedelta(hours=3):
                                # Kickoff was more than 3 hours ago - match is definitely finished
                                # Player has 0 points/minutes, so they didn't play
                                status = "Did not play"
                            else:
                                # Match might still be live (within 3 hours of kickoff)
                                # But if player has 0 points/minutes, they likely didn't play
                                # Check if we're past typical match end time (kickoff + 2 hours)
                                match_end_time = kickoff_dt_utc + timedelta(hours=2)
                                if now_utc > match_end_time:
                                    status = "Did not play"
                                else:
                                    # Match might still be live, show kickoff time in local timezone
                                    status = f"Playing {kickoff_dt_local.strftime('%a %H:%M')}"
                        except Exception as e:
                            logger.debug(f"Error parsing kickoff time for player {player_id}: {e}")
                            # If we can't parse, but fixture exists and player has 0 points/minutes,
                            # they likely didn't play
                            status = "Did not play"
                    else:
                        # No kickoff time available, but fixture exists
                        # If player has 0 points/minutes, they didn't play
                        status = "Did not play"
                else:
                    # No fixture found for this gameweek
                    status = "Did not play"
                
                # Calculate impact (ownership percentage)
                ownership = element.get('selected_by_percent', 0)
                
                # Apply captain multiplier
                if is_captain:
                    points *= 2
                
                # Get opponent information
                opponent_info = None
                if player_fixture:
                    # Determine if player's team is home or away
                    is_home = player_fixture.get('team_h') == team_id
                    opponent_team_id = player_fixture.get('team_a') if is_home else player_fixture.get('team_h')
                    opponent_team_data = teams.get(opponent_team_id, {})
                    opponent_team_name = opponent_team_data.get('short_name') or opponent_team_data.get('name') or 'Unknown'
                    opponent_info = f"{opponent_team_name} ({'H' if is_home else 'A'})"
                else:
                    opponent_info = "N/A"
                
                # Add kickoff_time_utc if available for frontend timezone conversion
                kickoff_time_utc = None
                if player_fixture and player_fixture.get('kickoff_time'):
                    kickoff_time_utc = player_fixture.get('kickoff_time')
                
                player_breakdown.append({
                    'id': player_id,
                    'name': element.get('web_name', 'Unknown'),
                    'team': team_name,
                    'team_id': team_id,
                    'opponent': opponent_info,
                    'position': position,
                    'points': points,
                    'base_points': element.get('event_points', 0),
                    'minutes': minutes,
                    'status': status,
                    'kickoff_time_utc': kickoff_time_utc,  # UTC ISO string for frontend timezone conversion
                    'ownership': ownership,
                    'is_captain': is_captain,
                    'is_vice': is_vice,
                    'is_vice_captain': is_vice,  # Alias for frontend compatibility
                    'element_type': element.get('element_type', 0),
                    'photo': f"https://resources.fantasy.premierleague.com/drf/element_photos/{player_id}.png",
                })
            
            # Sort by position (starting XI first, then bench)
            player_breakdown.sort(key=lambda x: x['position'])
            
            return player_breakdown
        except Exception as e:
            logger.error(f"Error getting player breakdown: {e}")
            return []
    
    def _display_live_update(self, live_points: Dict, auto_subs: List[Dict], 
                            bonus_predictions: Dict, rank_projection: Dict, alerts: List[Dict],
                            team_summary: Dict = None, player_breakdown: List[Dict] = None,
                            league_analysis: Dict = None):
        """Display live update information."""
        print("\n" + "="*70)
        print(f"📊 LIVE GAMEWEEK UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        print("="*70)
        
        # Team Summary
        if team_summary:
            print(f"\n👤 Name: {team_summary.get('manager_name', 'Unknown')}")
            seasons = team_summary.get('seasons_played', 0)
            avg_rank = team_summary.get('avg_rank', 0)
            if seasons > 0 and avg_rank > 0:
                print(f"📊 FPL History: {seasons} Season(s) (Avg Rank: {avg_rank:,})")
            
            print(f"🏆 Total Points: {team_summary.get('total_points', 0):,}")
            
            gw_points = live_points.get('total', 0)
            # Estimate expected final points (rough estimate: add 10-15% for remaining games)
            expected_final = int(gw_points * 1.15) if gw_points > 0 else 0
            print(f"📈 GW Points: {gw_points} (Expected Final: ~{expected_final})")
            
            transfers = team_summary.get('gw_transfers', 0)
            free_transfers = team_summary.get('free_transfers', 1)
            print(f"🔄 Transfers: {transfers} (Saved: {free_transfers})")
            
            # Only show overall rank if not using mini-league
            if not rank_projection.get('is_mini_league', False):
                live_rank = team_summary.get('live_rank', 0)
                gw_rank = team_summary.get('gw_rank', 0)
                if live_rank > 0:
                    rank_change = "↑" if gw_rank < live_rank else "↓" if gw_rank > live_rank else "→"
                    print(f"📊 Live Rank: {live_rank:,} {rank_change} (GW: {gw_rank:,})")
            
            # Mini-league rank
            mini_league_rank = team_summary.get('mini_league_rank')
            mini_league_name = team_summary.get('mini_league_name')
            if mini_league_rank is not None and mini_league_rank > 0:
                print(f"🏆 Mini-League Rank ({mini_league_name}): {mini_league_rank}")
            
            current_chip = team_summary.get('current_chip')
            chips_used = team_summary.get('chips_used', 'None')
            if current_chip:
                print(f"🎯 Chip: {current_chip} (Used: {chips_used})")
            else:
                print(f"🎯 Chip: None (Used: {chips_used})")
            
            total_value = team_summary.get('total_value', 0)
            squad_value = team_summary.get('squad_value', 0)
            bank = team_summary.get('bank', 0)
            print(f"💰 Team Value: £{total_value:.1f}m (£{squad_value:.1f}m + £{bank:.1f}m bank)")
        
        # Live Points
        bench_boost_active = live_points.get('bench_boost_active', False)
        if bench_boost_active:
            print(f"\n💰 LIVE POINTS: {live_points['total']} (Bench Boost active)")
        else:
            print(f"\n💰 LIVE POINTS: {live_points['total']}")
        print(f"   Starting XI: {live_points['starting_xi']} | Bench: {live_points['bench']}")
        print(f"   Captain: {live_points['captain']} | Vice: {live_points['vice_captain']}")
        
        # Player Breakdown
        if player_breakdown:
            print(f"\n👥 PLAYER BREAKDOWN:")
            print(f"{'Player':<22} {'Team':<6} {'Status':<22} {'Pts':<6} {'Ownership':<10}")
            print("-" * 70)
            for player in player_breakdown:
                name = player['name'][:20]
                team = player['team'][:5]
                status = player['status'][:21]
                points = player['points']
                ownership_val = float(player.get('ownership', 0) or 0)
                ownership = f"{ownership_val:.0f}%"
                
                # Add captain/vice indicator
                if player['is_captain']:
                    name += " (C)"
                elif player['is_vice']:
                    name += " (V)"
                
                print(f"{name:<22} {team:<6} {status:<22} {points:<6} {ownership:<10}")
        
        # Auto-Substitutions
        if auto_subs:
            print(f"\n🔄 AUTO-SUBSTITUTIONS ({len(auto_subs)}):")
            for sub in auto_subs:
                print(f"   {sub['out']['name']} (0 min) → {sub['in']['name']} (+{sub['points_gain']} pts)")
        
        # Bonus Predictions
        if bonus_predictions:
            print(f"\n⭐ BONUS POINTS PREDICTION (Top 3):")
            for player_id, data in list(bonus_predictions.items())[:3]:
                print(f"   {data['rank']}. {data['name']}: {data['current_bps']} BPS → {data['predicted_bonus']} bonus")
        
        # Rank Projection
        if rank_projection:
            rank_change = rank_projection.get('rank_change', 0)
            current_rank = rank_projection.get('current_rank', 0)
            projected_rank = rank_projection.get('projected_rank', 0)
            
            # Show mini-league rank projection if available, otherwise overall
            if rank_projection.get('is_mini_league'):
                # For mini-league: lower rank number = better (ranking up)
                # If projected_rank < current_rank, we're ranking UP (↑)
                # If projected_rank > current_rank, we're ranking DOWN (↓)
                if projected_rank < current_rank:
                    direction = "↑"  # Ranking UP (improving position)
                elif projected_rank > current_rank:
                    direction = "↓"  # Ranking DOWN (worse position)
                else:
                    direction = "→"  # No change
                print(f"\n📈 MINI-LEAGUE RANK PROJECTION: {current_rank:,} {direction} {projected_rank:,}")
            else:
                # For overall rank: lower rank number = better
                direction = "↓" if rank_change < 0 else "↑" if rank_change > 0 else "→"
                print(f"\n📈 RANK PROJECTION: {current_rank:,} {direction} {projected_rank:,}")
        
        # Alerts
        if alerts:
            print(f"\n🚨 ALERTS ({len(alerts)}):")
            for alert in alerts:
                print(f"   {alert['message']}")
        
        # Mini-League Intelligence
        if league_analysis and league_analysis.get('user_rank'):
            print(f"\n🧠 MINI-LEAGUE INTELLIGENCE ({league_analysis.get('league_name', 'Unknown')}):")
            print(f"   Your Rank: {league_analysis.get('user_rank')} of {league_analysis.get('total_teams', 0)}")
            
            # Points gaps
            points_gaps = league_analysis.get('points_gaps', {})
            if points_gaps.get('next_rank') is not None:
                print(f"   📊 Points to next rank: {points_gaps['next_rank']} pts ({points_gaps.get('next_rank_name', 'Unknown')})")
            if points_gaps.get('last_shown') is not None:
                print(f"   📉 Points to last shown: {points_gaps['last_shown']} pts ({points_gaps.get('last_shown_name', 'Unknown')})")
            if points_gaps.get('top_team') is not None:
                print(f"   🏆 Points to top: {points_gaps['top_team']} pts ({points_gaps.get('top_team_name', 'Unknown')})")
            
            # Threats (teams climbing fast)
            threats = league_analysis.get('threats', [])
            if threats:
                print(f"\n   ⚠️  THREATS ({len(threats)} teams climbing fast):")
                for threat in threats[:5]:  # Top 5 threats
                    print(f"      {threat['name']} (Rank {threat['rank']}): +{threat['gw_points']} GW pts "
                          f"(Gap: {threat['points_gap']} pts) - {threat['threat_level']} threat")
            
            # Opportunities (teams above struggling)
            opportunities = league_analysis.get('opportunities', [])
            if opportunities:
                print(f"\n   🎯 OPPORTUNITIES ({len(opportunities)} teams above struggling):")
                for opp in opportunities[:5]:  # Top 5 opportunities
                    print(f"      {opp['name']} (Rank {opp['rank']}): {opp['gw_points']} GW pts "
                          f"(Gap: {opp['points_gap']} pts) - {opp['opportunity']} opportunity")
            
            # Closest competitors
            competitors_above = league_analysis.get('competitors_above', [])
            competitors_below = league_analysis.get('competitors_below', [])
            
            if competitors_above or competitors_below:
                user_total = league_analysis.get('user_total', 0)
                user_gw_points = league_analysis.get('user_gw_points', 0)
                print(f"\n   📍 CLOSEST COMPETITORS:")
                # Show 2 above and 2 below
                for comp in competitors_above[:2]:
                    print(f"      #{comp['rank']} {comp['name']}: {comp['total']} pts "
                          f"(+{comp['points_gap']} ahead, {comp['gw_points']} GW pts)")
                
                print(f"      → YOU (Rank {league_analysis.get('user_rank')}): {user_total} pts ({user_gw_points} GW pts)")
                
                for comp in competitors_below[:2]:
                    print(f"      #{comp['rank']} {comp['name']}: {comp['total']} pts "
                          f"(-{comp['points_gap']} behind, {comp['gw_points']} GW pts)")
        
        print("="*70)

