"""
Unit tests for visualization dashboard functions.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization_dashboard import VisualizationDashboard
from fpl_api import FPLAPIClient
from database import DatabaseManager


@pytest.fixture
def mock_api_client():
    """Create a mock FPL API client"""
    client = Mock(spec=FPLAPIClient)
    client.get_current_gameweek.return_value = 16
    client.get_bootstrap_static.return_value = {
        'elements': [
            {'id': 1, 'web_name': 'Player1', 'element_type': 1, 'now_cost': 50, 'selected_by_percent': 10.0},
            {'id': 2, 'web_name': 'Player2', 'element_type': 2, 'now_cost': 60, 'selected_by_percent': 20.0},
        ],
        'teams': [
            {'id': 1, 'name': 'Team1'},
            {'id': 2, 'name': 'Team2'},
        ],
        'events': []
    }
    client.get_entry_history.return_value = {
        'current': [
            {'event': 1, 'value': 1000, 'rank': 1000000, 'points': 50},
            {'event': 2, 'value': 1010, 'rank': 950000, 'points': 45},
        ],
        'chips': [
            {'name': 'wildcard', 'event': 8},
            {'name': 'freehit', 'event': 12}
        ]
    }
    client.get_entry_picks.return_value = {
        'picks': [
            {'element': 1, 'position': 1, 'is_captain': True, 'is_vice_captain': False},
            {'element': 2, 'position': 2, 'is_captain': False, 'is_vice_captain': False},
        ]
    }
    client.get_entry_transfers.return_value = [
        {'event': 5, 'element_in': 3, 'element_out': 1}
    ]
    client.get_fixtures.return_value = [
        {'event': 1, 'team_h': 1, 'team_a': 2, 'team_h_difficulty': 2, 'team_a_difficulty': 3},
        {'event': 2, 'team_h': 2, 'team_a': 1, 'team_h_difficulty': 3, 'team_a_difficulty': 2},
    ]
    client._request = Mock(return_value={'history': []})
    return client


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager"""
    manager = Mock(spec=DatabaseManager)
    manager.get_current_season_history.return_value = pd.DataFrame({
        'player_id': [1, 2, 1, 2],
        'gw': [1, 1, 2, 2],
        'total_points': [5, 3, 6, 4],
        'element_type': [1, 2, 1, 2]
    })
    manager.get_decisions.return_value = pd.DataFrame({
        'gw': [5],
        'recommended_transfers': [{'net_ev_gain': 5.0, 'players_in': [3], 'players_out': [1]}],
        'actual_transfers_made': [[{'id': 3}]]
    })
    return manager


@pytest.fixture
def dashboard(mock_api_client, mock_db_manager):
    """Create a dashboard instance with mocked dependencies"""
    return VisualizationDashboard(
        api_client=mock_api_client,
        db_manager=mock_db_manager,
        api_football_client=None
    )


class TestPerformanceHeatmap:
    """Tests for performance heatmap function"""
    
    def test_get_performance_heatmap(self, dashboard):
        """Test performance heatmap generation"""
        result = dashboard.get_performance_heatmap(entry_id=12345)
        
        assert 'players' in result
        assert 'gameweeks' in result
        assert isinstance(result['players'], list)
        assert isinstance(result['gameweeks'], list)
    
    def test_get_performance_heatmap_empty(self, dashboard):
        """Test performance heatmap with no data"""
        dashboard.api_client.get_entry_picks.return_value = None
        result = dashboard.get_performance_heatmap(entry_id=12345)
        
        assert result['players'] == []
        assert result['gameweeks'] == []


class TestValueTracker:
    """Tests for value tracker function"""
    
    def test_get_value_tracker(self, dashboard):
        """Test value tracker generation"""
        result = dashboard.get_value_tracker(entry_id=12345)
        
        assert 'gameweeks' in result
        assert 'your_value' in result
        assert 'league_avg' in result
        assert len(result['gameweeks']) == len(result['your_value'])
        assert len(result['gameweeks']) == len(result['league_avg'])


