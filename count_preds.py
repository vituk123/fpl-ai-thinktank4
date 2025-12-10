import sys
import os
sys.path.insert(0, 'src')

from database import DatabaseManager

try:
    db = DatabaseManager()
    
    # Get total count
    count_result = db.supabase_client.table('predictions').select('*', count='exact').execute()
    total_count = count_result.count
    
    print(f"Total ML predictions in database: {total_count}")
    
    # Get recent predictions with timestamps
    recent_preds = db.supabase_client.table('predictions').select('*').order('created_at', desc=True).limit(5).execute()
    
    print("\nMost recent predictions:")
    print("PLAYER_ID | EV | CREATED_AT")
    print("-" * 40)
    
    for p in recent_preds.data:
        created_at = p.get('created_at', 'Unknown')
        print(f"{p['player_id']} | {p['predicted_ev']:.2f} | {created_at}")
        
except Exception as e:
    print(f"Error: {e}")