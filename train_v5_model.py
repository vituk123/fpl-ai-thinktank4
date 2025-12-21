#!/usr/bin/env python3
"""
Training script for ML Model v5.0
Trains the stacked generalization model with all available historical data.
"""
import sys
import os
import logging

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)
sys.path.insert(0, os.path.dirname(__file__))

# Change to src directory for imports
os.chdir(src_path)

from database import DatabaseManager
from ml_engine_v5 import MLEngineV5

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Train v5.0 model with all available data."""
    print("="*70)
    print("ML MODEL v5.0 TRAINING")
    print("Stacked Generalization Architecture")
    print("="*70)
    print()
    
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        db = DatabaseManager()
        
        # Initialize ML Engine v5.0
        logger.info("Initializing ML Engine v5.0...")
        ml = MLEngineV5(db, model_version='v5.0')
        
        print("\nStarting training with ALL available historical data...")
        print("Features:")
        print("  - Exhaustive data loading (no season filtering)")
        print("  - Exponential decay weighting")
        print("  - Stacked generalization (Tree + Forest → XGBoost)")
        print("  - Mandatory backtesting validation")
        print()
        
        # Train the model
        result = ml.train_model()
        
        if result and result.get('status') == 'success':
            print("\n" + "="*70)
            print("TRAINING COMPLETED SUCCESSFULLY!")
            print("="*70)
            print(f"\nOptimal Decay Rate: {ml.optimal_decay_rate}")
            print(f"Current Season: {ml.current_season}")
            
            if ml.validation_metrics:
                print("\nValidation Metrics:")
                if 'defensive' in ml.validation_metrics:
                    def_metrics = ml.validation_metrics['defensive']
                    print(f"  Defensive Model:")
                    print(f"    R² Score: {def_metrics.get('r2', 0):.4f}")
                    print(f"    MAE: {def_metrics.get('mae', 0):.2f}")
                    print(f"    RMSE: {def_metrics.get('rmse', 0):.2f}")
                
                if 'attacking' in ml.validation_metrics:
                    att_metrics = ml.validation_metrics['attacking']
                    print(f"  Attacking Model:")
                    print(f"    R² Score: {att_metrics.get('r2', 0):.4f}")
                    print(f"    MAE: {att_metrics.get('mae', 0):.2f}")
                    print(f"    RMSE: {att_metrics.get('rmse', 0):.2f}")
            
            # Save the model
            print("\nSaving model components...")
            ml.save_model()
            print("✓ Model saved successfully!")
            print("\nModel files:")
            print("  - models/fpl_ml_model_v5.0_base_tree_def.pkl")
            print("  - models/fpl_ml_model_v5.0_base_tree_att.pkl")
            print("  - models/fpl_ml_model_v5.0_base_forest_def.pkl")
            print("  - models/fpl_ml_model_v5.0_base_forest_att.pkl")
            print("  - models/fpl_ml_model_v5.0_meta_def.pkl")
            print("  - models/fpl_ml_model_v5.0_meta_att.pkl")
            print("  - models/fpl_ml_model_v5.0_metadata.pkl")
            
            print("\n" + "="*70)
            print("Training complete! Model v5.0 is ready to use.")
            print("="*70)
            return 0
        else:
            print("\n" + "="*70)
            print("TRAINING FAILED!")
            print("="*70)
            print(f"Result: {result}")
            return 1
            
    except Exception as e:
        logger.error(f"Error during training: {e}", exc_info=True)
        print("\n" + "="*70)
        print("TRAINING FAILED WITH ERROR!")
        print("="*70)
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

