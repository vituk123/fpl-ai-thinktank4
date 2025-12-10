"""
Sentiment Analyzer Module for FPL Sentinel System
Analyzes tweets for transfer and captaincy recommendations.
"""
import re
import logging
from typing import Dict, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

# VADER sentiment analyzer
VADER_AVAILABLE = False
SentimentIntensityAnalyzer = None
try:
    from vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        VADER_AVAILABLE = True
    except ImportError:
        logger.warning("VADER sentiment analyzer not available, using simple fallback")

# TextBlob is optional
TEXTBLOB_AVAILABLE = False
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    pass


class SentimentAnalyzer:
    """
    Analyzes FPL expert tweets for transfer and captaincy recommendations.
    Uses entity recognition, intent detection, and sentiment analysis.
    """
    
    def __init__(self, players_df: pd.DataFrame):
        """
        Initialize the sentiment analyzer.
        
        Args:
            players_df: DataFrame with columns: web_name, first_name, second_name, id
        """
        self.players_df = players_df.copy()
        
        if VADER_AVAILABLE and SentimentIntensityAnalyzer:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
            logger.warning("Using simple sentiment fallback (VADER not available)")
        
        # Build player name mapping (handles nicknames and variations)
        self.player_mapping = self._build_player_mapping()
        
        # Intent detection patterns - Enhanced with more FPL-specific keywords
        self.buy_patterns = [
            r'(bring|get|transfer|buy)\s+in',
            r'(need|want|should|must)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # Player name after need/want
            r'bring\s+([A-Z][a-z]+)',
            r'get\s+([A-Z][a-z]+)',
            r'add\s+([A-Z][a-z]+)',
            r'bring\s+in\s+([A-Z][a-z]+)',
            r'\b(essential|must-have|must have|should get|recommend|bring in|add to team)\b',
            r'([A-Z][a-z]+)\s+is\s+(essential|must-have|must have|a must)',
            r'([A-Z][a-z]+)\s+is\s+(great|excellent|top|strong|good)\s+(option|pick|choice)',
            r'get\s+([A-Z][a-z]+)\s+in',
            r'bring\s+([A-Z][a-z]+)\s+in',
            r'add\s+([A-Z][a-z]+)\s+to',
        ]
        
        self.sell_patterns = [
            r'(sell|drop|transfer|ship)\s+out',
            r'get\s+rid\s+of',
            r'replace\s+([A-Z][a-z]+)',
            r'sell\s+([A-Z][a-z]+)',
            r'drop\s+([A-Z][a-z]+)',
            r'remove\s+([A-Z][a-z]+)',
            r'(-|out)\s+([A-Z][a-z]+)',  # "- Player" or "out Player"
            r'\b(avoid|stay away|don\'t get|skip|not worth|poor form|bad form)\b',
            r'([A-Z][a-z]+)\s+is\s+(injured|doubtful|out|suspended)',
            r'([A-Z][a-z]+)\s+should\s+be\s+(sold|transferred|dropped|removed)',
            r'([A-Z][a-z]+)\s+is\s+(not|isn\'t)\s+(worth|good|viable)',
            r'transfer\s+([A-Z][a-z]+)\s+out',
            r'ship\s+([A-Z][a-z]+)\s+out',
        ]
        
        self.captain_patterns = [
            r'captain',
            r'\b(c)\b',  # Standalone (c)
            r'cap\s+([A-Z][a-z]+)',
            r'captain\s+([A-Z][a-z]+)',
            r'c\s+([A-Z][a-z]+)',
            r'armband',
            r'triple\s+captain',
            r'vc\b',  # Vice captain
            r'vice\s+captain',
            r'captaincy',
            r'([A-Z][a-z]+)\s+\(c\)',  # Player (C)
            r'([A-Z][a-z]+)\s+for\s+captain',
            r'captain\s+([A-Z][a-z]+)',
            r'best\s+captain',
            r'top\s+captain',
        ]
        
        logger.info(f"Initialized SentimentAnalyzer with {len(self.player_mapping)} player mappings")
    
    def _build_player_mapping(self) -> Dict[str, str]:
        """
        Build a mapping of player names, nicknames, and variations.
        
        Returns:
            Dictionary mapping variations to standard web_name
        """
        mapping = {}
        
        for _, player in self.players_df.iterrows():
            web_name = player.get('web_name', '')
            first_name = player.get('first_name', '')
            second_name = player.get('second_name', '')
            full_name = f"{first_name} {second_name}".strip()
            
            if web_name:
                # Add web_name as key
                mapping[web_name.lower()] = web_name
                mapping[web_name] = web_name
                
                # Add first name only (if unique enough)
                if first_name and len(first_name) > 3:
                    mapping[first_name.lower()] = web_name
                
                # Add last name only
                if second_name:
                    mapping[second_name.lower()] = web_name
                    mapping[second_name] = web_name
                
                # Add full name
                if full_name:
                    mapping[full_name.lower()] = web_name
                    mapping[full_name] = web_name
        
        # Add common nicknames - Expanded list
        nickname_mappings = {
            'salah': 'Salah',
            'kdb': 'De Bruyne',
            'de bruyne': 'De Bruyne',
            'kevin de bruyne': 'De Bruyne',
            'taa': 'Alexander-Arnold',
            'trent': 'Alexander-Arnold',
            'trent alexander-arnold': 'Alexander-Arnold',
            'haaland': 'Haaland',
            'erling haaland': 'Haaland',
            'erling': 'Haaland',
            'kane': 'Kane',
            'harry kane': 'Kane',
            'son': 'Son',
            'son heung-min': 'Son',
            'heung-min son': 'Son',
            'bruno': 'Fernandes',
            'bruno fernandes': 'Fernandes',
            'rashford': 'Rashford',
            'marcus rashford': 'Rashford',
            'saka': 'Saka',
            'bukayo saka': 'Saka',
            'martinelli': 'Martinelli',
            'gabriel martinelli': 'Martinelli',
            'odegaard': 'Ødegaard',
            'martin odegaard': 'Ødegaard',
            'trippier': 'Trippier',
            'kieran trippier': 'Trippier',
            'mitoma': 'Mitoma',
            'kaoru mitoma': 'Mitoma',
            'foden': 'Foden',
            'phil foden': 'Foden',
            'watkins': 'Watkins',
            'ollie watkins': 'Watkins',
            'isak': 'Isak',
            'alexander isak': 'Isak',
            'palmer': 'Palmer',
            'cole palmer': 'Palmer',
            'gordon': 'Gordon',
            'anthony gordon': 'Gordon',
            'bowen': 'Bowen',
            'jarrod bowen': 'Bowen',
            'salah': 'Salah',
            'mo salah': 'Salah',
            'mohamed salah': 'Salah',
            'vvd': 'Van Dijk',
            'van dijk': 'Van Dijk',
            'virgil van dijk': 'Van Dijk',
            'gabriel': 'Gabriel',
            'gabriel magalhaes': 'Gabriel',
            'saliba': 'Saliba',
            'william saliba': 'Saliba',
            'white': 'White',
            'ben white': 'White',
            'zinchenko': 'Zinchenko',
            'oleksandr zinchenko': 'Zinchenko',
            'rice': 'Rice',
            'declan rice': 'Rice',
            'maddison': 'Maddison',
            'james maddison': 'Maddison',
            'garnacho': 'Garnacho',
            'alejandro garnacho': 'Garnacho',
            'højlund': 'Højlund',
            'rasmus højlund': 'Højlund',
            'darwin': 'Núñez',
            'darwin núñez': 'Núñez',
            'darwin nunez': 'Núñez',
            'jota': 'Jota',
            'diogo jota': 'Jota',
            'diaz': 'Díaz',
            'luis diaz': 'Díaz',
            'luis díaz': 'Díaz',
        }
        
        # Add nickname mappings if players exist
        for nickname, standard_name in nickname_mappings.items():
            if standard_name in self.players_df['web_name'].values:
                mapping[nickname] = standard_name
        
        return mapping
    
    def _detect_intent(self, text: str) -> Dict[str, bool]:
        """
        Detect intent in tweet text (buy, sell, captain) with improved context awareness.
        
        Args:
            text: Tweet text
        
        Returns:
            Dictionary with 'buy', 'sell', 'captain' boolean flags
        """
        text_lower = text.lower()
        
        intent = {
            'buy': False,
            'sell': False,
            'captain': False
        }
        
        # Check for buy patterns (case-insensitive, more flexible)
        for pattern in self.buy_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                intent['buy'] = True
                break
        
        # Check for sell patterns
        for pattern in self.sell_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                intent['sell'] = True
                break
        
        # Check for captain patterns
        for pattern in self.captain_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                intent['captain'] = True
                break
        
        # Context-aware detection for implicit recommendations
        # "Player X is essential" → buy
        if re.search(r'is\s+(essential|must-have|must have|a must|great|excellent|top|strong)', text_lower):
            intent['buy'] = True
        
        # "Avoid Player X" or "Don't get Player X" → sell
        if re.search(r'(avoid|don\'t get|skip|not worth|poor form|bad form)', text_lower):
            intent['sell'] = True
        
        # "Player X (C)" or "Player X for captain" → captain
        if re.search(r'\(c\)|for\s+captain|captaincy|armband', text_lower):
            intent['captain'] = True
        
        return intent
    
    def _extract_players(self, text: str) -> List[str]:
        """
        Extract player names mentioned in text.
        
        Args:
            text: Tweet text
        
        Returns:
            List of player web_names found in text
        """
        found_players = []
        text_lower = text.lower()
        
        # Check each player mapping
        for variation, standard_name in self.player_mapping.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variation.lower()) + r'\b'
            if re.search(pattern, text_lower):
                if standard_name not in found_players:
                    found_players.append(standard_name)
        
        return found_players
    
    def _calculate_sentiment(self, text: str, intent: Dict[str, bool]) -> float:
        """
        Calculate sentiment score for text.
        Forces sentiment based on intent if detected.
        
        Args:
            text: Tweet text
            intent: Intent dictionary with buy/sell/captain flags
        
        Returns:
            Sentiment score (-1 to 1)
        """
        # Use VADER for sentiment if available (better for social media)
        if self.vader:
            vader_score = self.vader.polarity_scores(text)['compound']
        else:
            # Simple fallback: count positive/negative words
            positive_words = ['good', 'great', 'excellent', 'must', 'essential', 'best', 'top', 'strong']
            negative_words = ['bad', 'poor', 'avoid', 'drop', 'sell', 'injured', 'doubtful']
            text_lower = text.lower()
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            if pos_count > neg_count:
                vader_score = 0.3
            elif neg_count > pos_count:
                vader_score = -0.3
            else:
                vader_score = 0.0
        
        # Force sentiment based on intent
        if intent['sell']:
            # Sell = negative sentiment
            return min(vader_score, -0.3)
        elif intent['buy'] or intent['captain']:
            # Buy/Captain = positive sentiment
            return max(vader_score, 0.3)
        
        return vader_score
    
    def analyze_tweets(self, tweets_df: pd.DataFrame) -> Dict:
        """
        Analyze tweets for transfer and captaincy recommendations.
        
        Args:
            tweets_df: DataFrame with columns: date, username, content
        
        Returns:
            Dictionary with analysis results including:
            - top_3_transfer_targets
            - top_3_sell_targets
            - top_3_captain_picks
        """
        if tweets_df.empty:
            logger.warning("No tweets to analyze")
            return {
                'top_3_transfer_targets': [],
                'top_3_sell_targets': [],
                'top_3_captain_picks': []
            }
        
        player_scores = {
            'buy': {},  # player_name -> total positive sentiment
            'sell': {},  # player_name -> total negative sentiment
            'captain': {}  # player_name -> total positive sentiment
        }
        
        for _, tweet in tweets_df.iterrows():
            content = tweet.get('content', '')
            
            # Process all tweets, even if content is empty (might have images with FPL info)
            # If content is empty but has images, note that in analysis
            has_images = tweet.get('has_images', False) or len(tweet.get('images', [])) > 0
            
            # If no content and no images, skip (truly empty tweet)
            if not content and not has_images:
                continue
            
            # For tweets with images but no text, we still want to analyze
            # (images might contain FPL data, lineups, etc.)
            if not content:
                content = "[Image tweet]"  # Placeholder for image-only tweets
            
            intent = self._detect_intent(content)
            sentiment = self._calculate_sentiment(content, intent)
            players = self._extract_players(content)
            
            # If no players found but tweet has images, it might still be FPL-related
            # (e.g., lineup images, stats graphics)
            if not players and has_images:
                # Don't skip - images might contain valuable FPL info
                pass
            
            for player in players:
                if intent['buy']:
                    if player not in player_scores['buy']:
                        player_scores['buy'][player] = 0
                    player_scores['buy'][player] += max(sentiment, 0.1)  # Ensure positive
                
                if intent['sell']:
                    if player not in player_scores['sell']:
                        player_scores['sell'][player] = 0
                    player_scores['sell'][player] += min(sentiment, -0.1)  # Ensure negative
                
                if intent['captain']:
                    if player not in player_scores['captain']:
                        player_scores['captain'][player] = 0
                    player_scores['captain'][player] += max(sentiment, 0.1)  # Ensure positive
        
        # Get top 3 for each category
        top_buy = sorted(player_scores['buy'].items(), key=lambda x: x[1], reverse=True)[:3]
        top_sell = sorted(player_scores['sell'].items(), key=lambda x: x[1])[:3]  # Most negative first
        top_captain = sorted(player_scores['captain'].items(), key=lambda x: x[1], reverse=True)[:3]
        
        result = {
            'top_3_transfer_targets': [{'player': name, 'score': score} for name, score in top_buy],
            'top_3_sell_targets': [{'player': name, 'score': score} for name, score in top_sell],
            'top_3_captain_picks': [{'player': name, 'score': score} for name, score in top_captain]
        }
        
        logger.info(f"Analysis complete: {len(top_buy)} buy targets, {len(top_sell)} sell targets, {len(top_captain)} captain picks")
        return result

