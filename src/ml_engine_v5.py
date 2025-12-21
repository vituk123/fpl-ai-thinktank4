"""
ML Engine v5.0: Stacked Generalization Architecture
Builds on v4.6 feature engineering with exhaustive data loading and exponential decay weighting.
"""
import logging
import pickle
import math
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.model_selection import cross_val_predict, KFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import xgboost as xgb
try:
    from .database import DatabaseManager
    from .ml_engine import MLEngine  # Import v4.6 for feature engineering
    from .fpl_api import FPLAPIClient
except ImportError:
    # Fallback for direct execution
    from database import DatabaseManager
    from ml_engine import MLEngine
    from fpl_api import FPLAPIClient

logger = logging.getLogger(__name__)


class MLEngineV5(MLEngine):
    """
    ML Engine v5.0 with Stacked Generalization Architecture.
    Inherits feature engineering from v4.6 but implements new training pipeline.
    """
    
    def __init__(self, db_manager: DatabaseManager, model_version: str = "v5.0"):
        # Initialize parent class (v4.6) for feature engineering
        super().__init__(db_manager, model_version)
        self.model_version = model_version
        
        # Ensure time_decay_weights exists (parent class sets this, but we override it)
        # We'll use exponential decay instead, but need this for feature engineering compatibility
        if not hasattr(self, 'time_decay_weights'):
            self.time_decay_weights = {
                '2025-26': 1.0, 
                '2024-25': 0.7,
                '2023-24': 0.5,
                'Archived': 0.4
            }
        
        # Ensure model_config exists (inherited from parent but ensure it's accessible)
        if not hasattr(self, 'model_config'):
            self.model_config = {
                'max_depth': 4,
                'learning_rate': 0.1,
                'n_estimators': 200,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1
            }
        
        # Stacking model components
        self.base_tree_def = None
        self.base_tree_att = None
        self.base_forest_def = None
        self.base_forest_att = None
        self.meta_model_def = None
        self.meta_model_att = None
        
        # Metadata
        self.optimal_decay_rate = None
        self.current_season = None
        self.validation_metrics = {}
        
        # Decay rate tuning candidates
        self.decay_rate_candidates = [0.0001, 0.0005, 0.001, 0.002, 0.005]
        
        # FPL API client for current season detection
        self.api_client = FPLAPIClient(cache_dir='.cache')
        
        logger.info(f"ML Engine v5.0 initialized with stacking architecture")

    def _get_current_season(self) -> str:
        """
        Get current season identifier from FPL API.
        Returns season string like '2024-25' or '2025-26'.
        """
        try:
            bootstrap = self.api_client.get_bootstrap_static(use_cache=True)
            events = bootstrap.get('events', [])
            
            if not events:
                logger.warning("No events found in bootstrap, using fallback")
                # Fallback: infer from current date
                now = datetime.now()
                if now.month >= 8:  # August onwards = new season
                    season = f"{now.year}-{str(now.year + 1)[-2:]}"
                else:  # Jan-July = previous season
                    season = f"{now.year - 1}-{str(now.year)[-2:]}"
                return season
            
            # Get the most recent event to infer season
            # FPL API doesn't directly give season, but we can infer from event dates
            # For now, use a heuristic based on current date
            now = datetime.now()
            if now.month >= 8:  # August onwards = new season
                season = f"{now.year}-{str(now.year + 1)[-2:]}"
            else:  # Jan-July = previous season
                season = f"{now.year - 1}-{str(now.year)[-2:]}"
            
            logger.info(f"Detected current season: {season}")
            return season
            
        except Exception as e:
            logger.warning(f"Error detecting current season from API: {e}, using fallback")
            # Fallback: infer from current date
            now = datetime.now()
            if now.month >= 8:
                season = f"{now.year}-{str(now.year + 1)[-2:]}"
            else:
                season = f"{now.year - 1}-{str(now.year)[-2:]}"
            return season

    def load_data(self) -> pd.DataFrame:
        """
        Load ALL historical data without season filtering.
        Calculate days_since_match for exponential decay weighting.
        """
        try:
            logger.info("Loading exhaustive historical data (v5.0)...")
            
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

            if archived.empty and current.empty:
                logger.error("   Completely failed to load any data")
                return pd.DataFrame()

            dfs = []
            if not archived.empty:
                if 'season' not in archived.columns:
                    archived['season'] = 'Archived'
                
                # Handle player_id column
                if 'player_id' not in archived.columns:
                    id_columns = ['element', 'id', 'playerid']
                    for col in id_columns:
                        if col in archived.columns:
                            archived['player_id'] = archived[col]
                            logger.info(f"   Using '{col}' as player_id")
                            break
                    
                    if 'player_id' not in archived.columns:
                        logger.warning("   No player ID column found, creating synthetic IDs")
                        archived['player_id'] = range(len(archived))
                
                if 'element_type' not in archived.columns:
                    archived['element_type'] = 3
                    logger.info("   Added default element_type=3 for archive data")
                
                dfs.append(archived)
            
            if not current.empty:
                # Determine current season
                current_season = self._get_current_season()
                current['season'] = current_season
                dfs.append(current)

            if not dfs:
                logger.error("No training data available from any source")
                return pd.DataFrame()

            combined = pd.concat(dfs, ignore_index=True)
            logger.info(f"   Combined dataset: {len(combined)} total records")
            
            # Calculate days_since_match for exponential decay
            # Use created_at if available, otherwise estimate from season + gw
            if 'created_at' in combined.columns:
                combined['match_date'] = pd.to_datetime(combined['created_at'], errors='coerce')
            else:
                # Estimate match date from season and gameweek
                # FPL seasons typically start in August
                def estimate_match_date(row):
                    season_str = str(row.get('season', '2024-25'))
                    gw = row.get('gw', 1)
                    
                    # Parse season (e.g., '2024-25' -> 2024)
                    try:
                        year = int(season_str.split('-')[0])
                    except:
                        year = 2024
                    
                    # Season starts in August
                    season_start = datetime(year, 8, 1)
                    # Each gameweek is roughly 7 days apart
                    match_date = season_start + timedelta(days=(gw - 1) * 7)
                    return match_date
                
                combined['match_date'] = combined.apply(estimate_match_date, axis=1)
            
            # Fill missing dates with current date (will get low weight)
            combined['match_date'] = combined['match_date'].fillna(pd.Timestamp.now())
            
            # Calculate days since match
            now = pd.Timestamp.now()
            combined['days_since_match'] = (now - combined['match_date']).dt.days
            combined['days_since_match'] = combined['days_since_match'].clip(lower=0)
            
            logger.info(f"   Date range: {combined['match_date'].min()} to {combined['match_date'].max()}")
            logger.info(f"   Days since match range: {combined['days_since_match'].min()} to {combined['days_since_match'].max()}")
            
            return self._handle_missing_values(combined)
            
        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            return pd.DataFrame()

    def _calculate_exponential_decay_weights(self, df: pd.DataFrame, decay_rate: float) -> pd.Series:
        """
        Calculate sample weights using exponential decay based on days since match.
        
        Formula: weight = exp(-decay_rate * days_since_match)
        
        Args:
            df: DataFrame with 'days_since_match' column
            decay_rate: Decay rate parameter (higher = faster decay)
        
        Returns:
            Series of sample weights
        """
        if 'days_since_match' not in df.columns:
            logger.warning("days_since_match not found, using uniform weights")
            return pd.Series(1.0, index=df.index)
        
        weights = np.exp(-decay_rate * df['days_since_match'])
        
        # Normalize weights to prevent extreme values
        # Clip to reasonable range (0.01 to 1.0)
        weights = weights.clip(lower=0.01, upper=1.0)
        
        logger.info(f"   Exponential decay weights: min={weights.min():.4f}, max={weights.max():.4f}, mean={weights.mean():.4f}")
        return weights

    def _prepare_backtest_split(self, data: pd.DataFrame) -> tuple:
        """
        Prepare train/test split for backtesting.
        Train on all historical data except current season.
        Test on current season (only finished gameweeks).
        
        Returns:
            (train_data, test_data) tuple
        """
        current_season = self._get_current_season()
        self.current_season = current_season
        
        logger.info(f"Preparing backtest split: current_season={current_season}")
        
        # Split by season
        train_data = data[data['season'] != current_season].copy()
        test_data = data[data['season'] == current_season].copy()
        
        logger.info(f"   Train set: {len(train_data)} records (all seasons except {current_season})")
        logger.info(f"   Test set: {len(test_data)} records (season {current_season})")
        
        # Filter test set to only finished gameweeks
        # We need to check which gameweeks are finished
        try:
            bootstrap = self.api_client.get_bootstrap_static(use_cache=True)
            events = bootstrap.get('events', [])
            finished_gws = {e['id'] for e in events if e.get('finished', False)}
            
            if finished_gws:
                test_data = test_data[test_data['gw'].isin(finished_gws)].copy()
                logger.info(f"   Test set (finished GWs only): {len(test_data)} records")
            else:
                logger.warning("   No finished gameweeks found, using all test data")
        except Exception as e:
            logger.warning(f"   Could not filter finished gameweeks: {e}, using all test data")
        
        return train_data, test_data

    def _train_base_tree(self, X, y, weights, name: str, element_type: str = "def"):
        """
        Train DecisionTreeRegressor as base layer model.
        
        Args:
            X: Feature matrix
            y: Target values
            weights: Sample weights
            name: Model name for logging
            element_type: "def" or "att"
        
        Returns:
            Trained DecisionTreeRegressor
        """
        try:
            logger.info(f"   Training base tree ({name})...")
            
            model = DecisionTreeRegressor(
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42
            )
            
            model.fit(X, y, sample_weight=weights)
            
            # Evaluate
            preds = model.predict(X)
            r2 = r2_score(y, preds, sample_weight=weights)
            mae = mean_absolute_error(y, preds, sample_weight=weights)
            
            logger.info(f"   Base Tree ({name}) -> R2: {r2:.4f} | MAE: {mae:.2f}")
            
            return model
            
        except Exception as e:
            logger.error(f"   Error training base tree ({name}): {e}")
            return None

    def _train_base_forest(self, X, y, weights, name: str, element_type: str = "def"):
        """
        Train RandomForestRegressor as base layer model.
        
        Args:
            X: Feature matrix
            y: Target values
            weights: Sample weights
            name: Model name for logging
            element_type: "def" or "att"
        
        Returns:
            Trained RandomForestRegressor
        """
        try:
            logger.info(f"   Training base forest ({name})...")
            
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X, y, sample_weight=weights)
            
            # Evaluate
            preds = model.predict(X)
            r2 = r2_score(y, preds, sample_weight=weights)
            mae = mean_absolute_error(y, preds, sample_weight=weights)
            
            logger.info(f"   Base Forest ({name}) -> R2: {r2:.4f} | MAE: {mae:.2f}")
            
            return model
            
        except Exception as e:
            logger.error(f"   Error training base forest ({name}): {e}")
            return None

    def _train_meta_model(self, X_train, y_train, w_train, base_tree, base_forest, 
                         name: str, element_type: str = "def"):
        """
        Train meta model (XGBRegressor) using base model predictions as features.
        
        Uses cross-validation to generate out-of-fold predictions for training.
        
        Args:
            X_train: Training features
            y_train: Training targets
            w_train: Training weights
            base_tree: Trained DecisionTreeRegressor
            base_forest: Trained RandomForestRegressor
            name: Model name for logging
            element_type: "def" or "att"
        
        Returns:
            Trained XGBRegressor meta model
        """
        try:
            logger.info(f"   Training meta model ({name})...")
            
            # Generate out-of-fold predictions from base models using 5-fold CV
            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            
            tree_preds = cross_val_predict(base_tree, X_train, y_train, cv=kf, 
                                          n_jobs=-1, method='predict')
            forest_preds = cross_val_predict(base_forest, X_train, y_train, cv=kf,
                                            n_jobs=-1, method='predict')
            
            # Create meta features: base predictions + original features
            meta_features = np.column_stack([
                tree_preds,
                forest_preds,
                X_train.values
            ])
            
            # Train meta model (XGBRegressor)
            meta_model = xgb.XGBRegressor(**self.model_config)
            meta_model.fit(meta_features, y_train, sample_weight=w_train)
            
            # Evaluate
            meta_preds = meta_model.predict(meta_features)
            r2 = r2_score(y_train, meta_preds, sample_weight=w_train)
            mae = mean_absolute_error(y_train, meta_preds, sample_weight=w_train)
            
            logger.info(f"   Meta Model ({name}) -> R2: {r2:.4f} | MAE: {mae:.2f}")
            
            return meta_model
            
        except Exception as e:
            logger.error(f"   Error training meta model ({name}): {e}", exc_info=True)
            return None

    def _validate_backtest(self, model_tree, model_forest, model_meta, 
                          X_test, y_test, w_test, name: str) -> dict:
        """
        Validate stacked model on test set (current season).
        
        Returns:
            Dictionary with validation metrics
        """
        try:
            # Generate base predictions
            tree_preds = model_tree.predict(X_test)
            forest_preds = model_forest.predict(X_test)
            
            # Create meta features
            meta_features = np.column_stack([
                tree_preds,
                forest_preds,
                X_test.values
            ])
            
            # Get final predictions from meta model
            final_preds = model_meta.predict(meta_features)
            
            # Calculate metrics
            r2 = r2_score(y_test, final_preds, sample_weight=w_test)
            mae = mean_absolute_error(y_test, final_preds, sample_weight=w_test)
            rmse = np.sqrt(mean_squared_error(y_test, final_preds, sample_weight=w_test))
            
            metrics = {
                'r2': r2,
                'mae': mae,
                'rmse': rmse,
                'n_samples': len(y_test)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"   Error validating backtest ({name}): {e}")
            return {'r2': -1, 'mae': float('inf'), 'rmse': float('inf'), 'n_samples': 0}

    def _print_validation_report(self, metrics_def: dict, metrics_att: dict, decay_rate: float):
        """
        Print comprehensive validation report.
        """
        print("\n" + "="*70)
        print("BACKTESTING VALIDATION REPORT")
        print("="*70)
        print(f"Test Set: Current Season ({self.current_season})")
        print(f"Decay Rate: {decay_rate}")
        print()
        
        print("DEFENSIVE MODEL (GK + DEF):")
        print(f"  - R² Score: {metrics_def.get('r2', 0):.4f}")
        print(f"  - MAE: {metrics_def.get('mae', 0):.2f}")
        print(f"  - RMSE: {metrics_def.get('rmse', 0):.2f}")
        print(f"  - Test Samples: {metrics_def.get('n_samples', 0)}")
        print()
        
        print("ATTACKING MODEL (MID + FWD):")
        print(f"  - R² Score: {metrics_att.get('r2', 0):.4f}")
        print(f"  - MAE: {metrics_att.get('mae', 0):.2f}")
        print(f"  - RMSE: {metrics_att.get('rmse', 0):.2f}")
        print(f"  - Test Samples: {metrics_att.get('n_samples', 0)}")
        print()
        
        # Overall assessment
        avg_r2 = (metrics_def.get('r2', 0) + metrics_att.get('r2', 0)) / 2
        
        print("DECAY RATE ANALYSIS:")
        if avg_r2 < 0.3:
            print("  ⚠️  WARNING - Model may be over-indexing on ancient history")
            print("  → Consider increasing decay_rate to prioritize recent data")
        elif avg_r2 < 0.5:
            print("  ⚠️  CAUTION - Model performance is moderate")
            print("  → May need to tune decay_rate or check data quality")
        elif avg_r2 < 0.7:
            print("  ✓  GOOD - Model captures recent trends reasonably well")
        else:
            print("  ✓✓ SUCCESS - Model captures recent trends excellently")
        
        print("="*70 + "\n")

    def _tune_decay_rate(self, train_data: pd.DataFrame, test_data: pd.DataFrame) -> float:
        """
        Tune decay_rate by trying multiple values and selecting the best.
        
        Returns:
            Optimal decay_rate value
        """
        logger.info("Tuning decay_rate parameter...")
        
        best_decay_rate = self.decay_rate_candidates[0]
        best_score = -float('inf')
        best_metrics = {}
        
        for decay_rate in self.decay_rate_candidates:
            logger.info(f"   Trying decay_rate={decay_rate}...")
            
            try:
                # Calculate weights
                train_weights = self._calculate_exponential_decay_weights(train_data, decay_rate)
                test_weights = self._calculate_exponential_decay_weights(test_data, decay_rate)
                
                # Engineer features
                train_processed = self.engineer_features(train_data, is_training=True)
                test_processed = self.engineer_features(test_data, is_training=False)
                
                if train_processed.empty or test_processed.empty:
                    logger.warning(f"   Skipping decay_rate={decay_rate} (empty data after feature engineering)")
                    continue
                
                # Filter valid targets
                train_valid = train_processed[train_processed['points_per_90'] >= 0].copy()
                test_valid = test_processed[test_processed['points_per_90'] >= 0].copy()
                
                if train_valid.empty or test_valid.empty:
                    logger.warning(f"   Skipping decay_rate={decay_rate} (no valid targets)")
                    continue
                
                features = self.ALL_FEATURES
                
                # Quick training and validation (simplified for speed)
                # Train on defensive subset
                mask_def_train = train_valid['element_type'].isin([1, 2])
                mask_def_test = test_valid['element_type'].isin([1, 2])
                
                if mask_def_train.sum() > 50 and mask_def_test.sum() > 10:
                    # Train simple model for quick evaluation
                    tree = DecisionTreeRegressor(max_depth=5, random_state=42)
                    tree.fit(
                        train_valid[mask_def_train][features],
                        train_valid[mask_def_train]['points_per_90'],
                        sample_weight=train_weights[mask_def_train]
                    )
                    
                    preds = tree.predict(test_valid[mask_def_test][features])
                    score = r2_score(
                        test_valid[mask_def_test]['points_per_90'],
                        preds,
                        sample_weight=test_weights[mask_def_test]
                    )
                    
                    logger.info(f"   decay_rate={decay_rate} -> R²={score:.4f}")
                    
                    if score > best_score:
                        best_score = score
                        best_decay_rate = decay_rate
                else:
                    logger.warning(f"   Insufficient data for decay_rate={decay_rate}")
                    
            except Exception as e:
                logger.warning(f"   Error evaluating decay_rate={decay_rate}: {e}")
                continue
        
        logger.info(f"   Optimal decay_rate: {best_decay_rate} (R²={best_score:.4f})")
        return best_decay_rate

    def train_model(self) -> dict:
        """
        Main training pipeline with stacking architecture.
        """
        logger.info(f"Starting v5.0 model training with stacking architecture...")
        
        # 1. Load exhaustive data
        data = self.load_data()
        if data.empty:
            logger.error("No data available for training")
            return {}
        
        # 2. Prepare backtest split
        train_data, test_data = self._prepare_backtest_split(data)
        
        if train_data.empty:
            logger.error("No training data available")
            return {}
        
        if test_data.empty:
            logger.warning("No test data available (current season), skipping validation")
            test_data = None
        
        # 3. Tune decay_rate if test data available
        if test_data is not None and len(test_data) > 50:
            self.optimal_decay_rate = self._tune_decay_rate(train_data, test_data)
        else:
            self.optimal_decay_rate = 0.001  # Default
            logger.info(f"Using default decay_rate={self.optimal_decay_rate}")
        
        # 4. Calculate exponential decay weights
        train_weights = self._calculate_exponential_decay_weights(train_data, self.optimal_decay_rate)
        train_data['sample_weight'] = train_weights
        
        if test_data is not None:
            test_weights = self._calculate_exponential_decay_weights(test_data, self.optimal_decay_rate)
            test_data['sample_weight'] = test_weights
        
        # 5. Engineer features (reuse v4.6 pipeline)
        train_processed = self.engineer_features(train_data, is_training=True)
        if train_processed.empty:
            logger.error("No data after feature engineering")
            return {}
        
        if test_data is not None:
            test_processed = self.engineer_features(test_data, is_training=False)
        else:
            test_processed = pd.DataFrame()
        
        # 6. Filter valid targets
        training_data = train_processed[train_processed['points_per_90'] >= 0].copy()
        logger.info(f"   Training on {len(training_data)} rows with valid targets")
        
        features = self.ALL_FEATURES
        
        # Ensure element_type exists
        if 'element_type' not in training_data.columns:
            logger.warning("   No element_type found, creating proxy")
            if 'goals_scored' in training_data.columns:
                max_goals = training_data.groupby('player_id')['goals_scored'].transform('max')
                training_data['element_type'] = max_goals.apply(lambda x: 2 if x < 1 else 3)
            else:
                training_data['element_type'] = 3
        
        # 7. Train stacked models for defensive players
        mask_def = training_data['element_type'].isin([1, 2])
        if mask_def.sum() > 50:
            X_def = training_data[mask_def][features]
            y_def = training_data[mask_def]['points_per_90']
            w_def = training_data[mask_def]['sample_weight']
            
            # Train base models
            self.base_tree_def = self._train_base_tree(X_def, y_def, w_def, "Defensive", "def")
            self.base_forest_def = self._train_base_forest(X_def, y_def, w_def, "Defensive", "def")
            
            if self.base_tree_def and self.base_forest_def:
                # Train meta model
                self.meta_model_def = self._train_meta_model(
                    X_def, y_def, w_def,
                    self.base_tree_def, self.base_forest_def,
                    "Defensive", "def"
                )
        else:
            logger.warning(f"   Insufficient defensive data: {mask_def.sum()} records")
        
        # 8. Train stacked models for attacking players
        mask_att = training_data['element_type'].isin([3, 4])
        if mask_att.sum() > 50:
            X_att = training_data[mask_att][features]
            y_att = training_data[mask_att]['points_per_90']
            w_att = training_data[mask_att]['sample_weight']
            
            # Train base models
            self.base_tree_att = self._train_base_tree(X_att, y_att, w_att, "Attacking", "att")
            self.base_forest_att = self._train_base_forest(X_att, y_att, w_att, "Attacking", "att")
            
            if self.base_tree_att and self.base_forest_att:
                # Train meta model
                self.meta_model_att = self._train_meta_model(
                    X_att, y_att, w_att,
                    self.base_tree_att, self.base_forest_att,
                    "Attacking", "att"
                )
        else:
            logger.warning(f"   Insufficient attacking data: {mask_att.sum()} records")
        
        # 9. Validate on test set if available
        if test_processed is not None and not test_processed.empty:
            test_valid = test_processed[test_processed['points_per_90'] >= 0].copy()
            
            if not test_valid.empty:
                # Validate defensive model
                metrics_def = {}
                mask_def_test = test_valid['element_type'].isin([1, 2])
                if mask_def_test.sum() > 10 and self.meta_model_def:
                    X_test_def = test_valid[mask_def_test][features]
                    y_test_def = test_valid[mask_def_test]['points_per_90']
                    w_test_def = test_valid[mask_def_test]['sample_weight']
                    
                    metrics_def = self._validate_backtest(
                        self.base_tree_def, self.base_forest_def, self.meta_model_def,
                        X_test_def, y_test_def, w_test_def, "Defensive"
                    )
                
                # Validate attacking model
                metrics_att = {}
                mask_att_test = test_valid['element_type'].isin([3, 4])
                if mask_att_test.sum() > 10 and self.meta_model_att:
                    X_test_att = test_valid[mask_att_test][features]
                    y_test_att = test_valid[mask_att_test]['points_per_90']
                    w_test_att = test_valid[mask_att_test]['sample_weight']
                    
                    metrics_att = self._validate_backtest(
                        self.base_tree_att, self.base_forest_att, self.meta_model_att,
                        X_test_att, y_test_att, w_test_att, "Attacking"
                    )
                
                # Store validation metrics
                self.validation_metrics = {
                    'defensive': metrics_def,
                    'attacking': metrics_att,
                    'decay_rate': self.optimal_decay_rate
                }
                
                # Print validation report
                self._print_validation_report(metrics_def, metrics_att, self.optimal_decay_rate)
        
        self.is_trained = True
        logger.info(f"   Training complete - Defensive: {self.meta_model_def is not None}, Attacking: {self.meta_model_att is not None}")
        
        return {
            'status': 'success',
            'decay_rate': self.optimal_decay_rate,
            'validation_metrics': self.validation_metrics
        }

    def save_model(self):
        """Save all stacked model components and metadata."""
        if not self.is_trained:
            return
        
        Path('models').mkdir(exist_ok=True)
        
        # Save base models
        if self.base_tree_def:
            with open(f'models/fpl_ml_model_{self.model_version}_base_tree_def.pkl', 'wb') as f:
                pickle.dump(self.base_tree_def, f)
        
        if self.base_tree_att:
            with open(f'models/fpl_ml_model_{self.model_version}_base_tree_att.pkl', 'wb') as f:
                pickle.dump(self.base_tree_att, f)
        
        if self.base_forest_def:
            with open(f'models/fpl_ml_model_{self.model_version}_base_forest_def.pkl', 'wb') as f:
                pickle.dump(self.base_forest_def, f)
        
        if self.base_forest_att:
            with open(f'models/fpl_ml_model_{self.model_version}_base_forest_att.pkl', 'wb') as f:
                pickle.dump(self.base_forest_att, f)
        
        # Save meta models
        if self.meta_model_def:
            with open(f'models/fpl_ml_model_{self.model_version}_meta_def.pkl', 'wb') as f:
                pickle.dump(self.meta_model_def, f)
        
        if self.meta_model_att:
            with open(f'models/fpl_ml_model_{self.model_version}_meta_att.pkl', 'wb') as f:
                pickle.dump(self.meta_model_att, f)
        
        # Save metadata
        metadata = {
            'decay_rate': self.optimal_decay_rate,
            'current_season': self.current_season,
            'validation_metrics': self.validation_metrics,
            'model_version': self.model_version
        }
        
        with open(f'models/fpl_ml_model_{self.model_version}_metadata.pkl', 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"   Saved v5.0 stacked models and metadata")

    def load_model(self):
        """Load all stacked model components and metadata."""
        try:
            # Load metadata
            metadata_path = f'models/fpl_ml_model_{self.model_version}_metadata.pkl'
            if not Path(metadata_path).exists():
                return False
            
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
                self.optimal_decay_rate = metadata.get('decay_rate')
                self.current_season = metadata.get('current_season')
                self.validation_metrics = metadata.get('validation_metrics', {})
            
            # Load base models
            tree_def_path = f'models/fpl_ml_model_{self.model_version}_base_tree_def.pkl'
            tree_att_path = f'models/fpl_ml_model_{self.model_version}_base_tree_att.pkl'
            forest_def_path = f'models/fpl_ml_model_{self.model_version}_base_forest_def.pkl'
            forest_att_path = f'models/fpl_ml_model_{self.model_version}_base_forest_att.pkl'
            
            if Path(tree_def_path).exists():
                with open(tree_def_path, 'rb') as f:
                    self.base_tree_def = pickle.load(f)
            
            if Path(tree_att_path).exists():
                with open(tree_att_path, 'rb') as f:
                    self.base_tree_att = pickle.load(f)
            
            if Path(forest_def_path).exists():
                with open(forest_def_path, 'rb') as f:
                    self.base_forest_def = pickle.load(f)
            
            if Path(forest_att_path).exists():
                with open(forest_att_path, 'rb') as f:
                    self.base_forest_att = pickle.load(f)
            
            # Load meta models
            meta_def_path = f'models/fpl_ml_model_{self.model_version}_meta_def.pkl'
            meta_att_path = f'models/fpl_ml_model_{self.model_version}_meta_att.pkl'
            
            if Path(meta_def_path).exists():
                with open(meta_def_path, 'rb') as f:
                    self.meta_model_def = pickle.load(f)
            
            if Path(meta_att_path).exists():
                with open(meta_att_path, 'rb') as f:
                    self.meta_model_att = pickle.load(f)
            
            self.is_trained = (
                (self.meta_model_def is not None) or 
                (self.meta_model_att is not None)
            )
            
            return self.is_trained
            
        except Exception as e:
            logger.error(f"Error loading v5.0 model: {e}")
            return False

    def predict_player_performance(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Predict using stacked model architecture.
        Generates base predictions, combines into meta features, then gets final prediction.
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning empty predictions")
            return pd.DataFrame()
        
        logger.info("   Generating v5.0 stacked predictions...")
        
        snapshot = player_data.copy()
        if 'id' in snapshot.columns:
            snapshot['player_id'] = snapshot['id']
        
        if 'player_id' not in snapshot.columns:
            logger.warning("   No player ID in snapshot data")
            return pd.DataFrame()
        
        enriched_df = snapshot
        
        # Enrich with history (reuse parent logic)
        if self.db_manager:
            try:
                history = self.db_manager.get_current_season_history()
                if not history.empty:
                    current_season = self._get_current_season()
                    history['season'] = current_season
                    
                    snapshot_row = snapshot.copy()
                    snapshot_row['gw'] = 999
                    snapshot_row['season'] = current_season
                    for c in ['minutes', 'total_points', 'xg', 'xa', 'ict_index']:
                        if c not in snapshot_row.columns:
                            snapshot_row[c] = 0
                    
                    combined = pd.concat([history, snapshot_row], ignore_index=True)
                    combined = self._calculate_rolling(combined)
                    
                    rolling_cols = [c for c in combined.columns if 'rolling' in c]
                    current_rolling = combined[combined['gw'] == 999][['player_id'] + rolling_cols]
                    current_rolling = current_rolling.drop_duplicates(subset=['player_id'])
                    
                    enriched_df = snapshot.merge(current_rolling, on='player_id', how='left')
            except Exception as e:
                logger.warning(f"   History enrichment failed: {e}")
        
        # Feature engineering (reuse parent)
        X = self.engineer_features(enriched_df, is_training=False)
        if X.empty:
            logger.error("   No data after feature engineering for prediction")
            return pd.DataFrame()
        
        features = self.ALL_FEATURES
        
        # Ensure all features exist
        missing_features = [f for f in features if f not in X.columns]
        if missing_features:
            logger.warning(f"   Missing features: {missing_features}, adding defaults")
            for feat in missing_features:
                if feat == 'xg_x_ease':
                    inv_fdr = (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                    X['xg_x_ease'] = X.get('xg_rolling_3', 0) * inv_fdr
                elif feat == 'points_x_ease':
                    inv_fdr = (6 - X.get('fixture_difficulty', 3)).clip(1, 5)
                    X['points_x_ease'] = X.get('total_points_rolling_3', 0) * inv_fdr
                else:
                    X[feat] = 0.0
        
        X['predicted_points_per_90'] = 0.0
        
        if 'element_type' not in X.columns:
            X['element_type'] = 3
        
        # Predict for defensive players
        mask_def = X['element_type'].isin([1, 2])
        if mask_def.any() and self.base_tree_def and self.base_forest_def and self.meta_model_def:
            X_def = X.loc[mask_def, features]
            
            # Generate base predictions
            tree_preds = self.base_tree_def.predict(X_def)
            forest_preds = self.base_forest_def.predict(X_def)
            
            # Create meta features
            meta_features = np.column_stack([
                tree_preds,
                forest_preds,
                X_def.values
            ])
            
            # Get final predictions from meta model
            preds = self.meta_model_def.predict(meta_features)
            X.loc[mask_def, 'predicted_points_per_90'] = np.clip(preds, 0, 15.0)
        
        # Predict for attacking players
        mask_att = X['element_type'].isin([3, 4])
        if mask_att.any() and self.base_tree_att and self.base_forest_att and self.meta_model_att:
            X_att = X.loc[mask_att, features]
            
            # Generate base predictions
            tree_preds = self.base_tree_att.predict(X_att)
            forest_preds = self.base_forest_att.predict(X_att)
            
            # Create meta features
            meta_features = np.column_stack([
                tree_preds,
                forest_preds,
                X_att.values
            ])
            
            # Get final predictions from meta model
            preds = self.meta_model_att.predict(meta_features)
            X.loc[mask_att, 'predicted_points_per_90'] = np.clip(preds, 0, 18.0)
        
        # Calculate expected minutes and EV (reuse parent logic)
        if 'minutes_rolling_3' in X.columns:
            rolling_mins = X['minutes_rolling_3']
            expected_mins = rolling_mins.copy()
            zero_min_mask = (rolling_mins == 0) & rolling_mins.notna()
            expected_mins.loc[zero_min_mask] = 0
            nan_mask = rolling_mins.isna()
            if nan_mask.any():
                if 'total_points' in X.columns and 'minutes' in X.columns:
                    season_mins = X.loc[nan_mask, 'minutes'].fillna(0)
                    has_data = season_mins > 0
                    if has_data.any():
                        estimated = (season_mins / 14).clip(45, 75)
                        expected_mins.loc[nan_mask[has_data]] = estimated
                    expected_mins.loc[nan_mask[~has_data]] = 0
        else:
            expected_mins = pd.Series(60, index=X.index)
        
        expected_mins = expected_mins.clip(0, 90)
        
        # Calculate expected points
        X['predicted_ev'] = (X['predicted_points_per_90'] * expected_mins) / 90.0
        X['predicted_ev'] = X['predicted_ev'].replace([np.inf, -np.inf], 0).fillna(0)
        X['predicted_ev'] = X['predicted_ev'].clip(0, 9.0)
        
        # Prepare results
        results = player_data[['id', 'web_name']].copy()
        results.columns = ['player_id', 'player_name']
        
        if 'player_id' in X.columns:
            ev_df = X[['player_id', 'predicted_ev']].copy()
            results = results.merge(ev_df, on='player_id', how='left')
            results['predicted_ev'] = results['predicted_ev'].fillna(0)
        else:
            results['predicted_ev'] = X['predicted_ev'].values if len(X) == len(results) else 0
        
        logger.info(f"   Stacked predictions generated for {len(results)} players")
        return results

