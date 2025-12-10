"""
Image Downloader Module
Downloads player photos and team logos from API-Football.
"""
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Downloads images from API-Football media API."""
    
    MEDIA_BASE_URL = "https://media.api-sports.io/football"
    
    def __init__(self, download_dir: str = ".cache/images", max_retries: int = 3):
        """
        Initialize image downloader.
        
        Args:
            download_dir: Directory to save downloaded images
            max_retries: Maximum retry attempts for failed downloads
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.players_dir = self.download_dir / "players"
        self.teams_dir = self.download_dir / "teams"
        self.players_dir.mkdir(exist_ok=True)
        self.teams_dir.mkdir(exist_ok=True)
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://fantasy.premierleague.com/',
            'Origin': 'https://fantasy.premierleague.com'
        })
    
    def download_player_image_from_fpl(self, fpl_player_id: int, photo_id: str) -> Optional[Path]:
        """
        Download a player image from FPL API using photo ID.
        
        Args:
            fpl_player_id: FPL player ID (for filename)
            photo_id: Photo ID from FPL API (e.g., "154561.jpg" or "154561")
            
        Returns:
            Path to downloaded image or None if failed
        """
        filename = f"{fpl_player_id}.png"
        filepath = self.players_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            logger.debug(f"Player image already exists: {filename}")
            return filepath
        
        # Clean photo ID (remove .jpg extension if present)
        clean_photo_id = photo_id.replace('.jpg', '').replace('.png', '').strip()
        
        if not clean_photo_id or clean_photo_id == '':
            logger.debug(f"No photo ID for player {fpl_player_id}")
            return None
        
        # Try different FPL photo URL patterns (most common first)
        urls_to_try = [
            f"https://resources.premierleague.com/premierleague/photos/players/110x140/p{clean_photo_id}.png",
            f"https://resources.premierleague.com/premierleague/photos/players/110x140/p{clean_photo_id}.jpg",
            # Alternative patterns
            f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{clean_photo_id}.png",
            f"https://fantasy.premierleague.com/img/players/p{clean_photo_id}.png",
        ]
        
        for image_url in urls_to_try:
            try:
                response = self.session.get(image_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    # Check if it's actually an image
                    content_type = response.headers.get('content-type', '')
                    content_length = len(response.content)
                    if 'image' in content_type and content_length > 1000:  # Valid image > 1KB
                        filepath.write_bytes(response.content)
                        logger.debug(f"Downloaded player image: {filename} ({content_length} bytes)")
                        return filepath
                    elif content_length < 1000:
                        # Too small, probably an error page
                        continue
                elif response.status_code == 403:
                    # 403 means forbidden - FPL CDN blocking, skip this URL pattern
                    continue
                elif response.status_code == 404:
                    # 404 means not found - try next URL
                    continue
            except Exception as e:
                # Silent fail, try next URL
                continue
        
        # If all URLs failed, return None silently (we'll log summary at batch level)
        return None
    
    def download_player_image(self, api_football_player_id: int, fpl_player_id: int = None) -> Optional[Path]:
        """
        Download a single player image from API-Football.
        
        Args:
            api_football_player_id: API-Football player ID
            fpl_player_id: FPL player ID (for filename)
            
        Returns:
            Path to downloaded image or None if failed
        """
        image_url = f"{self.MEDIA_BASE_URL}/players/{api_football_player_id}.png"
        filename = f"{fpl_player_id or api_football_player_id}.png"
        filepath = self.players_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            logger.debug(f"Player image already exists: {filename}")
            return filepath
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(image_url, timeout=10)
                if response.status_code == 200:
                    filepath.write_bytes(response.content)
                    logger.debug(f"Downloaded player image: {filename}")
                    return filepath
                elif response.status_code == 404:
                    logger.warning(f"Player image not found: {api_football_player_id}")
                    return None
                else:
                    logger.warning(f"Failed to download player image {api_football_player_id}: HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"Error downloading player image {api_football_player_id} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
        
        return None
    
    def download_fpl_player_images_batch(self, fpl_players: List[Dict],
                                         progress_callback=None) -> Dict[int, Optional[Path]]:
        """
        Download multiple player images from FPL API.
        
        Args:
            fpl_players: List of FPL player dictionaries with 'id' and 'photo' fields
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping FPL player_id -> downloaded file path (or None)
        """
        results = {}
        total = len(fpl_players)
        failed_count = 0
        
        logger.info(f"Downloading {total} player images from FPL API...")
        
        for idx, player in enumerate(fpl_players, 1):
            if progress_callback and (idx % 50 == 0 or idx == total):
                progress_callback(idx, total)
            
            fpl_id = player.get('id')
            photo_id = player.get('photo', '')
            
            if not fpl_id:
                results[fpl_id] = None
                continue
            
            if not photo_id or photo_id == '':
                results[fpl_id] = None
                failed_count += 1
                continue
            
            filepath = self.download_player_image_from_fpl(fpl_id, photo_id)
            results[fpl_id] = filepath
            
            if filepath is None:
                failed_count += 1
            
            # Small delay to avoid overwhelming the server (reduced since we're skipping 403s faster)
            time.sleep(0.05)
        
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"Downloaded {successful}/{total} player images from FPL ({failed_count} failed/skipped)")
        
        return results
    
    def download_team_logo(self, team_id: int, logo_url: str = None) -> Optional[Path]:
        """
        Download a team logo.
        
        Args:
            team_id: Team ID (for filename)
            logo_url: Direct logo URL (from FPL API or API-Football)
            
        Returns:
            Path to downloaded logo or None if failed
        """
        filename = f"{team_id}.png"
        filepath = self.teams_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            logger.debug(f"Team logo already exists: {filename}")
            return filepath
        
        # Try direct logo URL first, then fallback to media API
        urls_to_try = []
        if logo_url:
            urls_to_try.append(logo_url)
        urls_to_try.append(f"{self.MEDIA_BASE_URL}/teams/{team_id}.png")
        
        for image_url in urls_to_try:
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(image_url, timeout=10)
                    if response.status_code == 200:
                        filepath.write_bytes(response.content)
                        logger.debug(f"Downloaded team logo: {filename} from {image_url}")
                        return filepath
                    elif response.status_code == 404:
                        continue  # Try next URL
                    else:
                        logger.warning(f"Failed to download team logo {team_id}: HTTP {response.status_code}")
                except Exception as e:
                    logger.warning(f"Error downloading team logo {team_id} (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(1)
        
        logger.warning(f"Could not download team logo for team {team_id}")
        return None
    
    def download_player_images_batch(self, player_mappings: Dict[int, int], 
                                     progress_callback=None) -> Dict[int, Optional[Path]]:
        """
        Download multiple player images in batch.
        
        Args:
            player_mappings: Dictionary mapping FPL player_id -> API-Football player_id
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping FPL player_id -> downloaded file path (or None)
        """
        results = {}
        total = len(player_mappings)
        
        logger.info(f"Downloading {total} player images...")
        
        for idx, (fpl_id, api_football_id) in enumerate(player_mappings.items(), 1):
            if progress_callback:
                progress_callback(idx, total)
            
            filepath = self.download_player_image(api_football_id, fpl_id)
            results[fpl_id] = filepath
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.2)
        
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"Downloaded {successful}/{total} player images")
        
        return results
    
    def download_team_logos_batch(self, team_data: List[Dict], 
                                  progress_callback=None) -> Dict[int, Optional[Path]]:
        """
        Download multiple team logos in batch.
        
        Args:
            team_data: List of team dictionaries with 'id' and optional 'logo' URL
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping team_id -> downloaded file path (or None)
        """
        results = {}
        total = len(team_data)
        
        logger.info(f"Downloading {total} team logos...")
        
        for idx, team in enumerate(team_data, 1):
            if progress_callback:
                progress_callback(idx, total)
            
            team_id = team.get('id')
            logo_url = team.get('logo')
            filepath = self.download_team_logo(team_id, logo_url)
            results[team_id] = filepath
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.2)
        
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"Downloaded {successful}/{total} team logos")
        
        return results


