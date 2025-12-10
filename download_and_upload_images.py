#!/usr/bin/env python3
"""
Download and Upload Images Script
Downloads player photos and team logos from API-Football and uploads to Supabase storage.
"""
import sys
from pathlib import Path
import yaml
import logging
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fpl_api import FPLAPIClient
from api_football_client import APIFootballClient
from database import DatabaseManager
from image_downloader import ImageDownloader, create_player_id_mapping, load_manual_mapping
from image_uploader import ImageUploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.yml"""
    config_path = Path('config.yml')
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def progress_callback(current: int, total: int):
    """Progress callback for batch operations"""
    if current % 10 == 0 or current == total:
        logger.info(f"Progress: {current}/{total} ({current*100//total}%)")


def main():
    """Main workflow for downloading and uploading images"""
    logger.info("=" * 70)
    logger.info("IMAGE DOWNLOAD AND UPLOAD SYSTEM")
    logger.info("=" * 70)
    
    # Load configuration
    config = load_config()
    images_config = config.get('images', {})
    api_football_config = config.get('api_football', {})
    
    bucket_name = images_config.get('supabase_bucket', 'fpl-images')
    download_dir = images_config.get('download_dir', '.cache/images')
    mapping_file = images_config.get('player_mapping_file', 'player_id_mapping.json')
    season = images_config.get('season', 2024)
    
    # Initialize clients
    logger.info("\n1. Initializing clients...")
    
    # FPL API client
    fpl_client = FPLAPIClient()
    logger.info("   ✓ FPL API client initialized")
    
    # API-Football client
    api_key = api_football_config.get('api_key')
    if not api_key:
        logger.error("API-Football API key not found in config.yml")
        return 1
    
    api_football_client = APIFootballClient(
        api_key=api_key,
        requests_per_minute=api_football_config.get('requests_per_minute', 10),
        requests_per_day=api_football_config.get('requests_per_day', 100)
    )
    logger.info("   ✓ API-Football client initialized")
    
    # Database manager
    db_manager = None
    try:
        db_manager = DatabaseManager()
        # Ensure image tables exist
        db_manager.create_image_tables()
        logger.info("   ✓ Database manager initialized")
    except Exception as e:
        logger.warning(f"   ⚠ Database not available: {e}")
    
    # Image downloader
    downloader = ImageDownloader(download_dir=download_dir)
    logger.info("   ✓ Image downloader initialized")
    
    # Image uploader
    if db_manager:
        uploader = ImageUploader(db_manager.supabase_client, db_manager)
    else:
        logger.error("Database manager required for image uploader")
        return 1
    logger.info("   ✓ Image uploader initialized")
    
    # Get FPL players
    logger.info("\n2. Fetching FPL players...")
    bootstrap = fpl_client.get_bootstrap_static()
    fpl_players = bootstrap.get('elements', [])
    logger.info(f"   ✓ Found {len(fpl_players)} FPL players")
    
    # Download player images directly from FPL API
    logger.info("\n3. Downloading player images from FPL API...")
    player_images = downloader.download_fpl_player_images_batch(
        fpl_players,
        progress_callback=progress_callback
    )
    successful_downloads = sum(1 for v in player_images.values() if v is not None)
    logger.info(f"   ✓ Downloaded {successful_downloads}/{len(fpl_players)} player images from FPL")
    
    # Create player mapping for database (FPL ID -> FPL ID, since we're using FPL photos)
    player_mapping = {player.get('id'): player.get('id') for player in fpl_players if player.get('id')}
    
    # Get FPL teams (use FPL API for team logos)
    logger.info("\n4. Fetching team data...")
    fpl_teams = bootstrap.get('teams', [])
    logger.info(f"   ✓ Found {len(fpl_teams)} FPL teams")
    
    # Download team logos from FPL API
    logger.info("\n5. Downloading team logos from FPL API...")
    team_data = []
    for team in fpl_teams:
        team_id = team.get('id')
        # FPL API has team logos in the code field, we can construct URL
        # FPL team logos: https://resources.premierleague.com/premierleague/badges/t{code}.png
        team_code = team.get('code')
        if team_code:
            team_data.append({
                'id': team_id,
                'logo': f"https://resources.premierleague.com/premierleague/badges/t{team_code}.png"
            })
    
    # Download team logos
    team_logos = downloader.download_team_logos_batch(
        team_data,
        progress_callback=progress_callback
    )
    successful_logos = sum(1 for v in team_logos.values() if v is not None)
    logger.info(f"   ✓ Downloaded {successful_logos}/{len(team_data)} team logos")
    
    # Upload player images to Supabase
    logger.info("\n6. Uploading player images to Supabase...")
    player_image_urls = uploader.upload_player_images(
        bucket_name,
        {k: v for k, v in player_images.items() if v is not None},
        progress_callback=progress_callback
    )
    logger.info(f"   ✓ Uploaded {len(player_image_urls)} player images")
    
    # Upload team logos to Supabase
    logger.info("\n7. Uploading team logos to Supabase...")
    team_logo_urls = uploader.upload_team_logos(
        bucket_name,
        {k: v for k, v in team_logos.items() if v is not None},
        progress_callback=progress_callback
    )
    logger.info(f"   ✓ Uploaded {len(team_logo_urls)} team logos")
    
    # Save metadata to database
    logger.info("\n8. Saving metadata to database...")
    if player_image_urls:
        uploader.save_player_mappings(player_mapping, player_image_urls)
        logger.info("   ✓ Saved player mappings")
    
    if team_logo_urls:
        uploader.save_team_logos(team_logo_urls)
        logger.info("   ✓ Saved team logos")
    
    # Generate summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Player images: {len(player_image_urls)}/{len(player_mapping)}")
    logger.info(f"Team logos: {len(team_logo_urls)}/{len(team_data)}")
    logger.info(f"Storage bucket: {bucket_name}")
    logger.info(f"Images available at: {bucket_name}/players/ and {bucket_name}/teams/")
    logger.info("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

