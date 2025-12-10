"""
Dashboard Helper Functions
Provides helper functions for complex data aggregations used by the visualization dashboard.
"""
import logging
import random
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from fpl_api import FPLAPIClient

logger = logging.getLogger(__name__)


def sample_high_ranked_teams(api_client: FPLAPIClient, rank_range: Tuple[int, int] = (1, 10000), 
                             sample_size: int = 100) -> List[Dict]:
    """
    Sample high-ranked teams from FPL API and aggregate their picks.
    
    Args:
        api_client: FPL API client instance
        rank_range: Tuple of (min_rank, max_rank) to sample from
        sample_size: Number of teams to sample
        
    Returns:
        List of team data dictionaries with picks
    """
    try:
        # Get current gameweek
        current_gw = api_client.get_current_gameweek()
        
        # Strategy: Sample from leaderboard
        # Note: FPL API doesn't provide direct access to top 10k, so we'll use a workaround
        # We can try to access teams by rank if available, or use a different strategy
        
        sampled_teams = []
        
        # Try to get teams from different rank ranges
        # Since we can't directly query by rank, we'll use a sampling strategy
        # For now, return empty list and note that this requires manual entry IDs
        # In production, you might maintain a list of high-ranked team IDs
        
        logger.warning("High-ranked team sampling requires manual team IDs or external data source")
        logger.info(f"Would sample {sample_size} teams from rank range {rank_range[0]}-{rank_range[1]}")
        
        return sampled_teams
        
    except Exception as e:
        logger.error(f"Error sampling high-ranked teams: {e}")
        return []


def analyze_optimal_chip_timing(api_client: FPLAPIClient, entry_id: int, 
                                season: Optional[int] = None) -> Dict:
    """
    Analyze optimal chip timing vs actual usage.
    
    Args:
        api_client: FPL API client instance
        entry_id: FPL entry ID
        season: Season year (default: current season)
        
    Returns:
        Dictionary with optimal timing analysis
    """
    try:
        entry_history = api_client.get_entry_history(entry_id)
        chips_used = entry_history.get('chips', [])
        current = entry_history.get('current', [])
        
        # Get fixtures for analysis
        fixtures = api_client.get_fixtures()
        bootstrap = api_client.get_bootstrap_static()
        
        optimal_timing = {}
        
        # Analyze each chip type
        chip_types = ['wildcard', 'freehit', 'bboost', '3xc']
        
        for chip_type in chip_types:
            # Find when this chip was actually used
            actual_usage = next((c for c in chips_used if c.get('name') == chip_type), None)
            actual_gw = actual_usage.get('event', 0) if actual_usage else None
            
            # Calculate optimal timing based on fixture difficulty and DGWs
            optimal_gw = None
            reason = ""
            
            if chip_type == 'wildcard':
                # Optimal: Early in season (GW 4-8) or before big fixture swings
                optimal_gw = 6  # Example
                reason = "Early season allows maximum value building"
            elif chip_type == 'freehit':
                # Optimal: During blank gameweeks or when many top players are unavailable
                optimal_gw = None  # Would analyze BGWs
                reason = "Best used during blank gameweeks"
            elif chip_type == 'bboost':
                # Optimal: During double gameweeks
                optimal_gw = None  # Would analyze DGWs
                reason = "Best used during double gameweeks for maximum points"
            elif chip_type == '3xc':
                # Optimal: On premium captain during easy fixture or DGW
                optimal_gw = None  # Would analyze fixture difficulty
                reason = "Best used on premium captain with easy fixture or DGW"
            
            optimal_timing[chip_type] = {
                'actual_gw': actual_gw,
                'optimal_gw': optimal_gw,
                'reason': reason,
                'was_optimal': actual_gw == optimal_gw if optimal_gw else None
            }
        
        return optimal_timing
        
    except Exception as e:
        logger.error(f"Error analyzing optimal chip timing: {e}")
        return {}


def aggregate_template_team(sampled_teams: List[Dict], gameweek: int) -> Dict:
    """
    Aggregate picks from sampled teams to create template team.
    
    Args:
        sampled_teams: List of team data with picks
        gameweek: Gameweek number
        
    Returns:
        Dictionary with template team data
    """
    try:
        if not sampled_teams:
            return {'squad': [], 'formation': '3-4-3'}
        
        # Count player selections
        player_counts = {}
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
        for team in sampled_teams:
            picks = team.get('picks', [])
            for pick in picks:
                player_id = pick.get('element', 0)
                position = pick.get('position', 0)
                element_type = pick.get('element_type', 0)
                
                if player_id not in player_counts:
                    player_counts[player_id] = {
                        'count': 0,
                        'position': position_map.get(element_type, 'UNK'),
                        'element_type': element_type
                    }
                player_counts[player_id]['count'] += 1
        
        # Build template squad (most selected player in each position)
        template_squad = {
            'GK': [],
            'DEF': [],
            'MID': [],
            'FWD': []
        }
        
        for player_id, data in player_counts.items():
            position = data['position']
            if position in template_squad:
                template_squad[position].append({
                    'player_id': player_id,
                    'count': data['count'],
                    'ownership_percent': (data['count'] / len(sampled_teams)) * 100
                })
        
        # Sort by count and take top players
        for position in template_squad:
            template_squad[position].sort(key=lambda x: x['count'], reverse=True)
            template_squad[position] = template_squad[position][:5]  # Top 5 per position
        
        # Determine formation
        def_count = len([p for p in template_squad['DEF'] if p['count'] > len(sampled_teams) * 0.5])
        mid_count = len([p for p in template_squad['MID'] if p['count'] > len(sampled_teams) * 0.5])
        fwd_count = len([p for p in template_squad['FWD'] if p['count'] > len(sampled_teams) * 0.5])
        
        formation = f"{def_count}-{mid_count}-{fwd_count}"
        
        # Format squad for output
        squad = []
        for position, players in template_squad.items():
            for player in players[:3]:  # Top 3 per position
                squad.append({
                    'position': position,
                    'player_id': player['player_id'],
                    'ownership_in_top10k': round(player['ownership_percent'], 1)
                })
        
        return {
            'squad': squad,
            'formation': formation
        }
        
    except Exception as e:
        logger.error(f"Error aggregating template team: {e}")
        return {'squad': [], 'formation': '3-4-3'}


def calculate_transfer_success(actual_gain: float, predicted_gain: float) -> Dict:
    """
    Calculate transfer success metrics.
    
    Args:
        actual_gain: Actual points gained from transfer
        predicted_gain: Predicted points gain
        
    Returns:
        Dictionary with success metrics
    """
    try:
        if predicted_gain == 0:
            success_rate = 0
        else:
            success_rate = (actual_gain / predicted_gain) * 100
        
        was_successful = actual_gain >= predicted_gain * 0.8  # 80% of prediction
        
        return {
            'success_rate': round(success_rate, 1),
            'was_successful': was_successful,
            'difference': round(actual_gain - predicted_gain, 2)
        }
    except Exception as e:
        logger.error(f"Error calculating transfer success: {e}")
        return {'success_rate': 0, 'was_successful': False, 'difference': 0}

