"""
Advanced Statistical Models for FPL Analysis
Includes form models, team tactics analysis, and injury/fatigue predictions.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from fpl_api import FPLAPIClient

logger = logging.getLogger(__name__)


class PlayerFormModel:
    """
    Advanced player form analysis including momentum, regression to mean, and matchup analysis.
    """
    
    def __init__(self, api_client: FPLAPIClient, db_manager=None):
        """
        Initialize player form model.
        
        Args:
            api_client: FPL API client instance
            db_manager: Optional database manager for historical data
        """
        self.api_client = api_client
        self.db_manager = db_manager
        self.form_cache = {}
        
    def detect_momentum(self, player_id: int, gameweek: int, window: int = 5, history_df: pd.DataFrame = None) -> Dict:
        """
        Detect if player is entering a hot streak using Poisson regression on recent xG.
        
        Args:
            player_id: Player ID
            gameweek: Current gameweek
            window: Number of recent games to analyze
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            Dictionary with momentum score, trend, and streak status
        """
        try:
            # Use provided history_df or load if not provided (backward compatibility)
            if history_df is None:
                if self.db_manager:
                    history_df = self.db_manager.get_current_season_history()
                else:
                    history_df = pd.DataFrame()
            
            if not history_df.empty:
                player_history = history_df[
                    (history_df['player_id'] == player_id) &
                    (history_df['gw'] < gameweek)
                ].sort_values('gw', ascending=False).head(window)
                
                if len(player_history) >= 3 and 'xg' in player_history.columns:
                    xg_values = player_history['xg'].fillna(0).values
                    points_values = player_history['total_points'].fillna(0).values
                    
                    # Simple momentum: trend in xG and points
                    xg_trend = np.polyfit(range(len(xg_values)), xg_values, 1)[0] if len(xg_values) > 1 else 0
                    points_trend = np.polyfit(range(len(points_values)), points_values, 1)[0] if len(points_values) > 1 else 0
                    
                    # Momentum score (0-1, higher = stronger momentum)
                    momentum_score = min(1.0, max(0.0, (xg_trend * 2 + points_trend * 0.5) / 2))
                    
                    # Streak detection: consecutive games with points
                    recent_points = points_values[:3] if len(points_values) >= 3 else points_values
                    streak_count = sum(1 for p in recent_points if p > 0)
                    is_hot_streak = streak_count >= 2 and momentum_score > 0.3
                    
                    return {
                        'momentum_score': round(momentum_score, 3),
                        'xg_trend': round(xg_trend, 3),
                        'points_trend': round(points_trend, 3),
                        'is_hot_streak': is_hot_streak,
                        'streak_games': streak_count
                    }
        except Exception as e:
            logger.debug(f"Error detecting momentum for player {player_id}: {e}")
        
        return {
            'momentum_score': 0.5,
            'xg_trend': 0.0,
            'points_trend': 0.0,
            'is_hot_streak': False,
            'streak_games': 0
        }
    
    def detect_regression_to_mean(self, player_id: int, gameweek: int, history_df: pd.DataFrame = None) -> Dict:
        """
        Flag players overperforming xG (likely to cool off).
        
        Args:
            player_id: Player ID
            gameweek: Current gameweek
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            Dictionary with regression risk and overperformance metrics
        """
        try:
            # Use provided history_df or load if not provided (backward compatibility)
            if history_df is None:
                if self.db_manager:
                    history_df = self.db_manager.get_current_season_history()
                else:
                    history_df = pd.DataFrame()
            
            if not history_df.empty:
                player_history = history_df[
                    (history_df['player_id'] == player_id) &
                    (history_df['gw'] < gameweek)
                ].sort_values('gw', ascending=False)
                
                if len(player_history) >= 5 and 'xg' in player_history.columns and 'goals_scored' in player_history.columns:
                    recent = player_history.head(5)
                    season = player_history
                    
                    # Recent performance vs xG
                    recent_xg = recent['xg'].fillna(0).sum()
                    recent_goals = recent['goals_scored'].fillna(0).sum()
                    
                    # Season average
                    season_xg = season['xg'].fillna(0).mean()
                    season_goals = season['goals_scored'].fillna(0).mean()
                    
                    # Overperformance ratio
                    if recent_xg > 0:
                        xg_conversion = recent_goals / recent_xg
                        season_conversion = season_goals / season_xg if season_xg > 0 else 1.0
                        overperformance_ratio = xg_conversion / season_conversion if season_conversion > 0 else 1.0
                    else:
                        overperformance_ratio = 1.0
                    
                    # Regression risk (higher if overperforming significantly)
                    regression_risk = min(1.0, max(0.0, (overperformance_ratio - 1.0) * 2))
                    is_overperforming = overperformance_ratio > 1.2
                    
                    return {
                        'regression_risk': round(regression_risk, 3),
                        'overperformance_ratio': round(overperformance_ratio, 3),
                        'is_overperforming': is_overperforming,
                        'recent_goals_vs_xg': round(recent_goals - recent_xg, 2)
                    }
        except Exception as e:
            logger.debug(f"Error detecting regression for player {player_id}: {e}")
        
        return {
            'regression_risk': 0.0,
            'overperformance_ratio': 1.0,
            'is_overperforming': False,
            'recent_goals_vs_xg': 0.0
        }
    
    def analyze_matchup(self, player_id: int, opponent_team_id: int, gameweek: int, history_df: pd.DataFrame = None) -> Dict:
        """
        Analyze player's historical performance vs specific opponent.
        
        Args:
            player_id: Player ID
            opponent_team_id: Opponent team ID
            gameweek: Current gameweek
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            Dictionary with matchup stats and performance vs opponent
        """
        try:
            # Use provided history_df or load if not provided (backward compatibility)
            if history_df is None:
                if self.db_manager:
                    history_df = self.db_manager.get_current_season_history()
                else:
                    history_df = pd.DataFrame()
            
            if not history_df.empty:
                # Get player's games vs this opponent
                player_history = history_df[
                    (history_df['player_id'] == player_id) &
                    (history_df['gw'] < gameweek)
                ]
                
                if 'opponent_team' in player_history.columns:
                    vs_opponent = player_history[player_history['opponent_team'] == opponent_team_id]
                    
                    if len(vs_opponent) > 0:
                        avg_points = vs_opponent['total_points'].fillna(0).mean()
                        avg_goals = vs_opponent['goals_scored'].fillna(0).mean()
                        avg_assists = vs_opponent['assists'].fillna(0).mean()
                        
                        # Compare to overall average
                        overall_avg = player_history['total_points'].fillna(0).mean()
                        matchup_factor = avg_points / overall_avg if overall_avg > 0 else 1.0
                        
                        return {
                            'matchup_avg_points': round(avg_points, 2),
                            'matchup_avg_goals': round(avg_goals, 2),
                            'matchup_avg_assists': round(avg_assists, 2),
                            'matchup_factor': round(matchup_factor, 3),
                            'games_vs_opponent': len(vs_opponent),
                            'is_favorable_matchup': matchup_factor > 1.1
                        }
        except Exception as e:
            logger.debug(f"Error analyzing matchup for player {player_id} vs team {opponent_team_id}: {e}")
        
        return {
            'matchup_avg_points': 0.0,
            'matchup_avg_goals': 0.0,
            'matchup_avg_assists': 0.0,
            'matchup_factor': 1.0,
            'games_vs_opponent': 0,
            'is_favorable_matchup': False
        }
    
    def analyze_home_away_splits(self, player_id: int, gameweek: int, history_df: pd.DataFrame = None) -> Dict:
        """
        Analyze player performance at home vs away.
        
        Args:
            player_id: Player ID
            gameweek: Current gameweek
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            Dictionary with home/away performance splits
        """
        try:
            # Use provided history_df or load if not provided (backward compatibility)
            if history_df is None:
                if self.db_manager:
                    history_df = self.db_manager.get_current_season_history()
                else:
                    history_df = pd.DataFrame()
            
            if not history_df.empty:
                player_history = history_df[
                    (history_df['player_id'] == player_id) &
                    (history_df['gw'] < gameweek)
                ]
                
                if 'was_home' in player_history.columns:
                    home_games = player_history[player_history['was_home'] == True]
                    away_games = player_history[player_history['was_home'] == False]
                    
                    if len(home_games) > 0 and len(away_games) > 0:
                        home_avg_points = home_games['total_points'].fillna(0).mean()
                        away_avg_points = away_games['total_points'].fillna(0).mean()
                        
                        home_avg_goals = home_games['goals_scored'].fillna(0).mean()
                        away_avg_goals = away_games['goals_scored'].fillna(0).mean()
                        
                        home_factor = home_avg_points / away_avg_points if away_avg_points > 0 else 1.0
                        
                        return {
                            'home_avg_points': round(home_avg_points, 2),
                            'away_avg_points': round(away_avg_points, 2),
                            'home_avg_goals': round(home_avg_goals, 2),
                            'away_avg_goals': round(away_avg_goals, 2),
                            'home_advantage_factor': round(home_factor, 3),
                            'is_home_specialist': home_factor > 1.3
                        }
        except Exception as e:
            logger.debug(f"Error analyzing home/away splits for player {player_id}: {e}")
        
        return {
            'home_avg_points': 0.0,
            'away_avg_points': 0.0,
            'home_avg_goals': 0.0,
            'away_avg_goals': 0.0,
            'home_advantage_factor': 1.0,
            'is_home_specialist': False
        }
    
    def add_form_analysis(self, players_df: pd.DataFrame, gameweek: int, fixtures: List[Dict] = None, relevant_player_ids: set = None, bootstrap_data: Dict = None, history_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Add comprehensive form analysis to player DataFrame.
        Optimized to only process relevant players for performance.
        
        Args:
            players_df: DataFrame with player data
            gameweek: Current gameweek
            fixtures: Optional list of fixtures for matchup analysis
            relevant_player_ids: Optional set of player IDs to process (for performance)
            bootstrap_data: Optional pre-loaded bootstrap data (for performance, not used here but for consistency)
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            DataFrame with added form analysis columns
        """
        df = players_df.copy()
        
        # Initialize columns with defaults
        df['momentum_score'] = 0.5
        df['is_hot_streak'] = False
        df['regression_risk'] = 0.0
        df['is_overperforming'] = False
        df['home_advantage_factor'] = 1.0
        df['is_home_specialist'] = False
        df['matchup_factor'] = 1.0
        df['is_favorable_matchup'] = False
        
        # Filter to relevant players if specified
        if relevant_player_ids:
            df_to_process = df[df['id'].isin(relevant_player_ids)].copy()
        else:
            # Limit to top 100 players by price/points for performance
            df_to_process = df.nlargest(100, ['now_cost', 'total_points'], keep='all').copy()
        
        # Get next fixture for matchup analysis
        if fixtures is None:
            try:
                fixtures = self.api_client.get_fixtures_for_gameweek(gameweek)
            except:
                fixtures = []
        
        # Create fixture lookup
        fixture_lookup = {}
        for f in fixtures:
            fixture_lookup[f.get('team_h')] = f.get('team_a')
            fixture_lookup[f.get('team_a')] = f.get('team_h')
        
        # Use pre-loaded history or load if not provided (PERFORMANCE OPTIMIZATION: avoid redundant database queries)
        if history_df is None and self.db_manager:
            try:
                history_df = self.db_manager.get_current_season_history()
                if history_df.empty:
                    history_df = None
            except Exception as e:
                logger.debug(f"Could not load history for form analysis: {e}")
                history_df = None
        
        # Process only relevant players (iterrows is necessary here for individual player analysis)
        for idx in df_to_process.index:
            player = df_to_process.loc[idx]
            player_id = player.get('id')
            if pd.isna(player_id):
                continue
            
            player_id = int(player_id)
            
            # Momentum detection
            momentum = self.detect_momentum(player_id, gameweek, history_df=history_df)
            df.at[idx, 'momentum_score'] = momentum['momentum_score']
            df.at[idx, 'is_hot_streak'] = momentum['is_hot_streak']
            
            # Regression to mean
            regression = self.detect_regression_to_mean(player_id, gameweek, history_df=history_df)
            df.at[idx, 'regression_risk'] = regression['regression_risk']
            df.at[idx, 'is_overperforming'] = regression['is_overperforming']
            
            # Home/away splits
            splits = self.analyze_home_away_splits(player_id, gameweek, history_df=history_df)
            df.at[idx, 'home_advantage_factor'] = splits['home_advantage_factor']
            df.at[idx, 'is_home_specialist'] = splits['is_home_specialist']
            
            # Matchup analysis (if fixture available)
            team_id = player.get('team')
            if not pd.isna(team_id) and int(team_id) in fixture_lookup:
                opponent_id = fixture_lookup[int(team_id)]
                matchup = self.analyze_matchup(player_id, opponent_id, gameweek, history_df=history_df)
                df.at[idx, 'matchup_factor'] = matchup['matchup_factor']
                df.at[idx, 'is_favorable_matchup'] = matchup['is_favorable_matchup']
        
        logger.info(f"Added form analysis for {len(df_to_process)} relevant players")
        return df


