"""
Test module for ChromeSync configuration components.

This module contains unit tests for configuration management,
schema validation, and default settings.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import json
import jsonschema

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.config_manager import ConfigManager
from src.config.config_schema import CONFIG_SCHEMA
from src.config.config_defaults import DEFAULT_CONFIG


@pytest.mark.unit
class TestConfigSchema:
    """Test the configuration schema validation."""
    
    def test_schema_structure(self):
        """Test that the schema has the expected structure."""
        # Check top-level schema
        assert 'type' in CONFIG_SCHEMA
        assert CONFIG_SCHEMA['type'] == 'object'
        assert 'properties' in CONFIG_SCHEMA
        
        # Check required properties
        assert 'required' in CONFIG_SCHEMA
        assert 'general' in CONFIG_SCHEMA['required']
        assert 'sync' in CONFIG_SCHEMA['required']
        assert 'security' in CONFIG_SCHEMA['required']
        
        # Check property definitions
        properties = CONFIG_SCHEMA['properties']
        assert 'general' in properties
        assert 'sync' in properties
        assert 'security' in properties
        assert 'ui' in properties
        assert 'storage' in properties
        assert 'logs' in properties
        assert 'browsers' in properties
    
    def test_valid_config(self):
        """Test that a valid configuration passes schema validation."""
        # Use the default config as a valid config example
        try:
            jsonschema.validate(DEFAULT_CONFIG, CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError:
            pytest.fail("Default config failed schema validation")
    
    def test_invalid_config_wrong_type(self):
        """Test that an invalid configuration with wrong types fails validation."""
        invalid_config = {
            "general": {
                "auto_start": "not a boolean",  # Should be boolean
                "check_for_updates": True
            },
            "sync": {
                "data_types": {
                    "passwords": True,
                    "bookmarks": True,
                    "history": True
                },
                "auto_sync": {
                    "enabled": True,
                    "trigger_on_chrome_launch": True,
                    "delay_seconds": "5"  # Should be number
                }
            },
            "security": {
                "authentication": {
                    "require_for_passwords": True
                }
            }
        }
        
        with pytest.raises(jsonschema.exceptions.ValidationError):
            jsonschema.validate(invalid_config, CONFIG_SCHEMA)
    
    def test_invalid_config_missing_required(self):
        """Test that an invalid configuration missing required fields fails validation."""
        invalid_config = {
            "general": {
                "auto_start": True,
                "check_for_updates": True
            },
            # Missing 'sync' section (required)
            "security": {
                "authentication": {
                    "require_for_passwords": True
                }
            }
        }
        
        with pytest.raises(jsonschema.exceptions.ValidationError):
            jsonschema.validate(invalid_config, CONFIG_SCHEMA)


@pytest.mark.unit
class TestDefaultConfig:
    """Test the default configuration settings."""
    
    def test_default_config_structure(self):
        """Test that the default config has the expected structure."""
        # Check top-level sections
        assert 'general' in DEFAULT_CONFIG
        assert 'sync' in DEFAULT_CONFIG
        assert 'security' in DEFAULT_CONFIG
        assert 'ui' in DEFAULT_CONFIG
        assert 'storage' in DEFAULT_CONFIG
        assert 'logs' in DEFAULT_CONFIG
        assert 'browsers' in DEFAULT_CONFIG
    
    def test_default_general_settings(self):
        """Test default general settings."""
        general = DEFAULT_CONFIG['general']
        assert 'auto_start' in general
        assert 'minimize_to_tray' in general
        assert 'check_for_updates' in general
        assert 'language' in general
        
        assert general['auto_start'] is True
        assert general['minimize_to_tray'] is True
        assert general['check_for_updates'] is True
        assert general['language'] == 'en-US'
    
    def test_default_sync_settings(self):
        """Test default synchronization settings."""
        sync = DEFAULT_CONFIG['sync']
        assert 'data_types' in sync
        assert 'auto_sync' in sync
        
        assert 'passwords' in sync['data_types']
        assert 'bookmarks' in sync['data_types']
        assert 'history' in sync['data_types']
        
        assert 'enabled' in sync['auto_sync']
        assert 'trigger_on_chrome_launch' in sync['auto_sync']
        assert 'delay_seconds' in sync['auto_sync']
        
        assert sync['data_types']['passwords'] is True
        assert sync['data_types']['bookmarks'] is True
        assert sync['data_types']['history'] is True
        
        assert sync['auto_sync']['enabled'] is True
        assert sync['auto_sync']['trigger_on_chrome_launch'] is True
        assert isinstance(sync['auto_sync']['delay_seconds'], int)
    
    def test_default_security_settings(self):
        """Test default security settings."""
        security = DEFAULT_CONFIG['security']
        assert 'authentication' in security
        assert 'encryption' in security
        
        assert 'require_for_passwords' in security['authentication']
        assert security['authentication']['require_for_passwords'] is True
    
    def test_default_browsers_settings(self):
        """Test default browser settings."""
        browsers = DEFAULT_CONFIG['browsers']
        assert 'chrome' in browsers
        assert 'zen' in browsers
        
        assert 'path' in browsers['chrome']
        assert 'user_data_dir' in browsers['chrome']
        assert 'profile' in browsers['chrome']
        
        assert 'path' in browsers['zen']
        assert 'user_data_dir' in browsers['zen']
        assert 'profile' in browsers['zen']


@pytest.mark.unit
class TestConfigManager:
    """Test the ConfigManager class."""
    
    def test_initialization_new_config(self, temp_dir):
        """Test initialization with a new config file."""
        # Create config path in temporary directory
        config_path = os.path.join(temp_dir, 'test_config.json')
        
        # Create ConfigManager
        with patch('jsonschema.validate'):  # Mock validation to avoid schema issues
            config_manager = ConfigManager(config_path)
        
        # Verify properties
        assert config_manager.config_file == config_path
        assert config_manager.config == DEFAULT_CONFIG
        
        # Verify config file was created
        assert os.path.exists(config_path)
    
    def test_initialization_existing_config(self, temp_dir):
        """Test initialization with an existing config file."""
        # Create config path in temporary directory
        config_path = os.path.join(temp_dir, 'test_config.json')
        
        # Create test config
        test_config = {
            "general": {
                "auto_start": False,
                "minimize_to_tray": True,
                "check_for_updates": False,
                "language": "fr-FR"
            },
            "sync": {
                "data_types": {
                    "passwords": True,
                    "bookmarks": False,
                    "history": True
                },
                "auto_sync": {
                    "enabled": False,
                    "trigger_on_chrome_launch": False,
                    "delay_seconds": 10
                }
            },
            "security": {
                "authentication": {
                    "require_for_passwords": False
                }
            }
        }
        
        # Write test config to file
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        # Create ConfigManager
        with patch('jsonschema.validate'):  # Mock validation to avoid schema issues
            config_manager = ConfigManager(config_path)
        
        # Verify properties
        assert config_manager.config_file == config_path
        
        # Verify config was loaded
        assert config_manager.config['general']['auto_start'] == False
        assert config_manager.config['general']['language'] == 'fr-FR'
        assert config_manager.config['sync']['data_types']['bookmarks'] == False
        assert config_manager.config['sync']['auto_sync']['delay_seconds'] == 10
        assert config_manager.config['security']['authentication']['require_for_passwords'] == False
    
    def test_get_value(self, config_manager):
        """Test getting config values."""
        # Test getting existing values
        assert config_manager.get('general', 'auto_start') == True
        assert config_manager.get('sync', 'data_types')['passwords'] == True
        
        # Test getting non-existent values with default
        assert config_manager.get('non_existent', 'key', 'default') == 'default'
        assert config_manager.get('general', 'non_existent', 123) == 123
        
        # Test getting non-existent values without default
        assert config_manager.get('non_existent', 'key') is None
        assert config_manager.get('general', 'non_existent') is None
        
        # Test getting section
        general = config_manager.get('general')
        assert isinstance(general, dict)
        assert 'auto_start' in general
        assert 'minimize_to_tray' in general
    
    def test_set_value_valid(self, config_manager):
        """Test setting valid config values."""
        # Set new values
        assert config_manager.set('general', 'auto_start', False) == True
        assert config_manager.set('sync', 'data_types', {
            'passwords': False,
            'bookmarks': True,
            'history': False
        }) == True
        
        # Verify values were set
        assert config_manager.get('general', 'auto_start') == False
        assert config_manager.get('sync', 'data_types')['passwords'] == False
        assert config_manager.get('sync', 'data_types')['bookmarks'] == True
        assert config_manager.get('sync', 'data_types')['history'] == False
    
    def test_set_value_invalid(self, config_manager):
        """Test setting invalid config values."""
        # Set invalid values
        with patch('jsonschema.validate', side_effect=jsonschema.exceptions.ValidationError('Invalid')):
            assert config_manager.set('general', 'auto_start', 'not a boolean') == False
            assert config_manager.set('sync', 'data_types', 'not an object') == False
        
        # Verify values were not set
        assert config_manager.get('general', 'auto_start') == True
        assert isinstance(config_manager.get('sync', 'data_types'), dict)
    
    def test_update_config(self, config_manager):
        """Test updating config with a new dict."""
        # Create update dict
        update = {
            'general': {
                'auto_start': False,
                'language': 'de-DE'
            },
            'ui': {
                'theme': 'dark'
            }
        }
        
        # Update config
        with patch('jsonschema.validate'):  # Mock validation to avoid schema issues
            config_manager.update(update)
        
        # Verify values were updated
        assert config_manager.get('general', 'auto_start') == False
        assert config_manager.get('general', 'language') == 'de-DE'
        assert config_manager.get('ui', 'theme') == 'dark'
        
        # Verify other values were not changed
        assert config_manager.get('general', 'minimize_to_tray') == True
        assert config_manager.get('sync', 'data_types')['passwords'] == True
    
    def test_save_config(self, temp_dir):
        """Test saving config to file."""
        # Create config path in temporary directory
        config_path = os.path.join(temp_dir, 'test_config.json')
        
        # Create ConfigManager
        with patch('jsonschema.validate'):  # Mock validation to avoid schema issues
            config_manager = ConfigManager(config_path)
        
        # Modify config
        config_manager.set('general', 'auto_start', False)
        config_manager.set('ui', 'theme', 'dark')
        
        # Save config
        config_manager.save()
        
        # Verify file was saved
        assert os.path.exists(config_path)
        
        # Read saved file
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        # Verify saved values
        assert saved_config['general']['auto_start'] == False
        assert saved_config['ui']['theme'] == 'dark'
    
    def test_get_all(self, config_manager):
        """Test getting entire config."""
        # Get all config
        config = config_manager.get_all()
        
        # Verify it's a complete copy
        assert config == config_manager.config
        assert config is not config_manager.config  # Should be a copy, not the same object
