"""
Image Uploader Module
Uploads images to Supabase storage and manages metadata.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class ImageUploader:
    """Uploads images to Supabase storage."""
    
    def __init__(self, supabase_client, db_manager=None):
        """
        Initialize image uploader.
        
        Args:
            supabase_client: Supabase client instance
            db_manager: DatabaseManager instance (optional, for metadata storage)
        """
        self.supabase = supabase_client
        self.db_manager = db_manager
    
    def ensure_bucket_exists(self, bucket_name: str, public: bool = True) -> bool:
        """
        Ensure storage bucket exists, create if it doesn't.
        
        Args:
            bucket_name: Name of the bucket
            public: Whether bucket should be public
            
        Returns:
            True if bucket exists or was created successfully
        """
        try:
            # Try to list buckets to check if it exists
            try:
                buckets = self.supabase.storage.list_buckets()
                bucket_names = [b.name for b in buckets] if hasattr(buckets, '__iter__') else []
                
                if bucket_name in bucket_names:
                    logger.info(f"Bucket '{bucket_name}' already exists")
                    return True
            except:
                pass  # If listing fails, try to create anyway
            
            # Create bucket
            try:
                self.supabase.storage.create_bucket(
                    bucket_name,
                    options={"public": public} if public else {}
                )
                logger.info(f"Created bucket '{bucket_name}'")
            except Exception as create_error:
                # Bucket might already exist
                if "already exists" in str(create_error).lower() or "duplicate" in str(create_error).lower():
                    logger.info(f"Bucket '{bucket_name}' already exists")
                else:
                    raise create_error
            
            return True
            
        except Exception as e:
            # Bucket might already exist or we might not have permission
            logger.warning(f"Could not ensure bucket exists (may already exist): {e}")
            return True  # Assume it's okay to continue
    
    def upload_file(self, bucket_name: str, file_path: Path, storage_path: str,
                   content_type: str = "image/png") -> Optional[str]:
        """
        Upload a single file to Supabase storage.
        
        Args:
            bucket_name: Name of the storage bucket
            file_path: Local path to the file
            storage_path: Path in storage (e.g., 'players/123.png')
            content_type: MIME type of the file
            
        Returns:
            Public URL of uploaded file or None if failed
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            storage = self.supabase.storage.from_(bucket_name)
            
            # Try to remove existing file first (for upsert behavior)
            try:
                storage.remove([storage_path])
            except:
                pass  # File might not exist, which is fine
            
            # Upload file
            storage.upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            # Get public URL
            public_url = storage.get_public_url(storage_path)
            
            logger.debug(f"Uploaded {storage_path} -> {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading {storage_path}: {e}")
            return None
    
    def upload_player_images(self, bucket_name: str, player_images: Dict[int, Path],
                            progress_callback=None) -> Dict[int, str]:
        """
        Upload multiple player images.
        
        Args:
            bucket_name: Name of the storage bucket
            player_images: Dictionary mapping FPL player_id -> local file path
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping FPL player_id -> public URL
        """
        self.ensure_bucket_exists(bucket_name)
        
        results = {}
        total = len(player_images)
        logger.info(f"Uploading {total} player images to Supabase...")
        
        for idx, (player_id, file_path) in enumerate(player_images.items(), 1):
            if file_path is None:
                continue
            
            if progress_callback:
                progress_callback(idx, total)
            
            storage_path = f"players/{player_id}.png"
            public_url = self.upload_file(bucket_name, file_path, storage_path)
            
            if public_url:
                results[player_id] = public_url
        
        successful = len(results)
        logger.info(f"Uploaded {successful}/{total} player images")
        
        return results
    
    def upload_team_logos(self, bucket_name: str, team_logos: Dict[int, Path],
                         progress_callback=None) -> Dict[int, str]:
        """
        Upload multiple team logos.
        
        Args:
            bucket_name: Name of the storage bucket
            team_logos: Dictionary mapping team_id -> local file path
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping team_id -> public URL
        """
        self.ensure_bucket_exists(bucket_name)
        
        results = {}
        total = len(team_logos)
        logger.info(f"Uploading {total} team logos to Supabase...")
        
        for idx, (team_id, file_path) in enumerate(team_logos.items(), 1):
            if file_path is None:
                continue
            
            if progress_callback:
                progress_callback(idx, total)
            
            storage_path = f"teams/{team_id}.png"
            public_url = self.upload_file(bucket_name, file_path, storage_path)
            
            if public_url:
                results[team_id] = public_url
        
        successful = len(results)
        logger.info(f"Uploaded {successful}/{total} team logos")
        
        return results
    
    def save_player_mappings(self, player_mappings: Dict[int, int],
                            image_urls: Dict[int, str]) -> bool:
        """
        Save player ID mappings and image URLs to database.
        
        Args:
            player_mappings: Dictionary mapping FPL player_id -> API-Football player_id (or FPL ID if using FPL photos)
            image_urls: Dictionary mapping FPL player_id -> image URL
            
        Returns:
            True if successful
        """
        if not self.db_manager:
            logger.warning("No database manager available, skipping metadata storage")
            return False
        
        try:
            # Try to create table first if it doesn't exist
            try:
                self.db_manager.create_image_tables()
            except:
                pass  # Table might already exist or connection issue
            
            records = []
            for fpl_id, api_football_id in player_mappings.items():
                image_url = image_urls.get(fpl_id)
                records.append({
                    'fpl_player_id': fpl_id,
                    'api_football_player_id': api_football_id if api_football_id != fpl_id else None,  # None if using FPL photos
                    'image_url': image_url,
                    'updated_at': datetime.now().isoformat()
                })
            
            # Use Supabase to insert/update records
            if records:
                try:
                    # Delete existing records for these players (ignore if table doesn't exist)
                    fpl_ids = [r['fpl_player_id'] for r in records]
                    self.db_manager.supabase_client.table('player_image_mappings').delete().in_('fpl_player_id', fpl_ids).execute()
                except:
                    pass  # Table might not exist yet or records don't exist
                
                # Insert new records
                try:
                    self.db_manager.supabase_client.table('player_image_mappings').insert(records).execute()
                    logger.info(f"Saved {len(records)} player mappings to database")
                except Exception as insert_error:
                    logger.warning(f"Could not save via REST API, table may need to be created manually: {insert_error}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving player mappings: {e}")
            return False
    
    def save_team_logos(self, team_logo_urls: Dict[int, str]) -> bool:
        """
        Save team logo URLs to database.
        
        Args:
            team_logo_urls: Dictionary mapping team_id -> logo URL
            
        Returns:
            True if successful
        """
        if not self.db_manager:
            logger.warning("No database manager available, skipping metadata storage")
            return False
        
        try:
            # Try to create table first if it doesn't exist
            try:
                self.db_manager.create_image_tables()
            except:
                pass  # Table might already exist or connection issue
            
            records = []
            for team_id, logo_url in team_logo_urls.items():
                records.append({
                    'team_id': team_id,
                    'logo_url': logo_url,
                    'uploaded_at': datetime.now().isoformat()
                })
            
            # Use Supabase to insert/update records
            if records:
                try:
                    # Try to delete existing records for these teams (ignore if table doesn't exist)
                    team_ids = [r['team_id'] for r in records]
                    self.db_manager.supabase_client.table('team_logos').delete().in_('team_id', team_ids).execute()
                except:
                    pass  # Table might not exist yet or records don't exist
                
                # Insert new records
                try:
                    self.db_manager.supabase_client.table('team_logos').insert(records).execute()
                    logger.info(f"Saved {len(records)} team logos to database")
                except Exception as insert_error:
                    # If table doesn't exist in Supabase REST API, try SQL
                    logger.warning(f"Could not save via REST API, table may need to be created manually: {insert_error}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving team logos: {e}")
            return False
