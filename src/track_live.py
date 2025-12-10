#!/usr/bin/env python3
"""
Live Gameweek Tracker - Standalone CLI tool for real-time FPL tracking.
Run this script during live gameweeks to track your team's performance.
"""
import argparse
import sys
import logging
from fpl_api import FPLAPIClient
from live_tracker import LiveGameweekTracker

def setup_logging(level=logging.INFO):
    """Setup logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main():
    """Main entry point for live tracker."""
    parser = argparse.ArgumentParser(
        description='Live Gameweek Tracker - Real-time FPL tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Track current gameweek with default 60s updates
  python src/track_live.py --entry-id 2568103
  
  # Track specific gameweek with custom update interval
  python src/track_live.py --entry-id 2568103 --gw 16 --update-interval 30
  
  # One-time snapshot (no continuous tracking)
  python src/track_live.py --entry-id 2568103 --snapshot-only
  
  # Track with mini-league
  python src/track_live.py --entry-id 2568103 --league-id 12345
        """
    )
    
    parser.add_argument('--entry-id', type=int, required=True, help='Your FPL entry ID')
    parser.add_argument('--gw', type=int, default=None, help='Gameweek to track (default: current)')
    parser.add_argument('--update-interval', type=int, default=60, help='Update interval in seconds (default: 60)')
    parser.add_argument('--snapshot-only', action='store_true', help='Show one-time snapshot instead of continuous tracking')
    parser.add_argument('--league-id', type=int, default=None, help='Mini-league ID to track (optional)')
    parser.add_argument('--list-leagues', action='store_true', help='List all available mini-leagues and exit')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("🔴 LIVE GAMEWEEK TRACKER")
    logger.info("=" * 70)
    
    # Initialize API client (no caching for live data)
    api_client = FPLAPIClient(cache_dir='.cache')
    
    # Determine gameweek
    if args.gw is None:
        gameweek = api_client.get_current_gameweek()
    else:
        gameweek = args.gw
    
    logger.info(f"Tracking entry {args.entry_id} for Gameweek {gameweek}")
    
    # Initialize tracker
    try:
        tracker = LiveGameweekTracker(api_client, args.entry_id)
    except Exception as e:
        logger.error(f"Failed to initialize tracker: {e}")
        return 1
    
    # List leagues if requested
    if args.list_leagues:
        logger.info("Available Mini-Leagues:")
        leagues = tracker.get_user_leagues()
        if leagues:
            print(f"\n{'ID':<10} {'Name':<40} {'Your Rank':<12} {'Total Teams':<12}")
            print("-" * 80)
            for league in leagues:
                league_id = league.get('id', 0) or 0
                league_name = str(league.get('name', 'Unknown'))[:39]
                league_rank = league.get('rank', 0) or 0
                total_teams = league.get('total_teams', 0) or 0
                print(f"{league_id:<10} {league_name:<40} {league_rank:<12} {total_teams:<12}")
            print(f"\nUse --league-id <ID> to track a specific league")
        else:
            logger.warning("No mini-leagues found")
        return 0
    
    # Check if gameweek is live
    bootstrap = api_client.get_bootstrap_static(use_cache=False)
    current_event = next((e for e in bootstrap['events'] if e['id'] == gameweek), None)
    
    is_live = current_event and current_event.get('is_current', False)
    
    if args.snapshot_only or not is_live:
        # Show one-time snapshot
        if not is_live:
            logger.warning(f"Gameweek {gameweek} is not currently live. Showing snapshot...")
        else:
            logger.info("Showing one-time snapshot (use without --snapshot-only for continuous tracking)")
        
        # Get live data
        live_points = tracker.get_live_points(gameweek)
        auto_subs = tracker.calculate_auto_substitutions(gameweek)
        bonus_predictions = tracker.predict_bonus_points(gameweek)
        alerts = tracker.check_alerts(gameweek)
        team_summary = tracker.get_team_summary(gameweek, league_id=args.league_id)
        player_breakdown = tracker.get_player_breakdown(gameweek)
        
        # Get mini-league analysis if league specified
        league_analysis = None
        if args.league_id:
            # Pass user's GW points for accurate analysis
            user_gw_points = live_points.get('total', 0)
            league_analysis = tracker.analyze_mini_league_competitors(args.league_id, gameweek, user_gw_points=user_gw_points)
        
        # Project rank change (use mini-league if specified)
        if args.league_id and league_analysis:
            rank_projection = tracker.project_rank_change(gameweek, live_points['total'], league_id=args.league_id, league_analysis=league_analysis)
        else:
            rank_projection = tracker.project_rank_change(gameweek, live_points['total'])
        
        # Display update
        tracker._display_live_update(live_points, auto_subs, bonus_predictions, rank_projection, alerts,
                                     team_summary, player_breakdown, league_analysis)
        
        # Show mini-league if requested
        mini_league, league_name = tracker.get_mini_league_table(args.league_id)
        
        if mini_league:
            print(f"\n📊 MINI-LEAGUE TABLE: {league_name}")
            print(f"{'Rank':<6} {'Team':<25} {'GW Points':<12} {'Total':<10}")
            print("-" * 70)
            for team in mini_league[:20]:  # Top 20
                entry_name = team['entry_name'][:24] if len(team['entry_name']) > 24 else team['entry_name']
                print(f"{team['rank']:<6} {entry_name:<25} {team['event_total']:<12} {team['total']:<10}")
        
    else:
        # Continuous live tracking
        logger.info(f"Gameweek {gameweek} is LIVE! Starting real-time tracking...")
        logger.info(f"Updates every {args.update_interval} seconds. Press Ctrl+C to stop.")
        logger.info("")
        
        try:
            tracker.track_live(gameweek, update_interval=args.update_interval)
        except KeyboardInterrupt:
            logger.info("\n\nLive tracking stopped by user.")
            return 0
        except Exception as e:
            logger.error(f"Error during live tracking: {e}")
            return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

