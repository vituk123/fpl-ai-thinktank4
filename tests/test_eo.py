"""
Unit tests for EO calculator.
"""
import pytest
import pandas as pd
from src.eo import EOCalculator


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'risk_tolerance': 0.6,
        'eo_weight': 0.1
    }


@pytest.fixture
def sample_players():
    """Sample player data with EO."""
    return pd.DataFrame({
        'id': [1, 2, 3],
        'web_name': ['Template', 'Mid', 'Differential'],
        'selected_by_percent': [80.0, 30.0, 5.0],
        'EV': [8.0, 6.0, 7.0]
    })


def test_calculate_eo(config, sample_players):
    """Test EO calculation."""
    calc = EOCalculator(config)
    eo = calc.calculate_eo(sample_players)
    assert eo.tolist() == [0.8, 0.3, 0.05]


def test_apply_eo_adjustment(config, sample_players):
    """Test EO adjustment."""
    calc = EOCalculator(config)
    result = calc.apply_eo_adjustment(sample_players, target_rank=50000)
    
    # Differential should get a bigger boost
    template_boost = result.loc[0, 'EV'] - sample_players.loc[0, 'EV']
    diff_boost = result.loc[2, 'EV'] - sample_players.loc[2, 'EV']
    
    assert diff_boost > template_boost

