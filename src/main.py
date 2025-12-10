"""
FPL Optimizer - Main CLI entrypoint with ML, Database, and Supabase integration.
"""
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import pandas as pd
import yaml

# Add src directory to path for imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Conditional Imports
DATABASE_AVAILABLE = False
ML_ENGINE_AVAILABLE = False
INGESTOR_AVAILABLE = False

try:
    from database import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError: DatabaseManager = None

try:
    from ml_engine import MLEngine
    ML_ENGINE_AVAILABLE = True
except ImportError: MLEngine = None

try:
    from ingest_history import HistoricalDataIngestor
    INGESTOR_AVAILABLE = True
except ImportError: HistoricalDataIngestor = None

from fpl_api import FPLAPIClient
from projections import ProjectionEngine
from eo import EOCalculator
from optimizer import TransferOptimizer
from chips import ChipEvaluator
from report import ReportGenerator
from utils import validate_squad_constraints, create_markdown_table

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError: pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_config(path='config.yml'):
    try:
        with open(path, 'r') as f: return yaml.safe_load(f)
    except FileNotFoundError: return {}

def initialize_database(config: dict):
    if not DATABASE_AVAILABLE or DatabaseManager is None: return None
    try:
        db_manager = DatabaseManager()
        # Try health check but don't fail if it times out (connection pool issues)
        try:
            health = db_manager.health_check()
            if not any(health.values()): 
                logger.warning("Database health check failed, but continuing anyway...")
        except Exception as health_error:
            logger.warning(f"Database health check failed: {health_error}, but continuing anyway...")
        
        # Try to create tables but don't fail if connection issues
        try:
            db_manager.create_tables()
        except Exception as table_error:
            logger.warning(f"Could not verify/create tables: {table_error}, but continuing anyway...")
        
        return db_manager
    except Exception as e:
        logger.warning(f"Database initialization had issues: {e}, but continuing without database features...")
        return None

def add_fixture_difficulty(players_df: pd.DataFrame, api_client, gameweek: int, db_manager=None, relevant_team_ids: set = None, all_fixtures: List[Dict] = None, bootstrap_data: Dict = None) -> pd.DataFrame:
    """
    Add comprehensive fixture difficulty ratings using the Fixture Analysis Engine.
    
    Args:
        players_df: DataFrame with player data
        api_client: FPL API client instance
        gameweek: Current gameweek
        db_manager: Optional database manager for historical data
        all_fixtures: Optional pre-loaded all fixtures list (for performance)
        bootstrap_data: Optional pre-loaded bootstrap data (for performance)
    
    Returns:
        DataFrame with added fixture difficulty columns
    """
    logger.info("Injecting fixture difficulty data with advanced analysis...")
    try:
        # First, add basic FPL fixture difficulty (for compatibility)
        if all_fixtures is None:
            fixtures = api_client.get_fixtures_for_gameweek(gameweek)
        else:
            fixtures = [f for f in all_fixtures if f.get('event') == gameweek]
        
        team_difficulty = {}

        for f in fixtures:
            team_difficulty[f['team_h']] = f['team_a_difficulty']
            team_difficulty[f['team_a']] = f['team_h_difficulty']

        players_df = players_df.copy()  # Avoid SettingWithCopyWarning
        players_df['fixture_difficulty'] = players_df['team'].map(team_difficulty).fillna(3)
        
        # Now add advanced fixture analysis
        try:
            from fixture_analyzer import FixtureAnalyzer, FixtureCongestionTracker, FixturePredictor
            
            # Use pre-loaded fixtures or load once (PERFORMANCE OPTIMIZATION: avoid redundant API calls)
            if all_fixtures is None:
                try:
                    all_fixtures = api_client.get_fixtures()
                except Exception as e:
                    logger.debug(f"Could not load all fixtures: {e}")
                    all_fixtures = []
            
            # Custom FDR calculations (pass pre-loaded data)
            analyzer = FixtureAnalyzer(api_client, db_manager)
            players_df = analyzer.calculate_fixture_difficulty(players_df, gameweek, relevant_team_ids, all_fixtures=all_fixtures, bootstrap_data=bootstrap_data)
            
            # Congestion tracking (optimized to process only relevant teams, pass pre-loaded data)
            congestion_tracker = FixtureCongestionTracker(api_client)
            players_df = congestion_tracker.calculate_congestion(players_df, gameweek, relevant_team_ids, all_fixtures=all_fixtures)
            
            # DGW/BGW predictions (optimized to process only relevant teams, pass pre-loaded data)
            predictor = FixturePredictor(api_client)
            players_df = predictor.add_dgw_bgw_predictions(players_df, gameweek, relevant_team_ids, all_fixtures=all_fixtures, bootstrap_data=bootstrap_data)
            
            logger.info("Advanced fixture analysis complete")
        except ImportError:
            logger.warning("Fixture analyzer not available, using basic FDR only")
        except Exception as e:
            logger.warning(f"Error in advanced fixture analysis: {e}, using basic FDR only")
        
        return players_df
    except Exception as e:
        logger.error(f"Error injecting fixtures: {e}")
        players_df['fixture_difficulty'] = 3
        return players_df

