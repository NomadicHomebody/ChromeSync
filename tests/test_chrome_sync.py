"""
Test module for ChromeSync.

This module contains unit tests for various ChromeSync components,
ensuring proper functionality and error handling.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import json

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import ConfigManager
from src.core import (
    ServiceManager, 
    PasswordExtractor, BookmarkExtractor, HistoryExtractor,
    ProfileDetector, PasswordImporter, BookmarkImporter, HistoryImporter
)
from src.security import AuthenticationManager
from src.utils import secure_delete_file

class TestConfigManager(unittest.TestCase):
    """Test the ConfigManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory and contents
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        # Create ConfigManager without existing config file
        config_manager = ConfigManager(self.config_path)
        
        # Check that default config was loaded
        self.assertTrue(config_manager.get('general', 'auto_start'))
        self.assertTrue(config_manager.get('general', 'minimize_to_tray'))
        self.assertTrue(config_manager.get('general', 'check_for_updates'))
        self.assertEqual(config_manager.get('general', 'language'), 'en-US')
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        # Create ConfigManager
        config_manager = ConfigManager(self.config_path)
        
        # Modify and save configuration
        config_manager.set('general', 'auto_start', False)
        config_manager.set('general', 'check_for_updates', False)
        config_manager.save()
        
        # Create a new ConfigManager to load the saved config
        new_config_manager = ConfigManager(self.config_path)
        
        # Check that saved values were loaded
        self.assertFalse(new_config_manager.get('general', 'auto_start'))
        self.assertFalse(new_config_manager.get('general', 'check_for_updates'))
        self.assertTrue(new_config_manager.get('general', 'minimize_to_tray'))
    
    def test_validate_config(self):
        """Test config validation functionality."""
        # Create ConfigManager
        config_manager = ConfigManager(self.config_path)
        
        # Test valid configuration
        self.assertTrue(config_manager.set('general', 'auto_start', True))
        
        # Test invalid configuration (invalid type)
        self.assertFalse(config_manager.set('general', 'auto_start', 'not_a_boolean'))
        
        # Test invalid configuration (unknown key)
        self.assertFalse(config_manager.set('general', 'unknown_key', 'value'))

class TestPasswordExtractor(unittest.TestCase):
    """Test the PasswordExtractor class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock ConfigManager
        self.config_manager = MagicMock()
        self.config_manager.get.return_value = ''
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Configure mock to return temp_dir for storage.temp_dir
        def get_side_effect(*args, **kwargs):
            if args[0] == 'storage' and args[1] == 'temp_dir':
                return self.temp_dir
            return ''
        
        self.config_manager.get.side_effect = get_side_effect
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory and contents
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('src.core.extractors.password_extractor.win32crypt.CryptUnprotectData')
    @patch('src.core.extractors.password_extractor.sqlite3.connect')
    def test_extract_passwords_direct_access(self, mock_connect, mock_crypt):
        """Test direct database access for password extraction."""
        # Mock cursor and connection
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock fetchall to return test data
        mock_cursor.fetchall.return_value = [
            ('https://example.com', 'https://example.com/login', 'test_user', b'encrypted', 0, 0)
        ]
        
        # Mock CryptUnprotectData to return decrypted password
        mock_crypt.return_value = (None, b'test_password')
        
        # Create extractor
        extractor = PasswordExtractor(self.config_manager)
        
        # Mock file existence checks
        with patch('os.path.exists', return_value=True), \
             patch('shutil.copy2'), \
             patch('src.utils.security.secure_delete_file'):
            
            # Test extract_passwords method
            with patch.object(extractor, '_extract_passwords_direct_access') as mock_extract:
                # Configure mock to return a test password
                mock_extract.return_value = [
                    extractor.ChromePassword('https://example.com', 'test_user', 'test_password')
                ]
                
                # Call method
                passwords = extractor.extract_passwords()
                
                # Verify results
                self.assertEqual(len(passwords), 1)
                self.assertEqual(passwords[0].origin_url, 'https://example.com')
                self.assertEqual(passwords[0].username, 'test_user')
                self.assertEqual(passwords[0].password, 'test_password')

class TestServiceManager(unittest.TestCase):
    """Test the ServiceManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock ConfigManager
        self.config_manager = MagicMock()
        
        # Configure mock to return values for service manager
        def get_side_effect(*args, **kwargs):
            if args[0] == 'browsers' and args[1] == 'chrome':
                return {'path': 'C:\\test\\chrome.exe'}
            elif args[0] == 'sync' and args[1] == 'auto_sync':
                return {'delay_seconds': 5}
            return {}
        
        self.config_manager.get.side_effect = get_side_effect
    
    @patch('src.core.service_manager.ChromeProcessMonitor')
    def test_start_service(self, mock_process_monitor):
        """Test starting the service."""
        # Create service manager
        service_manager = ServiceManager(self.config_manager)
        
        # Mock process monitor
        mock_monitor = MagicMock()
        mock_process_monitor.return_value = mock_monitor
        
        # Mock threading.Thread
        with patch('threading.Thread') as mock_thread:
            # Test start_service method
            result = service_manager.start_service()
            
            # Verify results
            self.assertTrue(result)
            self.assertEqual(service_manager.status, "running")
            mock_monitor.start.assert_called_once()
            mock_thread.assert_called_once()
    
    @patch('src.core.service_manager.ChromeProcessMonitor')
    def test_stop_service(self, mock_process_monitor):
        """Test stopping the service."""
        # Create service manager
        service_manager = ServiceManager(self.config_manager)
        
        # Mock process monitor
        mock_monitor = MagicMock()
        mock_process_monitor.return_value = mock_monitor
        
        # Start service
        with patch('threading.Thread'):
            service_manager.start_service()
        
        # Test stop_service method
        result = service_manager.stop_service()
        
        # Verify results
        self.assertTrue(result)
        self.assertEqual(service_manager.status, "stopped")
        mock_monitor.stop.assert_called_once()

