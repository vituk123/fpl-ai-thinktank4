"""
Debug script to check why players with zero recent points are getting high EV predictions
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from ml_engine import MLEngine
from fpl_api import FPLAPIClient

# Initialize
db = DatabaseManager()
api = FPLAPIClient()

# Get current players
bootstrap = api.get_bootstrap_static()
players_df = pd.DataFrame(bootstrap['elements'])

# Get current gameweek
gw = api.get_current_gameweek()
print(f"Current gameweek: {gw}\n")

# Get recent history
history = db.get_current_season_history()
if not history.empty:
    # Get last 3 gameweeks
    recent_gws = sorted(history['gw'].unique())[-3:]
    print(f"Recent gameweeks: {recent_gws}\n")
    
    # Find players with zero points in recent weeks
    recent_history = history[history['gw'].isin(recent_gws)]
    player_points = recent_history.groupby('player_id')['total_points'].sum()
    zero_point_players = player_points[player_points == 0].index.tolist()
    
    print(f"Players with 0 total points in last 3 GWs: {len(zero_point_players)}\n")
    
    # Get ML predictions
    ml = MLEngine(db, model_version='v3.7')
    ml.load_model()
    
    # Add fixture difficulty
    teams_df = pd.DataFrame(bootstrap['teams'])
    team_map = teams_df.set_index('id')['name'].to_dict()
    players_df['team_name'] = players_df['team'].map(team_map)
    
    fixtures = api.get_fixtures_for_gameweek(gw)
    team_difficulty = {}
    for f in fixtures:
        team_difficulty[f['team_h']] = f['team_a_difficulty']
        team_difficulty[f['team_a']] = f['team_h_difficulty']
    players_df['fixture_difficulty'] = players_df['team'].map(team_difficulty).fillna(3)
    
    predictions = ml.predict_player_performance(players_df)
    
    # Merge with player info
    predictions = predictions.merge(
        players_df[['id', 'web_name', 'team_name', 'element_type', 'total_points', 'minutes']],
        left_on='player_id', right_on='id', how='left'
    )
    
    # Filter to zero point players
    zero_point_predictions = predictions[predictions['player_id'].isin(zero_point_players)].copy()
    
    # Add rolling features if available in players_df
    if 'minutes_rolling_3' in players_df.columns:
        zero_point_predictions = zero_point_predictions.merge(
            players_df[['id', 'minutes_rolling_3', 'total_points_rolling_3']],
            left_on='player_id', right_on='id', how='left'
        )
    
    # Sort by predicted EV
    zero_point_predictions = zero_point_predictions.sort_values('predicted_ev', ascending=False)
    
    print("="*80)
    print("TOP 20 ZERO-POINT PLAYERS BY PREDICTED EV:")
    print("="*80)
    if 'total_points_rolling_3' in zero_point_predictions.columns:
        print(f"{'Player':<20} {'Team':<15} {'Pos':<5} {'Recent Pts':<12} {'Roll3 Pts':<12} {'Roll3 Mins':<12} {'Pred EV':<10}")
        print("-"*80)
    else:
        print(f"{'Player':<20} {'Team':<15} {'Pos':<5} {'Recent Pts':<12} {'Pred EV':<10} {'Total Pts':<10} {'Minutes':<10}")
        print("-"*80)
    
    for _, row in zero_point_predictions.head(20).iterrows():
        pos_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        pos = pos_map.get(row['element_type'], '?')
        if 'total_points_rolling_3' in zero_point_predictions.columns:
            roll3_pts = row.get('total_points_rolling_3', 0)
            roll3_mins = row.get('minutes_rolling_3', 0)
            print(f"{row['web_name']:<20} {row['team_name']:<15} {pos:<5} {0:<12} {roll3_pts:<12.2f} {roll3_mins:<12.1f} {row['predicted_ev']:<10.2f}")
        else:
            print(f"{row['web_name']:<20} {row['team_name']:<15} {pos:<5} {0:<12} {row['predicted_ev']:<10.2f} {row['total_points']:<10} {row['minutes']:<10}")
    
    # Check their rolling averages
    print("\n" + "="*80)
    print("CHECKING ROLLING AVERAGES FOR TOP 5:")
    print("="*80)
    
    for player_id in zero_point_predictions.head(5)['player_id'].values:
        player_history = history[history['player_id'] == player_id].sort_values('gw')
        recent = player_history.tail(5)
        
        player_name = predictions[predictions['player_id'] == player_id]['web_name'].iloc[0]
        print(f"\n{player_name} (ID: {player_id}):")
        print(f"  Last 5 GWs:")
        for _, h in recent.iterrows():
            print(f"    GW{h['gw']}: {h['minutes']} mins, {h['total_points']} pts, xG={h.get('xg', 0):.2f}, xA={h.get('xa', 0):.2f}")
        
        # Calculate rolling averages manually
        if len(recent) >= 3:
            rolling_3_mins = recent['minutes'].tail(3).mean()
            rolling_3_pts = recent['total_points'].tail(3).mean()
            rolling_3_xg = recent.get('xg', pd.Series([0]*len(recent))).tail(3).mean()
            print(f"  Rolling 3: {rolling_3_mins:.1f} mins, {rolling_3_pts:.2f} pts, {rolling_3_xg:.2f} xG")
else:
    print("No history data available")

