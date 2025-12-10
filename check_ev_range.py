import sys
sys.path.insert(0, 'src')
from database import DatabaseManager
from ml_engine import MLEngine
import pandas as pd

db = DatabaseManager()
ml = MLEngine(db, 'v1.0')
ml.load_model()

# Get the actual prediction values
from fpl_api import FPLAPIClient
api = FPLAPIClient()
bootstrap = api.get_bootstrap_static()
players_df = pd.DataFrame(bootstrap['elements'])

# Make predictions
preds = ml.predict_player_performance(players_df)
print("Top 10 ML Predictions:")
print(preds.sort_values('predicted_ev', ascending=False).head(10)[['player_name', 'predicted_ev']])
print(f"\nAverage EV: {preds['predicted_ev'].mean():.2f}")
print(f"Max EV: {preds['predicted_ev'].max():.2f}")
print(f"Min EV: {preds['predicted_ev'].min():.2f}")