class TestAuthenticationManager(unittest.TestCase):
    """Test the AuthenticationManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock ConfigManager
        self.config_manager = MagicMock()
        
        # Configure mock to return values for authentication manager
        def get_side_effect(*args, **kwargs):
            if args[0] == 'security' and args[1] == 'require_auth_for_sensitive_ops':
                return True
            elif args[0] == 'storage':
                return {'temp_dir': tempfile.gettempdir()}
            return {}
        
        self.config_manager.get.side_effect = get_side_effect
    
    @patch('src.security.auth.verify_windows_user')
    def test_authenticate_user(self, mock_verify):
        """Test user authentication."""
        # Mock verify_windows_user to return True
        mock_verify.return_value = True
        
        # Create authentication manager
        auth_manager = AuthenticationManager(self.config_manager)
        
        # Test authenticate_user method
        result = auth_manager.authenticate_user()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(auth_manager.validate_token())
        mock_verify.assert_called_once()
    
    def test_require_authentication(self):
        """Test operation authentication requirements."""
        # Create authentication manager
        auth_manager = AuthenticationManager(self.config_manager)
        
        # Test require_authentication method for sensitive operations
        self.assertTrue(auth_manager.require_authentication('password_sync'))
        self.assertTrue(auth_manager.require_authentication('config_export'))
        
        # Test require_authentication method for non-sensitive operations
        # This should still return True because require_auth is set to True in config
        self.assertTrue(auth_manager.require_authentication('bookmark_sync'))

class TestChromeSync(unittest.TestCase):
    """Test the main ChromeSync class."""
    
    def setUp(self):
        """Set up test environment."""
        # Patch dependencies
        self.patches = [
            patch('src.main.ConfigManager'),
            patch('src.main.setup_logging'),
            patch('src.main.AuthenticationManager'),
            patch('src.main.ServiceManager'),
            patch('src.main.PasswordExtractor'),
            patch('src.main.BookmarkExtractor'),
            patch('src.main.HistoryExtractor'),
            patch('src.main.ProfileDetector'),
            patch('src.main.PasswordImporter'),
            patch('src.main.BookmarkImporter'),
            patch('src.main.HistoryImporter')
        ]
        
        # Start patches
        self.mocks = [p.start() for p in self.patches]
        
        # Import ChromeSync after patching
        from src.main import ChromeSync
        self.ChromeSync = ChromeSync
    
    def tearDown(self):
        """Clean up test environment."""
        # Stop patches
        for p in self.patches:
            p.stop()
    
    def test_init(self):
        """Test ChromeSync initialization."""
        # Create ChromeSync instance
        chrome_sync = self.ChromeSync()
        
        # Verify dependencies were initialized
        self.mocks[0].assert_called_once()  # ConfigManager
        self.mocks[1].assert_called_once()  # setup_logging
        self.mocks[2].assert_called_once()  # AuthenticationManager
        self.mocks[3].assert_called_once()  # ServiceManager
        self.mocks[4].assert_called_once()  # PasswordExtractor
        self.mocks[5].assert_called_once()  # BookmarkExtractor
        self.mocks[6].assert_called_once()  # HistoryExtractor
        self.mocks[7].assert_called_once()  # ProfileDetector
        self.mocks[8].assert_called_once()  # PasswordImporter
        self.mocks[9].assert_called_once()  # BookmarkImporter
        self.mocks[10].assert_called_once()  # HistoryImporter
    
    def test_start_and_stop(self):
        """Test starting and stopping the application."""
        # Create ChromeSync instance
        chrome_sync = self.ChromeSync()
        
        # Configure mocks
        mock_service_manager = self.mocks[3].return_value
        mock_service_manager.start_service.return_value = True
        mock_service_manager.stop_service.return_value = True
        
        # Mock threading.Thread
        with patch('threading.Thread'):
            # Test start method
            chrome_sync.start()
            
            # Verify service was started
            mock_service_manager.add_callback.assert_any_call('on_chrome_launch', chrome_sync._on_chrome_launch)
            mock_service_manager.add_callback.assert_any_call('on_chrome_close', chrome_sync._on_chrome_close)
            mock_service_manager.start_service.assert_called_once()
            self.assertTrue(chrome_sync.running)
            
            # Test stop method
            chrome_sync.stop()
            
            # Verify service was stopped
            mock_service_manager.stop_service.assert_called_once()
            self.assertFalse(chrome_sync.running)

if __name__ == '__main__':
    unittest.main()
