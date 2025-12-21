#!/usr/bin/env python3
"""Train ML Model v5.0"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager
from ml_engine_v5 import MLEngineV5
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print('='*70)
print('ML MODEL v5.0 TRAINING - FULL RUN')
print('='*70)
print()

db = DatabaseManager()
ml = MLEngineV5(db, model_version='v5.0')

# Check data loading
print('Step 1: Loading data...')
data = ml.load_data()
print(f'   Total records loaded: {len(data)}')
if not data.empty:
    element_counts = data['element_type'].value_counts().to_dict()
    print(f'   Element types: {element_counts}')
    defensive_count = (data['element_type'].isin([1, 2])).sum()
    attacking_count = (data['element_type'].isin([3, 4])).sum()
    print(f'   Defensive (1,2): {defensive_count}')
    print(f'   Attacking (3,4): {attacking_count}')

print()
print('Step 2: Training model...')
result = ml.train_model()

if result and result.get('status') == 'success':
    print()
    print('='*70)
    print('TRAINING COMPLETED!')
    print('='*70)
    print(f'Optimal Decay Rate: {ml.optimal_decay_rate}')
    print(f'Current Season: {ml.current_season}')
    
    if ml.validation_metrics:
        print()
        print('Validation Metrics:')
        if 'defensive' in ml.validation_metrics:
            d = ml.validation_metrics['defensive']
            print(f'  Defensive - R²: {d.get("r2", 0):.4f}, MAE: {d.get("mae", 0):.2f}, RMSE: {d.get("rmse", 0):.2f}')
        if 'attacking' in ml.validation_metrics:
            a = ml.validation_metrics['attacking']
            print(f'  Attacking - R²: {a.get("r2", 0):.4f}, MAE: {a.get("mae", 0):.2f}, RMSE: {a.get("rmse", 0):.2f}')
    
    ml.save_model()
    print()
    print('✓ Model saved successfully!')
else:
    print('✗ Training failed!')
    print(f'Result: {result}')

