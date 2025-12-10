"""
Learning System for FPL Optimizer
Learns from past decisions and outcomes to improve recommendations.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from database import DatabaseManager
from fpl_api import FPLAPIClient

logger = logging.getLogger(__name__)


class LearningSystem:
    """
    System that learns from past decisions and outcomes to improve recommendations.
    """
    
    def __init__(self, db_manager: DatabaseManager, api_client: FPLAPIClient, entry_id: int):
        """
        Initialize learning system.
        
        Args:
            db_manager: Database manager instance
            api_client: FPL API client instance
            entry_id: User's entry ID
        """
        self.db_manager = db_manager
        self.api_client = api_client
        self.entry_id = entry_id
        self.user_preferences = {}
        self.decision_history = None
        
    def load_decision_history(self, min_gw: int = 1, max_gw: int = None) -> pd.DataFrame:
        """
        Load past decisions from the database.
        
        Args:
            min_gw: Minimum gameweek to load
            max_gw: Maximum gameweek to load (None = current)
        
        Returns:
            DataFrame with decision history
        """
        try:
            self.decision_history = self.db_manager.get_decisions(
                entry_id=self.entry_id,
                min_gw=min_gw,
                max_gw=max_gw
            )
            logger.info(f"Loaded {len(self.decision_history)} past decisions")
            return self.decision_history
        except Exception as e:
            logger.warning(f"Error loading decision history: {e}")
            return pd.DataFrame()
    
    def compare_outcomes_vs_predictions(self, gameweek: int) -> pd.DataFrame:
        """
        Compare actual outcomes vs predictions for a specific gameweek.
        
        Args:
            gameweek: Gameweek to analyze
        
        Returns:
            DataFrame with comparison metrics
        """
        try:
            # Get predictions for this gameweek
            predictions = self.db_manager.get_predictions_for_gw(gameweek)
            if predictions.empty:
                logger.debug(f"No predictions found for GW{gameweek}")
                return pd.DataFrame()
            
            # Get actual player performance from history
            history = self.db_manager.get_current_season_history()
            if history.empty:
                logger.debug("No history data available")
                return pd.DataFrame()
            
            gw_history = history[history['gw'] == gameweek].copy()
            if gw_history.empty:
                logger.debug(f"No history data for GW{gameweek}")
                return pd.DataFrame()
            
            # Merge predictions with actual outcomes
            comparison = predictions.merge(
                gw_history[['player_id', 'total_points', 'minutes']],
                on='player_id',
                how='inner',
                suffixes=('_pred', '_actual')
            )
            
            if comparison.empty:
                return pd.DataFrame()
            
            # Calculate prediction errors
            comparison['prediction_error'] = comparison['predicted_ev'] - comparison['total_points']
            comparison['absolute_error'] = comparison['prediction_error'].abs()
            comparison['squared_error'] = comparison['prediction_error'] ** 2
            
            # Only count players who actually played
            comparison = comparison[comparison['minutes'] > 0]
            
            logger.info(f"Compared {len(comparison)} predictions vs outcomes for GW{gameweek}")
            return comparison
            
        except Exception as e:
            logger.warning(f"Error comparing outcomes: {e}")
            return pd.DataFrame()
    
    def analyze_user_preferences(self) -> Dict:
        """
        Analyze user preferences from past decisions.
        
        Returns:
            Dictionary with learned preferences
        """
        if self.decision_history is None or self.decision_history.empty:
            logger.debug("No decision history available for preference analysis")
            return {}
        
        try:
            preferences = {
                'risk_tolerance': 'medium',  # low, medium, high
                'transfer_frequency': 'medium',  # low, medium, high
                'hit_taking_tendency': 0.0,  # 0-1, probability of taking hits
                'follows_recommendations': 0.0,  # 0-1, how often user follows top recommendation
                'preferred_transfer_count': 1,  # Most common number of transfers
                'forced_transfer_handling': 'immediate',  # immediate, delayed, ignored
            }
            
            # Analyze transfer patterns
            total_decisions = len(self.decision_history)
            if total_decisions == 0:
                return preferences
            
            # Count how often user follows recommendations
            follows_count = 0
            hit_count = 0
            transfer_counts = []
            
            for _, decision in self.decision_history.iterrows():
                rec_transfers = decision.get('recommended_transfers', {})
                actual_transfers = decision.get('actual_transfers_made', [])
                
                if isinstance(rec_transfers, str):
                    try:
                        rec_transfers = eval(rec_transfers)
                    except:
                        rec_transfers = {}
                
                if isinstance(actual_transfers, str):
                    try:
                        actual_transfers = eval(actual_transfers) if actual_transfers else []
                    except:
                        actual_transfers = []
                
                # Check if user followed top recommendation
                if rec_transfers and actual_transfers:
                    rec_players_out = set(rec_transfers.get('players_out', []))
                    rec_players_in = set(rec_transfers.get('players_in', []))
                    actual_players_out = set([t.get('id', t.get('player_id')) for t in actual_transfers if isinstance(t, dict)])
                    actual_players_in = set([t.get('id', t.get('player_id')) for t in actual_transfers if isinstance(t, dict)])
                    
                    # Check if actual matches recommended (at least partially)
                    if rec_players_out and actual_players_out:
                        overlap = len(rec_players_out & actual_players_out) / len(rec_players_out)
                        if overlap > 0.5:  # At least 50% match
                            follows_count += 1
                
                # Count transfers
                num_transfers = len(actual_transfers) if isinstance(actual_transfers, list) else 0
                transfer_counts.append(num_transfers)
                
                # Check for hits (transfers > free transfers)
                free_transfers = rec_transfers.get('free_transfers', 1) if isinstance(rec_transfers, dict) else 1
                if num_transfers > free_transfers:
                    hit_count += 1
            
            # Calculate preferences
            preferences['follows_recommendations'] = follows_count / total_decisions if total_decisions > 0 else 0.0
            preferences['hit_taking_tendency'] = hit_count / total_decisions if total_decisions > 0 else 0.0
            preferences['preferred_transfer_count'] = int(np.median(transfer_counts)) if transfer_counts else 1
            
            # Determine risk tolerance
            if preferences['hit_taking_tendency'] > 0.3:
                preferences['risk_tolerance'] = 'high'
            elif preferences['hit_taking_tendency'] < 0.1:
                preferences['risk_tolerance'] = 'low'
            else:
                preferences['risk_tolerance'] = 'medium'
            
            # Determine transfer frequency
            avg_transfers = np.mean(transfer_counts) if transfer_counts else 1
            if avg_transfers > 2:
                preferences['transfer_frequency'] = 'high'
            elif avg_transfers < 1.2:
                preferences['transfer_frequency'] = 'low'
            else:
                preferences['transfer_frequency'] = 'medium'
            
            self.user_preferences = preferences
            logger.info(f"Analyzed user preferences: {preferences}")
            return preferences
            
        except Exception as e:
            logger.warning(f"Error analyzing user preferences: {e}")
            return {}
    
    def get_feedback_data_for_training(self, min_gw: int = 1, max_gw: int = None) -> pd.DataFrame:
        """
        Get feedback data (actual outcomes vs predictions) for ML model fine-tuning.
        
        Args:
            min_gw: Minimum gameweek
            max_gw: Maximum gameweek
        
        Returns:
            DataFrame with feedback data ready for training
        """
        try:
            if max_gw is None:
                # Get current gameweek
                bootstrap = self.api_client.get_bootstrap_static()
                current_gw = max([e['id'] for e in bootstrap['events'] if not e.get('finished', True)])
                max_gw = current_gw - 1  # Exclude current/upcoming GW
            
            all_feedback = []
            
            for gw in range(min_gw, max_gw + 1):
                comparison = self.compare_outcomes_vs_predictions(gw)
                if not comparison.empty:
                    comparison['gw'] = gw
                    all_feedback.append(comparison)
            
            if all_feedback:
                feedback_df = pd.concat(all_feedback, ignore_index=True)
                logger.info(f"Collected feedback data from {len(feedback_df)} player-gameweek combinations")
                return feedback_df
            else:
                logger.debug("No feedback data available")
                return pd.DataFrame()
                
        except Exception as e:
            logger.warning(f"Error collecting feedback data: {e}")
            return pd.DataFrame()
    
    def adjust_recommendation_priorities(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Adjust recommendation priorities based on learned user preferences.
        
        Args:
            recommendations: List of recommendation dictionaries
        
        Returns:
            Adjusted recommendations with updated priorities
        """
        if not self.user_preferences:
            self.analyze_user_preferences()
        
        if not self.user_preferences:
            return recommendations
        
        adjusted = []
        
        for rec in recommendations:
            # Create a copy to avoid modifying original
            adjusted_rec = rec.copy()
            
            # Adjust based on risk tolerance
            risk_tolerance = self.user_preferences.get('risk_tolerance', 'medium')
            penalty_hits = rec.get('penalty_hits', 0)
            
            if risk_tolerance == 'low' and penalty_hits > 0:
                # Lower priority for hits if user is risk-averse
                current_priority = rec.get('priority', 'MEDIUM')
                if current_priority == 'HIGH':
                    adjusted_rec['priority'] = 'MEDIUM'
                elif current_priority == 'MEDIUM':
                    adjusted_rec['priority'] = 'LOW'
                adjusted_rec['net_ev_gain_adjusted'] = rec.get('net_ev_gain_adjusted', 0) * 0.8  # Reduce value
            
            elif risk_tolerance == 'high' and penalty_hits > 0:
                # Increase priority for hits if user is risk-tolerant
                if rec.get('net_ev_gain_adjusted', 0) > 4:
                    if rec.get('priority') == 'LOW':
                        adjusted_rec['priority'] = 'MEDIUM'
            
            # Adjust based on preferred transfer count
            preferred_count = self.user_preferences.get('preferred_transfer_count', 1)
            num_transfers = rec.get('num_transfers', 0)
            
            if abs(num_transfers - preferred_count) <= 1:
                # Boost priority if matches user's preferred transfer count
                if rec.get('priority') == 'LOW':
                    adjusted_rec['priority'] = 'MEDIUM'
                elif rec.get('priority') == 'MEDIUM':
                    adjusted_rec['priority'] = 'HIGH'
            
            # Adjust based on whether user typically follows recommendations
            follows_rate = self.user_preferences.get('follows_recommendations', 0.5)
            if follows_rate < 0.3:
                # User rarely follows - emphasize different strategies
                if rec.get('strategy') == 'OPTIMIZE' and num_transfers == 1:
                    adjusted_rec['priority'] = 'LOW'  # User doesn't like single transfers
            
            adjusted.append(adjusted_rec)
        
        # Re-sort by adjusted priority and net gain
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'VERY LOW': 0}
        adjusted.sort(
            key=lambda x: (
                priority_order.get(x.get('priority', 'MEDIUM'), 2),
                x.get('net_ev_gain_adjusted', 0)
            ),
            reverse=True
        )
        
        logger.info(f"Adjusted {len(adjusted)} recommendations based on user preferences")
        return adjusted
    
    def get_model_fine_tuning_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get data for fine-tuning the ML model.
        
        Returns:
            Tuple of (features_df, targets_df) for training
        """
        try:
            feedback_df = self.get_feedback_data_for_training()
            if feedback_df.empty:
                return pd.DataFrame(), pd.DataFrame()
            
            # Get historical features for these players/gameweeks
            history = self.db_manager.get_current_season_history()
            if history.empty:
                return pd.DataFrame(), pd.DataFrame()
            
            # Merge feedback with history to get features
            features_df = feedback_df.merge(
                history,
                on=['player_id', 'gw'],
                how='left',
                suffixes=('', '_hist')
            )
            
            # Use actual points as target (what we want to predict better)
            targets_df = feedback_df[['player_id', 'gw', 'total_points']].copy()
            targets_df.rename(columns={'total_points': 'target_points'}, inplace=True)
            
            logger.info(f"Prepared fine-tuning data: {len(features_df)} samples")
            return features_df, targets_df
            
        except Exception as e:
            logger.warning(f"Error preparing fine-tuning data: {e}")
            return pd.DataFrame(), pd.DataFrame()