class TeamTacticsAnalyzer:
    """
    Analyzes team tactics including formations, set pieces, and underlying stats trends.
    """
    
    def __init__(self, api_client: FPLAPIClient, db_manager=None):
        """
        Initialize team tactics analyzer.
        
        Args:
            api_client: FPL API client instance
            db_manager: Optional database manager for historical data
        """
        self.api_client = api_client
        self.db_manager = db_manager
        
    def analyze_underlying_stats_trends(self, team_id: int, gameweek: int, history_df: pd.DataFrame = None, bootstrap_data: Dict = None) -> Dict:
        """
        Analyze team xG/xGA trends over last 5 games vs season average.
        
        Args:
            team_id: Team ID
            gameweek: Current gameweek
            history_df: Optional pre-loaded history DataFrame (for performance)
            bootstrap_data: Optional pre-loaded bootstrap data (for performance)
        
        Returns:
            Dictionary with trend analysis
        """
        try:
            # Use pre-loaded history or load if not provided (PERFORMANCE OPTIMIZATION)
            if history_df is None and self.db_manager:
                history_df = self.db_manager.get_current_season_history()
            
            if history_df is not None and not history_df.empty:
                    # Use pre-loaded bootstrap or load if not provided (PERFORMANCE OPTIMIZATION)
                    if bootstrap_data is None:
                        bootstrap_data = self.api_client.get_bootstrap_static()
                    players_df = pd.DataFrame(bootstrap_data['elements'])
                    team_players = players_df[players_df['team'] == team_id]['id'].tolist()
                    
                    if team_players:
                        team_history = history[
                            (history['player_id'].isin(team_players)) &
                            (history['gw'] < gameweek)
                        ]
                        
                        if len(team_history) >= 5:
                            # Recent 5 games
                            recent_gws = sorted(team_history['gw'].unique(), reverse=True)[:5]
                            recent_history = team_history[team_history['gw'].isin(recent_gws)]
                            
                            # Season average
                            season_history = team_history
                            
                            # Aggregate team stats
                            recent_xg = recent_history['xg'].fillna(0).sum() / len(recent_gws) if len(recent_gws) > 0 else 0
                            recent_xga = recent_history.get('xga', pd.Series([0] * len(recent_history))).sum() / len(recent_gws) if len(recent_gws) > 0 else 0
                            
                            season_xg = season_history['xg'].fillna(0).sum() / len(season_history['gw'].unique()) if len(season_history['gw'].unique()) > 0 else 0
                            season_xga = season_history.get('xga', pd.Series([0] * len(season_history))).sum() / len(season_history['gw'].unique()) if len(season_history['gw'].unique()) > 0 else 0
                            
                            xg_trend = (recent_xg - season_xg) / season_xg if season_xg > 0 else 0
                            xga_trend = (recent_xga - season_xga) / season_xga if season_xga > 0 else 0
                            
                            return {
                                'xg_trend': round(xg_trend, 3),
                                'xga_trend': round(xga_trend, 3),
                                'recent_xg_per_game': round(recent_xg, 2),
                                'season_xg_per_game': round(season_xg, 2),
                                'is_improving_attack': xg_trend > 0.1,
                                'is_improving_defence': xga_trend < -0.1
                            }
        except Exception as e:
            logger.debug(f"Error analyzing underlying stats for team {team_id}: {e}")
        
        return {
            'xg_trend': 0.0,
            'xga_trend': 0.0,
            'recent_xg_per_game': 0.0,
            'season_xg_per_game': 0.0,
            'is_improving_attack': False,
            'is_improving_defence': False
        }
    
    def analyze_set_piece_takers(self, team_id: int, bootstrap_data: Dict = None) -> Dict:
        """
        Track set piece takers (corners/free kicks) for assist potential.
        
        Args:
            team_id: Team ID
            bootstrap_data: Optional pre-loaded bootstrap data (for performance)
        
        Returns:
            Dictionary with set piece taker information
        """
        try:
            # Use provided bootstrap_data or load if not provided (backward compatibility)
            if bootstrap_data is None:
                bootstrap_data = self.api_client.get_bootstrap_static()
            
            players_df = pd.DataFrame(bootstrap_data['elements'])
            team_players = players_df[players_df['team'] == team_id]
            
            # Use corners_order and free_kicks_order from FPL API if available
            # Fallback: identify by position and selected percentage
            set_piece_candidates = team_players[
                (team_players['element_type'].isin([2, 3])) &  # DEF, MID
                (team_players['selected_by_percent'].astype(float) > 5.0)
            ].sort_values('selected_by_percent', ascending=False)
            
            if not set_piece_candidates.empty:
                primary_taker = set_piece_candidates.iloc[0]
                return {
                    'primary_set_piece_taker': primary_taker.get('web_name', 'Unknown'),
                    'set_piece_taker_id': int(primary_taker.get('id', 0)),
                    'has_set_piece_taker': True
                }
        except Exception as e:
            logger.debug(f"Error analyzing set piece takers for team {team_id}: {e}")
        
        return {
            'primary_set_piece_taker': None,
            'set_piece_taker_id': 0,
            'has_set_piece_taker': False
        }
    
    def add_team_tactics_analysis(self, players_df: pd.DataFrame, gameweek: int, relevant_player_ids: set = None, bootstrap_data: Dict = None, history_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Add team tactics analysis to player DataFrame.
        Optimized to only process relevant players for performance.
        
        Args:
            players_df: DataFrame with player data
            gameweek: Current gameweek
            relevant_player_ids: Optional set of player IDs to process (for performance)
            bootstrap_data: Optional pre-loaded bootstrap data (for performance)
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            DataFrame with added tactics columns
        """
        df = players_df.copy()
        
        # Initialize columns with defaults
        df['team_xg_trend'] = 0.0
        df['team_xga_trend'] = 0.0
        df['is_improving_attack'] = False
        df['is_improving_defence'] = False
        df['is_set_piece_taker'] = False
        
        # Filter to relevant players if specified
        if relevant_player_ids:
            df_to_process = df[df['id'].isin(relevant_player_ids)].copy()
        else:
            # Limit to top 100 players for performance
            df_to_process = df.nlargest(100, ['now_cost', 'total_points'], keep='all').copy()
        
        # Use pre-loaded bootstrap or load if not provided (PERFORMANCE OPTIMIZATION: avoid redundant API calls)
        if bootstrap_data is None:
            try:
                bootstrap_data = self.api_client.get_bootstrap_static()
            except Exception as e:
                logger.debug(f"Could not load bootstrap for tactics analysis: {e}")
                bootstrap_data = None
        
        # Analyze by team (only process teams with relevant players)
        teams_analyzed = set()
        for idx in df_to_process.index:
            player = df_to_process.loc[idx]
            team_id = player.get('team')
            if pd.isna(team_id):
                continue
            
            team_id = int(team_id)
            
            if team_id not in teams_analyzed:
                # Underlying stats trends (pass pre-loaded data)
                trends = self.analyze_underlying_stats_trends(team_id, gameweek, history_df=history_df, bootstrap_data=bootstrap_data)
                
                # Set piece takers (pass bootstrap_data to avoid redundant API calls)
                set_pieces = self.analyze_set_piece_takers(team_id, bootstrap_data)
                
                # Apply to all players from this team
                team_mask = df['team'] == team_id
                df.loc[team_mask, 'team_xg_trend'] = trends['xg_trend']
                df.loc[team_mask, 'team_xga_trend'] = trends['xga_trend']
                df.loc[team_mask, 'is_improving_attack'] = trends['is_improving_attack']
                df.loc[team_mask, 'is_improving_defence'] = trends['is_improving_defence']
                
                # Mark set piece taker
                if set_pieces['set_piece_taker_id'] > 0:
                    df.loc[df['id'] == set_pieces['set_piece_taker_id'], 'is_set_piece_taker'] = True
                
                teams_analyzed.add(team_id)
        
        logger.info(f"Added team tactics analysis for {len(teams_analyzed)} teams")
        return df


class InjuryRiskModel:
    """
    Predicts injury risk and minutes distribution for players.
    """
    
    def __init__(self, api_client: FPLAPIClient, db_manager=None):
        """
        Initialize injury risk model.
        
        Args:
            api_client: FPL API client instance
            db_manager: Optional database manager for historical data
        """
        self.api_client = api_client
        self.db_manager = db_manager
        
    def predict_injury_risk(self, player_id: int, gameweek: int, players_df: pd.DataFrame = None, history_df: pd.DataFrame = None) -> Dict:
        """
        Predict probability of injury in next 3 gameweeks.
        
        Args:
            player_id: Player ID
            gameweek: Current gameweek
            players_df: Optional DataFrame with player data for age/position
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            Dictionary with injury risk probability and factors
        """
        try:
            risk_factors = []
            base_risk = 0.05  # Base 5% injury risk
            
            # Get player info
            if players_df is not None:
                player = players_df[players_df['id'] == player_id]
                if not player.empty:
                    player = player.iloc[0]
                    age = player.get('age', 25)
                    position = player.get('element_type', 3)
                    status = player.get('status', 'a')
                    chance_playing = player.get('chance_of_playing_this_round', 100)
                    
                    # Age factor (older = higher risk)
                    if age > 30:
                        age_risk = (age - 30) * 0.01
                        risk_factors.append(('age', age_risk))
                    
                    # Position factor (forwards/midfielders more injury-prone)
                    if position in [3, 4]:  # MID, FWD
                        position_risk = 0.02
                        risk_factors.append(('position', position_risk))
                    
                    # Current status
                    if status == 'd' or chance_playing < 75:
                        status_risk = 0.15
                        risk_factors.append(('current_status', status_risk))
            
            # Minutes played factor (from history)
            # Use provided history_df or load if not provided (backward compatibility)
            if history_df is None:
                if self.db_manager:
                    history_df = self.db_manager.get_current_season_history()
                else:
                    history_df = pd.DataFrame()
            
            if not history_df.empty:
                player_history = history_df[
                    (history_df['player_id'] == player_id) &
                    (history_df['gw'] < gameweek)
                ].sort_values('gw', ascending=False).head(5)
                
                if len(player_history) > 0:
                    recent_mins = player_history['minutes'].fillna(0).mean()
                    total_mins = player_history['minutes'].fillna(0).sum()
                    
                    # High recent minutes = fatigue risk
                    if recent_mins > 85:
                        fatigue_risk = 0.03
                        risk_factors.append(('high_minutes', fatigue_risk))
                    
                    # Very high season total = overuse risk
                    if total_mins > 2000:
                        overuse_risk = 0.02
                        risk_factors.append(('overuse', overuse_risk))
            
            # Calculate total risk
            total_risk = base_risk + sum(factor[1] for factor in risk_factors)
            total_risk = min(1.0, max(0.0, total_risk))  # Cap at 0-1
            
            return {
                'injury_risk': round(total_risk, 3),
                'base_risk': base_risk,
                'risk_factors': [f[0] for f in risk_factors],
                'risk_level': 'high' if total_risk > 0.15 else 'medium' if total_risk > 0.10 else 'low'
            }
        except Exception as e:
            logger.debug(f"Error predicting injury risk for player {player_id}: {e}")
        
        return {
            'injury_risk': 0.05,
            'base_risk': 0.05,
            'risk_factors': [],
            'risk_level': 'low'
        }
    
    def predict_minutes_distribution(self, player_id: int, gameweek: int, players_df: pd.DataFrame = None, history_df: pd.DataFrame = None) -> Dict:
        """
        Predict expected minutes per gameweek for squad rotation.
        
        Args:
            player_id: Player ID
            gameweek: Current gameweek
            players_df: Optional DataFrame with player data
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            Dictionary with expected minutes and rotation risk
        """
        try:
            # Get player info
            if players_df is not None:
                player = players_df[players_df['id'] == player_id]
                if not player.empty:
                    player = player.iloc[0]
                    status = player.get('status', 'a')
                    chance_playing = player.get('chance_of_playing_this_round', 100)
                    selected = player.get('selected_by_percent', 0)
                    
                    # Base expected minutes from selection percentage
                    base_minutes = min(90, selected * 0.9) if selected > 0 else 0
                    
                    # Adjust for status
                    if status == 'i' or chance_playing == 0:
                        expected_minutes = 0
                    elif status == 'd' or chance_playing < 50:
                        expected_minutes = base_minutes * 0.3
                    elif chance_playing < 75:
                        expected_minutes = base_minutes * 0.6
                    else:
                        expected_minutes = base_minutes
                    
                    # Check recent minutes history
                    # Use provided history_df or load if not provided (backward compatibility)
                    if history_df is None:
                        if self.db_manager:
                            history_df = self.db_manager.get_current_season_history()
                        else:
                            history_df = pd.DataFrame()
                    
                    if not history_df.empty:
                        player_history = history_df[
                            (history_df['player_id'] == player_id) &
                            (history_df['gw'] < gameweek)
                        ].sort_values('gw', ascending=False).head(5)
                        
                        if len(player_history) > 0:
                            recent_avg = player_history['minutes'].fillna(0).mean()
                            # Use recent average if available
                            if recent_avg > 0:
                                expected_minutes = recent_avg * (chance_playing / 100)
                    
                    # Rotation risk
                    rotation_risk = 'low'
                    if expected_minutes < 60:
                        rotation_risk = 'medium'
                    if expected_minutes < 45:
                        rotation_risk = 'high'
                    
                    return {
                        'expected_minutes': round(expected_minutes, 1),
                        'rotation_risk': rotation_risk,
                        'confidence': 'high' if status == 'a' and chance_playing >= 90 else 'medium'
                    }
        except Exception as e:
            logger.debug(f"Error predicting minutes for player {player_id}: {e}")
        
        return {
            'expected_minutes': 60.0,
            'rotation_risk': 'medium',
            'confidence': 'low'
        }
    
    def add_injury_risk_analysis(self, players_df: pd.DataFrame, gameweek: int, relevant_player_ids: set = None, history_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Add injury risk and minutes predictions to player DataFrame.
        Optimized to only process relevant players for performance.
        
        Args:
            players_df: DataFrame with player data
            gameweek: Current gameweek
            relevant_player_ids: Optional set of player IDs to process (for performance)
            history_df: Optional pre-loaded history DataFrame (for performance)
        
        Returns:
            DataFrame with added injury/minutes columns
        """
        df = players_df.copy()
        
        # Initialize columns with defaults
        df['injury_risk'] = 0.05
        df['injury_risk_level'] = 'low'
        df['expected_minutes'] = 60.0
        df['rotation_risk'] = 'medium'
        
        # Filter to relevant players if specified
        if relevant_player_ids:
            df_to_process = df[df['id'].isin(relevant_player_ids)].copy()
        else:
            # Limit to top 100 players for performance
            df_to_process = df.nlargest(100, ['now_cost', 'total_points'], keep='all').copy()
        
        # Use pre-loaded history or load if not provided (PERFORMANCE OPTIMIZATION: avoid redundant database queries)
        if history_df is None and self.db_manager:
            try:
                history_df = self.db_manager.get_current_season_history()
                if history_df.empty:
                    history_df = None
            except Exception as e:
                logger.debug(f"Could not load history for injury analysis: {e}")
                history_df = None
        
        # Process only relevant players (iterrows is necessary here for individual player analysis)
        for idx in df_to_process.index:
            player = df_to_process.loc[idx]
            player_id = player.get('id')
            if pd.isna(player_id):
                continue
            
            player_id = int(player_id)
            
            # Injury risk (pass history_df to avoid redundant queries)
            injury = self.predict_injury_risk(player_id, gameweek, df, history_df=history_df)
            df.at[idx, 'injury_risk'] = injury['injury_risk']
            df.at[idx, 'injury_risk_level'] = injury['risk_level']
            
            # Minutes distribution (pass history_df to avoid redundant queries)
            minutes = self.predict_minutes_distribution(player_id, gameweek, df, history_df=history_df)
            df.at[idx, 'expected_minutes'] = minutes['expected_minutes']
            df.at[idx, 'rotation_risk'] = minutes['rotation_risk']
        
        logger.info(f"Added injury risk analysis for {len(df_to_process)} relevant players")
        return df

