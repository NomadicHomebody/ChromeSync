"""
Zen Browser password importer module for ChromeSync.

This module provides functionality to import passwords from Chrome to Zen Browser.
"""

import os
import time
import shutil
import logging
import tempfile
import subprocess
from typing import List, Dict, Any, Optional

import pyautogui

from ...config import ConfigManager
from ...utils.security import secure_delete_file
from ..extractors import ChromePassword, PasswordExtractor
from .profile_detector import ProfileDetector, ZenProfile

# Set up logging
logger = logging.getLogger(__name__)

class PasswordImporter:
    """
    Imports passwords from Chrome to Zen Browser.
    
    This class uses GUI automation to import passwords from a CSV file
    into Zen Browser.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the password importer.
        
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
    
    def import_passwords(self, passwords: List[ChromePassword], profile: Optional[ZenProfile] = None,
                        progress_callback=None) -> bool:
        """
        Import passwords into Zen Browser.
        
        Args:
            passwords: List of ChromePassword objects to import
            profile: Optional ZenProfile to import to (if None, uses default)
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            True if import was successful, False otherwise
        """
        if not passwords:
            logger.warning("No passwords to import")
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
        
        # Save passwords to CSV file
        temp_csv_path = None
        try:
            # Create password extractor
            password_extractor = PasswordExtractor(self.config_manager)
            
            # Save passwords to CSV
            if progress_callback:
                progress_callback(10, 100, "Saving passwords to CSV file")
            
            temp_csv_path = password_extractor.save_to_csv(passwords)
            
            if progress_callback:
                progress_callback(20, 100, f"Saved {len(passwords)} passwords to CSV")
            
            # Import passwords via GUI automation
            result = self._import_passwords_via_gui(temp_csv_path, profile, progress_callback)
            
            return result
        
        except Exception as e:
            error_msg = f"Failed to import passwords: {str(e)}"
            logger.error(error_msg)
            if progress_callback:
                progress_callback(0, 100, error_msg)
            return False
        
        finally:
            # Clean up the temporary file
            if temp_csv_path and os.path.exists(temp_csv_path):
                if progress_callback:
                    progress_callback(95, 100, "Cleaning up temporary files")
                
                if self.secure_delete:
                    secure_delete_file(temp_csv_path)
                else:
                    os.remove(temp_csv_path)
    
    def _import_passwords_via_gui(self, csv_path: str, profile: ZenProfile,
                                 progress_callback=None) -> bool:
        """
        Import passwords into Zen Browser via GUI automation.
        
        Args:
            csv_path: Path to the CSV file containing passwords
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
                "about:preferences#privacy"
            ]
            
            # Launch Zen Browser
            process = subprocess.Popen(cmd_args)
            
            # Wait for the browser to open
            time.sleep(5)
            
            if progress_callback:
                progress_callback(40, 100, "Navigating to password settings")
            
            # Define required coordinates (these will need to be adjusted based on screen resolution)
            # In a real implementation, these would be calculated dynamically
            # or use more robust methods like image recognition
            passwords_section_coords = (400, 300)
            saved_logins_button_coords = (500, 350)
            import_button_coords = (600, 400)
            file_input_coords = (500, 450)
            open_button_coords = (600, 500)
            close_button_coords = (700, 550)
            
            # Click on the Passwords section
            pyautogui.click(passwords_section_coords)
            time.sleep(1)
            
            # Click on Saved Logins button
            pyautogui.click(saved_logins_button_coords)
            time.sleep(2)
            
            if progress_callback:
                progress_callback(50, 100, "Opening import dialog")
            
            # Click on Import button
            pyautogui.click(import_button_coords)
            time.sleep(1)
            
            # Enter file path in the file input dialog
            pyautogui.click(file_input_coords)
            pyautogui.write(csv_path)
            time.sleep(1)
            
            if progress_callback:
                progress_callback(60, 100, "Importing passwords")
            
            # Click Open button
            pyautogui.click(open_button_coords)
            time.sleep(3)  # Wait for import to complete
            
            if progress_callback:
                progress_callback(80, 100, "Import completed")
            
            # Close the password manager window
            pyautogui.click(close_button_coords)
            time.sleep(1)
            
            # Close the browser
            if progress_callback:
                progress_callback(90, 100, "Closing browser")
            
            pyautogui.hotkey('alt', 'f4')
            
            # Wait for the process to close
            process.wait(timeout=5)
            
            logger.info("Password import completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to import passwords via GUI: {str(e)}")
            
            # Try to close the browser if it's still open
            try:
                pyautogui.hotkey('alt', 'f4')
            except:
                pass
            
            return False