def create_player_id_mapping(fpl_players: List[Dict], api_football_players: List[Dict],
                             manual_mapping: Dict[int, int] = None) -> Dict[int, int]:
    """
    Create mapping from FPL player IDs to API-Football player IDs.
    
    Uses fuzzy name matching with manual corrections.
    
    Args:
        fpl_players: List of FPL player dictionaries with 'id', 'web_name', 'first_name', 'second_name'
        api_football_players: List of API-Football player dictionaries with 'player' containing 'id', 'name'
        manual_mapping: Manual mapping dictionary (FPL ID -> API-Football ID)
        
    Returns:
        Dictionary mapping FPL player_id -> API-Football player_id
    """
    if manual_mapping is None:
        manual_mapping = {}
    
    # Create lookup for API-Football players by name
    api_football_by_name = {}
    for player in api_football_players:
        player_info = player.get('player', {})
        name = player_info.get('name', '').lower().strip()
        player_id = player_info.get('id')
        if name and player_id:
            api_football_by_name[name] = player_id
    
    mapping = {}
    matched = 0
    unmatched = []
    
    for fpl_player in fpl_players:
        fpl_id = fpl_player.get('id')
        if not fpl_id:
            continue
        
        # Check manual mapping first
        if fpl_id in manual_mapping:
            mapping[fpl_id] = manual_mapping[fpl_id]
            matched += 1
            continue
        
        # Try to match by name
        fpl_first = fpl_player.get('first_name', '').lower().strip()
        fpl_second = fpl_player.get('second_name', '').lower().strip()
        fpl_web = fpl_player.get('web_name', '').lower().strip()
        
        # Try different name combinations
        name_variants = [
            f"{fpl_first} {fpl_second}",
            f"{fpl_web}",
            f"{fpl_second}",
        ]
        
        best_match = None
        best_score = 0.0
        
        for variant in name_variants:
            if not variant:
                continue
            
            # Try exact match first
            if variant in api_football_by_name:
                mapping[fpl_id] = api_football_by_name[variant]
                matched += 1
                best_match = None  # Found exact match
                break
            
            # Try fuzzy matching
            for api_name, api_id in api_football_by_name.items():
                score = SequenceMatcher(None, variant, api_name).ratio()
                if score > best_score and score > 0.8:  # 80% similarity threshold
                    best_score = score
                    best_match = api_id
        
        if best_match:
            mapping[fpl_id] = best_match
            matched += 1
        else:
            unmatched.append({
                'fpl_id': fpl_id,
                'fpl_name': f"{fpl_first} {fpl_second}".strip() or fpl_web,
                'web_name': fpl_web
            })
    
    logger.info(f"Matched {matched}/{len(fpl_players)} players ({len(unmatched)} unmatched)")
    
    if unmatched:
        logger.warning(f"Unmatched players (add to manual mapping):")
        for player in unmatched[:10]:  # Show first 10
            logger.warning(f"  FPL ID {player['fpl_id']}: {player['fpl_name']} ({player['web_name']})")
    
    return mapping


def load_manual_mapping(mapping_file: str) -> Dict[int, int]:
    """
    Load manual player ID mapping from JSON file.
    
    Args:
        mapping_file: Path to JSON mapping file
        
    Returns:
        Dictionary mapping FPL player_id -> API-Football player_id
    """
    import json
    from pathlib import Path
    
    mapping_path = Path(mapping_file)
    if not mapping_path.exists():
        logger.info(f"Manual mapping file not found: {mapping_file}")
        return {}
    
    try:
        with open(mapping_path, 'r') as f:
            data = json.load(f)
            manual_mappings = data.get('manual_mappings', {})
            # Convert string keys to integers
            return {int(k): int(v) for k, v in manual_mappings.items()}
    except Exception as e:
        logger.error(f"Error loading manual mapping file: {e}")
        return {}
