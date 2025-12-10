"""
Fixture Analysis Engine
Provides advanced fixture difficulty ratings and analysis beyond FPL's basic ratings.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from fpl_api import FPLAPIClient

logger = logging.getLogger(__name__)


class FixtureAnalyzer:
    """
    Advanced fixture difficulty rating calculator based on actual team performance.
    """
    
    def __init__(self, api_client: FPLAPIClient, db_manager=None):
        """
        Initialize fixture analyzer.
        
        Args:
            api_client: FPL API client instance
            db_manager: Optional database manager for historical data
        """
        self.api_client = api_client
        self.db_manager = db_manager
        self.team_stats_cache = {}
        
    def _get_team_stats(self, team_id: int, gameweek: int, window: int = 10) -> Dict:
        """
        Get team statistics for recent games.
        
        Args:
            team_id: Team ID
            gameweek: Current gameweek
            window: Number of recent games to analyze
        
        Returns:
            Dictionary with team stats (goals_scored, goals_conceded, xg, xga, clean_sheets)
        """
        cache_key = f"{team_id}_{gameweek}_{window}"
        if cache_key in self.team_stats_cache:
            return self.team_stats_cache[cache_key]
        
        try:
            # Get historical data from database if available
            if self.db_manager:
                try:
                    history = self.db_manager.get_current_season_history()
                    if not history.empty and 'gw' in history.columns:
                        # Aggregate team stats from player history
                        # We need to get players from this team and aggregate their stats
                        bootstrap = self.api_client.get_bootstrap_static()
                        players_df = pd.DataFrame(bootstrap['elements'])
                        team_players = players_df[players_df['team'] == team_id]['id'].tolist()
                        
                        if team_players:
                            # Get history for all players from this team
                            team_history = history[
                                (history['player_id'].isin(team_players)) & 
                                (history['gw'] < gameweek)
                            ].sort_values('gw', ascending=False)
                            
                            if not team_history.empty:
                                # Aggregate team-level stats
                                # For goals_scored: sum of all goals by team players
                                # For goals_conceded: need to get from opponent perspective
                                # For now, use average per game
                                recent_gws = team_history['gw'].unique()[:window]
                                recent_history = team_history[team_history['gw'].isin(recent_gws)]
                                
                                if not recent_history.empty:
                                    # Calculate team stats from player data
                                    goals_scored = recent_history.groupby('gw')['goals_scored'].sum().mean() if 'goals_scored' in recent_history.columns else 1.5
                                    goals_conceded = recent_history.groupby('gw')['goals_conceded'].sum().mean() if 'goals_conceded' in recent_history.columns else 1.5
                                    
                                    stats = {
                                        'goals_scored': float(goals_scored) if not pd.isna(goals_scored) else 1.5,
                                        'goals_conceded': float(goals_conceded) if not pd.isna(goals_conceded) else 1.5,
                                        'xg': recent_history.get('xg', pd.Series([0] * len(recent_history))).mean() if 'xg' in recent_history.columns else 1.5,
                                        'xga': recent_history.get('xga', pd.Series([0] * len(recent_history))).mean() if 'xga' in recent_history.columns else 1.5,
                                        'clean_sheets': (recent_history.get('goals_conceded', pd.Series([1] * len(recent_history))) == 0).sum() / len(recent_gws) if len(recent_gws) > 0 else 0.3,
                                        'games_played': len(recent_gws)
                                    }
                                    self.team_stats_cache[cache_key] = stats
                                    return stats
                except Exception as e:
                    logger.debug(f"Could not get team stats from database: {e}")
            
            # Fallback: use season averages from bootstrap
            bootstrap = self.api_client.get_bootstrap_static()
            teams_df = pd.DataFrame(bootstrap['teams'])
            team = teams_df[teams_df['id'] == team_id].iloc[0] if len(teams_df[teams_df['id'] == team_id]) > 0 else None
            
            if team is not None:
                stats = {
                    'goals_scored': team.get('strength_attack', 3) / 10.0,  # Normalize from 1-100 scale
                    'goals_conceded': team.get('strength_defence', 3) / 10.0,
                    'xg': team.get('strength_attack', 3) / 10.0,
                    'xga': team.get('strength_defence', 3) / 10.0,
                    'clean_sheets': 0.3,  # Default estimate
                    'games_played': gameweek - 1
                }
                self.team_stats_cache[cache_key] = stats
                return stats
        except Exception as e:
            logger.warning(f"Error getting team stats for team {team_id}: {e}")
        
        # Default stats
        default_stats = {
            'goals_scored': 1.5,
            'goals_conceded': 1.5,
            'xg': 1.5,
            'xga': 1.5,
            'clean_sheets': 0.3,
            'games_played': 0
        }
        return default_stats
    
    def _calculate_custom_fdr(self, opponent_stats: Dict, is_home: bool = True) -> float:
        """
        Calculate custom FDR based on opponent's actual performance stats.
        
        Args:
            opponent_stats: Dictionary with opponent team stats
            is_home: Whether the fixture is at home
        
        Returns:
            FDR rating (1-5 scale, where 1=easiest, 5=hardest)
        """
        # Base FDR on opponent's strength
        # For attacking FDR: use opponent's defensive weakness (goals conceded, xGA)
        # For defensive FDR: use opponent's attacking weakness (goals scored, xG)
        
        # Normalize stats to 1-5 scale
        # Higher goals conceded/xGA = easier attacking fixture (lower FDR)
        # Higher goals scored/xG = harder defensive fixture (higher FDR)
        
        # Average of goals conceded and xGA for attacking difficulty
        defensive_weakness = (opponent_stats.get('goals_conceded', 1.5) + 
                            opponent_stats.get('xga', 1.5)) / 2
        
        # Average of goals scored and xG for defensive difficulty
        attacking_strength = (opponent_stats.get('goals_scored', 1.5) + 
                            opponent_stats.get('xg', 1.5)) / 2
        
        # Convert to FDR scale (1-5)
        # Teams conceding more = easier fixture (lower FDR)
        # Teams scoring more = harder fixture (higher FDR)
        
        # Inverse relationship: more goals conceded = lower FDR (easier)
        attacking_fdr = 5 - min(4, defensive_weakness * 1.2)  # Scale to 1-5
        
        # Direct relationship: more goals scored = higher FDR (harder)
        defensive_fdr = min(5, 1 + attacking_strength * 1.2)  # Scale to 1-5
        
        # Average for general FDR
        general_fdr = (attacking_fdr + defensive_fdr) / 2
        
        # Home advantage adjustment
        if is_home:
            general_fdr = max(1, general_fdr - 0.3)  # Slightly easier at home
        else:
            general_fdr = min(5, general_fdr + 0.3)  # Slightly harder away
        
        return round(general_fdr, 2)
    
    def calculate_fixture_difficulty(self, players_df: pd.DataFrame, gameweek: int, relevant_team_ids: set = None, all_fixtures: List[Dict] = None, bootstrap_data: Dict = None) -> pd.DataFrame:
        """
        Calculate comprehensive fixture difficulty ratings for all players.
        Optimized to only process relevant teams to avoid slow iterations.
        
        Args:
            players_df: DataFrame with player data
            gameweek: Current gameweek
            relevant_team_ids: Optional set of team IDs to process (for performance)
            all_fixtures: Optional pre-loaded all fixtures list (for performance)
            bootstrap_data: Optional pre-loaded bootstrap data (for performance)
        
        Returns:
            DataFrame with added fixture difficulty columns
        """
        df = players_df.copy()
        
        # Use pre-loaded fixtures or load if not provided (PERFORMANCE OPTIMIZATION)
        if all_fixtures is None:
            all_fixtures = self.api_client.get_fixtures()
        fixtures_df = pd.DataFrame(all_fixtures)
        
        # Use pre-loaded bootstrap or load if not provided (PERFORMANCE OPTIMIZATION)
        if bootstrap_data is None:
            bootstrap_data = self.api_client.get_bootstrap_static()
        teams_df = pd.DataFrame(bootstrap_data['teams'])
        team_map = teams_df.set_index('id')['name'].to_dict()
        
        # Initialize new columns with defaults
        df['fdr_custom'] = 3.0
        df['fdr_home'] = 3.0
        df['fdr_away'] = 3.0
        df['fdr_defensive'] = 3.0
        df['fdr_attacking'] = 3.0
        df['fdr_3gw'] = 3.0
        df['fdr_5gw'] = 3.0
        df['fdr_8gw'] = 3.0
        
        # Get unique teams to process (only relevant ones if specified for performance)
        if relevant_team_ids:
            teams_to_process = relevant_team_ids
            # Filter df to only relevant teams
            df = df[df['team'].isin(teams_to_process)].copy()
        else:
            # If not specified, process all teams but limit to top players for performance
            # Only process players with reasonable price (>4.0) or total points (>20) to avoid processing all 758 players
            df = df[(df['now_cost'] >= 40) | (df.get('total_points', 0) >= 20)].copy()
            teams_to_process = set(df['team'].dropna().unique())
        
        # Pre-calculate team stats for all opponents (cache to avoid redundant calls)
        opponent_stats_cache = {}
        
        # Vectorized approach: calculate once per team, then apply to all players on that team
        team_fdr_data = {}
        
        for team_id in teams_to_process:
            if pd.isna(team_id):
                continue
            team_id = int(team_id)
            
            # Get next fixture
            next_fixture = fixtures_df[
                ((fixtures_df['team_h'] == team_id) | (fixtures_df['team_a'] == team_id)) &
                (fixtures_df['event'] >= gameweek)
            ].sort_values('event').head(1)
            
            if next_fixture.empty:
                continue
            
            fixture = next_fixture.iloc[0]
            is_home = fixture['team_h'] == team_id
            opponent_id = fixture['team_a'] if is_home else fixture['team_h']
            
            # Get opponent stats (with caching)
            if opponent_id not in opponent_stats_cache:
                opponent_stats_cache[opponent_id] = self._get_team_stats(opponent_id, gameweek)
            opponent_stats = opponent_stats_cache[opponent_id]
            
            # Calculate custom FDR
            custom_fdr = self._calculate_custom_fdr(opponent_stats, is_home)
            fdr_home = self._calculate_custom_fdr(opponent_stats, is_home=True)
            fdr_away = self._calculate_custom_fdr(opponent_stats, is_home=False)
            
            # Defensive vs Attacking FDR
            attacking_strength = (opponent_stats.get('goals_scored', 1.5) + 
                                 opponent_stats.get('xg', 1.5)) / 2
            defensive_fdr = min(5, 1 + attacking_strength * 1.2)
            
            defensive_weakness = (opponent_stats.get('goals_conceded', 1.5) + 
                                opponent_stats.get('xga', 1.5)) / 2
            attacking_fdr = 5 - min(4, defensive_weakness * 1.2)
            
            # Rolling fixture difficulty (next 3, 5, 8 GWs)
            future_fixtures = fixtures_df[
                ((fixtures_df['team_h'] == team_id) | (fixtures_df['team_a'] == team_id)) &
                (fixtures_df['event'] >= gameweek) &
                (fixtures_df['event'] <= gameweek + 8)
            ].sort_values('event')
            
            fdr_3gw = 3.0
            fdr_5gw = 3.0
            fdr_8gw = 3.0
            
            if not future_fixtures.empty:
                fdr_values = []
                # Vectorized approach: process all future fixtures at once
                for idx in future_fixtures.index:
                    fut_fixture = future_fixtures.loc[idx]
                    fut_is_home = fut_fixture['team_h'] == team_id
                    fut_opponent_id = fut_fixture['team_a'] if fut_is_home else fut_fixture['team_h']
                    
                    if fut_opponent_id not in opponent_stats_cache:
                        opponent_stats_cache[fut_opponent_id] = self._get_team_stats(fut_opponent_id, gameweek)
                    fut_opponent_stats = opponent_stats_cache[fut_opponent_id]
                    
                    fut_fdr = self._calculate_custom_fdr(fut_opponent_stats, fut_is_home)
                    fdr_values.append((fut_fixture['event'], fut_fdr))
                
                # Calculate weighted averages
                if len(fdr_values) >= 3:
                    weights_3 = [1.0, 0.8, 0.6][:len(fdr_values[:3])]
                    fdr_3gw = np.average([f[1] for f in fdr_values[:3]], weights=weights_3)
                
                if len(fdr_values) >= 5:
                    weights_5 = [1.0, 0.9, 0.8, 0.7, 0.6][:len(fdr_values[:5])]
                    fdr_5gw = np.average([f[1] for f in fdr_values[:5]], weights=weights_5)
                
                if len(fdr_values) >= 8:
                    weights_8 = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65][:len(fdr_values[:8])]
                    fdr_8gw = np.average([f[1] for f in fdr_values[:8]], weights=weights_8)
            
            # Store FDR data for this team
            team_fdr_data[team_id] = {
                'fdr_custom': round(custom_fdr, 2),
                'fdr_home': round(fdr_home, 2),
                'fdr_away': round(fdr_away, 2),
                'fdr_defensive': round(defensive_fdr, 2),
                'fdr_attacking': round(attacking_fdr, 2),
                'fdr_3gw': round(fdr_3gw, 2),
                'fdr_5gw': round(fdr_5gw, 2),
                'fdr_8gw': round(fdr_8gw, 2)
            }
        
        # Apply FDR data to all players (vectorized)
        for team_id, fdr_data in team_fdr_data.items():
            mask = df['team'] == team_id
            for col, val in fdr_data.items():
                df.loc[mask, col] = val
        
        # Merge back to original dataframe to preserve all players
        if relevant_team_ids or len(df) < len(players_df):
            # Merge FDR columns back to original df using team mapping (avoid duplicate index issue)
            players_df = players_df.copy()
            # Create a mapping from team_id to FDR values (use first value per team since all players on same team have same FDR)
            team_fdr_map = {}
            for team_id, fdr_data in team_fdr_data.items():
                team_fdr_map[team_id] = fdr_data
            
            for col in ['fdr_custom', 'fdr_home', 'fdr_away', 'fdr_defensive', 'fdr_attacking', 'fdr_3gw', 'fdr_5gw', 'fdr_8gw']:
                players_df[col] = players_df['team'].apply(
                    lambda tid: team_fdr_map.get(int(tid), {}).get(col, 3.0) if pd.notna(tid) else 3.0
                )
            df = players_df
        
        logger.info(f"Calculated custom FDR for {len(teams_to_process)} teams ({len(df)} players)")
        return df


class FixtureCongestionTracker:
    """
    Tracks fixture congestion, rest days, and travel distance for rotation risk.
    """
    
    def __init__(self, api_client: FPLAPIClient):
        """
        Initialize congestion tracker.
        
        Args:
            api_client: FPL API client instance
        """
        self.api_client = api_client
        
    def _get_fixture_dates(self, fixtures_df: pd.DataFrame) -> Dict[int, List[datetime]]:
        """
        Extract fixture dates for each team.
        
        Args:
            fixtures_df: DataFrame with fixtures
        
        Returns:
            Dictionary mapping team_id to list of fixture dates
        """
        team_dates = {}
        
        # Vectorized approach: process all fixtures at once
        for idx in fixtures_df.index:
            fixture = fixtures_df.loc[idx]
            kickoff_time = fixture.get('kickoff_time')
            if pd.isna(kickoff_time) or not kickoff_time:
                continue
            
            try:
                fixture_date = pd.to_datetime(kickoff_time)
                # Normalize to timezone-naive
                if hasattr(fixture_date, 'tzinfo') and fixture_date.tzinfo:
                    fixture_date = fixture_date.replace(tzinfo=None)
                elif isinstance(fixture_date, pd.Timestamp) and fixture_date.tz is not None:
                    fixture_date = fixture_date.tz_localize(None)
                
                team_h = fixture.get('team_h')
                team_a = fixture.get('team_a')
                
                if team_h not in team_dates:
                    team_dates[team_h] = []
                if team_a not in team_dates:
                    team_dates[team_a] = []
                
                team_dates[team_h].append(fixture_date)
                team_dates[team_a].append(fixture_date)
            except:
                continue
        
        # Sort dates for each team
        for team_id in team_dates:
            team_dates[team_id].sort()
        
        return team_dates
    
    def calculate_congestion(self, players_df: pd.DataFrame, gameweek: int, relevant_team_ids: set = None, all_fixtures: List[Dict] = None) -> pd.DataFrame:
        """
        Calculate fixture congestion metrics for all players.
        Optimized to process by team instead of by player for performance.
        
        Args:
            players_df: DataFrame with player data
            gameweek: Current gameweek
            relevant_team_ids: Optional set of team IDs to process (for performance)
            all_fixtures: Optional pre-loaded all fixtures list (for performance)
        
        Returns:
            DataFrame with added congestion columns
        """
        df = players_df.copy()
        
        # Use pre-loaded fixtures or load if not provided (PERFORMANCE OPTIMIZATION)
        if all_fixtures is None:
            all_fixtures = self.api_client.get_fixtures()
        fixtures_df = pd.DataFrame(all_fixtures)
        
        # Filter to next 14 days from current date (timezone-naive)
        current_date = datetime.now().replace(tzinfo=None)
        future_date = current_date + timedelta(days=14)
        
        # Get fixture dates
        team_dates = self._get_fixture_dates(fixtures_df)
        
        # Initialize columns with defaults
        df['games_next_14_days'] = 0
        df['rest_days'] = 7  # Default
        df['rotation_risk'] = 'low'
        df['travel_distance'] = 0
        df['travel_risk'] = 'low'
        
        # Get unique teams to process (only relevant ones if specified for performance)
        if relevant_team_ids:
            teams_to_process = relevant_team_ids
        else:
            # If not specified, process all teams but limit to top players for performance
            df_filtered = df[(df['now_cost'] >= 40) | (df.get('total_points', 0) >= 20)].copy()
            teams_to_process = set(df_filtered['team'].dropna().unique())
        
        # Pre-calculate away fixtures for travel analysis
        away_fixtures_by_team = {}
        for team_id in teams_to_process:
            if pd.isna(team_id):
                continue
            team_id = int(team_id)
            away_fixtures = fixtures_df[
                (fixtures_df['team_a'] == team_id) &
                (fixtures_df['event'] >= gameweek) &
                (fixtures_df['event'] <= gameweek + 3)
            ]
            away_fixtures_by_team[team_id] = len(away_fixtures)
        
        # Calculate congestion metrics once per team, then apply to all players
        team_congestion_data = {}
        
        for team_id in teams_to_process:
            if pd.isna(team_id):
                continue
            team_id = int(team_id)
            
            if team_id not in team_dates:
                continue
            
            # Count games in next 14 days (normalize datetimes to timezone-naive)
            upcoming_dates = []
            for d in team_dates[team_id]:
                # Normalize to timezone-naive for comparison
                d_naive = d.replace(tzinfo=None) if d.tzinfo else d
                if current_date <= d_naive <= future_date:
                    upcoming_dates.append(d_naive)
            
            games_next_14_days = len(upcoming_dates)
            
            # Calculate rest days before next fixture
            rest_days = 7  # Default
            rotation_risk = 'low'
            if upcoming_dates:
                next_fixture_date = upcoming_dates[0]
                # Ensure both are timezone-naive for calculation
                if hasattr(next_fixture_date, 'tzinfo') and next_fixture_date.tzinfo:
                    next_fixture_date = next_fixture_date.replace(tzinfo=None)
                rest_days = max(0, (next_fixture_date - current_date).days)
                
                # Rotation risk based on rest days
                if rest_days < 3:
                    rotation_risk = 'high'
                elif rest_days < 5:
                    rotation_risk = 'medium'
                else:
                    rotation_risk = 'low'
            
            # Travel distance (simplified - flag European away games)
            away_count = away_fixtures_by_team.get(team_id, 0)
            travel_distance = 0
            travel_risk = 'low'
            if away_count >= 3:
                travel_distance = 2
                travel_risk = 'high'
            elif away_count >= 2:
                travel_distance = 1
                travel_risk = 'medium'
            
            # Store congestion data for this team
            team_congestion_data[team_id] = {
                'games_next_14_days': games_next_14_days,
                'rest_days': rest_days,
                'rotation_risk': rotation_risk,
                'travel_distance': travel_distance,
                'travel_risk': travel_risk
            }
        
        # Apply congestion data to all players (vectorized)
        for team_id, congestion_data in team_congestion_data.items():
            mask = df['team'] == team_id
            for col, val in congestion_data.items():
                df.loc[mask, col] = val
        
        # Merge back to original dataframe to preserve all players
        if relevant_team_ids or len(df) < len(players_df):
            # Merge congestion columns back to original df using team mapping
            players_df = players_df.copy()
            team_congestion_map = {}
            for team_id, congestion_data in team_congestion_data.items():
                team_congestion_map[team_id] = congestion_data
            
            for col in ['games_next_14_days', 'rest_days', 'rotation_risk', 'travel_distance', 'travel_risk']:
                if col == 'rotation_risk':
                    # Handle string column
                    players_df[col] = players_df['team'].apply(
                        lambda tid: team_congestion_map.get(int(tid), {}).get(col, 'low') if pd.notna(tid) else 'low'
                    )
                else:
                    # Handle numeric columns
                    players_df[col] = players_df['team'].apply(
                        lambda tid: team_congestion_map.get(int(tid), {}).get(col, 0 if col != 'rest_days' else 7) if pd.notna(tid) else (0 if col != 'rest_days' else 7)
                    )
            df = players_df
        
        logger.info(f"Calculated congestion metrics for {len(teams_to_process)} teams ({len(df)} players)")
        return df


class FixturePredictor:
    """
    Predicts Double Gameweeks (DGW) and Blank Gameweeks (BGW).
    """
    
    def __init__(self, api_client: FPLAPIClient):
        """
        Initialize fixture predictor.
        
        Args:
            api_client: FPL API client instance
        """
        self.api_client = api_client
        
    def predict_dgw_probability(self, gameweek: int, all_fixtures: List[Dict] = None) -> Dict[int, float]:
        """
        Predict probability of double gameweeks for each team.
        
        Args:
            gameweek: Gameweek to analyze
            all_fixtures: Optional pre-loaded all fixtures list (for performance)
        
        Returns:
            Dictionary mapping team_id to DGW probability (0-1)
        """
        dgw_probabilities = {}
        
        try:
            # Use pre-loaded fixtures or load if not provided (PERFORMANCE OPTIMIZATION)
            if all_fixtures is None:
                all_fixtures = self.api_client.get_fixtures()
            fixtures_df = pd.DataFrame(all_fixtures)
            
            # Optimize: pre-filter fixtures for relevant gameweeks
            relevant_gws = range(gameweek, gameweek + 10)
            relevant_fixtures = fixtures_df[fixtures_df['event'].isin(relevant_gws)]
            
            # Vectorized approach: count fixtures per team per gameweek
            for gw in relevant_gws:
                gw_fixtures = relevant_fixtures[relevant_fixtures['event'] == gw]
                
                # Process all fixtures for this gameweek at once
                for idx in gw_fixtures.index:
                    fixture = gw_fixtures.loc[idx]
                    team_h = fixture.get('team_h')
                    team_a = fixture.get('team_a')
                    
                    # Check if team already has a fixture this gameweek (vectorized)
                    team_h_fixtures = gw_fixtures[
                        (gw_fixtures['team_h'] == team_h) | (gw_fixtures['team_a'] == team_h)
                    ]
                    team_a_fixtures = gw_fixtures[
                        (gw_fixtures['team_h'] == team_a) | (gw_fixtures['team_a'] == team_a)
                    ]
                    
                    existing_h = len(team_h_fixtures)
                    existing_a = len(team_a_fixtures)
                    
                    # If team has 2+ fixtures, it's a DGW
                    if existing_h >= 2:
                        dgw_probabilities[team_h] = 1.0
                    elif existing_h == 1:
                        # Potential DGW if postponed matches exist
                        dgw_probabilities[team_h] = dgw_probabilities.get(team_h, 0.0) + 0.1
                    
                    if existing_a >= 2:
                        dgw_probabilities[team_a] = 1.0
                    elif existing_a == 1:
                        dgw_probabilities[team_a] = dgw_probabilities.get(team_a, 0.0) + 0.1
        except Exception as e:
            logger.warning(f"Error predicting DGW: {e}")
        
        # Cap probabilities at 1.0
        for team_id in dgw_probabilities:
            dgw_probabilities[team_id] = min(1.0, dgw_probabilities[team_id])
        
        return dgw_probabilities
    
    def predict_bgw_teams(self, gameweek: int, all_fixtures: List[Dict] = None, bootstrap_data: Dict = None) -> Dict[int, List[int]]:
        """
        Predict teams likely to have blank gameweeks.
        
        Args:
            gameweek: Gameweek to analyze
            all_fixtures: Optional pre-loaded all fixtures list (for performance)
            bootstrap_data: Optional pre-loaded bootstrap data (for performance)
        
        Returns:
            Dictionary mapping gameweek to list of team IDs that will blank
        """
        bgw_teams = {}
        
        try:
            # Use pre-loaded fixtures or load if not provided (PERFORMANCE OPTIMIZATION)
            if all_fixtures is None:
                all_fixtures = self.api_client.get_fixtures()
            fixtures_df = pd.DataFrame(all_fixtures)
            
            # Use pre-loaded bootstrap or load if not provided (PERFORMANCE OPTIMIZATION)
            if bootstrap_data is None:
                bootstrap_data = self.api_client.get_bootstrap_static()
            teams_df = pd.DataFrame(bootstrap_data['teams'])
            all_team_ids = teams_df['id'].tolist()
            
            # Optimize: pre-filter fixtures for relevant gameweeks
            relevant_gws = range(gameweek, gameweek + 10)
            relevant_fixtures = fixtures_df[fixtures_df['event'].isin(relevant_gws)]
            
            # Check each future gameweek (vectorized)
            for gw in relevant_gws:
                gw_fixtures = relevant_fixtures[relevant_fixtures['event'] == gw]
                teams_with_fixtures = set()
                
                # Vectorized approach: collect all teams at once
                if not gw_fixtures.empty:
                    teams_with_fixtures.update(gw_fixtures['team_h'].dropna().unique())
                    teams_with_fixtures.update(gw_fixtures['team_a'].dropna().unique())
                
                # Teams without fixtures = blank gameweek
                blank_teams = [tid for tid in all_team_ids if tid not in teams_with_fixtures]
                
                if blank_teams:
                    bgw_teams[gw] = blank_teams
        except Exception as e:
            logger.warning(f"Error predicting BGW: {e}")
        
        return bgw_teams
    
    def add_dgw_bgw_predictions(self, players_df: pd.DataFrame, gameweek: int, relevant_team_ids: set = None, all_fixtures: List[Dict] = None, bootstrap_data: Dict = None) -> pd.DataFrame:
        """
        Add DGW and BGW probability columns to player DataFrame.
        Optimized to process by team instead of by player for performance.
        
        Args:
            players_df: DataFrame with player data
            gameweek: Current gameweek
            relevant_team_ids: Optional set of team IDs to process (for performance)
            all_fixtures: Optional pre-loaded all fixtures list (for performance)
            bootstrap_data: Optional pre-loaded bootstrap data (for performance)
        
        Returns:
            DataFrame with added DGW/BGW columns
        """
        df = players_df.copy()
        
        # Initialize columns with defaults
        df['dgw_probability'] = 0.0
        df['bgw_probability'] = 0.0
        
        # Get DGW probabilities (pass pre-loaded data)
        dgw_probs = self.predict_dgw_probability(gameweek, all_fixtures=all_fixtures)
        
        # Get BGW teams (pass pre-loaded data)
        bgw_teams = self.predict_bgw_teams(gameweek, all_fixtures=all_fixtures, bootstrap_data=bootstrap_data)
        all_bgw_teams = set()
        for gw, teams in bgw_teams.items():
            all_bgw_teams.update(teams)
        
        # Get unique teams to process (only relevant ones if specified for performance)
        if relevant_team_ids:
            teams_to_process = relevant_team_ids
        else:
            # If not specified, process all teams but limit to top players for performance
            df_filtered = df[(df['now_cost'] >= 40) | (df.get('total_points', 0) >= 20)].copy()
            teams_to_process = set(df_filtered['team'].dropna().unique())
        
        # Calculate DGW/BGW probabilities once per team, then apply to all players
        team_dgw_bgw_data = {}
        
        for team_id in teams_to_process:
            if pd.isna(team_id):
                continue
            team_id = int(team_id)
            
            # DGW probability
            dgw_prob = dgw_probs.get(team_id, 0.0)
            
            # BGW probability (1.0 if team will blank, 0.0 otherwise)
            bgw_prob = 1.0 if team_id in all_bgw_teams else 0.0
            
            # Store DGW/BGW data for this team
            team_dgw_bgw_data[team_id] = {
                'dgw_probability': dgw_prob,
                'bgw_probability': bgw_prob
            }
        
        # Apply DGW/BGW data to all players (vectorized)
        for team_id, dgw_bgw_data in team_dgw_bgw_data.items():
            mask = df['team'] == team_id
            for col, val in dgw_bgw_data.items():
                df.loc[mask, col] = val
        
        # Merge back to original dataframe to preserve all players
        if relevant_team_ids or len(df) < len(players_df):
            # Merge DGW/BGW columns back to original df using team mapping
            players_df = players_df.copy()
            team_dgw_bgw_map = {}
            for team_id, dgw_bgw_data in team_dgw_bgw_data.items():
                team_dgw_bgw_map[team_id] = dgw_bgw_data
            
            for col in ['dgw_probability', 'bgw_probability']:
                players_df[col] = players_df['team'].apply(
                    lambda tid: team_dgw_bgw_map.get(int(tid), {}).get(col, 0.0) if pd.notna(tid) else 0.0
                )
            df = players_df
        
        logger.info(f"Added DGW/BGW predictions for {len(teams_to_process)} teams ({len(df)} players)")
        return df

