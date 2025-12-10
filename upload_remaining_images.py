#!/usr/bin/env python3
"""
Upload remaining player images to Supabase storage.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    logger.info("=" * 70)
    logger.info("UPLOADING REMAINING PLAYER IMAGES")
    logger.info("=" * 70)
    
    # Get local files
    local_dir = Path('.cache/images/players')
    local_files = {f.stem: f for f in local_dir.glob('*.png')}
    logger.info(f"Found {len(local_files)} local player images")
    
    # Get uploaded files from Supabase
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    storage = supabase.storage.from_('fpl-images')
    
    try:
        uploaded_files = storage.list('players')
        uploaded_names = {f['name'].replace('.png', '') for f in uploaded_files}
        logger.info(f"Already uploaded: {len(uploaded_names)}")
    except Exception as e:
        logger.warning(f"Could not list uploaded files: {e}")
        uploaded_names = set()
    
    # Find missing files
    missing = {player_id: filepath for player_id, filepath in local_files.items() if player_id not in uploaded_names}
    logger.info(f"Missing from Supabase: {len(missing)}")
    
    if not missing:
        logger.info("All images already uploaded!")
        return 0
    
    # Upload missing files
    logger.info(f"\nUploading {len(missing)} player images...")
    uploaded_count = 0
    failed_count = 0
    
    for idx, (player_id, filepath) in enumerate(missing.items(), 1):
        if idx % 50 == 0 or idx == len(missing):
            logger.info(f"Progress: {idx}/{len(missing)} ({idx*100//len(missing)}%)")
        
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
            
            # Small delay to avoid rate limiting
            if idx % 10 == 0:
                import time
                time.sleep(0.5)
                
        except Exception as e:
            logger.warning(f"Failed to upload {player_id}: {e}")
            failed_count += 1
    
    logger.info("\n" + "=" * 70)
    logger.info("UPLOAD SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Successfully uploaded: {uploaded_count}/{len(missing)}")
    logger.info(f"Failed: {failed_count}")
    logger.info("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

