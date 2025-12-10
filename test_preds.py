import sys
import os
sys.path.insert(0, 'src')

from database import DatabaseManager

try:
    db = DatabaseManager()
    preds = db.supabase_client.table('predictions').select('*').order('predicted_ev', desc=True).limit(10).execute()
    
    print("Top 10 ML Predictions:")
    print("PLAYER_ID | EV | CONFIDENCE | GW")
    print("-" * 40)
    
    for p in preds.data:
        print(f"{p['player_id']} | {p['predicted_ev']:.2f} | {p.get('confidence_score', 0)} | {p.get('gw', 0)}")
        
    print(f"\nTotal predictions in DB: {len(preds.data)}")
    
except Exception as e:
    print(f"Error: {e}")