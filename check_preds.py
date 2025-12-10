from src.database import DatabaseManager
import pandas as pd

db = DatabaseManager()
preds = db.supabase_client.table('predictions').select('*').order('predicted_ev', desc=True).limit(10).execute()

print(f"{'PLAYER_ID':<15} {'EV':<10} {'CONFIDENCE':<10} {'GW':<5}")
print('-'*45)
for p in preds.data:
    print(f"{p['player_id']:<15} {p['predicted_ev']:<10.2f} {p.get('confidence_score',0):<10} {p.get('gw', 0):<5}")