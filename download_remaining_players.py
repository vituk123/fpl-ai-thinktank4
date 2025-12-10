#!/usr/bin/env python3
"""
Download and upload remaining player images that haven't been downloaded yet.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import os
import logging
import time

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fpl_api import FPLAPIClient
from image_downloader import ImageDownloader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    logger.info("=" * 70)
    logger.info("DOWNLOADING AND UPLOADING REMAINING PLAYER IMAGES")
    logger.info("=" * 70)
    
    # Initialize clients
    fpl_client = FPLAPIClient()
    downloader = ImageDownloader(download_dir='.cache/images')
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    storage = supabase.storage.from_('fpl-images')
    
    # Get all FPL players
    logger.info("\n1. Fetching FPL players...")
    bootstrap = fpl_client.get_bootstrap_static()
    fpl_players = bootstrap.get('elements', [])
    logger.info(f"   ✓ Found {len(fpl_players)} FPL players")
    
    # Get already downloaded files
    local_dir = Path('.cache/images/players')
    downloaded_ids = {f.stem for f in local_dir.glob('*.png')}
    logger.info(f"   ✓ Already downloaded: {len(downloaded_ids)}")
    
    # Get already uploaded files (check a sample to avoid pagination issues)
    try:
        uploaded_files = storage.list('players')
        uploaded_ids = {f['name'].replace('.png', '') for f in uploaded_files}
        logger.info(f"   ✓ Already uploaded (from first page): {len(uploaded_ids)}")
    except:
        uploaded_ids = set()
    
    # Find missing players (not downloaded and have photo)
    missing_players = [
        p for p in fpl_players 
        if str(p.get('id')) not in downloaded_ids 
        and p.get('photo', '') 
        and p.get('photo', '') != ''
    ]
    
    logger.info(f"\n2. Missing players to download: {len(missing_players)}")
    
    if not missing_players:
        logger.info("   ✓ All players already downloaded!")
        return 0
    
    # Download missing player images
    logger.info(f"\n3. Downloading {len(missing_players)} player images...")
    downloaded_count = 0
    failed_downloads = []
    
    for idx, player in enumerate(missing_players, 1):
        if idx % 50 == 0 or idx == len(missing_players):
            logger.info(f"   Progress: {idx}/{len(missing_players)} ({idx*100//len(missing_players)}%)")
        
        fpl_id = player.get('id')
        photo_id = player.get('photo', '')
        
        if not photo_id:
            continue
        
        filepath = downloader.download_player_image_from_fpl(fpl_id, photo_id)
        if filepath:
            downloaded_count += 1
        else:
            failed_downloads.append(fpl_id)
        
        time.sleep(0.15)  # Rate limiting
    
    logger.info(f"   ✓ Downloaded {downloaded_count}/{len(missing_players)} player images")
    if failed_downloads:
        logger.warning(f"   ⚠ Failed to download: {len(failed_downloads)} players")
    
    # Upload newly downloaded images
    logger.info(f"\n4. Uploading newly downloaded images to Supabase...")
    
    # Get newly downloaded files
    newly_downloaded = {
        f.stem: f for f in local_dir.glob('*.png') 
        if f.stem not in downloaded_ids
    }
    
    logger.info(f"   Found {len(newly_downloaded)} new files to upload")
    
    uploaded_count = 0
    failed_uploads = []
    
    for idx, (player_id, filepath) in enumerate(newly_downloaded.items(), 1):
        if idx % 50 == 0 or idx == len(newly_downloaded):
            logger.info(f"   Progress: {idx}/{len(newly_downloaded)} ({idx*100//len(newly_downloaded)}%)")
        
        try:
            storage_path = f"players/{player_id}.png"
            
            # Read file
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            # Remove existing if any
            try:
                storage.remove([storage_path])
            except:
                pass
            
            # Upload
            storage.upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "image/png"}
            )
            
            uploaded_count += 1
            
            # Small delay
            if idx % 10 == 0:
                time.sleep(0.5)
                
        except Exception as e:
            logger.warning(f"   Failed to upload {player_id}: {e}")
            failed_uploads.append(player_id)
    
    logger.info(f"   ✓ Uploaded {uploaded_count}/{len(newly_downloaded)} images")
    if failed_uploads:
        logger.warning(f"   ⚠ Failed to upload: {len(failed_uploads)} images")
    
    # Final verification
    logger.info("\n" + "=" * 70)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 70)
    
    # Count total local files
    total_local = len(list(local_dir.glob('*.png')))
    logger.info(f"Total player images downloaded: {total_local}")
    logger.info(f"Newly downloaded: {downloaded_count}")
    logger.info(f"Newly uploaded: {uploaded_count}")
    
    # Verify in Supabase (sample check)
    try:
        uploaded_files = storage.list('players')
        logger.info(f"Files in Supabase (first page): {len(uploaded_files)}")
        logger.info("Note: Supabase list() has pagination, actual count may be higher")
    except:
        pass
    
    logger.info("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

