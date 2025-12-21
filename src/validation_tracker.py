"""
Real-World Validation Tracking System
Tracks ML model predictions and compares them to actual results.
"""
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from database import DatabaseManager
from fpl_api import FPLAPIClient

logger = logging.getLogger(__name__)


class ValidationTracker:
    """Tracks and validates ML model predictions against actual results."""
    
    def __init__(self, db_manager: DatabaseManager, api_client: Optional[FPLAPIClient] = None):
        self.db = db_manager
        self.api_client = api_client or FPLAPIClient(cache_dir='.cache')
    
    def record_prediction(self, player_id: int, gw: int, predicted_ev: float, 
                         predicted_points_per_90: float, model_version: str,
                         player_name: Optional[str] = None, season: Optional[str] = None) -> bool:
        """
        Record a prediction for later validation.
        
        Args:
            player_id: FPL player ID
            gw: Gameweek number
            predicted_ev: Predicted expected value (points)
            predicted_points_per_90: Predicted points per 90 minutes
            model_version: Model version (e.g., 'v5.0')
            player_name: Player name (optional)
            season: Season string (e.g., '2025-26')
        
        Returns:
            True if successful
        """
        try:
            if not season:
                # Try to get current season
                try:
                    bootstrap = self.api_client.get_bootstrap_static(use_cache=True)
                    events = bootstrap.get('events', [])
                    if events:
                        # Infer season from first event
                        first_event = events[0]
                        # FPL seasons typically start in August
                        # This is a simple heuristic
                        season = f"2025-26"  # Default, should be improved
                except:
                    season = "2025-26"
            
            record = {
                'player_id': player_id,
                'player_name': player_name or f'Player_{player_id}',
                'gw': gw,
                'season': season,
                'model_version': model_version,
                'predicted_ev': float(predicted_ev),
                'predicted_points_per_90': float(predicted_points_per_90),
                'prediction_timestamp': datetime.utcnow().isoformat(),
                'is_validated': False
            }
            
            # Upsert to database
            self.db._execute_with_retry(
                self.db.supabase_client.table('validation_tracking').upsert(record)
            )
            
            logger.debug(f"Recorded prediction: Player {player_id}, GW{gw}, EV={predicted_ev:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording prediction: {e}")
            return False
    
    def validate_predictions_for_gw(self, gw: int, model_version: str = 'v5.0') -> Dict:
        """
        Validate predictions for a completed gameweek by comparing to actual results.
        
        Args:
            gw: Gameweek number to validate
            model_version: Model version to validate
        
        Returns:
            Dictionary with validation metrics
        """
        try:
            # Get all predictions for this gameweek
            predictions_df = self._get_predictions_for_gw(gw, model_version)
            
            if predictions_df.empty:
                logger.warning(f"No predictions found for GW{gw}, model {model_version}")
                return {'error': 'No predictions found'}
            
            # Get actual results from FPL API
            actual_results = self._get_actual_results_for_gw(gw)
            
            if actual_results.empty:
                logger.warning(f"No actual results found for GW{gw}")
                return {'error': 'No actual results found'}
            
            # Merge predictions with actual results
            merged = predictions_df.merge(
                actual_results,
                on='player_id',
                how='inner',
                suffixes=('_pred', '_actual')
            )
            
            if merged.empty:
                logger.warning(f"No matching players found between predictions and actual results for GW{gw}")
                return {'error': 'No matching players'}
            
            # Calculate errors
            merged['prediction_error'] = merged['predicted_ev'] - merged['actual_points']
            merged['absolute_error'] = merged['prediction_error'].abs()
            merged['squared_error'] = merged['prediction_error'] ** 2
            
            # Calculate metrics
            mae = merged['absolute_error'].mean()
            rmse = (merged['squared_error'].mean()) ** 0.5
            mape = (merged['absolute_error'] / (merged['actual_points'] + 0.1)).mean() * 100
            
            # Calculate R²
            try:
                from sklearn.metrics import r2_score
                r2 = r2_score(merged['actual_points'], merged['predicted_ev'])
            except ImportError:
                # Fallback R² calculation
                ss_res = ((merged['actual_points'] - merged['predicted_ev']) ** 2).sum()
                ss_tot = ((merged['actual_points'] - merged['actual_points'].mean()) ** 2).sum()
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Update database records
            validated_count = 0
            for _, row in merged.iterrows():
                update_record = {
                    'player_id': int(row['player_id']),
                    'gw': gw,
                    'model_version': model_version,
                    'actual_points': int(row['actual_points']),
                    'actual_points_per_90': float(row.get('actual_points_per_90', 0)),
                    'actual_minutes': int(row.get('actual_minutes', 0)),
                    'prediction_error': float(row['prediction_error']),
                    'absolute_error': float(row['absolute_error']),
                    'squared_error': float(row['squared_error']),
                    'is_validated': True,
                    'validation_timestamp': datetime.utcnow().isoformat()
                }
                
                try:
                    self.db._execute_with_retry(
                        self.db.supabase_client.table('validation_tracking')
                        .update(update_record)
                        .eq('player_id', int(row['player_id']))
                        .eq('gw', gw)
                        .eq('model_version', model_version)
                    )
                    validated_count += 1
                except Exception as e:
                    logger.warning(f"Error updating validation for player {row['player_id']}: {e}")
            
            metrics = {
                'gameweek': gw,
                'model_version': model_version,
                'total_predictions': len(predictions_df),
                'validated_predictions': validated_count,
                'matched_players': len(merged),
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
                'r2_score': float(r2),
                'mean_actual_points': float(merged['actual_points'].mean()),
                'mean_predicted_ev': float(merged['predicted_ev'].mean()),
                'validation_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Validated GW{gw}: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.4f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error validating predictions for GW{gw}: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _get_predictions_for_gw(self, gw: int, model_version: str) -> pd.DataFrame:
        """Get all predictions for a gameweek."""
        try:
            response = self.db.supabase_client.table('validation_tracking')\
                .select('*')\
                .eq('gw', gw)\
                .eq('model_version', model_version)\
                .eq('is_validated', False)\
                .execute()
            
            if not response.data:
                return pd.DataFrame()
            
            return pd.DataFrame(response.data)
            
        except Exception as e:
            logger.error(f"Error fetching predictions: {e}")
            return pd.DataFrame()
    
    def _get_actual_results_for_gw(self, gw: int) -> pd.DataFrame:
        """Get actual FPL results for a gameweek."""
        try:
            # Get from current_season_history table
            history = self.db.get_current_season_history()
            
            if history.empty:
                return pd.DataFrame()
            
            # Filter for the specific gameweek
            gw_data = history[history['gw'] == gw].copy()
            
            if gw_data.empty:
                return pd.DataFrame()
            
            # Calculate points per 90
            gw_data['actual_points_per_90'] = (
                gw_data['total_points'] / (gw_data['minutes'] / 90.0)
            ).replace([float('inf'), -float('inf')], 0).fillna(0)
            
            # Select relevant columns
            result = gw_data[[
                'player_id', 'total_points', 'actual_points_per_90', 'minutes'
            ]].copy()
            result.columns = ['player_id', 'actual_points', 'actual_points_per_90', 'actual_minutes']
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching actual results: {e}")
            return pd.DataFrame()
    
    def get_validation_summary(self, model_version: str = 'v5.0', 
                               min_gw: Optional[int] = None,
                               max_gw: Optional[int] = None) -> Dict:
        """
        Get validation summary across multiple gameweeks.
        
        Args:
            model_version: Model version to summarize
            min_gw: Minimum gameweek (optional)
            max_gw: Maximum gameweek (optional)
        
        Returns:
            Dictionary with summary metrics
        """
        try:
            query = self.db.supabase_client.table('validation_tracking')\
                .select('*')\
                .eq('model_version', model_version)\
                .eq('is_validated', True)
            
            if min_gw:
                query = query.gte('gw', min_gw)
            if max_gw:
                query = query.lte('gw', max_gw)
            
            response = query.execute()
            
            if not response.data:
                return {'error': 'No validated predictions found'}
            
            df = pd.DataFrame(response.data)
            
            # Calculate overall metrics
            overall_mae = df['absolute_error'].mean()
            overall_rmse = (df['squared_error'].mean()) ** 0.5
            
            try:
                from sklearn.metrics import r2_score
                overall_r2 = r2_score(df['actual_points'], df['predicted_ev'])
            except ImportError:
                # Fallback R² calculation
                ss_res = ((df['actual_points'] - df['predicted_ev']) ** 2).sum()
                ss_tot = ((df['actual_points'] - df['actual_points'].mean()) ** 2).sum()
                overall_r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Per-gameweek breakdown
            gw_metrics = []
            for gw in sorted(df['gw'].unique()):
                gw_data = df[df['gw'] == gw]
                gw_mae = gw_data['absolute_error'].mean()
                gw_rmse = (gw_data['squared_error'].mean()) ** 0.5
                try:
                    from sklearn.metrics import r2_score
                    gw_r2 = r2_score(gw_data['actual_points'], gw_data['predicted_ev'])
                except ImportError:
                    # Fallback R² calculation
                    ss_res = ((gw_data['actual_points'] - gw_data['predicted_ev']) ** 2).sum()
                    ss_tot = ((gw_data['actual_points'] - gw_data['actual_points'].mean()) ** 2).sum()
                    gw_r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                gw_metrics.append({
                    'gameweek': int(gw),
                    'predictions': len(gw_data),
                    'mae': float(gw_mae),
                    'rmse': float(gw_rmse),
                    'r2_score': float(gw_r2)
                })
            
            return {
                'model_version': model_version,
                'total_validated_predictions': len(df),
                'gameweeks_validated': len(df['gw'].unique()),
                'overall_mae': float(overall_mae),
                'overall_rmse': float(overall_rmse),
                'overall_r2_score': float(overall_r2),
                'per_gameweek': gw_metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            return {'error': str(e)}

