"""
Zen Browser bookmark importer module for ChromeSync.

This module provides functionality to import bookmarks from Chrome to Zen Browser.
"""

import os
import time
import logging
import tempfile
import subprocess
from typing import List, Dict, Any, Optional

import pyautogui

from ...config import ConfigManager
from ...utils.security import secure_delete_file
from ..extractors import ChromeBookmark, BookmarkExtractor
from .profile_detector import ProfileDetector, ZenProfile

# Set up logging
logger = logging.getLogger(__name__)

class BookmarkImporter:
    """
    Imports bookmarks from Chrome to Zen Browser.
    
    This class uses GUI automation to import bookmarks from an HTML file
    into Zen Browser.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the bookmark importer.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.zen_path = config_manager.get('browsers', 'zen', {}).get('path', '')
        self.user_data_dir = config_manager.get('browsers', 'zen', {}).get('user_data_dir', '')
        self.profile_name = config_manager.get('browsers', 'zen', {}).get('profile', 'default')
        self.temp_dir = config_manager.get('storage', {}).get('temp_dir', tempfile.gettempdir())
        self.secure_delete = config_manager.get('security', {}).get('secure_delete_temp_files', True)
    
    def import_bookmarks(self, bookmarks: List[ChromeBookmark], profile: Optional[ZenProfile] = None,
                        progress_callback=None) -> bool:
        """
        Import bookmarks into Zen Browser.
        
        Args:
            bookmarks: List of ChromeBookmark objects to import
            profile: Optional ZenProfile to import to (if None, uses default)
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            True if import was successful, False otherwise
        """
        if not bookmarks:
            logger.warning("No bookmarks to import")
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
        
        # Save bookmarks to HTML file
        temp_html_path = None
        try:
            # Create bookmark extractor
            bookmark_extractor = BookmarkExtractor(self.config_manager)
            
            # Save bookmarks to HTML
            if progress_callback:
                progress_callback(10, 100, "Saving bookmarks to HTML file")
            
            temp_html_path = bookmark_extractor.save_to_html(bookmarks)
            
            if progress_callback:
                progress_callback(20, 100, f"Saved bookmarks to HTML")
            
            # Import bookmarks via GUI automation
            result = self._import_bookmarks_via_gui(temp_html_path, profile, progress_callback)
            
            return result
        
        except Exception as e:
            error_msg = f"Failed to import bookmarks: {str(e)}"
            logger.error(error_msg)
            if progress_callback:
                progress_callback(0, 100, error_msg)
            return False
        
        finally:
            # Clean up the temporary file
            if temp_html_path and os.path.exists(temp_html_path):
                if progress_callback:
                    progress_callback(95, 100, "Cleaning up temporary files")
                
                if self.secure_delete:
                    secure_delete_file(temp_html_path)
                else:
                    os.remove(temp_html_path)
    
    def _import_bookmarks_via_gui(self, html_path: str, profile: ZenProfile,
                                 progress_callback=None) -> bool:
        """
        Import bookmarks into Zen Browser via GUI automation.
        
        Args:
            html_path: Path to the HTML file containing bookmarks
            profile: ZenProfile to import to
            progress_callback: Optional callback function to report progress
        
        Returns:
            True if import was successful, False otherwise
        """
        try:
            # Launch Zen Browser with the specified profile
            if progress_callback:
                progress_callback(30, 100, "Launching Zen Browser")
            
            # Define command-line arguments for launching Zen Browser
            cmd_args = [
                self.zen_path,
                "-P", profile.name,
                "--new-window",
                "about:preferences#general"
            ]
            
            # Launch Zen Browser
            process = subprocess.Popen(cmd_args)
            
            # Wait for the browser to open
            time.sleep(5)
            
            if progress_callback:
                progress_callback(40, 100, "Navigating to bookmark settings")
            
            # Define required coordinates (these will need to be adjusted based on screen resolution)
            # In a real implementation, these would be calculated dynamically
            # or use more robust methods like image recognition
            bookmarks_button_coords = (400, 300)
            import_button_coords = (500, 350)
            import_html_option_coords = (500, 400)
            file_input_coords = (500, 450)
            open_button_coords = (600, 500)
            
            # Click on the Bookmarks section
            pyautogui.click(bookmarks_button_coords)
            time.sleep(1)
            
            if progress_callback:
                progress_callback(50, 100, "Opening import dialog")
            
            # Click on Import button
            pyautogui.click(import_button_coords)
            time.sleep(1)
            
            # Click on Import HTML option
            pyautogui.click(import_html_option_coords)
            time.sleep(1)
            
            # Enter file path in the file input dialog
            pyautogui.click(file_input_coords)
            pyautogui.write(html_path)
            time.sleep(1)
            
            if progress_callback:
                progress_callback(60, 100, "Importing bookmarks")
            
            # Click Open button
            pyautogui.click(open_button_coords)
            time.sleep(3)  # Wait for import to complete
            
            if progress_callback:
                progress_callback(80, 100, "Import completed")
            
            # Close the browser
            if progress_callback:
                progress_callback(90, 100, "Closing browser")
            
            pyautogui.hotkey('alt', 'f4')
            
            # Wait for the process to close
            process.wait(timeout=5)
            
            logger.info("Bookmark import completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to import bookmarks via GUI: {str(e)}")
            
            # Try to close the browser if it's still open
            try:
                pyautogui.hotkey('alt', 'f4')
            except:
                pass
            
            return False
