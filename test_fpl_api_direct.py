"""
Direct test of FPL API to check what picks are returned for GW16
"""
import requests
import json

ENTRY_ID = 2568103
GAMEWEEK = 16

print(f"Testing FPL API directly for Entry {ENTRY_ID}, Gameweek {GAMEWEEK}")
print("=" * 80)

# Get picks for GW16
url = f"https://fantasy.premierleague.com/api/entry/{ENTRY_ID}/event/{GAMEWEEK}/picks/"
print(f"\nFetching: {url}")

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    picks = data.get('picks', [])
    
    print(f"\n✅ Success! Got {len(picks)} picks")
    print(f"\nPlayer IDs from GW{GAMEWEEK} picks:")
    player_ids = [p['element'] for p in picks]
    print(f"  {sorted(player_ids)}")
    
    # Check for blocked players
    blocked_players = {5, 241}  # Gabriel, Caicedo
    blocked_found = set(player_ids).intersection(blocked_players)
    
    if blocked_found:
        print(f"\n❌❌❌ BLOCKED PLAYERS FOUND: {blocked_found} ❌❌❌")
        print(f"\nThis means the FPL API is returning GW15 data for GW{GAMEWEEK}!")
        for pid in blocked_found:
            blocked_pick = next((p for p in picks if p['element'] == pid), None)
            print(f"\nBlocked player {pid} details:")
            print(f"  {json.dumps(blocked_pick, indent=2)}")
    else:
        print(f"\n✅ No blocked players found in GW{GAMEWEEK} picks")
    
    # Also check event info
    print(f"\nEvent info:")
    print(f"  Event ID: {data.get('event', {}).get('id', 'N/A')}")
    print(f"  Active chip: {data.get('active_chip', 'None')}")
    
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)

# Also check GW15 for comparison
print("\n" + "=" * 80)
print(f"\nFor comparison, checking GW15 picks:")
url_gw15 = f"https://fantasy.premierleague.com/api/entry/{ENTRY_ID}/event/15/picks/"
response_gw15 = requests.get(url_gw15)
if response_gw15.status_code == 200:
    data_gw15 = response_gw15.json()
    picks_gw15 = data_gw15.get('picks', [])
    player_ids_gw15 = [p['element'] for p in picks_gw15]
    blocked_in_gw15 = set(player_ids_gw15).intersection(blocked_players)
    
    print(f"GW15 picks: {len(picks_gw15)} players")
    print(f"GW15 player IDs: {sorted(player_ids_gw15)}")
    if blocked_in_gw15:
        print(f"GW15 contains blocked players: {blocked_in_gw15} (expected)")
    else:
        print(f"GW15 does NOT contain blocked players (unexpected)")

print("\n" + "=" * 80)

