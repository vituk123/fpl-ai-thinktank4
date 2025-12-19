#!/usr/bin/env python3
"""Test the V2 ML report generator"""
import sys
sys.path.insert(0, '.')
from src.ml_report_v2 import generate_ml_report_v2

print("Starting V2 generator test...")
result = generate_ml_report_v2(2568103)

if isinstance(result, dict):
    print(f"Result keys: {list(result.keys())}")
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        if 'transfer_recommendations' in result:
            top_sug = result.get('transfer_recommendations', {}).get('top_suggestion', {})
            if top_sug:
                players_out = top_sug.get('players_out', [])
                print(f"Players OUT: {[p.get('name') + '(' + str(p.get('id')) + ')' for p in players_out]}")
else:
    print(f"Unexpected result type: {type(result)}")
    print(f"Result: {result}")

