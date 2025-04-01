"""
Zen Browser profile detection module for ChromeSync.

This module provides functionality to detect and manage Zen Browser profiles
for importing data from Chrome.
"""

import os
import json
import logging
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ...config import ConfigManager

# Set up logging
logger = logging.getLogger(__name__)

class ZenProfile:
    """Class representing a Zen Browser profile."""
    
    def __init__(self, name: str, path: str, is_default: bool = False, is_active: bool = True):
        """
        Initialize a Zen Browser profile.
        
        Args:
            name: Profile name
            path: Profile path
            is_default: Whether this is the default profile
            is_active: Whether this profile is active
        """
        self.name = name
        self.path = path
        self.is_default = is_default
        self.is_active = is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'path': self.path,
            'is_default': self.is_default,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZenProfile':
        """Create from dictionary."""
        return cls(
            name=data.get('name', ''),
            path=data.get('path', ''),
            is_default=data.get('is_default', False),
            is_active=data.get('is_active', True)
        )
    
    def __str__(self) -> str:
        """String representation of the profile."""
        default_str = " (Default)" if self.is_default else ""
        active_str = " (Active)" if self.is_active else " (Inactive)"
        return f"{self.name}{default_str}{active_str} - {self.path}"


class ProfileDetector:
    """
    Detects and manages Zen Browser profiles.
    
    This class provides functionality to detect Zen Browser profiles
    for importing data from Chrome.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the profile detector.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.zen_path = config_manager.get('browsers', 'zen', {}).get('path', '')
        self.user_data_dir = config_manager.get('browsers', 'zen', {}).get('user_data_dir', '')
        self.default_profile = config_manager.get('browsers', 'zen', {}).get('profile', 'default')
    
    def detect_profiles(self) -> List[ZenProfile]:
        """
        Detect Zen Browser profiles.
        
        This method searches for Zen Browser profiles in the user data directory.
        
        Returns:
            List of ZenProfile objects
        
        Raises:
            RuntimeError: If profiles cannot be detected
        """
        if not self.user_data_dir:
            raise RuntimeError("Zen Browser user data directory not configured")
        
        user_data_dir = os.path.expandvars(self.user_data_dir)
        
        if not os.path.exists(user_data_dir):
            raise RuntimeError(f"Zen Browser user data directory not found: {user_data_dir}")
        
        profiles = []
        
        try:
            # Method 1: Look for profiles directly in the user data directory
            # Each subfolder that contains a "prefs.js" file is a profile
            for item in os.listdir(user_data_dir):
                profile_path = os.path.join(user_data_dir, item)
                
                # Skip files and special directories
                if not os.path.isdir(profile_path) or item.startswith('.'):
                    continue
                
                # Check if it's a profile directory (has prefs.js)
                if os.path.exists(os.path.join(profile_path, "prefs.js")):
                    # Determine if it's the default profile
                    is_default = item == self.default_profile
                    
                    # Create profile object
                    profile = ZenProfile(
                        name=item,
                        path=profile_path,
                        is_default=is_default,
                        is_active=True  # Assume all profiles are active
                    )
                    
                    profiles.append(profile)
            
            # Method 2: Look for profiles.ini file (similar to Firefox)
            profiles_ini_path = os.path.join(user_data_dir, "profiles.ini")
            if os.path.exists(profiles_ini_path):
                profiles_from_ini = self._parse_profiles_ini(profiles_ini_path, user_data_dir)
                
                # Merge profiles from both methods
                existing_paths = [os.path.normpath(p.path) for p in profiles]
                for p in profiles_from_ini:
                    if os.path.normpath(p.path) not in existing_paths:
                        profiles.append(p)
            
            # If no profiles found, try to launch Zen Browser and detect profiles
            if not profiles and os.path.exists(self.zen_path):
                logger.info("No profiles found. Attempting to launch Zen Browser to create a profile.")
                self._ensure_default_profile_exists()
                
                # Try detection again
                return self.detect_profiles()
            
            # If still no profiles, raise an error
            if not profiles:
                raise RuntimeError("No Zen Browser profiles found")
            
            logger.info(f"Detected {len(profiles)} Zen Browser profiles")
            for profile in profiles:
                logger.debug(f"Found profile: {profile}")
            
            return profiles
        
        except Exception as e:
            logger.error(f"Failed to detect Zen Browser profiles: {str(e)}")
            raise RuntimeError(f"Failed to detect Zen Browser profiles: {str(e)}")
    
    def _parse_profiles_ini(self, ini_path: str, user_data_dir: str) -> List[ZenProfile]:
        """
        Parse the profiles.ini file to extract profile information.
        
        Args:
            ini_path: Path to the profiles.ini file
            user_data_dir: Path to the user data directory
        
        Returns:
            List of ZenProfile objects
        """
        profiles = []
        
        try:
            # Parse ini file
            sections = {}
            current_section = None
            
            with open(ini_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith(';') or line.startswith('#'):
                        continue
                    
                    # Section header
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        sections[current_section] = {}
                        continue
                    
                    # Key-value pair
                    if current_section and '=' in line:
                        key, value = line.split('=', 1)
                        sections[current_section][key.strip()] = value.strip()
            
            # Process profile sections
            for section_name, properties in sections.items():
                if section_name.startswith('Profile'):
                    # Extract profile information
                    profile_name = properties.get('Name', section_name)
                    is_default = properties.get('Default', '0') == '1'
                    
                    # Determine profile path
                    profile_path = None
                    if 'Path' in properties:
                        path = properties['Path']
                        if 'IsRelative' in properties and properties['IsRelative'] == '1':
                            profile_path = os.path.join(user_data_dir, path)
                        else:
                            profile_path = path
                    
                    if profile_path and os.path.exists(profile_path):
                        profile = ZenProfile(
                            name=profile_name,
                            path=profile_path,
                            is_default=is_default,
                            is_active=True  # Assume all profiles are active
                        )
                        profiles.append(profile)
            
            return profiles
        
        except Exception as e:
            logger.warning(f"Failed to parse profiles.ini: {str(e)}")
            return []
    
    def _ensure_default_profile_exists(self):
        """
        Ensure that the default profile exists by launching Zen Browser.
        
        This method launches Zen Browser briefly to create a default profile
        if it doesn't exist already.
        """
        try:
            # Launch Zen Browser with --headless flag
            process = subprocess.Popen(
                [self.zen_path, "--headless", "--new-window", "about:blank"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait a few seconds for the profile to be created
            process.wait(timeout=5)
            
            # Kill the process
            process.kill()
            
            logger.info("Launched Zen Browser to create default profile")
        except Exception as e:
            logger.warning(f"Failed to launch Zen Browser: {str(e)}")
    
    def get_default_profile(self) -> Optional[ZenProfile]:
        """
        Get the default Zen Browser profile.
        
        Returns:
            Default ZenProfile object, or None if not found
        """
        profiles = self.detect_profiles()
        
        # First, look for the default profile based on the is_default flag
        for profile in profiles:
            if profile.is_default:
                return profile
        
        # If no default profile found, look for a profile matching the default name
        for profile in profiles:
            if profile.name == self.default_profile:
                return profile
        
        # If still no match, return the first profile
        if profiles:
            return profiles[0]
        
        return None
    
    def validate_profile(self, profile: ZenProfile) -> bool:
        """
        Validate a Zen Browser profile.
        
        Args:
            profile: ZenProfile object to validate
        
        Returns:
            True if the profile is valid, False otherwise
        """
        # Check if the profile path exists
        if not os.path.exists(profile.path):
            logger.warning(f"Profile path does not exist: {profile.path}")
            return False
        
        # Check if the profile contains necessary files
        required_files = ["prefs.js"]
        for file in required_files:
            file_path = os.path.join(profile.path, file)
            if not os.path.exists(file_path):
                logger.warning(f"Required profile file not found: {file_path}")
                return False
        
        return True
    
    def update_config_with_profile(self, profile: ZenProfile):
        """
        Update configuration with the selected profile.
        
        Args:
            profile: ZenProfile object to set as the current profile
        """
        self.config_manager.set('browsers', 'zen', {
            'path': self.zen_path,
            'user_data_dir': self.user_data_dir,
            'profile': profile.name
        })
        self.config_manager.save()
        logger.info(f"Updated configuration with profile: {profile.name}")
