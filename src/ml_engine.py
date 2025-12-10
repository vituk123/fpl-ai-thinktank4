"""
FINAL ROBUST ML Engine for FPL Optimizer - v4.6
Handles missing tables, schema mismatches, and all edge cases
"""
import logging
import pickle
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import xgboost as xgb
from database import DatabaseManager

logger = logging.getLogger(__name__)

class MLEngine:
    BASE_FEATURES = [
        'minutes_rolling_3', 'total_points_rolling_3', 'xg_rolling_3', 'xa_rolling_3', 
        'ict_index_rolling_3', 'total_points_rolling_5', 'xg_rolling_5', 'xa_rolling_5',
        'fixture_difficulty', 'was_home', 'value', 'selected'
    ]
    
    # Advanced fixture features (optional, will be added if available)
    ADVANCED_FIXTURE_FEATURES = [
        'fdr_custom', 'fdr_defensive', 'fdr_attacking', 
        'fdr_3gw', 'fdr_5gw', 'fdr_8gw'
    ]
    
    @property
    def ALL_FEATURES(self):
        """Returns all features including interaction features"""
        return self.BASE_FEATURES + ['xg_x_ease', 'points_x_ease']

    def __init__(self, db_manager: DatabaseManager, model_version: str = "v4.6"):
        self.db_manager = db_manager
        self.model_version = model_version
        self.model_def = None 
        self.model_att = None 
        self.is_trained = False
        # Fine-tuning models (non-destructive)
        self.fine_tune_model_def = None
        self.fine_tune_model_att = None
        self.fine_tune_weight = 0.0  # Weight for fine-tuned predictions

        # CONSERVATIVE HYPERPARAMETERS
        self.model_config = {
            'max_depth': 4,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1
        }

        self.time_decay_weights = {
            '2025-26': 1.0, 
            '2024-25': 0.7,
            '2023-24': 0.5,
            'Archived': 0.4
        }

        logger.info(f"ML Engine initialized ({model_version})")

    def load_data(self) -> pd.DataFrame:
        try:
            logger.info("Loading training data...")
            
            # ROBUST: Try to get data from both tables, handle missing tables gracefully
            archived = pd.DataFrame()
            current = pd.DataFrame()
            
            try:
                archived = self.db_manager.get_player_history()
                logger.info(f"   Loaded {len(archived)} records from player_history")
            except Exception as e:
                logger.warning(f"   No player_history table or error: {e}")
            
            try:
                current = self.db_manager.get_current_season_history()
                logger.info(f"   Loaded {len(current)} records from current_season_history")
            except Exception as e:
                logger.warning(f"   Error loading current_season_history: {e}")

            # If both failed, try direct SQL query as fallback
            if archived.empty and current.empty:
                logger.warning("   Both table queries failed, trying direct SQL...")
                try:
                    current = self.db_manager.get_current_season_history()
                except:
                    logger.error("   Completely failed to load any data")
                    return pd.DataFrame()

            dfs = []
            if not archived.empty:
                if 'season' not in archived.columns: 
                    archived['season'] = 'Archived'
                
                # ROBUST: Check if player_id exists, if not try different column names
                if 'player_id' not in archived.columns:
                    # Try other possible column names
                    id_columns = ['element', 'id', 'player_id', 'playerid']
                    for col in id_columns:
                        if col in archived.columns:
                            archived['player_id'] = archived[col]
                            logger.info(f"   Using '{col}' as player_id")
                            break
                    
                    # If still no ID column, create one
                    if 'player_id' not in archived.columns:
                        logger.warning("   No player ID column found, creating synthetic IDs")
                        archived['player_id'] = range(len(archived))
                
                # Add element_type if missing
                if 'element_type' not in archived.columns:
                    archived['element_type'] = 3  # Default to midfielder
                    logger.info("   Added default element_type=3 for archive data")
                
                dfs.append(archived)
            
            if not current.empty:
                current['season'] = '2025-26'
                dfs.append(current)

            if not dfs: 
                logger.error("No training data available from any source")
                return pd.DataFrame()

            combined = pd.concat(dfs, ignore_index=True)
            logger.info(f"   Combined dataset: {len(combined)} total records")
            
            return self._handle_missing_values(combined)
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame()

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Robust NaN/Inf handling"""
        if df.empty:
            return df
            
        logger.info("   Handling missing values...")
        
        # Essential columns that should exist
        essential_cols = ['player_id', 'gw', 'minutes', 'total_points']
        missing_essential = [col for col in essential_cols if col not in df.columns]
        
        if missing_essential:
            logger.warning(f"   Missing essential columns: {missing_essential}")
            
            # Try to create missing columns
            if 'player_id' not in df.columns and 'id' in df.columns:
                df['player_id'] = df['id']
            elif 'player_id' not in df.columns:
                df['player_id'] = range(len(df))
                
            if 'gw' not in df.columns:
                df['gw'] = 1  # Default gameweek
                
            if 'minutes' not in df.columns:
                df['minutes'] = 0
                
            if 'total_points' not in df.columns:
                df['total_points'] = 0
        
        # Handle numeric columns
        numerics = ['minutes', 'total_points', 'xg', 'xa', 'ict_index', 'value', 'selected']
        for c in numerics:
            if c in df.columns: 
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # Clean all numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        logger.info(f"   Data cleaned: {len(df)} records with NaN/Inf handled")
        return df

    def engineer_features(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        try:
            if df.empty:
                return df
                
            logger.info("   Engineering features...")
            df = df.copy()
            
            # Ensure required columns exist
            required_cols = ['player_id', 'gw', 'minutes', 'total_points']
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"   Missing required column {col}, adding default")
                    if col == 'player_id':
                        df[col] = range(len(df))
                    elif col == 'gw':
                        df[col] = 1
                    elif col in ['minutes', 'total_points']:
                        df[col] = 0
            
            sort_cols = [c for c in ['season', 'player_id', 'gw'] if c in df.columns]
            if sort_cols: 
                df = df.sort_values(sort_cols).reset_index(drop=True)

            df = self._calculate_rolling(df)

            # Calculate points per 90 safely
            df['points_per_90'] = 0.0
            mask_valid_minutes = (df['minutes'] > 0) & (df['minutes'] <= 90)
            if mask_valid_minutes.any():
                df.loc[mask_valid_minutes, 'points_per_90'] = (
                    df.loc[mask_valid_minutes, 'total_points'] / df.loc[mask_valid_minutes, 'minutes']
                ) * 90
                # Cap extreme values
                df.loc[mask_valid_minutes, 'points_per_90'] = df.loc[mask_valid_minutes, 'points_per_90'].clip(0, 15)

            # Calculate rolling points per 90
            if 'gw' in df.columns:
                df = df.sort_values(['player_id', 'gw'])

            group_cols = ['season', 'player_id'] if 'season' in df.columns and 'player_id' in df.columns else 'player_id'
            grouped = df.groupby(group_cols)

            for window in [3, 5]:
                col_name = f'points_per_90_rolling_{window}'
                df[col_name] = grouped['points_per_90'].transform(
                    lambda x: x.rolling(window=min(window, len(x)), min_periods=1).mean().fillna(0)
                )

            # Default values for missing features
            if 'fixture_difficulty' not in df.columns: 
                df['fixture_difficulty'] = 3
            if 'was_home' not in df.columns: 
                df['was_home'] = 0.5
            df['was_home'] = df['was_home'].astype(int)
            
            # Add advanced fixture features if available
            for feature in self.ADVANCED_FIXTURE_FEATURES:
                if feature not in df.columns:
                    # Use basic fixture_difficulty as fallback
                    df[feature] = df.get('fixture_difficulty', 3)

            # Safe interaction features - use appropriate FDR based on position
            inv_fdr = (6 - df['fixture_difficulty'].fillna(3)).clip(1, 5)  # Clamp to reasonable range
            
            # Get rolling features with fallback - ensure they're in the dataframe
            if 'xg_rolling_3' not in df.columns:
                if 'xg_rolling_5' in df.columns:
                    df['xg_rolling_3'] = df['xg_rolling_5']
                elif 'xg' in df.columns:
                    df['xg_rolling_3'] = df['xg'].fillna(0)
                else:
                    df['xg_rolling_3'] = 0.0
            
            if 'total_points_rolling_3' not in df.columns:
                if 'total_points_rolling_5' in df.columns:
                    df['total_points_rolling_3'] = df['total_points_rolling_5']
                elif 'total_points' in df.columns:
                    df['total_points_rolling_3'] = df['total_points'].fillna(0)
                else:
                    df['total_points_rolling_3'] = 0.0
            
            # Fill NaN values
            df['xg_rolling_3'] = df['xg_rolling_3'].fillna(0)
            df['total_points_rolling_3'] = df['total_points_rolling_3'].fillna(0)
            
            # Use advanced FDR if available
            if 'fdr_attacking' in df.columns and 'fdr_defensive' in df.columns and 'element_type' in df.columns:
                inv_fdr_attacking = (6 - df['fdr_attacking'].fillna(df['fixture_difficulty'])).clip(1, 5)
                inv_fdr_defensive = (6 - df['fdr_defensive'].fillna(df['fixture_difficulty'])).clip(1, 5)
                
                # Apply based on position
                attacking_mask = df['element_type'].isin([3, 4])  # MID, FWD
                defensive_mask = df['element_type'].isin([1, 2])  # GK, DEF
                
                # Initialize with basic FDR
                df['xg_x_ease'] = df['xg_rolling_3'] * inv_fdr
                df['points_x_ease'] = df['total_points_rolling_3'] * inv_fdr
                
                # Override for attacking players
                if attacking_mask.any():
                    df.loc[attacking_mask, 'xg_x_ease'] = df.loc[attacking_mask, 'xg_rolling_3'] * inv_fdr_attacking.loc[attacking_mask]
                    df.loc[attacking_mask, 'points_x_ease'] = df.loc[attacking_mask, 'total_points_rolling_3'] * inv_fdr_attacking.loc[attacking_mask]
                
                # Override for defensive players
                if defensive_mask.any():
                    df.loc[defensive_mask, 'xg_x_ease'] = df.loc[defensive_mask, 'xg_rolling_3'] * inv_fdr_defensive.loc[defensive_mask]
                    df.loc[defensive_mask, 'points_x_ease'] = df.loc[defensive_mask, 'total_points_rolling_3'] * inv_fdr_defensive.loc[defensive_mask]
            else:
                # Use basic FDR for all
                df['xg_x_ease'] = df['xg_rolling_3'] * inv_fdr
                df['points_x_ease'] = df['total_points_rolling_3'] * inv_fdr

            if is_training and 'season' in df.columns:
                df['sample_weight'] = df['season'].map(self.time_decay_weights).fillna(0.5)

            # Add missing base features with defaults
            for feature in self.BASE_FEATURES:
                if feature not in df.columns:
                    if 'rolling_3' in feature:
                        df[feature] = 0.0
                    elif feature in ['fixture_difficulty', 'was_home', 'value', 'selected']:
                        df[feature] = df.get(feature, 3 if feature == 'fixture_difficulty' else 0.5 if feature == 'was_home' else 100)

            # Final cleanup - ensure interaction features exist
            if 'xg_x_ease' not in df.columns:
                logger.warning("   xg_x_ease not created, adding default")
                df['xg_x_ease'] = 0.0
            if 'points_x_ease' not in df.columns:
                logger.warning("   points_x_ease not created, adding default")
                df['points_x_ease'] = 0.0
            
            # Final cleanup
            for col in self.BASE_FEATURES + ['xg_x_ease', 'points_x_ease']:
                if col in df.columns:
                    df[col] = df[col].replace([np.inf, -np.inf], 0).fillna(0)

            logger.info(f"   Feature engineering complete: {len(df)} records, {len(self.BASE_FEATURES)} base features + 2 interaction features")
            logger.info(f"   Interaction features present: xg_x_ease={('xg_x_ease' in df.columns)}, points_x_ease={('points_x_ease' in df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Feature engineering error: {e}")
            return pd.DataFrame()

    def _calculate_rolling(self, df: pd.DataFrame) -> pd.DataFrame:
        metrics = ['minutes', 'total_points', 'xg', 'xa', 'ict_index']
        windows = [3, 5]

        if 'gw' in df.columns:
            df = df.sort_values(['player_id', 'gw'])

        group_cols = ['season', 'player_id'] if 'season' in df.columns and 'player_id' in df.columns else 'player_id'
        grouped = df.groupby(group_cols)

        for w in windows:
            for m in metrics:
                if m not in df.columns: 
                    continue
                col = f"{m}_rolling_{w}"
                df[col] = grouped[m].transform(
                    lambda x: x.rolling(window=min(w, len(x)), min_periods=1).mean().fillna(0)
                )
        return df

    def _train_single_model(self, X, y, weights, name):
        try:
            X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
                X, y, weights, test_size=0.2, random_state=42
            )

            model = xgb.XGBRegressor(**self.model_config)
            model.fit(
                X_train, y_train, 
                sample_weight=w_train, 
                eval_set=[(X_test, y_test)],
                sample_weight_eval_set=[w_test],
                verbose=False
            )

            preds = model.predict(X_test)
            r2 = r2_score(y_test, preds, sample_weight=w_test)
            mae = mean_absolute_error(y_test, preds, sample_weight=w_test)
            logger.info(f"   🔹 {name} Model -> R2: {r2:.4f} | MAE: {mae:.2f}")
            return model
        except Exception as e:
            logger.error(f"   Error training {name} model: {e}")
            return None

    def train_model(self) -> dict:
        logger.info(f"Starting model training ({self.model_version})...")
        data = self.load_data()
        if data.empty: 
            logger.error("No data available for training")
            return {}

        processed_data = self.engineer_features(data, is_training=True)
        if processed_data.empty:
            logger.error("No data after feature engineering")
            return {}

        # Smart filtering: include all data but exclude invalid targets
        training_data = processed_data[processed_data['points_per_90'] >= 0].copy()
        logger.info(f"   Training on {len(training_data)} rows with valid targets")

        features = self.ALL_FEATURES
        
        # Ensure element_type exists
        if 'element_type' not in training_data.columns:
            logger.warning("   No element_type found, creating proxy based on goals")
            if 'goals_scored' in training_data.columns:
                max_goals = training_data.groupby('player_id')['goals_scored'].transform('max')
                training_data['element_type'] = max_goals.apply(lambda x: 2 if x < 1 else 3)
            else:
                training_data['element_type'] = 3  # Default to midfielder

        # Train defensive model
        mask_def = training_data['element_type'].isin([1, 2])
        if mask_def.sum() > 50:
            self.model_def = self._train_single_model(
                training_data[mask_def][features],
                training_data[mask_def]['points_per_90'],
                training_data[mask_def].get('sample_weight', pd.Series([1]*len(training_data[mask_def]))),
                "Defensive"
            )
        else:
            logger.warning(f"   Insufficient defensive data: {mask_def.sum()} records")

        # Train attacking model  
        mask_att = training_data['element_type'].isin([3, 4])
        if mask_att.sum() > 50:
            self.model_att = self._train_single_model(
                training_data[mask_att][features],
                training_data[mask_att]['points_per_90'],
                training_data[mask_att].get('sample_weight', pd.Series([1]*len(training_data[mask_att]))),
                "Attacking"
            )
        else:
            logger.warning(f"   Insufficient attacking data: {mask_att.sum()} records")

        self.is_trained = True
        logger.info(f"   Training complete - Defensive: {self.model_def is not None}, Attacking: {self.model_att is not None}")
        return {'status': 'success'}
    
    def fine_tune_with_feedback(self, feedback_df: pd.DataFrame, targets_df: pd.DataFrame, learning_rate: float = 0.01) -> dict:
        """
        Fine-tune the ML model using feedback data (actual outcomes vs predictions).
        This is a non-destructive operation that improves the model incrementally.
        
        Args:
            feedback_df: DataFrame with features from feedback data
            targets_df: DataFrame with actual outcomes (target_points column)
            learning_rate: Learning rate for fine-tuning (lower = more conservative)
        
        Returns:
            Dictionary with fine-tuning results
        """
        try:
            if feedback_df.empty or targets_df.empty:
                logger.warning("No feedback data provided for fine-tuning")
                return {'status': 'skipped', 'reason': 'no_data'}
            
            if not self.is_trained or (self.model_def is None and self.model_att is None):
                logger.warning("Models not trained yet, cannot fine-tune")
                return {'status': 'skipped', 'reason': 'not_trained'}
            
            # Merge feedback with targets
            training_data = feedback_df.merge(
                targets_df[['player_id', 'gw', 'target_points']],
                on=['player_id', 'gw'],
                how='inner'
            )
            
            if training_data.empty:
                logger.warning("No matching feedback data after merge")
                return {'status': 'skipped', 'reason': 'no_match'}
            
            # Engineer features for feedback data
            processed_data = self.engineer_features(training_data, is_training=True)
            if processed_data.empty:
                logger.warning("No data after feature engineering for fine-tuning")
                return {'status': 'skipped', 'reason': 'feature_engineering_failed'}
            
            # Calculate points_per_90 for targets
            if 'minutes' in processed_data.columns:
                processed_data['target_points_per_90'] = (
                    processed_data['target_points'] / processed_data['minutes'].clip(1, 90)
                ) * 90
            else:
                processed_data['target_points_per_90'] = processed_data['target_points']
            
            # Filter valid targets
            training_data = processed_data[processed_data['target_points_per_90'] >= 0].copy()
            if training_data.empty:
                logger.warning("No valid targets for fine-tuning")
                return {'status': 'skipped', 'reason': 'no_valid_targets'}
            
            logger.info(f"Fine-tuning with {len(training_data)} feedback samples")
            
            features = self.ALL_FEATURES
            results = {}
            
            # Fine-tune defensive model
            mask_def = training_data['element_type'].isin([1, 2])
            if mask_def.sum() > 10 and self.model_def is not None:
                X_feedback = training_data[mask_def][features]
                y_feedback = training_data[mask_def]['target_points_per_90']
                
                # Use lower learning rate for fine-tuning (more conservative)
                fine_tune_config = self.model_config.copy()
                fine_tune_config['learning_rate'] = learning_rate
                fine_tune_config['n_estimators'] = 50  # Fewer trees for fine-tuning
                
                # Create a new model and train on feedback data
                fine_tune_model = xgb.XGBRegressor(**fine_tune_config)
                fine_tune_model.fit(X_feedback, y_feedback)
                
                # Blend predictions: 90% original model, 10% fine-tuned model
                # This is non-destructive - we don't replace the original model
                # Instead, we'll use a weighted average during prediction
                self.fine_tune_model_def = fine_tune_model
                self.fine_tune_weight = 0.1  # 10% weight for fine-tuned model
                
                # Evaluate fine-tuning performance
                preds = fine_tune_model.predict(X_feedback)
                from sklearn.metrics import mean_absolute_error, r2_score
                mae = mean_absolute_error(y_feedback, preds)
                r2 = r2_score(y_feedback, preds)
                
                results['defensive'] = {
                    'samples': mask_def.sum(),
                    'mae': mae,
                    'r2': r2
                }
                logger.info(f"   Fine-tuned defensive model: {mask_def.sum()} samples, MAE: {mae:.2f}, R2: {r2:.4f}")
            
            # Fine-tune attacking model
            mask_att = training_data['element_type'].isin([3, 4])
            if mask_att.sum() > 10 and self.model_att is not None:
                X_feedback = training_data[mask_att][features]
                y_feedback = training_data[mask_att]['target_points_per_90']
                
                fine_tune_config = self.model_config.copy()
                fine_tune_config['learning_rate'] = learning_rate
                fine_tune_config['n_estimators'] = 50
                
                fine_tune_model = xgb.XGBRegressor(**fine_tune_config)
                fine_tune_model.fit(X_feedback, y_feedback)
                
                self.fine_tune_model_att = fine_tune_model
                
                preds = fine_tune_model.predict(X_feedback)
                from sklearn.metrics import mean_absolute_error, r2_score
                mae = mean_absolute_error(y_feedback, preds)
                r2 = r2_score(y_feedback, preds)
                
                results['attacking'] = {
                    'samples': mask_att.sum(),
                    'mae': mae,
                    'r2': r2
                }
                logger.info(f"   Fine-tuned attacking model: {mask_att.sum()} samples, MAE: {mae:.2f}, R2: {r2:.4f}")
            
            if results:
                logger.info(f"Fine-tuning complete: {results}")
                return {'status': 'success', 'results': results}
            else:
                return {'status': 'skipped', 'reason': 'insufficient_data'}
                
        except Exception as e:
            logger.error(f"Error during fine-tuning: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def __init__(self, db_manager: DatabaseManager, model_version: str = "v4.6"):
        self.db_manager = db_manager
        self.model_version = model_version
        self.model_def = None 
        self.model_att = None 
        self.is_trained = False
        # Fine-tuning models (non-destructive)
        self.fine_tune_model_def = None
        self.fine_tune_model_att = None
        self.fine_tune_weight = 0.0  # Weight for fine-tuned predictions

    def _calculate_recent_form_metrics(self, history: pd.DataFrame, lookback_gws: int = 3) -> pd.DataFrame:
        """
        Calculate recent form metrics directly from gameweek history.
        More reliable than rolling averages which can be skewed by older data.
        """
        if history.empty or 'gw' not in history.columns:
            return pd.DataFrame()
        
        # Get the most recent gameweeks
        recent_gws = sorted(history['gw'].unique(), reverse=True)[:lookback_gws]
        recent_history = history[history['gw'].isin(recent_gws)].copy()
        
        if recent_history.empty:
            return pd.DataFrame()
        
        # Calculate form metrics per player
        # Only count gameweeks where player actually played (minutes > 0)
        played_history = recent_history[recent_history['minutes'] > 0].copy()
        
        form_metrics = recent_history.groupby('player_id').agg({
            'total_points': ['sum', 'mean'],
            'minutes': ['sum', 'mean'],
            'gw': 'max'
        }).reset_index()
        
        form_metrics.columns = [
            'player_id', 'recent_points_sum', 'recent_points_avg',
            'recent_minutes_sum', 'recent_minutes_avg', 'last_gw_played'
        ]
        
        # Count games actually played (where minutes > 0)
        games_played = played_history.groupby('player_id').size().reset_index(name='recent_games_played')
        form_metrics = form_metrics.merge(games_played, on='player_id', how='left')
        form_metrics['recent_games_played'] = form_metrics['recent_games_played'].fillna(0).astype(int)
        
        # Recalculate average points per game (only for games played)
        form_metrics['recent_points_per_game'] = 0.0
        played_mask = form_metrics['recent_games_played'] > 0
        if played_mask.any():
            form_metrics.loc[played_mask, 'recent_points_per_game'] = (
                form_metrics.loc[played_mask, 'recent_points_sum'] / 
                form_metrics.loc[played_mask, 'recent_games_played']
            )
        
        # Calculate points per 90
        form_metrics['recent_points_per_90'] = 0.0
        valid_minutes = form_metrics['recent_minutes_sum'] > 0
        if valid_minutes.any():
            form_metrics.loc[valid_minutes, 'recent_points_per_90'] = (
                form_metrics.loc[valid_minutes, 'recent_points_sum'] / 
                form_metrics.loc[valid_minutes, 'recent_minutes_sum']
            ) * 90
        
        # Check if played in most recent gameweek
        most_recent_gw = max(recent_gws)
        form_metrics['played_most_recent_gw'] = form_metrics['last_gw_played'] == most_recent_gw
        
        return form_metrics

    def _apply_form_adjustments(self, X: pd.DataFrame, form_metrics: pd.DataFrame) -> pd.DataFrame:
        """
        Apply form-based adjustments following FPL best practices.
        Uses tiered approach: completely inactive → poor form → rotation risk → form boost.
        """
        if form_metrics.empty:
            return X
        
        # Merge form metrics
        X = X.merge(form_metrics, on='player_id', how='left')
        
        # Debug: Check if merge worked
        if 'recent_points_per_game' not in X.columns and 'recent_points_avg' in X.columns:
            # Fallback: calculate per_game from avg if not available
            # This handles cases where form_metrics might be missing the per_game column
            games_played = X['recent_games_played'].fillna(1)  # Avoid division by zero
            X['recent_points_per_game'] = X['recent_points_avg'] * (3 / games_played.clip(1, 3))
        
        # TIER 1: Completely inactive (0 pts, 0 mins)
        completely_inactive = (
            (X['recent_points_sum'].fillna(-1) == 0) &
            (X['recent_minutes_sum'].fillna(0) == 0)
        )
        if completely_inactive.any():
            X.loc[completely_inactive, 'predicted_ev'] = 0.0
            logger.info(f"   Zeroed {completely_inactive.sum()} completely inactive players")
        
        active = ~completely_inactive
        
        # TIER 2: Poor form penalties
        # 2a: 0 points but played
        played_no_points = (
            active & (X['recent_points_sum'].fillna(-1) == 0) & (X['recent_minutes_sum'].fillna(0) > 0)
        )
        if played_no_points.any():
            X.loc[played_no_points, 'predicted_ev'] = X.loc[played_no_points, 'predicted_ev'].clip(0, 1.0)
            logger.info(f"   Capped {played_no_points.sum()} players to 1.0 EV (played but 0 pts)")
        
        # Use points per game (only games played) instead of points per GW (includes non-played GWs)
        if 'recent_points_per_game' in X.columns:
            points_per_game = X['recent_points_per_game'].fillna(0)
        else:
            # Fallback to average if per_game not available
            points_per_game = X['recent_points_avg'].fillna(0)
        
        # 2b: Very poor form (<0.5 pts/game)
        very_poor = active & (points_per_game < 0.5) & (points_per_game > 0)
        if very_poor.any():
            X.loc[very_poor, 'predicted_ev'] = X.loc[very_poor, 'predicted_ev'].clip(0, 1.5)
            logger.info(f"   Capped {very_poor.sum()} players to 1.5 EV (very poor form <0.5 pts/game)")
        
        # 2c: Poor form (<1.5 pts/game) - more aggressive threshold
        poor = active & (points_per_game >= 0.5) & (points_per_game < 1.5)
        if poor.any():
            X.loc[poor, 'predicted_ev'] = X.loc[poor, 'predicted_ev'].clip(0, 2.5)
            logger.info(f"   Capped {poor.sum()} players to 2.5 EV (poor form <1.5 pts/game)")
        
        # 2d: Low minutes (<30/game)
        low_mins = active & (X['recent_minutes_avg'].fillna(0) > 0) & (X['recent_minutes_avg'].fillna(0) < 30)
        if low_mins.any():
            minute_factor = (X.loc[low_mins, 'recent_minutes_avg'] / 30.0).clip(0.2, 1.0)
            X.loc[low_mins, 'predicted_ev'] = X.loc[low_mins, 'predicted_ev'] * minute_factor
            logger.info(f"   Reduced EV for {low_mins.sum()} players with low minutes")
        
        # TIER 3: Rotation risk (didn't play last GW)
        rotation_risk = active & (X['played_most_recent_gw'].fillna(False) == False)
        if rotation_risk.any():
            X.loc[rotation_risk, 'predicted_ev'] = X.loc[rotation_risk, 'predicted_ev'] * 0.6
            logger.info(f"   Reduced EV by 40% for {rotation_risk.sum()} players (rotation risk)")
        
        # TIER 4: Poor season performance + missing form data = likely unreliable prediction
        # If player has <30 total points AND no recent form data, cap aggressively
        if 'total_points' in X.columns:
            low_season_points = X['total_points'].fillna(0) < 30
            missing_form = X['recent_points_sum'].isna() | (X['recent_points_sum'].fillna(0) == 0)
            unreliable = active & low_season_points & missing_form
            if unreliable.any():
                X.loc[unreliable, 'predicted_ev'] = X.loc[unreliable, 'predicted_ev'].clip(0, 3.0)
                logger.info(f"   Capped {unreliable.sum()} players to 3.0 EV (low season points + no recent form)")
        
        # TIER 5: Very low season points regardless of form (safety net)
        # Cap players with low total points to prevent overprediction
        if 'total_points' in X.columns:
            # Tier 5a: <25 pts -> max 2.5 EV
            very_low_points = active & (X['total_points'].fillna(0) < 25)
            if very_low_points.any():
                X.loc[very_low_points, 'predicted_ev'] = X.loc[very_low_points, 'predicted_ev'].clip(0, 2.5)
                logger.info(f"   Capped {very_low_points.sum()} players to 2.5 EV (very low season points <25)")
            
            # Tier 5b: 25-35 pts -> max 5.0 EV (prevent overprediction for unproven players)
            low_points = active & (X['total_points'].fillna(0) >= 25) & (X['total_points'].fillna(0) < 35)
            if low_points.any():
                X.loc[low_points, 'predicted_ev'] = X.loc[low_points, 'predicted_ev'].clip(0, 5.0)
                logger.info(f"   Capped {low_points.sum()} players to 5.0 EV (low season points 25-35)")
        
        return X

    def predict_player_performance(self, player_data: pd.DataFrame) -> pd.DataFrame:
        if not self.is_trained: 
            logger.warning("Model not trained, returning empty predictions")
            return pd.DataFrame()

        logger.info("   Generating ML predictions...")
        
        snapshot = player_data.copy()
        if 'id' in snapshot.columns: 
            snapshot['player_id'] = snapshot['id']
        
        if 'player_id' not in snapshot.columns:
            logger.warning("   No player ID in snapshot data")
            return pd.DataFrame()

        enriched_df = snapshot
        
        # Store recent gameweek data for form-based penalties
        recent_form_data = None
        
        # Enrich with history and calculate form metrics
        form_metrics = pd.DataFrame()
        if self.db_manager:
            try:
                history = self.db_manager.get_current_season_history()
                if not history.empty:
                    history['season'] = '2025-26'
                    
                    # Calculate recent form metrics using new method
                    form_metrics = self._calculate_recent_form_metrics(history, lookback_gws=3)
                    if not form_metrics.empty:
                        logger.info(f"   Calculated form metrics for {form_metrics['player_id'].nunique()} players")
                    
                    # Prepare snapshot for rolling calculations
                    snapshot_row = snapshot.copy()
                    snapshot_row['gw'] = 999 
                    snapshot_row['season'] = '2025-26'
                    for c in ['minutes', 'total_points', 'xg', 'xa', 'ict_index']:
                        if c not in snapshot_row.columns: 
                            snapshot_row[c] = 0

                    combined = pd.concat([history, snapshot_row], ignore_index=True)
                    combined = self._calculate_rolling(combined)

                    rolling_cols = [c for c in combined.columns if 'rolling' in c]
                    current_rolling = combined[combined['gw'] == 999][['player_id'] + rolling_cols]
                    current_rolling = current_rolling.drop_duplicates(subset=['player_id'])

                    enriched_df = snapshot.merge(current_rolling, on='player_id', how='left')
                    logger.info(f"   Enriched {len(enriched_df)} players with rolling features")
            except Exception as e:
                logger.warning(f"   History enrichment failed: {e}")
                enriched_df = snapshot

        # Feature engineering
        X = self.engineer_features(enriched_df, is_training=False)
        if X.empty:
            logger.error("   No data after feature engineering for prediction")
            return pd.DataFrame()
        
        # DEBUG: Check what features are actually in X after engineering
        logger.info(f"   DEBUG: X.columns after engineering: {list(X.columns)}")
        logger.info(f"   DEBUG: X.shape: {X.shape}")
        logger.info(f"   DEBUG: Interaction features in X: xg_x_ease={'xg_x_ease' in X.columns}, points_x_ease={'points_x_ease' in X.columns}")
            
        features = self.ALL_FEATURES
        logger.info(f"   DEBUG: Required features: {features}")
        logger.info(f"   DEBUG: Missing from X: {[f for f in features if f not in X.columns]}")
        
        # Ensure all required features exist (in case engineer_features didn't create them)
        missing_features = [f for f in features if f not in X.columns]
        if missing_features:
            logger.warning(f"   Missing features: {missing_features}, adding defaults")
            # Ensure fixture_difficulty exists for interaction features
            if 'fixture_difficulty' not in X.columns:
                X['fixture_difficulty'] = 3
            inv_fdr = (6 - X['fixture_difficulty'].fillna(3)).clip(1, 5)
            
            # Ensure rolling features exist for interaction features
            if 'xg_rolling_3' not in X.columns:
                if 'xg_rolling_5' in X.columns:
                    X['xg_rolling_3'] = X['xg_rolling_5']
                elif 'xg' in X.columns:
                    X['xg_rolling_3'] = X['xg'].fillna(0)
                else:
                    X['xg_rolling_3'] = 0.0
            
            if 'total_points_rolling_3' not in X.columns:
                if 'total_points_rolling_5' in X.columns:
                    X['total_points_rolling_3'] = X['total_points_rolling_5']
                elif 'total_points' in X.columns:
                    X['total_points_rolling_3'] = X['total_points'].fillna(0)
                else:
                    X['total_points_rolling_3'] = 0.0
            
            # Fill NaN values
            X['xg_rolling_3'] = X['xg_rolling_3'].fillna(0)
            X['total_points_rolling_3'] = X['total_points_rolling_3'].fillna(0)
            
            for feat in missing_features:
                if feat == 'xg_x_ease':
                    X['xg_x_ease'] = X['xg_rolling_3'] * inv_fdr
                elif feat == 'points_x_ease':
                    X['points_x_ease'] = X['total_points_rolling_3'] * inv_fdr
                else:
                    X[feat] = 0.0
            
            # Double-check that interaction features exist
            if 'xg_x_ease' not in X.columns:
                X['xg_x_ease'] = X['xg_rolling_3'] * inv_fdr
            if 'points_x_ease' not in X.columns:
                X['points_x_ease'] = X['total_points_rolling_3'] * inv_fdr
        X['predicted_points_per_90'] = 0.0

        # Element type
        if 'element_type' not in X.columns:
            X['element_type'] = 3  # Default to midfielder

        mask_def = X['element_type'].isin([1, 2])
        mask_att = X['element_type'].isin([3, 4])

        # CRITICAL: Ensure all features exist before prediction
        missing_before_pred = [f for f in features if f not in X.columns]
        if missing_before_pred:
            logger.warning(f"   Creating missing features before prediction: {missing_before_pred}")
            for f in missing_before_pred:
                if f == 'xg_x_ease':
                    X['xg_x_ease'] = X.get('xg_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                elif f == 'points_x_ease':
                    X['points_x_ease'] = X.get('total_points_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                else:
                    X[f] = 0.0

        # Predict (use fine-tuned model if available, blend with original)
        if self.model_def and mask_def.any():
            # Final check - ensure all features are present
            final_missing = [f for f in features if f not in X.columns]
            if final_missing:
                logger.error(f"   CRITICAL: Still missing features: {final_missing}")
            
            # CRITICAL: Get model's expected feature order and match it exactly
            try:
                model_feature_names = self.model_def.get_booster().feature_names
                if model_feature_names:
                    # Use model's feature order
                    ordered_features = [f for f in model_feature_names if f in X.columns]
                    missing_model_features = [f for f in model_feature_names if f not in X.columns]
                    if missing_model_features:
                        logger.error(f"   Model expects features not in X: {missing_model_features}")
                        # Create missing features
                        for f in missing_model_features:
                            if f == 'xg_x_ease':
                                X['xg_x_ease'] = X.get('xg_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                            elif f == 'points_x_ease':
                                X['points_x_ease'] = X.get('total_points_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                            else:
                                X[f] = 0.0
                        ordered_features = [f for f in model_feature_names if f in X.columns]
                    preds = self.model_def.predict(X.loc[mask_def, ordered_features])
                else:
                    # Fallback to our feature order
                    preds = self.model_def.predict(X.loc[mask_def, features])
            except Exception as e:
                logger.warning(f"   Could not get model feature names: {e}, using default order")
                preds = self.model_def.predict(X.loc[mask_def, features])
            
            # Blend with fine-tuned model if available (non-destructive approach)
            if self.fine_tune_model_def is not None and self.fine_tune_weight > 0:
                fine_tune_preds = self.fine_tune_model_def.predict(X.loc[mask_def, features])
                # Weighted average: mostly original model, some fine-tuned
                preds = (1 - self.fine_tune_weight) * preds + self.fine_tune_weight * fine_tune_preds
            
            # Increased cap to allow better differentiation (was 10.0, now 15.0)
            # This allows top defenders to have higher EV than average ones
            X.loc[mask_def, 'predicted_points_per_90'] = np.clip(preds, 0, 15.0)
            
            # Sanity check: zero out predictions for players with no recent playing time
            if 'minutes_rolling_3' in X.columns and 'total_points_rolling_3' in X.columns:
                # Create full mask for inactive defensive players
                inactive_def_mask = mask_def & \
                    (X['minutes_rolling_3'].fillna(0) == 0) & \
                    (X['total_points_rolling_3'].fillna(0) == 0)
                if inactive_def_mask.any():
                    X.loc[inactive_def_mask, 'predicted_points_per_90'] = 0

        if self.model_att and mask_att.any():
            # Verify all features exist
            available_features = [f for f in features if f in X.columns]
            if len(available_features) != len(features):
                missing = set(features) - set(available_features)
                logger.error(f"   Feature mismatch: expected {len(features)}, have {len(available_features)}")
                logger.error(f"   Missing: {missing}")
                # Create missing features
                for f in missing:
                    if f == 'xg_x_ease':
                        X['xg_x_ease'] = X.get('xg_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                    elif f == 'points_x_ease':
                        X['points_x_ease'] = X.get('total_points_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                    else:
                        X[f] = 0.0
            
            # CRITICAL: Get model's expected feature order and match it exactly
            try:
                model_feature_names = self.model_att.get_booster().feature_names
                if model_feature_names:
                    # Use model's feature order
                    ordered_features = [f for f in model_feature_names if f in X.columns]
                    missing_model_features = [f for f in model_feature_names if f not in X.columns]
                    if missing_model_features:
                        logger.error(f"   Model expects features not in X: {missing_model_features}")
                        # Create missing features
                        for f in missing_model_features:
                            if f == 'xg_x_ease':
                                X['xg_x_ease'] = X.get('xg_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                            elif f == 'points_x_ease':
                                X['points_x_ease'] = X.get('total_points_rolling_3', 0) * (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                            else:
                                X[f] = 0.0
                        ordered_features = [f for f in model_feature_names if f in X.columns]
                    preds = self.model_att.predict(X.loc[mask_att, ordered_features])
                else:
                    # Fallback to our feature order
                    preds = self.model_att.predict(X.loc[mask_att, features])
            except Exception as e:
                logger.warning(f"   Could not get model feature names: {e}, using default order")
                preds = self.model_att.predict(X.loc[mask_att, features])
            
            # Blend with fine-tuned model if available (non-destructive approach)
            if self.fine_tune_model_att is not None and self.fine_tune_weight > 0:
                fine_tune_preds = self.fine_tune_model_att.predict(X.loc[mask_att, features])
                # Weighted average: mostly original model, some fine-tuned
                preds = (1 - self.fine_tune_weight) * preds + self.fine_tune_weight * fine_tune_preds
            
            # Increased cap to allow better differentiation (was 12.0, now 18.0)
            # This allows top midfielders/forwards to have higher EV than average ones
            X.loc[mask_att, 'predicted_points_per_90'] = np.clip(preds, 0, 18.0)
            
            # Sanity check: zero out predictions for players with no recent playing time
            if 'minutes_rolling_3' in X.columns and 'total_points_rolling_3' in X.columns:
                # Create full mask for inactive attacking players
                inactive_att_mask = mask_att & \
                    (X['minutes_rolling_3'].fillna(0) == 0) & \
                    (X['total_points_rolling_3'].fillna(0) == 0)
                if inactive_att_mask.any():
                    X.loc[inactive_att_mask, 'predicted_points_per_90'] = 0

        # Calculate expected minutes - IMPROVED: More realistic based on recent playing time
        if 'minutes_rolling_3' in X.columns:
            rolling_mins = X['minutes_rolling_3']
            expected_mins = rolling_mins.copy()
            
            # For players with 0 rolling minutes (inactive), set expected to 0
            zero_min_mask = (rolling_mins == 0) & rolling_mins.notna()
            expected_mins.loc[zero_min_mask] = 0
            
            # For players with valid rolling minutes, use them directly (more realistic)
            # Don't default to 90 - use actual recent average
            valid_rolling = rolling_mins.notna() & (rolling_mins > 0)
            # Keep the rolling average as-is for active players
            
            # For players with NaN (no history data), estimate based on season totals
            nan_mask = rolling_mins.isna()
            if nan_mask.any():
                if 'total_points' in X.columns and 'minutes' in X.columns:
                    nan_indices = X.index[nan_mask]
                    # Calculate season average minutes per game
                    season_mins = X.loc[nan_indices, 'minutes'].fillna(0)
                    # Estimate games played (rough: assume 1 game per ~90 mins if they have points)
                    # More realistic: use actual season average if available
                    has_season_data = season_mins > 0
                    if has_season_data.any():
                        # Estimate: if they have significant minutes, they're likely playing regularly
                        # Use a conservative estimate: 60-75 mins for regular players
                        estimated_mins = (season_mins / 14).clip(45, 75)  # Rough estimate: 14 GWs so far
                        expected_mins.loc[nan_indices[has_season_data]] = estimated_mins.loc[has_season_data]
                    
                    # No season activity = inactive
                    no_season_activity = season_mins == 0
                    expected_mins.loc[nan_indices[no_season_activity]] = 0
                else:
                    # No data available, be conservative
                    expected_mins.loc[nan_mask] = 0
        else:
            # No rolling minutes column - estimate from season totals
            if 'total_points' in X.columns and 'minutes' in X.columns:
                # Estimate based on season average
                season_mins = X['minutes'].fillna(0)
                has_data = season_mins > 0
                expected_mins = pd.Series(0, index=X.index)
                if has_data.any():
                    # Rough estimate: average minutes per game
                    estimated = (season_mins / 14).clip(45, 75)
                    expected_mins.loc[has_data] = estimated.loc[has_data]
            else:
                expected_mins = pd.Series(60, index=X.index)  # Conservative default

        # Cap and apply chance of playing
        expected_mins = expected_mins.clip(0, 90)
        
        # CRITICAL: If player has 0 points in last 3 GWs, heavily reduce expected minutes
        # This penalizes poor recent form
        if 'total_points_rolling_3' in X.columns:
            # Check for exactly 0 or very close to 0 (handles floating point issues)
            zero_recent_points = (X['total_points_rolling_3'].fillna(0) < 0.1)
            if zero_recent_points.any():
                count = zero_recent_points.sum()
                # Players with 0 recent points AND 0 recent minutes should get 0 expected minutes
                if 'minutes_rolling_3' in X.columns:
                    also_no_minutes = (X['minutes_rolling_3'].fillna(0) < 0.1)
                    completely_inactive = zero_recent_points & also_no_minutes
                    expected_mins.loc[completely_inactive] = 0
                    # Players with 0 points but some minutes get reduced to max 15 minutes
                    some_minutes_but_no_points = zero_recent_points & ~also_no_minutes
                    expected_mins.loc[some_minutes_but_no_points] = expected_mins.loc[some_minutes_but_no_points].clip(0, 15)
                    logger.info(f"   Reduced expected minutes: {completely_inactive.sum()} to 0, {some_minutes_but_no_points.sum()} to max 15 (0 pts in last 3 GWs)")
                else:
                    # No minutes data, just reduce based on points
                    expected_mins.loc[zero_recent_points] = expected_mins.loc[zero_recent_points].clip(0, 15)
                    logger.info(f"   Reduced expected minutes for {count} players with 0 points in last 3 GWs")
        
        # Apply availability adjustments (chance of playing)
        if 'chance_of_playing_next_round' in X.columns:
            chance = pd.to_numeric(X['chance_of_playing_next_round'], errors='coerce').fillna(100) / 100.0
            expected_mins = expected_mins * chance
            
            # CRITICAL: If chance is very low (<50%), heavily penalize
            very_low_chance = chance < 0.5
            if very_low_chance.any():
                # Reduce expected minutes significantly for doubtful players
                expected_mins.loc[very_low_chance] = expected_mins.loc[very_low_chance] * 0.2
                logger.info(f"   Reduced expected minutes for {very_low_chance.sum()} players with <50% chance of playing")
        
        # Also check status field for doubtful players
        if 'status' in X.columns:
            doubtful = X['status'] == 'd'
            if doubtful.any():
                # Doubtful players get reduced minutes
                expected_mins.loc[doubtful] = expected_mins.loc[doubtful] * 0.3
                logger.info(f"   Reduced expected minutes for {doubtful.sum()} doubtful players")

        # Calculate expected points
        X['predicted_ev'] = (X['predicted_points_per_90'] * expected_mins) / 90.0
        X['predicted_ev'] = X['predicted_ev'].replace([np.inf, -np.inf], 0).fillna(0)
        
        # Apply form-based adjustments using new method
        if not form_metrics.empty:
            X = self._apply_form_adjustments(X, form_metrics)
        
        # IMPROVEMENT: Add season performance bonus ONLY for players with good season performance
        # This helps the optimizer select players with proven track records
        # Players with poor season performance should NOT get a bonus
        if 'total_points' in X.columns and 'minutes' in X.columns:
            # Calculate points per 90 for the season
            season_pp90 = pd.Series(0.0, index=X.index)
            valid_mins = X['minutes'].fillna(0) > 0
            if valid_mins.any():
                season_pp90.loc[valid_mins] = (
                    X.loc[valid_mins, 'total_points'] / X.loc[valid_mins, 'minutes']
                ) * 90
                season_pp90 = season_pp90.clip(0, 20)  # Cap at reasonable level
            
            # Only add bonus for players with good season performance (>3.0 pp90)
            # This prevents poor performers from getting an undeserved boost
            good_season = season_pp90 >= 3.0
            season_bonus = pd.Series(0.0, index=X.index)
            if good_season.any():
                # Bonus scales from 0.3 (at 3.0 pp90) to 2.0 (at 10.0+ pp90)
                season_bonus.loc[good_season] = ((season_pp90.loc[good_season] - 3.0) / 7.0).clip(0, 1.0) * 1.7 + 0.3
                season_bonus = season_bonus.clip(0, 2.0)  # Max 2 point bonus
            
            X['predicted_ev'] = X['predicted_ev'] + season_bonus
            
            bonus_count = (season_bonus > 0).sum()
            avg_bonus = season_bonus[season_bonus>0].mean() if bonus_count > 0 else 0.0
            logger.info(f"   Applied season performance bonus to {bonus_count} players with >3.0 pp90 (avg: {avg_bonus:.2f})")
        
        # Reapply caps after season bonus (safety net for low-scoring players)
        if 'total_points' in X.columns:
            # Reapply the 5.0 cap for 25-35 pts players (bonus might have pushed them over)
            low_points = X['total_points'].fillna(0) >= 25
            low_points = low_points & (X['total_points'].fillna(0) < 35)
            if low_points.any():
                X.loc[low_points, 'predicted_ev'] = X.loc[low_points, 'predicted_ev'].clip(0, 5.0)
        
        # REALISTIC EV CAPS based on actual points per gameweek (not total points)
        # At GW15, realistic expectations:
        # - Haaland: ~8.0 pts/GW (best player)
        # - Top 5%: ~5.75 pts/GW
        # - Top 10%: ~5.4 pts/GW
        # - Top 25%: ~5.15 pts/GW
        # - Average: ~4.5 pts/GW
        # Apply tiered caps based on points per gameweek (more realistic)
        if 'total_points' in X.columns:
            # Get current gameweek to calculate pts/GW
            try:
                from fpl_api import FPLAPIClient
                api = FPLAPIClient()
                current_gw = api.get_current_gameweek()
            except:
                current_gw = 15  # Fallback
            
            # Calculate points per gameweek
            total_pts = X['total_points'].fillna(0)
            pts_per_gw = total_pts / current_gw
            
            # Elite players (7.0+ pts/GW): cap at 8.5 points (allows for Haaland-level performance)
            elite_players = pts_per_gw >= 7.0
            if elite_players.any():
                X.loc[elite_players, 'predicted_ev'] = X.loc[elite_players, 'predicted_ev'].clip(0, 8.5)
                logger.info(f"   Capped {elite_players.sum()} elite players (7.0+ pts/GW) to 8.5 EV")
            
            # Top players (6.0-6.99 pts/GW): cap at 7.0 points
            top_players = (pts_per_gw >= 6.0) & (pts_per_gw < 7.0)
            if top_players.any():
                X.loc[top_players, 'predicted_ev'] = X.loc[top_players, 'predicted_ev'].clip(0, 7.0)
                logger.info(f"   Capped {top_players.sum()} top players (6.0-6.99 pts/GW) to 7.0 EV")
            
            # Very good players (5.5-5.99 pts/GW): cap at 6.0 points
            very_good = (pts_per_gw >= 5.5) & (pts_per_gw < 6.0)
            if very_good.any():
                X.loc[very_good, 'predicted_ev'] = X.loc[very_good, 'predicted_ev'].clip(0, 6.0)
                logger.info(f"   Capped {very_good.sum()} very good players (5.5-5.99 pts/GW) to 6.0 EV")
            
            # Good players (5.0-5.49 pts/GW): cap at 5.5 points
            good_players = (pts_per_gw >= 5.0) & (pts_per_gw < 5.5)
            if good_players.any():
                X.loc[good_players, 'predicted_ev'] = X.loc[good_players, 'predicted_ev'].clip(0, 5.5)
                logger.info(f"   Capped {good_players.sum()} good players (5.0-5.49 pts/GW) to 5.5 EV")
            
            # Average players (4.0-4.99 pts/GW): cap at 5.0 points
            avg_players = (pts_per_gw >= 4.0) & (pts_per_gw < 5.0)
            if avg_players.any():
                X.loc[avg_players, 'predicted_ev'] = X.loc[avg_players, 'predicted_ev'].clip(0, 5.0)
                logger.info(f"   Capped {avg_players.sum()} average players (4.0-4.99 pts/GW) to 5.0 EV")
            
            # Below average players (3.0-3.99 pts/GW): cap at 4.0 points
            below_avg = (pts_per_gw >= 3.0) & (pts_per_gw < 4.0)
            if below_avg.any():
                X.loc[below_avg, 'predicted_ev'] = X.loc[below_avg, 'predicted_ev'].clip(0, 4.0)
                logger.info(f"   Capped {below_avg.sum()} below average players (3.0-3.99 pts/GW) to 4.0 EV")
            
            # Low performers (<3.0 pts/GW): cap at 3.5 points
            low_performers = pts_per_gw < 3.0
            if low_performers.any():
                X.loc[low_performers, 'predicted_ev'] = X.loc[low_performers, 'predicted_ev'].clip(0, 3.5)
                logger.info(f"   Capped {low_performers.sum()} low performers (<3.0 pts/GW) to 3.5 EV")
        
        # Final absolute cap: 9.0 points (allows for exceptional single-gameweek performances)
        # This is above Haaland's average but accounts for potential hauls
        X['predicted_ev'] = X['predicted_ev'].clip(0, 9.0)
        
        # Final safety check: ensure completely inactive players are zeroed
        if 'minutes_rolling_3' in X.columns and 'total_points_rolling_3' in X.columns:
            definitely_inactive = (
                (X['minutes_rolling_3'].fillna(0) == 0) & 
                (X['total_points_rolling_3'].fillna(0) == 0)
            )
            if definitely_inactive.any():
                X.loc[definitely_inactive, 'predicted_ev'] = 0
                logger.info(f"   Final safety check: zeroed {definitely_inactive.sum()} inactive players")

        results = player_data[['id', 'web_name']].copy()
        results.columns = ['player_id', 'player_name']
        # Merge predicted_ev from X, ensuring proper alignment by player_id
        if 'player_id' in X.columns:
            ev_df = X[['player_id', 'predicted_ev']].copy()
            results = results.merge(ev_df, on='player_id', how='left')
            results['predicted_ev'] = results['predicted_ev'].fillna(0)
        else:
            # Fallback if player_id not available
            results['predicted_ev'] = X['predicted_ev'].values if len(X) == len(results) else 0
        
        logger.info(f"   Predictions generated for {len(results)} players")
        return results

    def save_model(self):
        if not self.is_trained: 
            return
        Path('models').mkdir(exist_ok=True)
        with open(f'models/fpl_ml_model_{self.model_version}.pkl', 'wb') as f:
            pickle.dump({'model_def': self.model_def, 'model_att': self.model_att}, f)

    def load_model(self):
        path = f'models/fpl_ml_model_{self.model_version}.pkl'
        if not Path(path).exists(): 
            return False
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.model_def = data.get('model_def')
                self.model_att = data.get('model_att')
                self.is_trained = True
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False