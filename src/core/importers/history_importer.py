"""
Zen Browser history importer module for ChromeSync.

This module provides functionality to import browsing history from Chrome to Zen Browser.
"""

import os
import time
import shutil
import logging
import sqlite3
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

from ...config import ConfigManager
from ...utils.security import secure_delete_file
from ..extractors import ChromeHistoryItem, HistoryExtractor
from .profile_detector import ProfileDetector, ZenProfile

# Set up logging
logger = logging.getLogger(__name__)

class HistoryImporter:
    """
    Imports browsing history from Chrome to Zen Browser.
    
    This class implements direct database manipulation to import browsing history
    from Chrome to Zen Browser.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the history importer.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.zen_path = config_manager.get('browsers', 'zen', {}).get('path', '')
        self.user_data_dir = config_manager.get('browsers', 'zen', {}).get('user_data_dir', '')
        self.profile_name = config_manager.get('browsers', 'zen', {}).get('profile', 'default')
        self.temp_dir = config_manager.get('storage', {}).get('temp_dir', tempfile.gettempdir())
        self.secure_delete = config_manager.get('security', {}).get('secure_delete_temp_files', True)
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def import_history(self, history_items: List[ChromeHistoryItem], profile: Optional[ZenProfile] = None,
                      progress_callback=None) -> bool:
        """
        Import browsing history into Zen Browser.
        
        Args:
            history_items: List of ChromeHistoryItem objects to import
            profile: Optional ZenProfile to import to (if None, uses default)
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            True if import was successful, False otherwise
        """
        if not history_items:
            logger.warning("No history items to import")
            return True
        
        # Get profile if not provided
        if not profile:
            profile_detector = ProfileDetector(self.config_manager)
            profile = profile_detector.get_default_profile()
            
            if not profile:
                error_msg = "No valid Zen Browser profile found"
                logger.error(error_msg)
                if progress_callback:
                    progress_callback(0, 100, error_msg)
                return False
        
        if progress_callback:
            progress_callback(5, 100, f"Using Zen Browser profile: {profile.name}")
        
        # Check if Zen Browser is running and prompt to close it
        if self._is_zen_browser_running():
            error_msg = "Zen Browser is running. Please close it before importing history."
            logger.error(error_msg)
            if progress_callback:
                progress_callback(0, 100, error_msg)
            return False
        
        # Create temporary SQLite database for import
        temp_db_path = None
        try:
            # Create history extractor
            history_extractor = HistoryExtractor(self.config_manager)
            
            # Save history to SQLite database
            if progress_callback:
                progress_callback(10, 100, "Saving history to temporary database")
            
            temp_db_path = history_extractor.save_to_sqlite(history_items)
            
            if progress_callback:
                progress_callback(30, 100, f"Saved {len(history_items)} history items to database")
            
            # Import history via direct database manipulation
            result = self._import_history_via_database(temp_db_path, profile, progress_callback)
            
            return result
        
        except Exception as e:
            error_msg = f"Failed to import history: {str(e)}"
            logger.error(error_msg)
            if progress_callback:
                progress_callback(0, 100, error_msg)
            return False
        
        finally:
            # Clean up the temporary file
            if temp_db_path and os.path.exists(temp_db_path):
                if progress_callback:
                    progress_callback(95, 100, "Cleaning up temporary files")
                
                if self.secure_delete:
                    secure_delete_file(temp_db_path)
                else:
                    os.remove(temp_db_path)
    
    def _is_zen_browser_running(self) -> bool:
        """
        Check if Zen Browser is running.
        
        Returns:
            True if Zen Browser is running, False otherwise
        """
        import psutil
        
        zen_exe = os.path.basename(self.zen_path)
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and zen_exe.lower() in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return False
    
    def _import_history_via_database(self, temp_db_path: str, profile: ZenProfile,
                                   progress_callback=None) -> bool:
        """
        Import history into Zen Browser via direct database manipulation.
        
        Args:
            temp_db_path: Path to the SQLite database containing history
            profile: ZenProfile to import to
            progress_callback: Optional callback function to report progress
        
        Returns:
            True if import was successful, False otherwise
        """
        # Locate the places.sqlite file in the profile directory
        places_db_path = os.path.join(profile.path, "places.sqlite")
        places_db_path_backup = os.path.join(self.temp_dir, f"places_backup_{int(time.time())}.sqlite")
        
        if not os.path.exists(places_db_path):
            logger.error(f"places.sqlite not found in profile: {profile.path}")
            return False
        
        if progress_callback:
            progress_callback(40, 100, "Creating backup of Zen Browser history database")
        
        # Create a backup of the places.sqlite file
        shutil.copy2(places_db_path, places_db_path_backup)
        
        try:
            if progress_callback:
                progress_callback(50, 100, "Importing history data")
            
            # Connect to the Zen Browser places database
            with sqlite3.connect(places_db_path) as zen_conn:
                zen_cursor = zen_conn.cursor()
                
                # Connect to the temp database
                with sqlite3.connect(temp_db_path) as temp_conn:
                    temp_conn.row_factory = sqlite3.Row
                    temp_cursor = temp_conn.cursor()
                    
                    # Get the highest place_id in the destination database to avoid conflicts
                    zen_cursor.execute("SELECT MAX(id) FROM moz_places")
                    max_place_id = zen_cursor.fetchone()[0] or 0
                    
                    # Get the highest visit_id in the destination database
                    zen_cursor.execute("SELECT MAX(id) FROM moz_historyvisits")
                    max_visit_id = zen_cursor.fetchone()[0] or 0
                    
                    # Get places data from temp database
                    temp_cursor.execute("SELECT * FROM moz_places")
                    places = temp_cursor.fetchall()
                    
                    # Create mapping of old place_ids to new ones
                    place_id_mapping = {}
                    
                    # Import places data
                    for i, place in enumerate(places):
                        if progress_callback and len(places) > 0:
                            progress = 50 + int(20 * ((i + 1) / len(places)))
                            progress_callback(progress, 100, f"Importing place {i+1}/{len(places)}")
                        
                        old_place_id = place['id']
                        new_place_id = max_place_id + old_place_id
                        place_id_mapping[old_place_id] = new_place_id
                        
                        # Check if URL already exists
                        zen_cursor.execute("SELECT id FROM moz_places WHERE url = ?", (place['url'],))
                        existing = zen_cursor.fetchone()
                        
                        if existing:
                            # URL exists, update the mapping to use existing place_id
                            place_id_mapping[old_place_id] = existing[0]
                            continue
                        
                        # Insert place
                        zen_cursor.execute("""
                            INSERT INTO moz_places (
                                id, url, title, rev_host, visit_count, hidden, typed,
                                frecency, last_visit_date, guid
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            new_place_id,
                            place['url'],
                            place['title'],
                            place['rev_host'],
                            place['visit_count'],
                            place['hidden'],
                            place['typed'],
                            place['frecency'],
                            place['last_visit_date'],
                            place['guid']
                        ))
                    
                    # Get visits data from temp database
                    temp_cursor.execute("SELECT * FROM moz_historyvisits")
                    visits = temp_cursor.fetchall()
                    
                    # Import visits data
                    for i, visit in enumerate(visits):
                        if progress_callback and len(visits) > 0:
                            progress = 70 + int(20 * ((i + 1) / len(visits)))
                            progress_callback(progress, 100, f"Importing visit {i+1}/{len(visits)}")
                        
                        old_place_id = visit['place_id']
                        
                        # Skip if we don't have a mapping for this place_id
                        if old_place_id not in place_id_mapping:
                            continue
                        
                        new_place_id = place_id_mapping[old_place_id]
                        new_visit_id = max_visit_id + i + 1
                        
                        # Insert visit
                        zen_cursor.execute("""
                            INSERT INTO moz_historyvisits (
                                id, from_visit, place_id, visit_date, visit_type, session
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            new_visit_id,
                            visit['from_visit'],
                            new_place_id,
                            visit['visit_date'],
                            visit['visit_type'],
                            visit['session']
                        ))
            
            if progress_callback:
                progress_callback(90, 100, "History import completed")
            
            logger.info("History import completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to import history: {str(e)}")
            
            # Restore backup
            if os.path.exists(places_db_path_backup):
                try:
                    if os.path.exists(places_db_path):
                        os.remove(places_db_path)
                    shutil.copy2(places_db_path_backup, places_db_path)
                    logger.info("Restored places.sqlite from backup")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {str(restore_error)}")
            
            return False
        
        finally:
            # Clean up the backup file
            if os.path.exists(places_db_path_backup):
                if self.secure_delete:
                    secure_delete_file(places_db_path_backup)
                else:
                    os.remove(places_db_path_backup)
    
    def create_empty_profile(self, profile_name: str) -> Optional[ZenProfile]:
        """
        Create an empty Zen Browser profile.
        
        Args:
            profile_name: Name of the profile to create
        
        Returns:
            ZenProfile object for the created profile, or None if creation failed
        """
        try:
            # Launch Zen Browser with -CreateProfile argument
            cmd_args = [
                self.zen_path,
                "-CreateProfile",
                f"{profile_name} {os.path.join(os.path.expandvars(self.user_data_dir), profile_name)}"
            ]
            
            # Execute the command
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode != 0:
                logger.error(f"Failed to create profile: {stderr}")
                return None
            
            # Create ZenProfile object
            profile = ZenProfile(
                name=profile_name,
                path=os.path.join(os.path.expandvars(self.user_data_dir), profile_name),
                is_default=False,
                is_active=True
            )
            
            return profile
        
        except Exception as e:
            logger.error(f"Failed to create profile: {str(e)}")
            return None
