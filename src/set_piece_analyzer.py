"""
Set Piece Analyzer - Track set piece takers and targets.
This module identifies corner takers, free kick specialists, penalty takers, and set piece targets.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SetPieceAnalyzer:
    """
    Analyzes set piece takers and targets for FPL advantage.
    """
    
    def __init__(self):
        """Initialize Set Piece Analyzer."""
        logger.info("Set Piece Analyzer initialized")
    
    def analyze_corner_takers(self, players_df: pd.DataFrame, 
                             history_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Identify corner takers by team.
        
        Args:
            players_df: DataFrame with player data
            history_df: Optional historical data for analysis
        
        Returns:
            DataFrame with corner taker information
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Use creativity metric as proxy for corner taking (high creativity often = set piece taker)
        # Also consider assists (corner assists are common)
        
        if 'creativity' not in df.columns:
            logger.warning("creativity column not found, using assists as proxy")
            df['creativity'] = pd.to_numeric(df.get('assists', 0), errors='coerce').fillna(0) * 10
        else:
            df['creativity'] = pd.to_numeric(df['creativity'], errors='coerce').fillna(0.0)
        
        # Identify potential corner takers:
        # - High creativity
        # - Midfielders or attacking players
        # - Regular starters
        
        is_midfielder = pd.to_numeric(df.get('element_type', 0), errors='coerce').fillna(0) == 3  # MID
        is_attacker = pd.to_numeric(df.get('element_type', 0), errors='coerce').fillna(0) == 4  # FWD
        
        creativity_quantile = df['creativity'].quantile(0.75) if len(df) > 0 and df['creativity'].notna().any() else 0
        high_creativity = df['creativity'] > creativity_quantile
        minutes = pd.to_numeric(df.get('minutes', 0), errors='coerce').fillna(0)
        regular_starter = minutes > (90 * 10)  # At least 10 full games
        
        corner_takers = df[(is_midfielder | is_attacker) & high_creativity & regular_starter].copy()
        
        if corner_takers.empty:
            logger.info("No corner takers identified")
            return pd.DataFrame()
        
        # Rank by creativity and assists
        corner_takers['corner_score'] = (
            corner_takers['creativity'] * 0.6 + 
            corner_takers.get('assists', 0) * 0.4
        )
        corner_takers = corner_takers.sort_values('corner_score', ascending=False)
        
        # Group by team to identify primary corner taker
        corner_takers['is_primary_corner_taker'] = False
        for team_id in corner_takers['team'].unique():
            team_corners = corner_takers[corner_takers['team'] == team_id]
            if not team_corners.empty:
                primary_idx = team_corners.index[0]
                corner_takers.loc[primary_idx, 'is_primary_corner_taker'] = True
        
        logger.info(f"Identified {len(corner_takers)} potential corner takers")
        
        return corner_takers
    
    def analyze_free_kick_takers(self, players_df: pd.DataFrame,
                                history_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Identify direct free kick specialists.
        
        Args:
            players_df: DataFrame with player data
            history_df: Optional historical data
        
        Returns:
            DataFrame with free kick taker information
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Free kick takers typically have:
        # - High threat score (shooting ability)
        # - Goals from outside box (if available)
        # - High creativity
        
        if 'threat' not in df.columns:
            logger.warning("threat column not found, using goals as proxy")
            df['threat'] = pd.to_numeric(df.get('goals_scored', 0), errors='coerce').fillna(0) * 10
        else:
            df['threat'] = pd.to_numeric(df['threat'], errors='coerce').fillna(0.0)
        
        threat_quantile = df['threat'].quantile(0.7) if len(df) > 0 and df['threat'].notna().any() else 0
        high_threat = df['threat'] > threat_quantile
        
        creativity = pd.to_numeric(df.get('creativity', 0), errors='coerce').fillna(0.0)
        creativity_quantile = creativity.quantile(0.7) if len(creativity) > 0 and creativity.notna().any() else 0
        high_creativity = creativity > creativity_quantile
        
        has_goals = pd.to_numeric(df.get('goals_scored', 0), errors='coerce').fillna(0) > 0
        
        fk_takers = df[high_threat & high_creativity & has_goals].copy()
        
        if fk_takers.empty:
            logger.info("No free kick specialists identified")
            return pd.DataFrame()
        
        # Rank by threat and goals (ensure numeric)
        fk_takers['threat'] = pd.to_numeric(fk_takers['threat'], errors='coerce').fillna(0.0)
        fk_takers['goals_scored'] = pd.to_numeric(fk_takers.get('goals_scored', 0), errors='coerce').fillna(0)
        fk_takers['creativity'] = pd.to_numeric(fk_takers.get('creativity', 0), errors='coerce').fillna(0.0)
        fk_takers['fk_score'] = (
            fk_takers['threat'] * 0.5 +
            fk_takers['goals_scored'] * 0.3 +
            fk_takers['creativity'] * 0.2
        )
        fk_takers = fk_takers.sort_values('fk_score', ascending=False)
        
        # Group by team to identify primary FK taker
        fk_takers['is_primary_fk_taker'] = False
        for team_id in fk_takers['team'].unique():
            team_fks = fk_takers[fk_takers['team'] == team_id]
            if not team_fks.empty:
                primary_idx = team_fks.index[0]
                fk_takers.loc[primary_idx, 'is_primary_fk_taker'] = True
        
        logger.info(f"Identified {len(fk_takers)} potential free kick specialists")
        
        return fk_takers
    
    def analyze_penalty_takers(self, players_df: pd.DataFrame,
                              history_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Identify penalty takers (first choice and backup).
        
        Args:
            players_df: DataFrame with player data
            history_df: Optional historical data
        
        Returns:
            DataFrame with penalty taker information
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Penalty takers typically:
        # - Have scored penalties (penalties_scored if available)
        # - High threat score
        # - Regular starters
        
        # Check for penalties_scored column (FPL API uses different naming)
        # FPL API has 'penalties_scored' in element-summary but may not be in bootstrap
        if 'penalties_scored' in df.columns:
            has_penalties = df['penalties_scored'] > 0
        elif 'penalties_missed' in df.columns:
            # If no penalties_scored, check for players who have taken penalties (missed or scored)
            has_penalties = df['penalties_missed'] >= 0  # Any penalty attempt
        else:
            # Fallback: use goals and threat as proxy for potential penalty takers
            # Look for players with goals (could be penalties) and high threat
            threat_threshold = df.get('threat', pd.Series([0])).quantile(0.6) if len(df) > 0 else 0
            has_penalties = (df.get('goals_scored', 0) > 1) & (df.get('threat', 0) > threat_threshold)
        
        regular_starter = df.get('minutes', 0) > (90 * 8)  # At least 8 full games
        
        penalty_takers = df[has_penalties & regular_starter].copy()
        
        if penalty_takers.empty:
            logger.info("No penalty takers identified")
            return pd.DataFrame()
        
        # Rank by penalty goals (if available) or threat
        if 'penalties_scored' in penalty_takers.columns:
            penalty_takers['penalty_score'] = (
                penalty_takers['penalties_scored'].fillna(0) * 10 +
                penalty_takers.get('threat', 0).fillna(0) * 0.1
            )
        else:
            penalty_takers['penalty_score'] = (
                penalty_takers.get('goals_scored', 0).fillna(0) * 2 +
                penalty_takers.get('threat', 0).fillna(0) * 0.1
            )
        
        penalty_takers = penalty_takers.sort_values('penalty_score', ascending=False)
        
        # Group by team to identify first and second choice
        penalty_takers['penalty_order'] = 0
        for team_id in penalty_takers['team'].unique():
            team_pens = penalty_takers[penalty_takers['team'] == team_id].sort_values('penalty_score', ascending=False)
            for i, idx in enumerate(team_pens.index):
                penalty_takers.loc[idx, 'penalty_order'] = i + 1  # 1 = first choice, 2 = second choice, etc.
        
        logger.info(f"Identified {len(penalty_takers)} potential penalty takers")
        
        return penalty_takers
    
    def analyze_set_piece_targets(self, players_df: pd.DataFrame,
                                history_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Identify defenders/midfielders who get on the end of set pieces.
        
        Args:
            players_df: DataFrame with player data
            history_df: Optional historical data
        
        Returns:
            DataFrame with set piece target information
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Set piece targets typically:
        # - Defenders or tall midfielders
        # - Score goals from headers (if data available)
        # - High threat in air (if available)
        # - Goals but low creativity (suggests headers/tap-ins)
        
        element_type = pd.to_numeric(df.get('element_type', 0), errors='coerce').fillna(0)
        is_defender = element_type == 2  # DEF
        is_tall_midfielder = element_type == 3  # MID
        
        has_goals = pd.to_numeric(df.get('goals_scored', 0), errors='coerce').fillna(0) > 0
        creativity = pd.to_numeric(df.get('creativity', 0), errors='coerce').fillna(0.0)
        creativity_quantile = creativity.quantile(0.5) if len(creativity) > 0 and creativity.notna().any() else 0
        low_creativity = creativity < creativity_quantile  # Goals without high creativity = headers
        
        # For defenders, goals usually come from set pieces
        # For midfielders, look for those with goals but low creativity
        
        targets = df[((is_defender & has_goals) | (is_tall_midfielder & has_goals & low_creativity))].copy()
        
        if targets.empty:
            logger.info("No set piece targets identified")
            return pd.DataFrame()
        
        # Rank by goals and threat (ensure numeric)
        targets['goals_scored'] = pd.to_numeric(targets.get('goals_scored', 0), errors='coerce').fillna(0)
        targets['threat'] = pd.to_numeric(targets.get('threat', 0), errors='coerce').fillna(0.0)
        targets['target_score'] = (
            targets['goals_scored'] * 5 +
            targets['threat'] * 0.2
        )
        targets = targets.sort_values('target_score', ascending=False)
        
        logger.info(f"Identified {len(targets)} potential set piece targets")
        
        return targets
    
    def generate_set_piece_report(self, players_df: pd.DataFrame,
                                 history_df: Optional[pd.DataFrame] = None) -> Dict:
        """
        Generate comprehensive set piece analysis report.
        
        Args:
            players_df: DataFrame with player data
            history_df: Optional historical data
        
        Returns:
            Dictionary with set piece analysis by category
        """
        report = {
            'corner_takers': self.analyze_corner_takers(players_df, history_df),
            'free_kick_takers': self.analyze_free_kick_takers(players_df, history_df),
            'penalty_takers': self.analyze_penalty_takers(players_df, history_df),
            'set_piece_targets': self.analyze_set_piece_targets(players_df, history_df)
        }
        
        return report

