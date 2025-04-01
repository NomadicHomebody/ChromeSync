"""
Chrome password extraction module for ChromeSync.

This module provides functionality to extract passwords from Google Chrome.
It implements two methods:
1. GUI automation for password export to CSV
2. Direct database access with DPAPI decryption
"""

import os
import csv
import time
import json
import shutil
import logging
import sqlite3
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union

import pyautogui
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import win32crypt

from ...config import ConfigManager
from ...utils.security import secure_delete_file

# Set up logging
logger = logging.getLogger(__name__)

class ChromePassword:
    """Class to store a Chrome password entry."""
    
    def __init__(self, origin_url: str, username: str, password: str, 
                 action_url: str = "", date_created: int = 0, 
                 date_last_used: int = 0):
        """
        Initialize a Chrome password entry.
        
        Args:
            origin_url: The URL where the password is used
            username: The username
            password: The password
            action_url: The action URL for the password form
            date_created: The creation timestamp
            date_last_used: The last used timestamp
        """
        self.origin_url = origin_url
        self.username = username
        self.password = password
        self.action_url = action_url
        self.date_created = date_created
        self.date_last_used = date_last_used
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'origin_url': self.origin_url,
            'username': self.username,
            'password': self.password,
            'action_url': self.action_url,
            'date_created': self.date_created,
            'date_last_used': self.date_last_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChromePassword':
        """Create from dictionary."""
        return cls(
            origin_url=data.get('origin_url', ''),
            username=data.get('username', ''),
            password=data.get('password', ''),
            action_url=data.get('action_url', ''),
            date_created=data.get('date_created', 0),
            date_last_used=data.get('date_last_used', 0)
        )


