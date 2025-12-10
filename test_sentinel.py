"""
Test script for FPL Sentinel system.
Tests the Twitter scraper and sentiment analyzer with sample data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

import pandas as pd
from fpl_api import FPLAPIClient
from sentiment_analyzer import SentimentAnalyzer

def test_sentiment_analyzer():
    """Test the sentiment analyzer with sample tweets."""
    print("=" * 60)
    print("Testing FPL Sentinel - Sentiment Analyzer")
    print("=" * 60)
    
    # Load player data
    api = FPLAPIClient()
    bootstrap = api.get_bootstrap_static()
    players_df = pd.DataFrame(bootstrap['elements'])
    
    # Initialize analyzer
    analyzer = SentimentAnalyzer(players_df)
    
    # Sample tweets (simulating expert recommendations)
    sample_tweets = pd.DataFrame([
        {
            'date': '2025-12-05',
            'username': 'FPLGeneral',
            'content': 'Bring in Haaland this week, he\'s essential for captaincy. Sell Gabriel, he\'s injured.'
        },
        {
            'date': '2025-12-05',
            'username': 'BigManBakar',
            'content': 'Salah is a must-have. Captain him this week. Transfer out Caicedo.'
        },
        {
            'date': '2025-12-05',
            'username': 'PrasFPL',
            'content': 'Get Saka in your team. He\'s in great form. Drop Pope, he\'s doubtful.'
        }
    ])
    
    # Analyze
    results = analyzer.analyze_tweets(sample_tweets)
    
    print("\nAnalysis Results:")
    print(f"Transfer Targets: {results['top_3_transfer_targets']}")
    print(f"Sell Targets: {results['top_3_sell_targets']}")
    print(f"Captain Picks: {results['top_3_captain_picks']}")
    
    print("\n✓ Sentiment analyzer test passed!")

if __name__ == "__main__":
    test_sentiment_analyzer()

