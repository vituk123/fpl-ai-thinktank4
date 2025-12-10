#!/usr/bin/env python3
"""
Test script to run core visualization dashboard functions
"""
import sys
from pathlib import Path
import yaml
import json
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from visualization_dashboard import VisualizationDashboard
from fpl_api import FPLAPIClient
from database import DatabaseManager
from api_football_client import APIFootballClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yml"""
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)

def main():
    """Run dashboard functions and display output"""
    logger.info("=" * 70)
    logger.info("VISUALIZATION DASHBOARD - CORE FUNCTIONS TEST")
    logger.info("=" * 70)
    
    # Load config
    config = load_config()
    entry_id = config.get('default_entry_id', 2568103)
    
    # Initialize clients
    logger.info("\n1. Initializing clients...")
    api_client = FPLAPIClient()
    
    db_manager = None
    try:
        db_manager = DatabaseManager()
        logger.info("   ✓ Database manager initialized")
    except Exception as e:
        logger.warning(f"   ⚠ Database not available: {e}")
    
    api_football_client = None
    api_football_config = config.get('api_football', {})
    if api_football_config.get('enabled', False):
        try:
            api_key = api_football_config.get('api_key')
            if api_key:
                api_football_client = APIFootballClient(api_key=api_key)
                logger.info("   ✓ API-Football client initialized")
        except Exception as e:
            logger.warning(f"   ⚠ API-Football not available: {e}")
    
    # Initialize dashboard
    logger.info("\n2. Initializing visualization dashboard...")
    dashboard = VisualizationDashboard(
        api_client=api_client,
        db_manager=db_manager,
        api_football_client=api_football_client
    )
    logger.info("   ✓ Dashboard initialized")
    
    logger.info(f"\n3. Testing with entry_id: {entry_id}")
    logger.info("=" * 70)
    
    # Test team-specific functions
    logger.info("\n📊 TEAM-SPECIFIC ANALYTICS")
    logger.info("-" * 70)
    
    # 1. Performance Heatmap
    logger.info("\n1. Performance Heatmap...")
    try:
        result = dashboard.get_performance_heatmap(entry_id)
        logger.info(f"   ✓ Generated heatmap data")
        logger.info(f"   - Players: {len(result.get('players', []))}")
        logger.info(f"   - Gameweeks: {len(result.get('gameweeks', []))}")
        if result.get('players'):
            sample_player = result['players'][0]
            logger.info(f"   - Sample player: {sample_player.get('name')} with {len(sample_player.get('points_by_gw', []))} gameweeks")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 2. Value Tracker
    logger.info("\n2. Value Tracker...")
    try:
        result = dashboard.get_value_tracker(entry_id)
        logger.info(f"   ✓ Generated value tracker data")
        logger.info(f"   - Gameweeks tracked: {len(result.get('gameweeks', []))}")
        if result.get('your_value'):
            logger.info(f"   - Current value: £{result['your_value'][-1]:.1f}m" if result['your_value'] else "   - No value data")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 3. Transfer Analysis
    logger.info("\n3. Transfer Analysis...")
    try:
        result = dashboard.get_transfer_analysis(entry_id)
        logger.info(f"   ✓ Generated transfer analysis")
        logger.info(f"   - Transfers analyzed: {len(result.get('transfers', []))}")
        if result.get('transfers'):
            sample = result['transfers'][0]
            logger.info(f"   - Sample: GW{sample.get('gw')} - Predicted: {sample.get('predicted_gain')}, Actual: {sample.get('actual_gain')}")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 4. Position Balance
    logger.info("\n4. Position Balance...")
    try:
        result = dashboard.get_position_balance(entry_id)
        logger.info(f"   ✓ Generated position balance")
        logger.info(f"   - Total value: £{result.get('total_value', 0):.1f}m")
        for pos in result.get('positions', []):
            logger.info(f"   - {pos.get('name')}: £{pos.get('investment', 0):.1f}m ({pos.get('percentage', 0):.1f}%)")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 5. Chip Usage Timeline
    logger.info("\n5. Chip Usage Timeline...")
    try:
        result = dashboard.get_chip_usage_timeline(entry_id)
        logger.info(f"   ✓ Generated chip usage timeline")
        logger.info(f"   - Chips used: {len(result.get('chips', []))}")
        for chip in result.get('chips', []):
            logger.info(f"   - {chip.get('name')}: GW{chip.get('gw_used')}")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 6. Captain Performance
    logger.info("\n6. Captain Performance...")
    try:
        result = dashboard.get_captain_performance(entry_id)
        logger.info(f"   ✓ Generated captain performance")
        logger.info(f"   - Captain picks: {len(result.get('captains', []))}")
        if result.get('captains'):
            # Group by player
            from collections import defaultdict
            captain_counts = defaultdict(int)
            total_points = defaultdict(int)
            for cap in result['captains']:
                name = cap.get('player_name')
                captain_counts[name] += 1
                total_points[name] += cap.get('doubled_points', 0)
            logger.info(f"   - Most captained: {max(captain_counts.items(), key=lambda x: x[1])[0]} ({max(captain_counts.values())} times)")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 7. Rank Progression
    logger.info("\n7. Rank Progression...")
    try:
        result = dashboard.get_rank_progression(entry_id)
        logger.info(f"   ✓ Generated rank progression")
        logger.info(f"   - Gameweeks tracked: {len(result.get('gameweeks', []))}")
        if result.get('overall_rank'):
            current_rank = result['overall_rank'][-1] if result['overall_rank'] else 0
            logger.info(f"   - Current rank: {current_rank:,}")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 8. Value Efficiency
    logger.info("\n8. Value Efficiency...")
    try:
        result = dashboard.get_value_efficiency(entry_id)
        logger.info(f"   ✓ Generated value efficiency")
        logger.info(f"   - Players analyzed: {len(result.get('players', []))}")
        if result.get('players'):
            top = result['players'][0]
            logger.info(f"   - Top value: {top.get('name')} - {top.get('efficiency_score')} efficiency score")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # Test league-wide functions
    logger.info("\n\n🌍 LEAGUE-WIDE ANALYTICS")
    logger.info("-" * 70)
    
    # 9. Ownership Correlation
    logger.info("\n9. Ownership vs Points Correlation...")
    try:
        result = dashboard.get_ownership_points_correlation()
        logger.info(f"   ✓ Generated ownership correlation")
        logger.info(f"   - Players analyzed: {len(result.get('players', []))}")
        logger.info(f"   - Correlation coefficient: {result.get('correlation_coefficient', 0):.3f}")
        if result.get('players'):
            top_diff = result['players'][0]
            logger.info(f"   - Top differential: {top_diff.get('name')} ({top_diff.get('ownership')}% owned, {top_diff.get('total_points')} pts)")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 10. Template Team
    logger.info("\n10. Template Team...")
    try:
        result = dashboard.get_template_team()
        logger.info(f"   ✓ Generated template team")
        logger.info(f"   - Formation: {result.get('formation')}")
        logger.info(f"   - Squad size: {len(result.get('squad', []))}")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 11. Price Change Predictors
    logger.info("\n11. Price Change Predictors...")
    try:
        result = dashboard.get_price_change_predictors()
        logger.info(f"   ✓ Generated price change predictors")
        logger.info(f"   - Players analyzed: {len(result.get('players', []))}")
        if result.get('players'):
            top_pred = result['players'][0]
            change = top_pred.get('predicted_change', 0)
            logger.info(f"   - Top prediction: {top_pred.get('name')} - {change:+.1f} change ({top_pred.get('confidence', 0):.0%} confidence)")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 12. Position Distribution
    logger.info("\n12. Position Points Distribution...")
    try:
        result = dashboard.get_position_points_distribution()
        logger.info(f"   ✓ Generated position distribution")
        logger.info(f"   - Positions analyzed: {len(result.get('positions', []))}")
        for pos in result.get('positions', []):
            logger.info(f"   - {pos.get('name')}: Avg {pos.get('avg', 0):.1f} pts, Range [{pos.get('points', [0,0,0,0,0])[0]}-{pos.get('points', [0,0,0,0,0])[4]}]")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 13. Fixture Swing Analysis
    logger.info("\n13. Fixture Difficulty Swing Analysis...")
    try:
        result = dashboard.get_fixture_swing_analysis(lookahead=5)
        logger.info(f"   ✓ Generated fixture swing analysis")
        logger.info(f"   - Teams analyzed: {len(result.get('teams', []))}")
        if result.get('teams'):
            easiest = result['teams'][0]  # Sorted by swing_score (easiest first)
            logger.info(f"   - Easiest swing: {easiest.get('name')} (swing: {easiest.get('swing_score', 0):.2f})")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 14. DGW Probability
    logger.info("\n14. Double Gameweek Probability...")
    try:
        result = dashboard.get_dgw_probability(lookahead=10)
        logger.info(f"   ✓ Generated DGW probability")
        logger.info(f"   - Gameweeks analyzed: {len(result.get('gameweeks', []))}")
        if result.get('gameweeks'):
            high_prob = [gw for gw in result['gameweeks'] if gw.get('probability', 0) > 0.3]
            if high_prob:
                logger.info(f"   - High probability DGWs: {len(high_prob)} gameweeks")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    # 15. Price Bracket Performers
    logger.info("\n15. Top Performers by Price Bracket...")
    try:
        result = dashboard.get_price_bracket_performers()
        logger.info(f"   ✓ Generated price bracket performers")
        logger.info(f"   - Brackets analyzed: {len(result.get('brackets', []))}")
        for bracket in result.get('brackets', []):
            logger.info(f"   - {bracket.get('range')}: {len(bracket.get('players', []))} top performers")
            if bracket.get('players'):
                top = bracket['players'][0]
                logger.info(f"     Top: {top.get('name')} - {top.get('value_score', 0):.2f} value score")
    except Exception as e:
        logger.error(f"   ✗ Error: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ ALL DASHBOARD FUNCTIONS COMPLETED")
    logger.info("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

