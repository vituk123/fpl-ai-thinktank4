import sys
sys.path.insert(0, 'src')

try:
    from team_search import TeamSearch, RAPIDFUZZ_AVAILABLE
    print(f'RAPIDFUZZ_AVAILABLE: {RAPIDFUZZ_AVAILABLE}')
    
    import os
    csv_path = r"C:\fpl-api\fpl_teams_full.csv"
    print(f'CSV exists: {os.path.exists(csv_path)}')
    
    if RAPIDFUZZ_AVAILABLE and os.path.exists(csv_path):
        ts = TeamSearch(csv_path)
        print('TeamSearch initialized successfully')
        
        # Test a search
        results = ts.search("arsenal", limit=3)
        print(f'Search results: {len(results)} matches')
        for r in results:
            print(f"  - {r['team_name']} (similarity: {r['similarity']:.2f})")
    else:
        print(f'RAPIDFUZZ_AVAILABLE: {RAPIDFUZZ_AVAILABLE}, CSV exists: {os.path.exists(csv_path)}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

