"""
Unit tests for FPL API client.
"""
import pytest
import json
from pathlib import Path
from src.fpl_api import FPLAPIClient


@pytest.fixture
def api_client(tmp_path):
    """Create API client with temp cache."""
    return FPLAPIClient(cache_dir=str(tmp_path), cache_ttl=3600)


def test_cache_path(api_client):
    """Test cache path generation."""
    path = api_client._get_cache_path('bootstrap-static/')
    assert path.name == 'bootstrap-static_.json'


def test_cache_operations(api_client, tmp_path):
    """Test cache set and get."""
    endpoint = 'test-endpoint'
    data = {'test': 'data', 'value': 123}
    
    # Set cache
    api_client._set_cache(endpoint, data)
    
    # Get cache
    cached = api_client._get_cached(endpoint)
    assert cached == data
    
    # Check file exists
    cache_file = tmp_path / 'test-endpoint.json'
    assert cache_file.exists()


def test_cache_validity(api_client, tmp_path):
    """Test cache validity check."""
    endpoint = 'test-endpoint'
    cache_path = tmp_path / 'test-endpoint.json'
    
    # No cache file
    assert not api_client._is_cache_valid(cache_path)
    
    # Create cache file
    with open(cache_path, 'w') as f:
        json.dump({'test': 'data'}, f)
    
    # Should be valid (just created)
    assert api_client._is_cache_valid(cache_path)


def test_clear_cache(api_client, tmp_path):
    """Test cache clearing."""
    # Create some cache files
    api_client._set_cache('endpoint1', {'data': 1})
    api_client._set_cache('endpoint2', {'data': 2})
    
    assert len(list(tmp_path.glob('*.json'))) == 2
    
    # Clear cache
    api_client.clear_cache()
    
    assert len(list(tmp_path.glob('*.json'))) == 0

