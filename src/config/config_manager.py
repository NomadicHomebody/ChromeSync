"""
Configuration manager for ChromeSync.

This module provides the ConfigManager class which handles loading,
saving, validating, and accessing configuration settings.
"""

import os
import json
import shutil
import logging
import pathlib
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .config_defaults import DEFAULT_CONFIG
from .config_schema import validate_config, validate_path_exists

# Set up logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration settings for ChromeSync.
    
    Handles loading, saving, validating, and accessing configuration
    settings from a JSON file, with encryption for sensitive data.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                If not provided, uses the default location.
        """
        # Set default config path if not provided
        if config_path is None:
            app_data = os.environ.get('APPDATA', '')
            if not app_data:
                app_data = os.path.join(str(pathlib.Path.home()), 'AppData', 'Roaming')
            self.config_dir = os.path.join(app_data, 'ChromeSync')
            self.config_path = os.path.join(self.config_dir, 'config.json')
        else:
            self.config_path = config_path
            self.config_dir = os.path.dirname(config_path)
        
        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
        
        # Instance variables
        self.config = {}
        self._encryption_key = None
        
        # Load configuration
        self.load()
    
    def load(self):
        """
        Load configuration from file.
        
        If the configuration file doesn't exist or is invalid,
        loads the default configuration instead.
        
        Returns:
            bool: True if configuration was loaded successfully, False otherwise.
        """
        # If config file exists, load it
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Validate config
                is_valid, error = validate_config(loaded_config)
                if is_valid:
                    self.config = loaded_config
                    logger.info("Configuration loaded successfully.")
                    return True
                else:
                    logger.error(f"Invalid configuration: {error}")
                    self._backup_invalid_config()
                    self.config = DEFAULT_CONFIG.copy()
                    self.save()
                    logger.warning("Reset to default configuration.")
                    return False
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading configuration: {str(e)}")
                self._backup_invalid_config()
                self.config = DEFAULT_CONFIG.copy()
                self.save()
                logger.warning("Reset to default configuration.")
                return False
        else:
            # If config file doesn't exist, use defaults
            self.config = DEFAULT_CONFIG.copy()
            self.save()
            logger.info("Created default configuration.")
            return True
    
    def _backup_invalid_config(self):
        """Back up the invalid configuration file."""
        if os.path.exists(self.config_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_path}.{timestamp}.bak"
            try:
                shutil.copy2(self.config_path, backup_path)
                logger.info(f"Backed up invalid configuration to {backup_path}")
            except IOError as e:
                logger.error(f"Failed to back up invalid configuration: {str(e)}")
    
    def save(self):
        """
        Save configuration to file.
        
        Returns:
            bool: True if configuration was saved successfully, False otherwise.
        """
        # Validate configuration before saving
        is_valid, error = validate_config(self.config)
        if not is_valid:
            logger.error(f"Cannot save invalid configuration: {error}")
            return False
        
        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir, exist_ok=True)
            except OSError as e:
                logger.error(f"Failed to create configuration directory: {str(e)}")
                return False
        
        # Save configuration
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved successfully.")
            return True
        except IOError as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def reset(self):
        """
        Reset configuration to defaults.
        
        Returns:
            bool: True if configuration was reset successfully, False otherwise.
        """
        self.config = DEFAULT_CONFIG.copy()
        return self.save()
    
    def get(self, section, key=None, default=None):
        """
        Get a configuration value.
        
        Args:
            section (str): Configuration section.
            key (str, optional): Key within the section. If not provided,
                returns the entire section.
            default (any, optional): Default value to return if the key doesn't exist.
        
        Returns:
            any: Configuration value, or default if not found.
        """
        if section not in self.config:
            return default
        
        if key is None:
            return self.config[section]
        
        return self.config[section].get(key, default)
    
    def set(self, section, key, value):
        """
        Set a configuration value.
        
        Args:
            section (str): Configuration section.
            key (str): Key within the section.
            value (any): Value to set.
        
        Returns:
            bool: True if value was set successfully, False otherwise.
        """
        # Create section if it doesn't exist
        if section not in self.config:
            self.config[section] = {}
        
        # Set value
        self.config[section][key] = value
        
        # Validate configuration
        is_valid, error = validate_config(self.config)
        if not is_valid:
            logger.error(f"Invalid configuration after setting {section}.{key}: {error}")
            # Revert the change
            if section in DEFAULT_CONFIG and key in DEFAULT_CONFIG[section]:
                self.config[section][key] = DEFAULT_CONFIG[section][key]
            else:
                del self.config[section][key]
            return False
        
        return True
    
    def validate_browser_paths(self):
        """
        Validate browser paths in configuration.
        
        Returns:
            dict: Dictionary of validation results with path names as keys and
                (is_valid, error_message) tuples as values.
        """
        results = {}
        
        # Chrome paths
        chrome_path = self.get('browsers', 'chrome', {}).get('path', '')
        chrome_user_data = self.get('browsers', 'chrome', {}).get('user_data_dir', '')
        
        # Zen Browser paths
        zen_path = self.get('browsers', 'zen', {}).get('path', '')
        zen_user_data = self.get('browsers', 'zen', {}).get('user_data_dir', '')
        
        # Validate paths
        results['chrome_path'] = validate_path_exists(chrome_path, is_file=True)
        results['chrome_user_data'] = validate_path_exists(chrome_user_data, is_file=False)
        results['zen_path'] = validate_path_exists(zen_path, is_file=True)
        results['zen_user_data'] = validate_path_exists(zen_user_data, is_file=False)
        
        return results
    
    def _get_encryption_key(self, password=None):
        """
        Get or generate the encryption key for sensitive data.
        
        Args:
            password (str, optional): Password to derive the key from.
                If not provided, uses a machine-specific identifier.
        
        Returns:
            bytes: Encryption key.
        """
        if self._encryption_key is not None:
            return self._encryption_key
        
        # Use machine-specific information if no password provided
        if password is None:
            # Combine username, hostname, and machine UUID for a unique salt
            import socket
            import getpass
            import uuid
            
            username = getpass.getuser()
            hostname = socket.gethostname()
            machine_id = str(uuid.getnode())
            
            password = f"{username}@{hostname}#{machine_id}"
        
        # Derive key using PBKDF2
        salt = b'ChromeSync_Static_Salt_Value'  # In production, this should be stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        self._encryption_key = key
        return key
    
    def encrypt_sensitive_data(self, data, password=None):
        """
        Encrypt sensitive data.
        
        Args:
            data (str): Data to encrypt.
            password (str, optional): Password to derive the encryption key from.
        
        Returns:
            str: Encrypted data as a base64-encoded string.
        """
        key = self._get_encryption_key(password)
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data, password=None):
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data (str): Encrypted data as a base64-encoded string.
            password (str, optional): Password to derive the encryption key from.
        
        Returns:
            str: Decrypted data, or None if decryption failed.
        """
        try:
            key = self._get_encryption_key(password)
            f = Fernet(key)
            decrypted_data = f.decrypt(base64.urlsafe_b64decode(encrypted_data))
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {str(e)}")
            return None
    
    def export_config(self, export_path, include_sensitive=False):
        """
        Export configuration to a JSON file.
        
        Args:
            export_path (str): Path to export configuration to.
            include_sensitive (bool): Whether to include sensitive data.
        
        Returns:
            bool: True if configuration was exported successfully, False otherwise.
        """
        try:
            # Create a copy of the configuration
            export_config = self.config.copy()
            
            # Remove sensitive data if requested
            if not include_sensitive:
                if 'security' in export_config:
                    if 'passwords' in export_config.get('sync', {}).get('data_types', {}):
                        export_config['sync']['data_types']['passwords'] = False
            
            # Write configuration to file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, indent=4)
            
            logger.info(f"Configuration exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export configuration: {str(e)}")
            return False
    
    def import_config(self, import_path):
        """
        Import configuration from a JSON file.
        
        Args:
            import_path (str): Path to import configuration from.
        
        Returns:
            bool: True if configuration was imported successfully, False otherwise.
        """
        try:
            # Read configuration from file
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validate configuration
            is_valid, error = validate_config(imported_config)
            if not is_valid:
                logger.error(f"Invalid imported configuration: {error}")
                return False
            
            # Back up current configuration
            self._backup_invalid_config()
            
            # Update configuration
            self.config = imported_config
            
            # Save configuration
            success = self.save()
            if success:
                logger.info(f"Configuration imported from {import_path}")
            
            return success
        except Exception as e:
            logger.error(f"Failed to import configuration: {str(e)}")
            return False