#!/usr/bin/env python3
"""
Debug the ML prediction pipeline step by step
"""
from ml_engine import MLEngine
from database import DatabaseManager
import pandas as pd
from fpl_api import FPLAPIClient

# Initialize
db = DatabaseManager()
ml = MLEngine(db, 'v3.2')
ml.load_model()

# Get player data
api = FPLAPIClient()
bootstrap = api.get_bootstrap_static()
players_df = pd.DataFrame(bootstrap['elements'])
snapshot = players_df.copy()
snapshot['player_id'] = snapshot['id']

print(f"=== STEP 1: Raw snapshot ===")
print(f"Snapshot shape: {snapshot.shape}")
print(f"Sample: {snapshot[['player_id', 'web_name']].head()}")

# Get history
print(f"\n=== STEP 2: Get current season history ===")
history = db.get_current_season_history()
print(f"History shape: {history.shape}")
if not history.empty:
    print(f"History sample:\n{history[['player_id', 'gw', 'minutes', 'total_points']].head()}")

# Create snapshot row for prediction
print(f"\n=== STEP 3: Create snapshot row ===")
snapshot_row = snapshot.head(1).copy()
snapshot_row['gw'] = 999 
snapshot_row['season'] = '2025-26'
for c in ['minutes', 'total_points', 'xg', 'xa', 'ict_index']:
    if c not in snapshot_row.columns: snapshot_row[c] = 0
print(f"Snapshot row: {snapshot_row[['player_id', 'gw', 'minutes']].to_dict()}")

# Combine
print(f"\n=== STEP 4: Combine data ===")
combined = pd.concat([history, snapshot_row], ignore_index=True)
print(f"Combined shape: {combined.shape}")

# Calculate rolling
print(f"\n=== STEP 5: Calculate rolling ===")
combined = ml._calculate_rolling(combined)
rolling_cols = [c for c in combined.columns if 'rolling' in c]
print(f"Rolling cols: {rolling_cols}")

# Get current rolling data
print(f"\n=== STEP 6: Extract current rolling ===")
current_rolling = combined[combined['gw'] == 999][['player_id'] + rolling_cols]
current_rolling = current_rolling.drop_duplicates(subset=['player_id'])
print(f"Current rolling shape: {current_rolling.shape}")
print(f"Current rolling data:\n{current_rolling}")

# Merge back
print(f"\n=== STEP 7: Merge back ===")
enriched_df = snapshot.merge(current_rolling, on='player_id', how='left')
print(f"Enriched df shape: {enriched_df.shape}")
print(f"Enriched df sample:\n{enriched_df[['player_id', 'web_name', 'minutes_rolling_3']].head()}")

# Feature engineering
print(f"\n=== STEP 8: Feature engineering ===")
X = ml.engineer_features(enriched_df, is_training=False)
print(f"X shape after features: {X.shape}")
print(f"X sample:\n{X[['player_id', 'minutes_rolling_3']].head()}")

# Check minutes_rolling_3
print(f"\n=== STEP 9: Check minutes_rolling_3 ===")
if 'minutes_rolling_3' in X.columns:
    mins = X['minutes_rolling_3'].fillna(0)
    print(f"minutes_rolling_3 stats: Min={mins.min():.1f}, Max={mins.max():.1f}, Mean={mins.mean():.1f}")
    print(f"Non-zero minutes: {(mins > 0).sum()}")
else:
    print("minutes_rolling_3 column missing!")

# Check prediction
print(f"\n=== STEP 10: Make prediction ===")
features = ml.BASE_FEATURES + ['xg_x_ease', 'points_x_ease']
X['predicted_ev'] = 0.0

mask_def = X['element_type'].isin([1, 2])
print(f"Defender players: {mask_def.sum()}")
if ml.model_def and mask_def.any():
    preds = ml.model_def.predict(X.loc[mask_def, features])
    X.loc[mask_def, 'predicted_ev'] = preds
    print(f"Raw defender predictions: Min={preds.min():.3f}, Max={preds.max():.3f}")

# Check final result
print(f"\n=== STEP 11: Final check ===")
if 'predicted_ev' in X.columns:
    print(f"Final predictions: Min={X['predicted_ev'].min():.3f}, Max={X['predicted_ev'].max():.3f}")
    results = players_df[['id', 'web_name']].copy()
    results.columns = ['player_id', 'player_name']
    results['predicted_ev'] = X['predicted_ev'].clip(lower=0.1)
    print(f"Final clipped: Min={results['predicted_ev'].min():.3f}, Max={results['predicted_ev'].max():.3f}")
else:
    print("No predicted_ev column!")