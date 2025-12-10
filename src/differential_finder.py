"""
Differential Finder - Find low-ownership gems and budget enablers.
This module identifies players with low ownership but high potential.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DifferentialFinder:
    """
    Finds differential players (low ownership, high potential).
    """
    
    def __init__(self, ownership_threshold: float = 5.0):
        """
        Initialize Differential Finder.
        
        Args:
            ownership_threshold: Maximum ownership percentage to consider (default: 5%)
        """
        self.ownership_threshold = ownership_threshold
        logger.info(f"Differential Finder initialized (ownership threshold: {ownership_threshold}%)")
    
    def find_low_ownership_gems(self, players_df: pd.DataFrame, min_ev: float = 3.0) -> pd.DataFrame:
        """
        Find players with low ownership but high predicted points.
        
        Args:
            players_df: DataFrame with player data including 'selected_by_percent' and 'EV'
            min_ev: Minimum expected value to consider
        
        Returns:
            DataFrame with low-ownership gems sorted by EV/ownership ratio
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Ensure ownership column exists and is numeric
        if 'selected_by_percent' not in df.columns:
            logger.warning("selected_by_percent column not found, using 0% ownership")
            df['selected_by_percent'] = 0.0
        else:
            df['selected_by_percent'] = pd.to_numeric(df['selected_by_percent'], errors='coerce').fillna(0.0)
        
        # Ensure EV column exists and is numeric
        if 'EV' not in df.columns:
            logger.warning("EV column not found, cannot find differentials")
            return pd.DataFrame()
        else:
            df['EV'] = pd.to_numeric(df['EV'], errors='coerce').fillna(0.0)
        
        # Filter for low ownership and decent EV
        low_ownership = df['selected_by_percent'] < self.ownership_threshold
        decent_ev = df['EV'] >= min_ev
        available = df.get('status', 'a') == 'a'  # Only available players
        
        gems = df[low_ownership & decent_ev & available].copy()
        
        if gems.empty:
            logger.info("No low-ownership gems found")
            return pd.DataFrame()
        
        # Calculate ownership vs EV ratio (higher is better)
        gems['ownership_ev_ratio'] = gems['EV'] / (gems['selected_by_percent'] + 0.1)  # +0.1 to avoid division by zero
        
        # Sort by ratio (best differentials first)
        gems = gems.sort_values('ownership_ev_ratio', ascending=False)
        
        logger.info(f"Found {len(gems)} low-ownership gems (<{self.ownership_threshold}% ownership, EV>={min_ev})")
        
        return gems
    
    def find_fixture_swing_players(self, players_df: pd.DataFrame, api_client, gameweek: int, 
                                   all_fixtures: List[Dict] = None) -> pd.DataFrame:
        """
        Find players with tough fixtures behind them, easy fixtures ahead.
        
        Args:
            players_df: DataFrame with player data
            api_client: FPL API client
            gameweek: Current gameweek
            all_fixtures: Pre-loaded fixtures data
        
        Returns:
            DataFrame with players who have fixture swings
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Get fixture difficulty data if available
        if 'next_3_fixtures_avg_difficulty' not in df.columns:
            logger.debug("Fixture difficulty data not available for swing analysis")
            return pd.DataFrame()
        
        # Look for players with:
        # - Recent tough fixtures (high difficulty in past 3)
        # - Upcoming easy fixtures (low difficulty in next 3)
        # - Decent EV
        
        # Check for fixture difficulty columns (may have different names)
        if 'recent_3_fixtures_avg_difficulty' not in df.columns:
            # Try alternative column names
            if 'avg_fixture_difficulty' in df.columns:
                df['recent_3_fixtures_avg_difficulty'] = df['avg_fixture_difficulty']
            else:
                # Estimate recent difficulty from form/points
                df['recent_3_fixtures_avg_difficulty'] = 3.0  # Default medium
        
        # Ensure columns are numeric
        df['recent_3_fixtures_avg_difficulty'] = pd.to_numeric(df['recent_3_fixtures_avg_difficulty'], errors='coerce').fillna(3.0)
        df['next_3_fixtures_avg_difficulty'] = pd.to_numeric(df['next_3_fixtures_avg_difficulty'], errors='coerce').fillna(3.0)
        df['EV'] = pd.to_numeric(df.get('EV', 0), errors='coerce').fillna(0.0)
        
        # Calculate fixture swing (negative = easy fixtures ahead after tough ones)
        df['fixture_swing'] = df['recent_3_fixtures_avg_difficulty'] - df['next_3_fixtures_avg_difficulty']
        
        # Find players with positive swing (tough behind, easy ahead)
        swing_players = df[
            (df['fixture_swing'] > 0.5) &  # At least 0.5 difficulty swing
            (df['next_3_fixtures_avg_difficulty'] < 3.0) &  # Easy fixtures ahead
            (df['EV'] >= 2.0)  # Decent EV
        ].copy()
        
        if swing_players.empty:
            logger.info("No fixture swing players found")
            return pd.DataFrame()
        
        swing_players = swing_players.sort_values('fixture_swing', ascending=False)
        
        logger.info(f"Found {len(swing_players)} players with fixture swings (tough behind, easy ahead)")
        
        return swing_players
    
    def find_budget_enablers(self, players_df: pd.DataFrame, max_price: int = 45) -> pd.DataFrame:
        """
        Find cheap players who are nailed starters.
        
        Args:
            players_df: DataFrame with player data
            max_price: Maximum price in 0.1M units (e.g., 45 = £4.5M)
        
        Returns:
            DataFrame with budget enablers
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Filter for budget players
        budget = df['now_cost'] <= max_price
        
        # Look for players with high minutes (nailed starters)
        if 'minutes' not in df.columns:
            logger.warning("minutes column not found, cannot identify nailed starters")
            return pd.DataFrame()
        
        # Consider players with >80% of possible minutes as "nailed"
        # Assuming ~90 minutes per gameweek for outfield players
        min_minutes = 90 * 0.8 * 15  # 80% of 15 gameweeks
        
        nailed = df['minutes'] >= min_minutes
        
        # Also check recent minutes (last 3 gameweeks)
        if 'minutes_rolling_3' in df.columns:
            recent_nailed = df['minutes_rolling_3'] >= (90 * 0.8 * 3)
            nailed = nailed | recent_nailed
        
        budget_enablers = df[budget & nailed].copy()
        
        if budget_enablers.empty:
            logger.info("No budget enablers found")
            return pd.DataFrame()
        
        # Sort by value (points per 0.1M)
        if 'total_points' in budget_enablers.columns and 'now_cost' in budget_enablers.columns:
            budget_enablers['value_ratio'] = budget_enablers['total_points'] / (budget_enablers['now_cost'] / 10)
            budget_enablers = budget_enablers.sort_values('value_ratio', ascending=False)
        
        logger.info(f"Found {len(budget_enablers)} budget enablers (≤£{max_price/10:.1f}M, nailed starters)")
        
        return budget_enablers
    
    def find_new_signings(self, players_df: pd.DataFrame, api_client, 
                         min_gw_joined: int = None) -> pd.DataFrame:
        """
        Find new signings or loan returns not yet on FPL radar.
        
        Args:
            players_df: DataFrame with player data
            api_client: FPL API client
            min_gw_joined: Minimum gameweek when player joined (if None, uses recent)
        
        Returns:
            DataFrame with new signings
        """
        if players_df.empty:
            return pd.DataFrame()
        
        df = players_df.copy()
        
        # Check news field for transfer/loan information
        if 'news' in df.columns:
            # Look for transfer-related keywords
            transfer_keywords = ['signed', 'loan', 'transfer', 'joined', 'arrived', 'returned']
            has_transfer_news = df['news'].str.lower().str.contains('|'.join(transfer_keywords), na=False)
            
            # Also check for low ownership (not on radar yet)
            low_ownership = df.get('selected_by_percent', 0) < 2.0
            
            new_signings = df[has_transfer_news & low_ownership].copy()
            
            if not new_signings.empty:
                logger.info(f"Found {len(new_signings)} potential new signings/loan returns")
                return new_signings
        
        logger.debug("No new signings identified")
        return pd.DataFrame()
    
    def generate_differential_report(self, players_df: pd.DataFrame, api_client, 
                                     gameweek: int, all_fixtures: List[Dict] = None) -> Dict:
        """
        Generate comprehensive differential report.
        
        Args:
            players_df: DataFrame with player data
            api_client: FPL API client
            gameweek: Current gameweek
            all_fixtures: Pre-loaded fixtures data
        
        Returns:
            Dictionary with different categories of differentials
        """
        report = {
            'low_ownership_gems': self.find_low_ownership_gems(players_df),
            'fixture_swing_players': self.find_fixture_swing_players(players_df, api_client, gameweek, all_fixtures),
            'budget_enablers': self.find_budget_enablers(players_df),
            'new_signings': self.find_new_signings(players_df, api_client)
        }
        
        return report

