"""
Player projection engine with multiple models.
"""
import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ProjectionEngine:
    """Engine for calculating player expected points."""
    
    def __init__(self, config: Dict):
        """
        Initialize projection engine.
        """
        self.config = config.get('projection', {})
        self.coeffs = self.config.get('regression_coefficients', {})
        
        self.xg_coef = self.coeffs.get('xg_per90', 5.0)
        self.xa_coef = self.coeffs.get('xa_per90', 3.0)
        self.form_coef = self.coeffs.get('form', 0.3)
        
        self.official_weight = self.config.get('official_weight', 0.6)
        self.regression_weight = self.config.get('regression_weight', 0.4)
        
        self.doubtful_factor = self.config.get('doubtful_multiplier', 0.3)
        self.injured_factor = self.config.get('injured_multiplier', 0.0)
    
    def calculate_official_projection(self, players_df: pd.DataFrame) -> pd.Series:
        """
        Get official FPL projections (ep_next).
        """
        return pd.to_numeric(players_df['ep_next'], errors='coerce').fillna(0.0)
    
    def calculate_regression_projection(self, players_df: pd.DataFrame) -> pd.Series:
        """
        Calculate regression-based projections.
        """
        minutes = pd.to_numeric(players_df['minutes'], errors='coerce').replace(0, np.nan)
        
        xg_per90 = (pd.to_numeric(players_df['expected_goals'], errors='coerce') / minutes * 90).fillna(0)
        xa_per90 = (pd.to_numeric(players_df['expected_assists'], errors='coerce') / minutes * 90).fillna(0)
        form = pd.to_numeric(players_df['form'], errors='coerce').fillna(0)
        
        projection = (
            xg_per90 * self.xg_coef +
            xa_per90 * self.xa_coef +
            form * self.form_coef
        )
        
        return projection.clip(lower=0)
    
    def calculate_combined_projection(self, players_df: pd.DataFrame) -> pd.Series:
        """
        Calculate combined projection (weighted average of official and regression).
        """
        official = self.calculate_official_projection(players_df)
        regression = self.calculate_regression_projection(players_df)
        
        combined = (
            official * self.official_weight +
            regression * self.regression_weight
        )
        
        return combined
    
    def apply_injury_adjustments(self, projections: pd.Series, players_df: pd.DataFrame) -> pd.Series:
        """
        Apply injury/availability adjustments to projections.
        IMPROVED: Use chance_of_playing_next_round for more nuanced adjustments.
        """
        adjusted = projections.copy()
        
        # Get chance of playing (0-100)
        chance = pd.to_numeric(players_df['chance_of_playing_next_round'], errors='coerce')
        
        # For players with explicit chance ratings
        has_chance = ~chance.isna()
        
        # Apply chance-based adjustment
        # 100% = 1.0, 75% = 0.75, 50% = 0.50, 25% = 0.25, 0% = 0.0
        adjusted.loc[has_chance] = adjusted.loc[has_chance] * (chance.loc[has_chance] / 100.0)
        
        # For players without chance rating, use status
        # Status codes: 'a' = available, 'd' = doubtful, 'i' = injured, 's' = suspended, 'u' = unavailable
        no_chance = chance.isna()
        
        # Doubtful players without chance rating: 30% expected availability
        doubtful_mask = no_chance & (players_df['status'] == 'd')
        adjusted.loc[doubtful_mask] *= self.doubtful_factor
        
        # Fully unavailable (injured, suspended, unavailable): 0%
        unavailable_mask = no_chance & players_df['status'].isin(['i', 's', 'u'])
        adjusted.loc[unavailable_mask] = 0.0
        
        # Log adjustments
        num_chance_adjusted = has_chance.sum()
        num_doubtful = doubtful_mask.sum()
        num_unavailable = unavailable_mask.sum()
        
        logger.info(f"Injury adjustments applied:")
        logger.info(f"  - {num_chance_adjusted} players adjusted by chance_of_playing")
        logger.info(f"  - {num_doubtful} doubtful players (×{self.doubtful_factor})")
        logger.info(f"  - {num_unavailable} unavailable players (×0.0)")
        
        # Show some examples of adjusted players
        if num_chance_adjusted > 0:
            adjusted_players = players_df[has_chance].copy()
            adjusted_players['adjusted_ev'] = adjusted.loc[has_chance]
            adjusted_players['original_ev'] = projections.loc[has_chance]
            
            # Show players with significant adjustments
            significant = adjusted_players[adjusted_players['adjusted_ev'] < adjusted_players['original_ev'] * 0.9]
            if not significant.empty:
                logger.info(f"\n  Players with reduced EV due to injury concerns:")
                for _, player in significant.head(5).iterrows():
                    logger.info(f"    {player['web_name']}: {player['original_ev']:.2f} → {player['adjusted_ev']:.2f} "
                              f"({player['chance_of_playing_next_round']}% chance)")
        
        return adjusted
    
    def calculate_projections(self, players_df: pd.DataFrame, model: str = 'combined') -> pd.DataFrame:
        """
        Calculate projections for all players.
        IMPROVED: Better logging and validation.
        """
        df = players_df.copy()
        
        # Calculate all projection models
        df['xP_official'] = self.calculate_official_projection(df)
        df['xP_regression'] = self.calculate_regression_projection(df)
        df['xP_combined'] = self.calculate_combined_projection(df)
        
        # Select model
        if model == 'official':
            df['xP_raw'] = df['xP_official']
        elif model == 'regression':
            df['xP_raw'] = df['xP_regression']
        else:
            df['xP_raw'] = df['xP_combined']
        
        # Apply injury adjustments
        df['xP_adjusted'] = self.apply_injury_adjustments(df['xP_raw'], df)
        
        # Final EV
        df['EV'] = df['xP_adjusted']
        
        # Validation: Check for unreasonable values
        zero_ev_count = (df['EV'] == 0.0).sum()
        negative_ev_count = (df['EV'] < 0.0).sum()
        high_ev_count = (df['EV'] > 15.0).sum()
        
        logger.info(f"Projection Statistics:")
        logger.info(f"  Model: {model}")
        logger.info(f"  Average EV: {df['EV'].mean():.2f}")
        logger.info(f"  Median EV: {df['EV'].median():.2f}")
        logger.info(f"  Max EV: {df['EV'].max():.2f}")
        logger.info(f"  Players with EV = 0: {zero_ev_count}")
        logger.info(f"  Players with EV < 0: {negative_ev_count}")
        logger.info(f"  Players with EV > 15: {high_ev_count}")
        
        # Show top projected players
        top_5 = df.nlargest(5, 'EV')[['web_name', 'team_name', 'xP_raw', 'EV', 'status', 'chance_of_playing_next_round']]
        logger.info(f"\nTop 5 projected players:")
        for _, player in top_5.iterrows():
            chance = player.get('chance_of_playing_next_round', 100)
            logger.info(f"  {player['web_name']:20s} {player['team_name']:15s} "
                      f"Raw: {player['xP_raw']:5.2f} → Final: {player['EV']:5.2f} "
                      f"[{player['status']}, {chance}%]")
        
        return df