class PasswordExtractor:
    """
    Extracts passwords from Google Chrome.
    
    This class implements two methods for extracting passwords:
    1. GUI automation using PyAutoGUI to export passwords to CSV
    2. Direct database access using SQLite and DPAPI decryption
    
    It automatically falls back to the second method if the first fails.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the password extractor.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.chrome_path = config_manager.get('browsers', 'chrome', {}).get('path', '')
        self.user_data_dir = config_manager.get('browsers', 'chrome', {}).get('user_data_dir', '')
        self.profile = config_manager.get('browsers', 'chrome', {}).get('profile', 'Default')
        self.use_gui_automation = config_manager.get('browsers', 'chrome', {}).get('use_gui_automation', True)
        self.temp_dir = config_manager.get('storage', {}).get('temp_dir', tempfile.gettempdir())
        self.encrypt_temp_files = config_manager.get('security', {}).get('encrypt_temp_files', True)
        self.secure_delete = config_manager.get('security', {}).get('secure_delete_temp_files', True)
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def extract_passwords(self, progress_callback=None) -> List[ChromePassword]:
        """
        Extract passwords from Chrome.
        
        This method will try GUI automation first if configured,
        and fall back to direct database access if that fails.
        
        Args:
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            List of ChromePassword objects
        
        Raises:
            RuntimeError: If both extraction methods fail
        """
        passwords = []
        
        # Try GUI automation method first if configured
        if self.use_gui_automation:
            try:
                if progress_callback:
                    progress_callback(0, 100, "Extracting passwords via GUI automation")
                
                passwords = self._extract_passwords_gui_automation(progress_callback)
                
                if progress_callback:
                    progress_callback(100, 100, f"Extracted {len(passwords)} passwords")
                
                return passwords
            
            except Exception as e:
                logger.warning(f"GUI automation failed: {str(e)}. Falling back to direct database access.")
                if progress_callback:
                    progress_callback(0, 100, "GUI automation failed. Trying direct database access...")
        
        # Fall back to direct database access
        try:
            if progress_callback:
                progress_callback(0, 100, "Extracting passwords via direct database access")
            
            passwords = self._extract_passwords_direct_access(progress_callback)
            
            if progress_callback:
                progress_callback(100, 100, f"Extracted {len(passwords)} passwords")
            
            return passwords
        
        except Exception as e:
            logger.error(f"Failed to extract passwords: {str(e)}")
            if progress_callback:
                progress_callback(0, 100, f"Failed to extract passwords: {str(e)}")
            
            raise RuntimeError(f"Failed to extract passwords: {str(e)}")
    
    def _extract_passwords_gui_automation(self, progress_callback=None) -> List[ChromePassword]:
        """
        Extract passwords using GUI automation.
        
        This method launches Chrome and navigates to chrome://settings/passwords
        to export passwords to a CSV file.
        
        Args:
            progress_callback: Optional callback function to report progress
        
        Returns:
            List of ChromePassword objects
        
        Raises:
            RuntimeError: If GUI automation fails
        """
        temp_csv_path = os.path.join(self.temp_dir, f"chrome_passwords_{int(time.time())}.csv")
        
        try:
            # Define required coordinates (these will need to be adjusted based on screen resolution)
            # In a real implementation, these would be calculated dynamically
            # or use more robust methods like image recognition
            settings_search_coords = (800, 100)
            password_manager_coords = (400, 200)
            three_dots_coords = (900, 300)
            export_option_coords = (900, 350)
            export_button_coords = (700, 400)
            save_dialog_coords = (700, 450)
            
            # Launch Chrome with password settings URL
            logger.info("Launching Chrome for password export")
            subprocess.Popen([self.chrome_path, "chrome://settings/passwords"])
            
            if progress_callback:
                progress_callback(10, 100, "Launched Chrome for password export")
            
            # Wait for Chrome to open
            time.sleep(3)
            
            # Navigate to search and type "password"
            pyautogui.click(settings_search_coords)
            pyautogui.write("password")
            time.sleep(1)
            
            # Click on Password Manager
            pyautogui.click(password_manager_coords)
            time.sleep(1)
            
            if progress_callback:
                progress_callback(30, 100, "Navigating to password settings")
            
            # Click three dots menu
            pyautogui.click(three_dots_coords)
            time.sleep(1)
            
            # Click export option
            pyautogui.click(export_option_coords)
            time.sleep(1)
            
            if progress_callback:
                progress_callback(50, 100, "Exporting passwords")
            
            # Confirm export
            pyautogui.click(export_button_coords)
            time.sleep(2)
            
            # Save dialog - type the path and press Enter
            pyautogui.click(save_dialog_coords)
            pyautogui.write(temp_csv_path)
            pyautogui.press('enter')
            time.sleep(3)
            
            if progress_callback:
                progress_callback(70, 100, "Saving exported passwords")
            
            # Close Chrome
            pyautogui.hotkey('alt', 'f4')
            
            # Parse the CSV file
            if os.path.exists(temp_csv_path):
                passwords = self._parse_csv_passwords(temp_csv_path)
                
                if progress_callback:
                    progress_callback(90, 100, f"Parsed {len(passwords)} passwords")
                
                return passwords
            else:
                raise RuntimeError(f"Password export file not found: {temp_csv_path}")
        
        except Exception as e:
            logger.error(f"Failed to extract passwords via GUI automation: {str(e)}")
            raise
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_csv_path):
                if self.secure_delete:
                    secure_delete_file(temp_csv_path)
                else:
                    os.remove(temp_csv_path)
    
    def _parse_csv_passwords(self, csv_path: str) -> List[ChromePassword]:
        """
        Parse passwords from a CSV file exported by Chrome.
        
        Args:
            csv_path: Path to the CSV file
        
        Returns:
            List of ChromePassword objects
        """
        passwords = []
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    password = ChromePassword(
                        origin_url=row.get('url', ''),
                        username=row.get('username', ''),
                        password=row.get('password', ''),
                        action_url=row.get('action_url', ''),
                        date_created=0,  # Not available in CSV
                        date_last_used=0   # Not available in CSV
                    )
                    passwords.append(password)
        
        except Exception as e:
            logger.error(f"Failed to parse CSV file: {str(e)}")
            raise
        
        return passwords
    
    def _extract_passwords_direct_access(self, progress_callback=None) -> List[ChromePassword]:
        """
        Extract passwords using direct database access.
        
        This method accesses the Chrome Login Data SQLite database directly
        and decrypts passwords using the Windows Data Protection API.
        
        Args:
            progress_callback: Optional callback function to report progress
        
        Returns:
            List of ChromePassword objects
        
        Raises:
            RuntimeError: If database access or decryption fails
        """
        # Locate the Login Data file
        login_data_path = os.path.join(
            os.path.expandvars(self.user_data_dir),
            self.profile,
            "Login Data"
        )
        
        local_state_path = os.path.join(
            os.path.expandvars(self.user_data_dir),
            "Local State"
        )
        
        if not os.path.exists(login_data_path):
            raise RuntimeError(f"Login Data file not found: {login_data_path}")
        
        if not os.path.exists(local_state_path):
            raise RuntimeError(f"Local State file not found: {local_state_path}")
        
        if progress_callback:
            progress_callback(10, 100, "Located Chrome password database")
        
        # Create a temporary copy of the database
        temp_db_path = os.path.join(self.temp_dir, f"chrome_login_data_{int(time.time())}.db")
        shutil.copy2(login_data_path, temp_db_path)
        
        try:
            # Read encryption key from Local State
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            # Get the encrypted key
            encrypted_key = local_state.get('os_crypt', {}).get('encrypted_key', '')
            if not encrypted_key:
                raise RuntimeError("Encrypted key not found in Local State")
            
            # Decode the key
            encrypted_key = encrypted_key.encode('utf-8')
            encrypted_key = encrypted_key[5:]  # Remove 'DPAPI' prefix
            decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            
            if progress_callback:
                progress_callback(20, 100, "Obtained decryption key")
            
            # Connect to the database
            passwords = []
            with sqlite3.connect(temp_db_path) as conn:
                cursor = conn.cursor()
                
                # Get all saved logins
                cursor.execute("""
                    SELECT origin_url, action_url, username_value, password_value,
                           date_created, date_last_used
                    FROM logins
                    ORDER BY date_last_used DESC
                """)
                
                # Total number of rows for progress reporting
                total = len(cursor.fetchall())
                cursor.execute("""
                    SELECT origin_url, action_url, username_value, password_value,
                           date_created, date_last_used
                    FROM logins
                    ORDER BY date_last_used DESC
                """)
                
                if progress_callback:
                    progress_callback(30, 100, f"Found {total} stored passwords")
                
                for i, (origin_url, action_url, username, encrypted_password, 
                         date_created, date_last_used) in enumerate(cursor.fetchall()):
                    try:
                        # Report progress
                        if progress_callback and total > 0:
                            progress = 30 + int(60 * (i / total))
                            progress_callback(progress, 100, f"Decrypting password {i+1}/{total}")
                        
                        # Skip empty passwords
                        if not encrypted_password:
                            continue
                        
                        # Decrypt the password
                        if encrypted_password.startswith(b'v10'):
                            # AES-256-GCM decryption for newer Chrome versions
                            initialization_vector = encrypted_password[3:15]
                            encrypted_password = encrypted_password[15:]
                            
                            cipher = AESGCM(decrypted_key)
                            decrypted_password = cipher.decrypt(
                                initialization_vector, 
                                encrypted_password, 
                                None
                            ).decode('utf-8')
                        else:
                            # DPAPI decryption for older Chrome versions
                            decrypted_password = win32crypt.CryptUnprotectData(
                                encrypted_password, 
                                None, 
                                None, 
                                None, 
                                0
                            )[1].decode('utf-8')
                        
                        # Create ChromePassword object
                        password = ChromePassword(
                            origin_url=origin_url,
                            username=username,
                            password=decrypted_password,
                            action_url=action_url,
                            date_created=date_created,
                            date_last_used=date_last_used
                        )
                        
                        passwords.append(password)
                    
                    except Exception as e:
                        logger.warning(f"Failed to decrypt password for {origin_url}: {str(e)}")
            
            if progress_callback:
                progress_callback(95, 100, f"Extracted {len(passwords)} passwords")
            
            return passwords
        
        except Exception as e:
            logger.error(f"Failed to extract passwords via direct access: {str(e)}")
            raise
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_db_path):
                if self.secure_delete:
                    secure_delete_file(temp_db_path)
                else:
                    os.remove(temp_db_path)
    
    def save_to_csv(self, passwords: List[ChromePassword], output_path: str = None) -> str:
        """
        Save passwords to a CSV file.
        
        Args:
            passwords: List of ChromePassword objects
            output_path: Path to save the CSV file (optional)
        
        Returns:
            Path to the saved CSV file
        """
        if not output_path:
            output_path = os.path.join(self.temp_dir, f"chrome_passwords_{int(time.time())}.csv")
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['url', 'username', 'password', 'action_url'])
                
                # Write password data
                for password in passwords:
                    writer.writerow([
                        password.origin_url,
                        password.username,
                        password.password,
                        password.action_url
                    ])
            
            logger.info(f"Saved {len(passwords)} passwords to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to save passwords to CSV: {str(e)}")
            raise