class TestTransferAnalysis:
    """Tests for transfer analysis function"""
    
    def test_get_transfer_analysis(self, dashboard):
        """Test transfer analysis generation"""
        result = dashboard.get_transfer_analysis(entry_id=12345)
        
        assert 'transfers' in result
        assert isinstance(result['transfers'], list)


class TestPositionBalance:
    """Tests for position balance function"""
    
    def test_get_position_balance(self, dashboard):
        """Test position balance generation"""
        result = dashboard.get_position_balance(entry_id=12345, gameweek=16)
        
        assert 'positions' in result
        assert 'total_value' in result
        assert isinstance(result['positions'], list)
        assert result['total_value'] >= 0


class TestChipUsage:
    """Tests for chip usage timeline function"""
    
    def test_get_chip_usage_timeline(self, dashboard):
        """Test chip usage timeline generation"""
        result = dashboard.get_chip_usage_timeline(entry_id=12345)
        
        assert 'chips' in result
        assert isinstance(result['chips'], list)


class TestCaptainPerformance:
    """Tests for captain performance function"""
    
    def test_get_captain_performance(self, dashboard):
        """Test captain performance generation"""
        result = dashboard.get_captain_performance(entry_id=12345)
        
        assert 'captains' in result
        assert isinstance(result['captains'], list)


class TestRankProgression:
    """Tests for rank progression function"""
    
    def test_get_rank_progression(self, dashboard):
        """Test rank progression generation"""
        result = dashboard.get_rank_progression(entry_id=12345)
        
        assert 'gameweeks' in result
        assert 'overall_rank' in result
        assert 'mini_leagues' in result
        assert len(result['gameweeks']) == len(result['overall_rank'])


class TestValueEfficiency:
    """Tests for value efficiency function"""
    
    def test_get_value_efficiency(self, dashboard):
        """Test value efficiency generation"""
        result = dashboard.get_value_efficiency(entry_id=12345)
        
        assert 'players' in result
        assert isinstance(result['players'], list)


class TestOwnershipCorrelation:
    """Tests for ownership correlation function"""
    
    def test_get_ownership_points_correlation(self, dashboard):
        """Test ownership correlation generation"""
        result = dashboard.get_ownership_points_correlation(gameweek=16)
        
        assert 'players' in result
        assert 'correlation_coefficient' in result
        assert isinstance(result['players'], list)
        assert isinstance(result['correlation_coefficient'], (int, float))


class TestPriceChangePredictors:
    """Tests for price change predictors function"""
    
    def test_get_price_change_predictors(self, dashboard):
        """Test price change predictors generation"""
        result = dashboard.get_price_change_predictors(gameweek=16)
        
        assert 'players' in result
        assert isinstance(result['players'], list)


class TestPositionDistribution:
    """Tests for position distribution function"""
    
    def test_get_position_points_distribution(self, dashboard):
        """Test position distribution generation"""
        result = dashboard.get_position_points_distribution(gameweek=16)
        
        assert 'positions' in result
        assert isinstance(result['positions'], list)


class TestFixtureSwing:
    """Tests for fixture swing analysis function"""
    
    def test_get_fixture_swing_analysis(self, dashboard):
        """Test fixture swing analysis generation"""
        result = dashboard.get_fixture_swing_analysis(gameweek=16, lookahead=5)
        
        assert 'teams' in result
        assert isinstance(result['teams'], list)


class TestDGWProbability:
    """Tests for DGW probability function"""
    
    def test_get_dgw_probability(self, dashboard):
        """Test DGW probability generation"""
        result = dashboard.get_dgw_probability(gameweek=16, lookahead=10)
        
        assert 'gameweeks' in result
        assert 'historical_patterns' in result
        assert isinstance(result['gameweeks'], list)


class TestPriceBrackets:
    """Tests for price bracket performers function"""
    
    def test_get_price_bracket_performers(self, dashboard):
        """Test price bracket performers generation"""
        result = dashboard.get_price_bracket_performers(gameweek=16)
        
        assert 'brackets' in result
        assert isinstance(result['brackets'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

