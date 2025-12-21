#!/usr/bin/env python3
"""
Validation Script
Validates ML model predictions against actual FPL results.
Run this after each gameweek completes to track real-world performance.
"""
import sys
import os
import argparse
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from database import DatabaseManager
from validation_tracker import ValidationTracker
from fpl_api import FPLAPIClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Validate ML predictions against actual results')
    parser.add_argument('--gw', type=int, help='Gameweek to validate (default: latest finished)')
    parser.add_argument('--model-version', type=str, default='v5.0', help='Model version to validate')
    parser.add_argument('--all', action='store_true', help='Validate all unvalidated gameweeks')
    parser.add_argument('--summary', action='store_true', help='Show validation summary')
    parser.add_argument('--min-gw', type=int, help='Minimum gameweek for summary')
    parser.add_argument('--max-gw', type=int, help='Maximum gameweek for summary')
    
    args = parser.parse_args()
    
    db = DatabaseManager()
    api = FPLAPIClient(cache_dir='.cache')
    tracker = ValidationTracker(db, api)
    
    if args.summary:
        # Show validation summary
        print("="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        print()
        
        summary = tracker.get_validation_summary(
            model_version=args.model_version,
            min_gw=args.min_gw,
            max_gw=args.max_gw
        )
        
        if 'error' in summary:
            print(f"Error: {summary['error']}")
            return 1
        
        print(f"Model Version: {summary['model_version']}")
        print(f"Total Validated Predictions: {summary['total_validated_predictions']:,}")
        print(f"Gameweeks Validated: {summary['gameweeks_validated']}")
        print()
        print("Overall Metrics:")
        print(f"  MAE: {summary['overall_mae']:.2f} points")
        print(f"  RMSE: {summary['overall_rmse']:.2f} points")
        print(f"  R² Score: {summary['overall_r2_score']:.4f}")
        print()
        
        if summary['per_gameweek']:
            print("Per-Gameweek Breakdown:")
            print(f"{'GW':<5} {'Predictions':<12} {'MAE':<8} {'RMSE':<8} {'R²':<8}")
            print("-" * 50)
            for gw_metric in summary['per_gameweek']:
                print(f"{gw_metric['gameweek']:<5} "
                      f"{gw_metric['predictions']:<12} "
                      f"{gw_metric['mae']:<8.2f} "
                      f"{gw_metric['rmse']:<8.2f} "
                      f"{gw_metric['r2_score']:<8.4f}")
        
        return 0
    
    if args.all:
        # Validate all unvalidated gameweeks
        print("="*70)
        print("VALIDATING ALL UNVALIDATED GAMEWEEKS")
        print("="*70)
        print()
        
        # Get list of unvalidated gameweeks
        try:
            response = db.supabase_client.table('validation_tracking')\
                .select('gw')\
                .eq('model_version', args.model_version)\
                .eq('is_validated', False)\
                .execute()
            
            unvalidated_gws = sorted(set([r['gw'] for r in response.data]))
            
            if not unvalidated_gws:
                print("No unvalidated gameweeks found.")
                return 0
            
            print(f"Found {len(unvalidated_gws)} unvalidated gameweek(s): {unvalidated_gws}")
            print()
            
            for gw in unvalidated_gws:
                print(f"Validating GW{gw}...")
                result = tracker.validate_predictions_for_gw(gw, args.model_version)
                
                if 'error' in result:
                    print(f"  Error: {result['error']}")
                else:
                    print(f"  ✓ Validated {result['validated_predictions']} predictions")
                    print(f"    MAE: {result['mae']:.2f}, RMSE: {result['rmse']:.2f}, R²: {result['r2_score']:.4f}")
                print()
            
            return 0
        
        except Exception as e:
            logger.error(f"Error validating all gameweeks: {e}")
            return 1
    
    # Validate specific gameweek
    if args.gw:
        gw = args.gw
    else:
        # Get latest finished gameweek
        try:
            bootstrap = api.get_bootstrap_static(use_cache=True)
            events = bootstrap.get('events', [])
            finished_events = [e for e in events if e.get('finished', False)]
            if not finished_events:
                print("No finished gameweeks found.")
                return 1
            gw = max([e['id'] for e in finished_events])
            print(f"Using latest finished gameweek: GW{gw}")
        except Exception as e:
            logger.error(f"Error getting current gameweek: {e}")
            return 1
    
    print("="*70)
    print(f"VALIDATING PREDICTIONS FOR GW{gw}")
    print("="*70)
    print()
    
    result = tracker.validate_predictions_for_gw(gw, args.model_version)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        return 1
    
    print("Validation Results:")
    print(f"  Gameweek: {result['gameweek']}")
    print(f"  Model Version: {result['model_version']}")
    print(f"  Total Predictions: {result['total_predictions']}")
    print(f"  Validated Predictions: {result['validated_predictions']}")
    print(f"  Matched Players: {result['matched_players']}")
    print()
    print("Metrics:")
    print(f"  MAE (Mean Absolute Error): {result['mae']:.2f} points")
    print(f"  RMSE (Root Mean Squared Error): {result['rmse']:.2f} points")
    print(f"  MAPE (Mean Absolute Percentage Error): {result['mape']:.2f}%")
    print(f"  R² Score: {result['r2_score']:.4f}")
    print()
    print(f"  Mean Actual Points: {result['mean_actual_points']:.2f}")
    print(f"  Mean Predicted EV: {result['mean_predicted_ev']:.2f}")
    print()
    print("✓ Validation complete!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

