"""
Effective Ownership (EO) calculations and adjustments.
"""
import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class EOCalculator:
    """Calculator for Effective Ownership adjustments."""
    
    def __init__(self, config: Dict):
        """
        Initialize EO calculator.
        """
        self.config = config
        self.risk_tolerance = config.get('risk_tolerance', 0.6)
        self.eo_weight = config.get('eo_weight', 0.1)
    
    def calculate_eo(self, players_df: pd.DataFrame) -> pd.Series:
        """
        Calculate effective ownership from selected_by_percent.
        """
        return pd.to_numeric(players_df['selected_by_percent'], errors='coerce').fillna(0.0) / 100.0
    
    def apply_eo_adjustment(self, players_df: pd.DataFrame, target_rank: int) -> pd.DataFrame:
        """
        Apply EO adjustment to expected values.
        """
        df = players_df.copy()
        df['EO'] = self.calculate_eo(df)
        
        # Adjust risk based on rank
        if target_rank < 10000:
            risk = self.risk_tolerance + 0.2  # Higher risk for top ranks
        elif target_rank < 100000:
            risk = self.risk_tolerance
        else:
            risk = self.risk_tolerance - 0.2  # Lower risk
        
        risk = np.clip(risk, 0.1, 0.9)

        differential_bonus = (1 - df['EO']) * self.eo_weight * df['EV']
        df['EV_adjusted'] = df['EV'] + risk * differential_bonus
        
        # Replace original EV with adjusted
        df['EV'] = df['EV_adjusted']
        
        logger.info(f"Applied EO adjustment with risk factor {risk:.2f}")
        
        return df