def add_statistical_analysis(players_df: pd.DataFrame, api_client, gameweek: int, db_manager=None, relevant_player_ids: set = None, fixtures: List[Dict] = None, bootstrap_data: Dict = None, history_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Add advanced statistical analysis including form models, team tactics, and injury risk.
    
    Args:
        players_df: DataFrame with player data
        api_client: FPL API client instance
        gameweek: Current gameweek
        db_manager: Optional database manager for historical data
        fixtures: Optional pre-loaded fixtures for gameweek (for performance)
        bootstrap_data: Optional pre-loaded bootstrap data (for performance)
        history_df: Optional pre-loaded history DataFrame (for performance)
    
    Returns:
        DataFrame with added statistical analysis columns
    """
    logger.info("Adding advanced statistical analysis...")
    try:
        from statistical_models import PlayerFormModel, TeamTacticsAnalyzer, InjuryRiskModel
        
        # Get fixtures for matchup analysis (use pre-loaded if available)
        if fixtures is None:
            fixtures = api_client.get_fixtures_for_gameweek(gameweek)
        
        # Player form models (pass pre-loaded data)
        form_model = PlayerFormModel(api_client, db_manager)
        players_df = form_model.add_form_analysis(players_df, gameweek, fixtures, relevant_player_ids, bootstrap_data=bootstrap_data, history_df=history_df)
        
        # Team tactics analysis (pass pre-loaded data)
        tactics_analyzer = TeamTacticsAnalyzer(api_client, db_manager)
        players_df = tactics_analyzer.add_team_tactics_analysis(players_df, gameweek, relevant_player_ids, bootstrap_data=bootstrap_data, history_df=history_df)
        
        # Injury/fatigue models (pass pre-loaded data)
        injury_model = InjuryRiskModel(api_client, db_manager)
        players_df = injury_model.add_injury_risk_analysis(players_df, gameweek, relevant_player_ids, history_df=history_df)
        
        logger.info("Advanced statistical analysis complete")
    except ImportError:
        logger.warning("Statistical models not available, skipping advanced analysis")
    except Exception as e:
        logger.warning(f"Error in statistical analysis: {e}, continuing without advanced features")
    
    return players_df

def train_and_predict_ml(db_manager, players_df: pd.DataFrame, config: dict, model_version: str) -> pd.DataFrame:
    if not ML_ENGINE_AVAILABLE or MLEngine is None: return players_df
    
    try:
        logger.info(f"Initializing ML Engine ({model_version})...")
        ml_engine = MLEngine(db_manager, model_version=model_version)
        
        if not ml_engine.load_model():
            logger.info("No trained model found, training new model...")
            ml_engine.train_model()
            ml_engine.save_model()
        else:
            logger.info("Loaded existing trained model")
        
        logger.info("Generating player performance predictions...")
        predictions_df = ml_engine.predict_player_performance(players_df)
        
        if not predictions_df.empty:
            # SANITY CHECK: If ML predictions are broken (Max EV < 2.0), abort ML
            max_ev = predictions_df['predicted_ev'].max()
            if max_ev < 1.0: # Lowered threshold slightly to be less aggressive
                logger.warning(f"⚠️ ML Predictions look invalid (Max EV: {max_ev:.2f}).")
                logger.warning("   Likely missing current season history in DB.")
                logger.warning("   Run 'python src/update_stats.py' to fix.")
                logger.warning("   Falling back to standard projections.")
                return players_df # Return without merging
            
            # Save to DB
            if db_manager:
                save_df = predictions_df.copy()
                save_df['gw'] = 999 
                save_df['model_version'] = model_version
                db_manager.save_predictions(save_df.to_dict('records'))
            
            # Merge
            predictions_df = predictions_df[['player_id', 'predicted_ev']]
            players_df = players_df.merge(predictions_df, left_on='id', right_on='player_id', how='left')
            
            # Apply 'Chance of Playing' logic
            if 'chance_of_playing_next_round' in players_df.columns:
                chance = pd.to_numeric(players_df['chance_of_playing_next_round'], errors='coerce').fillna(100)
                multiplier = chance / 100.0
                players_df['predicted_ev'] = players_df['predicted_ev'] * multiplier

            players_df['EV'] = players_df['predicted_ev'].fillna(0)
            
            # Verify high scorers
            top_scorer = players_df.sort_values('EV', ascending=False).iloc[0]
            logger.info(f"Top predicted player: {top_scorer['web_name']} (EV: {top_scorer['EV']:.2f})")
            
        return players_df
    except Exception as e:
        logger.error(f"Error in ML prediction: {e}")
        return players_df

def record_transfer_decision(db_manager, gameweek: int, recommendations: list, entry_id: int = None):
    if not db_manager or not recommendations: return
    try:
        best_rec = recommendations[0]
        data = {
            'players_out': best_rec.get('players_out', []),
            'players_in': best_rec.get('players_in', []),
            'num_transfers': best_rec.get('num_transfers', 0),
            'net_ev_gain': best_rec.get('net_ev_gain', 0)
        }
        db_manager.save_decision(gameweek, data, entry_id=entry_id)
        logger.info("Transfer decision recorded successfully")
    except Exception as e:
        logger.error(f"Error recording decision: {e}")

def apply_learning_system(db_manager, api_client, entry_id: int, gameweek: int, recommendations: list, ml_engine=None) -> list:
    """
    Apply learning system to improve recommendations based on past decisions.
    This is a non-destructive operation that enhances recommendations.
    
    Args:
        db_manager: Database manager instance
        api_client: FPL API client instance
        entry_id: User's entry ID
        gameweek: Current gameweek
        recommendations: List of recommendations
        ml_engine: Optional ML engine instance for fine-tuning
    
    Returns:
        Adjusted recommendations (or original if learning fails)
    """
    try:
        from learning_system import LearningSystem
        
        learning = LearningSystem(db_manager, api_client, entry_id)
        
        # Load past decisions
        decision_history = learning.load_decision_history(min_gw=max(1, gameweek - 10))
        
        if decision_history.empty:
            logger.debug("No past decisions found, skipping learning system")
            return recommendations
        
        # Analyze user preferences
        preferences = learning.analyze_user_preferences()
        if not preferences:
            logger.debug("Could not analyze preferences, using original recommendations")
            return recommendations
        
        # Adjust recommendations based on preferences
        adjusted_recommendations = learning.adjust_recommendation_priorities(recommendations)
        
        # Fine-tune ML model if requested and ML engine provided
        if ml_engine is not None:
            logger.info("Fine-tuning ML model with feedback data...")
            features_df, targets_df = learning.get_model_fine_tuning_data()
            if not features_df.empty and not targets_df.empty:
                fine_tune_result = ml_engine.fine_tune_with_feedback(features_df, targets_df)
                if fine_tune_result.get('status') == 'success':
                    logger.info("ML model fine-tuned successfully")
                else:
                    logger.debug(f"Fine-tuning skipped: {fine_tune_result.get('reason', 'unknown')}")
        
        logger.info("Learning system applied successfully")
        return adjusted_recommendations
        
    except ImportError:
        logger.debug("Learning system not available, using original recommendations")
        return recommendations
    except Exception as e:
        logger.warning(f"Error applying learning system: {e}, using original recommendations")
        return recommendations

def display_smart_recommendations(smart_recs: Dict, free_transfers: int):
    """Display smart recommendations with clear priority guidance."""
    print("\n" + "="*70)
    print("🎯 SMART TRANSFER RECOMMENDATIONS")
    print("="*70)
    
    num_forced = smart_recs['num_forced_transfers']
    if num_forced > 0:
        print(f"\n🚨 URGENT: {num_forced} player(s) MUST be replaced (injured/unavailable):")
        for player in smart_recs['forced_players']:
            print(f"   ❌ {player['web_name']} ({player['team_name']})")
    
    print(f"\n💰 Available: {free_transfers} Free Transfer(s)")
    print("\n" + "-"*70)
    
    recommendations = smart_recs['recommendations']
    
    if not recommendations:
        print("\n❌ NO BENEFICIAL TRANSFERS FOUND")
        if num_forced == 0:
            print("\n✅ RECOMMENDATION: ROLL YOUR FREE TRANSFER")
        return
    
    for i, rec in enumerate(recommendations, 1):
        priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢', 'VERY LOW': '⚪'}.get(rec['priority'], '⚪')
        print(f"\n{priority_emoji} Option {i}: {rec['description'].upper()}")
        print(f"   Strategy: {rec['num_transfers']} transfer(s), {rec['penalty_hits']} hit(s)")
        print(f"   Net Expected Gain: +{rec['net_ev_gain']:.2f} points")
        
        if i == 1:
            print(f"\n   OUT: {', '.join([p['name'] for p in rec['players_out']])}")
            print(f"   IN:  {', '.join([p['name'] for p in rec['players_in']])}")
    
    print("\n" + "="*70 + "\n")

def analyze_transfer_scenarios(recommendations: List[Dict], free_transfers: int, current_squad_ev: float):
    print("\n" + "="*70)
    print("TRANSFER SCENARIO ANALYSIS")
    print("="*70)
    print(f"Current Squad EV: {current_squad_ev:.2f}")
    
    if not recommendations: return
    
    print("\n📊 SCENARIO COMPARISON:\n")
    print(f"{'Scenario':<30} {'Transfers':<12} {'Hits':<8} {'Raw Gain':<12} {'Penalty':<10} {'Net Gain':<12} {'Risk':<10}")
    print("-" * 70)
    print(f"{'0. ROLL FT (Bank)':<30} {0:<12} {0:<8} {0.0:<12.2f} {0:<10.0f} {0.0:<12.2f} {'LOW':<10}")
    
    for i, rec in enumerate(recommendations, 1):
        num_transfers = rec['num_transfers']
        hits = rec['penalty_hits']
        raw_gain = rec['original_net_gain']
        penalty = rec['transfer_penalty']
        net_gain = rec['net_ev_gain_adjusted']  # Use adjusted gain (after penalty)
        
        risk = "LOW" if hits == 0 else ("MEDIUM" if hits == 1 and net_gain > 3 else "HIGH")
        print(f"{f'{i}. {num_transfers} TRANSFER(S)':<30} {num_transfers:<12} {hits:<8} {raw_gain:<12.2f} {-penalty:<10.0f} {net_gain:<12.2f} {risk:<10}")
        
        # Show players in/out for this scenario
        players_out = rec.get('players_out', [])
        players_in = rec.get('players_in', [])
        
        if players_out or players_in:
            out_names = [f"{p['name']} ({p.get('team', 'Unknown')})" for p in players_out]
            in_names = [f"{p['name']} ({p.get('team', 'Unknown')})" for p in players_in]
            
            out_str = ", ".join(out_names) if out_names else "None"
            in_str = ", ".join(in_names) if in_names else "None"
            
            print(f"   OUT: {out_str}")
            print(f"   IN:  {in_str}")
            print()  # Empty line for readability
    
    print("="*70)

def main():
    parser = argparse.ArgumentParser(description='FPL Optimizer v3.2')
    parser.add_argument('--entry-id', type=int)
    parser.add_argument('--gw', type=int, default=None)
    parser.add_argument('--max-transfers', type=int, default=4)
    parser.add_argument('--output-dir', type=str, default='output')
    parser.add_argument('--config', type=str, default='config.yml')
    parser.add_argument('--cache-dir', type=str, default='.cache')
    parser.add_argument('--clear-cache', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--record-decision', action='store_true')
    parser.add_argument('--train-ml', action='store_true')
    parser.add_argument('--ingest-history', type=str, nargs='+')
    parser.add_argument('--model-version', type=str, default='v3.7') # Default is v3.7
    parser.add_argument('--enable-learning', action='store_true', help='Enable learning system to improve recommendations based on past decisions')
    parser.add_argument('--differential-analysis', action='store_true', help='Run differential finder to identify low-ownership gems')
    parser.add_argument('--set-piece-analysis', action='store_true', help='Run set piece analyzer to identify corner/FK/penalty takers')
    
    args = parser.parse_args()
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    logger.info("=" * 60)
    logger.info("FPL OPTIMIZER v3.2 - ML-POWERED EDITION")
    logger.info("=" * 60)
    
    if args.ingest_history and INGESTOR_AVAILABLE:
        db = initialize_database({})
        ingestor = HistoricalDataIngestor(db)
        ingestor.ingest_all_seasons()
        return 0

    config = load_config(args.config)
    db_manager = initialize_database(config)
    entry_id = args.entry_id if args.entry_id else config.get('default_entry_id')
    
    if not entry_id:
        logger.error("No entry ID provided.")
        return 1

    api_client = FPLAPIClient(cache_dir=args.cache_dir)
    if args.clear_cache: api_client.clear_cache()
    
    gameweek = args.gw if args.gw is not None else api_client.get_current_gameweek()
    logger.info(f"Target gameweek: GW{gameweek}")
    
    # Load shared data once (PERFORMANCE OPTIMIZATION: avoid redundant API calls)
    bootstrap = api_client.get_bootstrap_static()
    entry_info = api_client.get_entry_info(entry_id)
    entry_history = api_client.get_entry_history(entry_id)
    all_fixtures = api_client.get_fixtures()  # Load once, pass to all functions
    
    # Load history DataFrame once if database is available (PERFORMANCE OPTIMIZATION)
    history_df = None
    if db_manager:
        try:
            history_df = db_manager.get_current_season_history()
            if history_df.empty:
                history_df = None
        except Exception as e:
            logger.debug(f"Could not load history DataFrame: {e}")
            history_df = None
    
    players_df = pd.DataFrame(bootstrap['elements'])
    teams_df = pd.DataFrame(bootstrap['teams'])
    team_map = teams_df.set_index('id')['name'].to_dict()
    
    players_df['team_name'] = players_df['team'].map(team_map)
    players_df['position'] = players_df['element_type']
    
    # Get current squad IDs early to identify relevant teams/players for performance optimization
    # Use entry_history already loaded (PERFORMANCE OPTIMIZATION: avoid duplicate call)
    try:
        last_played_gw = max(1, gameweek - 1)
        chips_used = entry_history.get('chips', [])
        free_hit_active = any(c['event'] == last_played_gw and c['name'] == 'freehit' for c in chips_used)
        target_picks_gw = max(1, last_played_gw - 1) if free_hit_active else last_played_gw
        picks_data = api_client.get_entry_picks(entry_id, target_picks_gw)
        current_squad_ids = set([p['element'] for p in picks_data.get('picks', [])]) if picks_data else set()
        current_squad_teams = set(players_df[players_df['id'].isin(current_squad_ids)]['team'].dropna().unique())
    except:
        current_squad_ids = set()
        current_squad_teams = set()
    
    # Identify top transfer targets (top 200 by price or points) to limit processing
    top_players = players_df.nlargest(200, ['now_cost', 'total_points'], keep='all')
    relevant_team_ids = current_squad_teams | set(top_players['team'].dropna().unique())
    
    # Get fixtures for current gameweek (from pre-loaded all_fixtures)
    fixtures_for_gw = [f for f in all_fixtures if f.get('event') == gameweek]
    
    logger.info(f"Processing fixture analysis for {len(relevant_team_ids)} relevant teams (optimized)...")
    players_df = add_fixture_difficulty(players_df, api_client, gameweek, db_manager, relevant_team_ids, all_fixtures=all_fixtures, bootstrap_data=bootstrap)
    
    # --- ADVANCED STATISTICAL MODELS (OPTIONAL) ---
    # Only process current squad + top players for performance
    relevant_player_ids = current_squad_ids | set(top_players['id'].head(100))
    logger.info(f"Processing statistical analysis for {len(relevant_player_ids)} relevant players (optimized)...")
    players_df = add_statistical_analysis(players_df, api_client, gameweek, db_manager, relevant_player_ids, fixtures=fixtures_for_gw, bootstrap_data=bootstrap, history_df=history_df)

    # --- ML PREDICTION BLOCK (FIXED) ---
    MODEL_VERSION = args.model_version  # Use CLI argument or default 'v3.2'

    if db_manager and not args.train_ml:
        # Pass MODEL_VERSION explicitly
        players_df = train_and_predict_ml(db_manager, players_df, config, MODEL_VERSION)
    elif args.train_ml and db_manager:
        logger.info("Forcing ML training...")
        ml = MLEngine(db_manager, MODEL_VERSION) # Use MODEL_VERSION
        ml.train_model()
        ml.save_model()
        # Pass MODEL_VERSION to load the model we just trained
        players_df = train_and_predict_ml(db_manager, players_df, config, MODEL_VERSION)
    
    # Fallback to Projections if ML failed or was skipped
    if 'EV' not in players_df.columns or players_df['EV'].sum() < 10:
        logger.info("Using standard projections (Fallback/Hybrid)...")
        proj = ProjectionEngine(config)
        players_df = proj.calculate_projections(players_df)
    
    eo_calc = EOCalculator(config)
    players_df = eo_calc.apply_eo_adjustment(players_df, entry_info.get('summary_overall_rank', 100000))
    
    optimizer = TransferOptimizer(config)
    current_squad = optimizer.get_current_squad(entry_id, gameweek, api_client, players_df)
    
    # --- Bank & FT Logic ---
    bank = entry_info.get('last_deadline_bank', 0) / 10.0
    try:
        current_event = entry_history.get('current', [])[-1]
        last_event = current_event.get('event', gameweek - 1)
        transfers_data = api_client.get_entry_transfers(entry_id)
        
        # Group transfers by gameweek
        transfers_by_gw = {}
        for t in transfers_data:
            gw = t.get('event', 0)
            transfers_by_gw[gw] = transfers_by_gw.get(gw, 0) + 1
        
        # Calculate free transfers by checking consecutive gameweeks with no transfers
        # Start from last_event and work backwards
        free_transfers = 1  # Base: always get 1 free transfer per gameweek
        consecutive_no_transfers = 0
        
        # Check gameweeks from last_event down to 1 (or reasonable limit)
        for gw in range(last_event, max(1, last_event - 10), -1):
            if gw not in transfers_by_gw or transfers_by_gw[gw] == 0:
                consecutive_no_transfers += 1
                if consecutive_no_transfers > 0:
                    # Each gameweek with no transfers banks an additional free transfer
                    free_transfers = min(consecutive_no_transfers + 1, 3)  # Cap at 3
            else:
                # Transfers were made this gameweek, reset
                break
        
        if free_transfers > 1:
            logger.info(f"✓ {free_transfers - 1} Free Transfer(s) banked (Total: {free_transfers} FT)")
        else:
            logger.info(f"✓ Used FTs in recent gameweeks, reset to 1 FT")
    except Exception as e:
        free_transfers = 1
        logger.warning(f"Could not determine free transfers, assuming 1 FT: {e}")

    logger.info(f"💰 Budget: £{bank}m | 🔄 Free Transfers: {free_transfers}")
    logger.info(f"Optimizing transfers (Max: {args.max_transfers})...")
    
    current_squad_ids = set(current_squad['id'])
    available_players = players_df[~players_df['id'].isin(current_squad_ids)].copy()
    
    smart_recs = optimizer.generate_smart_recommendations(
        current_squad, available_players, bank, free_transfers, max_transfers=args.max_transfers
    )
    
    # Apply learning system if enabled (non-destructive)
    if args.enable_learning and db_manager:
        try:
            ml_engine_instance = None
            if ML_ENGINE_AVAILABLE and MLEngine is not None:
                ml_engine_instance = MLEngine(db_manager, MODEL_VERSION)
                if ml_engine_instance.load_model():
                    ml_engine_instance.is_trained = True
            
            adjusted_recommendations = apply_learning_system(
                db_manager, api_client, entry_id, gameweek, 
                smart_recs['recommendations'], ml_engine_instance
            )
            smart_recs['recommendations'] = adjusted_recommendations
            logger.info("✓ Learning system applied to recommendations")
        except Exception as e:
            logger.warning(f"Learning system failed, using original recommendations: {e}")
    
    display_smart_recommendations(smart_recs, free_transfers)
    analyze_transfer_scenarios(smart_recs['recommendations'], free_transfers, current_squad['EV'].sum())
    
    # --- DIFFERENTIAL FINDER (OPTIONAL) ---
    if args.differential_analysis:
        try:
            from differential_finder import DifferentialFinder
            logger.info("\n" + "="*70)
            logger.info("🔍 DIFFERENTIAL FINDER ANALYSIS")
            logger.info("="*70)
            
            diff_finder = DifferentialFinder(ownership_threshold=5.0)
            diff_report = diff_finder.generate_differential_report(
                players_df, api_client, gameweek, all_fixtures=all_fixtures
            )
            
            # Display low-ownership gems
            if not diff_report['low_ownership_gems'].empty:
                try:
                    gems = diff_report['low_ownership_gems'].head(10)
                    print("\n💎 LOW-OWNERSHIP GEMS (<5% ownership, high EV):")
                    print(f"{'Player':<20} {'Team':<15} {'Ownership':<12} {'EV':<8} {'Ratio':<10}")
                    print("-" * 70)
                    for _, player in gems.iterrows():
                        try:
                            web_name = str(player.get('web_name', 'Unknown'))[:19]
                            team_name = str(player.get('team_name', 'Unknown'))[:14]
                            ownership = float(pd.to_numeric(player.get('selected_by_percent', 0), errors='coerce') or 0)
                            ev = float(pd.to_numeric(player.get('EV', 0), errors='coerce') or 0)
                            ratio = float(pd.to_numeric(player.get('ownership_ev_ratio', 0), errors='coerce') or 0)
                            print(f"{web_name:<20} {team_name:<15} {ownership:.1f}%{'':<7} {ev:.2f}{'':<4} {ratio:.2f}")
                        except Exception as e:
                            logger.debug(f"Error displaying gem: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error displaying low-ownership gems: {e}")
            
            # Display fixture swing players
            if not diff_report['fixture_swing_players'].empty:
                try:
                    swings = diff_report['fixture_swing_players'].head(5)
                    print("\n📈 FIXTURE SWING PLAYERS (tough behind, easy ahead):")
                    print(f"{'Player':<20} {'Team':<15} {'Swing':<10} {'Next 3 FDR':<12}")
                    print("-" * 70)
                    for _, player in swings.iterrows():
                        try:
                            web_name = str(player.get('web_name', 'Unknown'))[:19]
                            team_name = str(player.get('team_name', 'Unknown'))[:14]
                            swing = float(pd.to_numeric(player.get('fixture_swing', 0), errors='coerce') or 0)
                            next_fdr = float(pd.to_numeric(player.get('next_3_fixtures_avg_difficulty', 0), errors='coerce') or 0)
                            print(f"{web_name:<20} {team_name:<15} {swing:.2f}{'':<6} {next_fdr:.2f}")
                        except Exception as e:
                            logger.debug(f"Error displaying swing player: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error displaying fixture swing players: {e}")
            
            # Display budget enablers
            if not diff_report['budget_enablers'].empty:
                try:
                    enablers = diff_report['budget_enablers'].head(10)
                    print("\n💰 BUDGET ENABLERS (≤£4.5M, nailed starters):")
                    print(f"{'Player':<20} {'Team':<15} {'Price':<10} {'Minutes':<10} {'Value':<10}")
                    print("-" * 70)
                    for _, player in enablers.iterrows():
                        try:
                            web_name = str(player.get('web_name', 'Unknown'))[:19]
                            team_name = str(player.get('team_name', 'Unknown'))[:14]
                            price = float(pd.to_numeric(player.get('now_cost', 0), errors='coerce') or 0) / 10.0
                            minutes = int(pd.to_numeric(player.get('minutes', 0), errors='coerce') or 0)
                            value = float(pd.to_numeric(player.get('value_ratio', 0), errors='coerce') or 0)
                            print(f"{web_name:<20} {team_name:<15} £{price:.1f}M{'':<5} {minutes:<10} {value:.2f}")
                        except Exception as e:
                            logger.debug(f"Error displaying budget enabler: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error displaying budget enablers: {e}")
            
            # Display new signings
            if not diff_report['new_signings'].empty:
                signings = diff_report['new_signings']
                print("\n🆕 NEW SIGNINGS/LOAN RETURNS (not yet on radar):")
                print(f"{'Player':<20} {'Team':<15} {'Ownership':<12} {'News':<30}")
                print("-" * 70)
                for _, player in signings.iterrows():
                    web_name = str(player.get('web_name', 'Unknown'))[:19]
                    team_name = str(player.get('team_name', 'Unknown'))[:14]
                    ownership = float(player.get('selected_by_percent', 0))
                    news = str(player.get('news', ''))[:28] if pd.notna(player.get('news')) else 'N/A'
                    print(f"{web_name:<20} {team_name:<15} {ownership:.1f}%{'':<7} {news}")
            
            logger.info("\n✓ Differential analysis complete")
        except ImportError as e:
            logger.warning(f"Differential finder not available: {e}")
        except Exception as e:
            logger.warning(f"Error running differential analysis: {e}")
    
    # --- SET PIECE ANALYZER (OPTIONAL) ---
    if args.set_piece_analysis:
        try:
            from set_piece_analyzer import SetPieceAnalyzer
            logger.info("\n" + "="*70)
            logger.info("⚽ SET PIECE ANALYSIS")
            logger.info("="*70)
            
            set_piece = SetPieceAnalyzer()
            history_df = None
            if db_manager:
                try:
                    history_df = db_manager.get_current_season_history()
                except:
                    pass
            
            sp_report = set_piece.generate_set_piece_report(players_df, history_df)
            
            # Display corner takers
            if not sp_report['corner_takers'].empty:
                try:
                    corners = sp_report['corner_takers'].groupby('team').first().head(15)
                    print("\n📐 CORNER TAKERS (by team):")
                    print(f"{'Player':<20} {'Team':<15} {'Creativity':<12} {'Assists':<10} {'Primary':<10}")
                    print("-" * 70)
                    for _, player in corners.iterrows():
                        try:
                            web_name = str(player.get('web_name', 'Unknown'))[:19]
                            team_name = str(player.get('team_name', 'Unknown'))[:14]
                            creativity = float(pd.to_numeric(player.get('creativity', 0), errors='coerce') or 0)
                            assists = int(pd.to_numeric(player.get('assists', 0), errors='coerce') or 0)
                            primary = "✓" if player.get('is_primary_corner_taker', False) else ""
                            print(f"{web_name:<20} {team_name:<15} {creativity:.1f}{'':<7} {assists:<10} {primary:<10}")
                        except Exception as e:
                            logger.debug(f"Error displaying corner taker: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error displaying corner takers: {e}")
            
            # Display free kick takers
            if not sp_report['free_kick_takers'].empty:
                try:
                    fks = sp_report['free_kick_takers'].groupby('team').first().head(15)
                    print("\n🎯 FREE KICK SPECIALISTS (by team):")
                    print(f"{'Player':<20} {'Team':<15} {'Threat':<12} {'Goals':<10} {'Primary':<10}")
                    print("-" * 70)
                    for _, player in fks.iterrows():
                        try:
                            web_name = str(player.get('web_name', 'Unknown'))[:19]
                            team_name = str(player.get('team_name', 'Unknown'))[:14]
                            threat = float(pd.to_numeric(player.get('threat', 0), errors='coerce') or 0)
                            goals = int(pd.to_numeric(player.get('goals_scored', 0), errors='coerce') or 0)
                            primary = "✓" if player.get('is_primary_fk_taker', False) else ""
                            print(f"{web_name:<20} {team_name:<15} {threat:.1f}{'':<7} {goals:<10} {primary:<10}")
                        except Exception as e:
                            logger.debug(f"Error displaying FK taker: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error displaying free kick takers: {e}")
            
            # Display penalty takers
            if not sp_report['penalty_takers'].empty:
                pens = sp_report['penalty_takers'].groupby('team').apply(
                    lambda x: x.sort_values('penalty_order').head(2)
                ).reset_index(drop=True)
                print("\n⚽ PENALTY TAKERS (by team, 1st & 2nd choice):")
                print(f"{'Player':<20} {'Team':<15} {'Order':<10} {'Penalties':<12}")
                print("-" * 70)
                for _, player in pens.iterrows():
                    web_name = str(player.get('web_name', 'Unknown'))[:19]
                    team_name = str(player.get('team_name', 'Unknown'))[:14]
                    order_num = int(player.get('penalty_order', 0))
                    order = f"{order_num}st" if order_num == 1 else f"{order_num}nd" if order_num == 2 else f"{order_num}rd"
                    pens_scored = int(player.get('penalties_scored', player.get('goals_scored', 0)))
                    print(f"{web_name:<20} {team_name:<15} {order:<10} {pens_scored:<12}")
            
            # Display set piece targets
            if not sp_report['set_piece_targets'].empty:
                targets = sp_report['set_piece_targets'].head(10)
                print("\n🎯 SET PIECE TARGETS (defenders/midfielders who score from set pieces):")
                print(f"{'Player':<20} {'Team':<15} {'Position':<12} {'Goals':<10} {'Threat':<10}")
                print("-" * 70)
                for _, player in targets.iterrows():
                    web_name = str(player.get('web_name', 'Unknown'))[:19]
                    team_name = str(player.get('team_name', 'Unknown'))[:14]
                    pos_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
                    pos = pos_map.get(int(player.get('element_type', 0)), 'UNK')
                    goals = int(player.get('goals_scored', 0))
                    threat = float(player.get('threat', 0))
                    print(f"{web_name:<20} {team_name:<15} {pos:<12} {goals:<10} {threat:.1f}")
            
            logger.info("\n✓ Set piece analysis complete")
        except ImportError as e:
            logger.warning(f"Set piece analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Error running set piece analysis: {e}")

    # Generate Report
    chip_eval = ChipEvaluator(config)
    chips_used = [c['name'] for c in entry_history.get('chips', [])]
    avail_chips = [c for c in ['bboost', '3xc', 'freehit', 'wildcard'] if c not in chips_used]
    evals = chip_eval.evaluate_all_chips(
        current_squad, players_df, gameweek, avail_chips, bank, smart_recs['recommendations']
    )
    
    Path(args.output_dir).mkdir(exist_ok=True)
    # Use pre-loaded fixtures instead of making another API call
    ReportGenerator(config).generate_report(
        entry_info, gameweek, current_squad, smart_recs['recommendations'],
        evals, players_df, f"{args.output_dir}/fpl_gw{gameweek}_report.md", 
        fixtures_for_gw, team_map
    )
    
    if args.record_decision and db_manager:
        record_transfer_decision(db_manager, gameweek, smart_recs['recommendations'], entry_id=entry_id)
        
    return 0

if __name__ == '__main__':
    sys.exit(main())
