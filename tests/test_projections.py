"""
Unit tests for projection engine.
"""
import pytest
import pandas as pd
from src.projections import ProjectionEngine


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'projection': {
            'regression_coefficients': {
                'xg_per90': 5.0,
                'xa_per90': 3.0,
                'form': 0.3,
            },
            'official_weight': 0.6,
            'regression_weight': 0.4,
            'doubtful_multiplier': 0.3,
            'injured_multiplier': 0.0,
        }
    }


@pytest.fixture
def sample_players():
    """Sample player data."""
    return pd.DataFrame({
        'ep_next': ['5.0', '3.2', '7.1'],
        'expected_goals': ['2.5', '1.0', '3.5'],
        'expected_assists': ['1.5', '2.0', '0.5'],
        'minutes': [900, 450, 810],
        'form': ['6.0', '4.0', '8.0'],
        'status': ['a', 'd', 'i']
    })


def test_official_projection(config, sample_players):
    """Test official projection calculation."""
    engine = ProjectionEngine(config)
    result = engine.calculate_official_projection(sample_players)
    assert result.tolist() == [5.0, 3.2, 7.1]


def test_regression_projection(config, sample_players):
    """Test regression projection calculation."""
    engine = ProjectionEngine(config)
    result = engine.calculate_regression_projection(sample_players)
    
    # Expected for first player: (2.5/900*90)*5 + (1.5/900*90)*3 + 6.0*0.3 = 1.25 + 0.45 + 1.8 = 3.5
    assert result.iloc[0] == pytest.approx(3.5)


def test_injury_adjustments(config, sample_players):
    """Test injury adjustments."""
    engine = ProjectionEngine(config)
    projections = pd.Series([10.0, 10.0, 10.0])
    adjusted = engine.apply_injury_adjustments(projections, sample_players)
    
    assert adjusted.iloc[0] == 10.0  # Available
    assert adjusted.iloc[1] == 3.0   # Doubtful (10 * 0.3)
    assert adjusted.iloc[2] == 0.0   # Injured

