"""
Test module for ChromeSync core components.

This module contains unit tests for core components like process monitoring,
service management, data extraction and importing.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock, call
import tempfile
import json
import sqlite3
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.process_monitor import ChromeProcessMonitor
from src.core.service_manager import ServiceManager
from src.core.extractors import (
    PasswordExtractor, BookmarkExtractor, HistoryExtractor,
    ChromePassword, ChromeBookmark, ChromeHistoryItem
)
from src.core.importers import (
    ProfileDetector, PasswordImporter, BookmarkImporter, HistoryImporter,
    ZenProfile
)


@pytest.mark.unit
class TestChromeProcessMonitor:
    """Test the ChromeProcessMonitor class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of ChromeProcessMonitor."""
        with patch('src.core.process_monitor.psutil') as mock_psutil:
            monitor = ChromeProcessMonitor(mock_config_manager)
            
            assert monitor.config_manager == mock_config_manager
            assert monitor.interval == 2
            assert monitor.chrome_path == 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
            assert monitor.on_chrome_launch_callbacks == []
            assert monitor.on_chrome_close_callbacks == []
            assert monitor.running == False
            assert monitor.chrome_running == False
    
    def test_is_chrome_running(self, mock_config_manager):
        """Test is_chrome_running method."""
        with patch('src.core.process_monitor.psutil') as mock_psutil:
            # Set up psutil mock to find Chrome
            mock_proc1 = MagicMock()
            mock_proc1.name.return_value = "chrome.exe"
            mock_proc1.exe.return_value = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            
            mock_proc2 = MagicMock()
            mock_proc2.name.return_value = "chrome.exe"
            mock_proc2.exe.return_value = "C:\\Users\\test\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
            
            mock_proc3 = MagicMock()
            mock_proc3.name.return_value = "firefox.exe"
            mock_proc3.exe.return_value = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
            
            mock_psutil.process_iter.return_value = [mock_proc1, mock_proc2, mock_proc3]
            
            # Create monitor
            monitor = ChromeProcessMonitor(mock_config_manager)
            
            # Test is_chrome_running
            result = monitor.is_chrome_running()
            
            # Verify Chrome was detected
            assert result == True
    
    def test_is_chrome_running_not_found(self, mock_config_manager):
        """Test is_chrome_running method when Chrome is not running."""
        with patch('src.core.process_monitor.psutil') as mock_psutil:
            # Set up psutil mock to not find Chrome
            mock_proc = MagicMock()
            mock_proc.name.return_value = "firefox.exe"
            mock_proc.exe.return_value = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
            
            mock_psutil.process_iter.return_value = [mock_proc]
            
            # Create monitor
            monitor = ChromeProcessMonitor(mock_config_manager)
            
            # Test is_chrome_running
            result = monitor.is_chrome_running()
            
            # Verify Chrome was not detected
            assert result == False
    
    def test_add_callback(self, mock_config_manager):
        """Test add_callback method."""
        with patch('src.core.process_monitor.psutil'):
            # Create monitor
            monitor = ChromeProcessMonitor(mock_config_manager)
            
            # Create test callbacks
            callback1 = MagicMock()
            callback2 = MagicMock()
            
            # Add callbacks
            monitor.add_callback('on_chrome_launch', callback1)
            monitor.add_callback('on_chrome_close', callback2)
            
            # Verify callbacks were added
            assert callback1 in monitor.on_chrome_launch_callbacks
            assert callback2 in monitor.on_chrome_close_callbacks
    
    def test_remove_callback(self, mock_config_manager):
        """Test remove_callback method."""
        with patch('src.core.process_monitor.psutil'):
            # Create monitor
            monitor = ChromeProcessMonitor(mock_config_manager)
            
            # Create test callbacks
            callback1 = MagicMock()
            callback2 = MagicMock()
            
            # Add callbacks
            monitor.add_callback('on_chrome_launch', callback1)
            monitor.add_callback('on_chrome_close', callback2)
            
            # Remove callbacks
            monitor.remove_callback('on_chrome_launch', callback1)
            monitor.remove_callback('on_chrome_close', callback2)
            
            # Verify callbacks were removed
            assert callback1 not in monitor.on_chrome_launch_callbacks
            assert callback2 not in monitor.on_chrome_close_callbacks
    
    def test_monitor_process_launch(self, mock_config_manager):
        """Test _monitor_process method for Chrome launch."""
        with patch('src.core.process_monitor.psutil'):
            # Create monitor with chrome_running=False
            monitor = ChromeProcessMonitor(mock_config_manager)
            monitor.chrome_running = False
            
            # Mock is_chrome_running to return True
            monitor.is_chrome_running = MagicMock(return_value=True)
            
            # Create test callback
            callback = MagicMock()
            monitor.on_chrome_launch_callbacks.append(callback)
            
            # Call _monitor_process
            monitor._monitor_process()
            
            # Verify callback was called
            callback.assert_called_once()
            assert monitor.chrome_running == True
    
    def test_monitor_process_close(self, mock_config_manager):
        """Test _monitor_process method for Chrome close."""
        with patch('src.core.process_monitor.psutil'):
            # Create monitor with chrome_running=True
            monitor = ChromeProcessMonitor(mock_config_manager)
            monitor.chrome_running = True
            
            # Mock is_chrome_running to return False
            monitor.is_chrome_running = MagicMock(return_value=False)
            
            # Create test callback
            callback = MagicMock()
            monitor.on_chrome_close_callbacks.append(callback)
            
            # Call _monitor_process
            monitor._monitor_process()
            
            # Verify callback was called
            callback.assert_called_once()
            assert monitor.chrome_running == False


@pytest.mark.unit
class TestServiceManager:
    """Test the ServiceManager class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of ServiceManager."""
        with patch('src.core.service_manager.ChromeProcessMonitor') as mock_monitor:
            # Create service manager
            service_manager = ServiceManager(mock_config_manager)
            
            # Verify properties
            assert service_manager.config_manager == mock_config_manager
            assert service_manager.status == "stopped"
            assert service_manager.error_message == ""
            assert service_manager.chrome_monitor is not None
            assert service_manager.callbacks == {
                'on_chrome_launch': [],
                'on_chrome_close': []
            }
    
    def test_start_service(self, service_manager):
        """Test start_service method."""
        # Verify service is initially stopped
        assert service_manager.status == "stopped"
        
        # Start service
        result = service_manager.start_service()
        
        # Verify service was started
        assert result == True
        assert service_manager.status == "running"
        assert service_manager.error_message == ""
    
    def test_stop_service(self, service_manager):
        """Test stop_service method."""
        # Start service first
        service_manager.start_service()
        
        # Verify service is running
        assert service_manager.status == "running"
        
        # Stop service
        result = service_manager.stop_service()
        
        # Verify service was stopped
        assert result == True
        assert service_manager.status == "stopped"
        assert service_manager.error_message == ""
    
    def test_is_chrome_running(self, service_manager):
        """Test is_chrome_running method."""
        # Mock chrome_monitor.is_chrome_running
        service_manager.chrome_monitor.is_chrome_running = MagicMock(return_value=True)
        
        # Call is_chrome_running
        result = service_manager.is_chrome_running()
        
        # Verify result
        assert result == True
        service_manager.chrome_monitor.is_chrome_running.assert_called_once()
    
    def test_add_callback(self, service_manager):
        """Test add_callback method."""
        # Create test callback
        callback = MagicMock()
        
        # Add callback
        service_manager.add_callback('on_chrome_launch', callback)
        
        # Verify callback was added
        assert callback in service_manager.callbacks['on_chrome_launch']
        
        # Verify callback was added to chrome_monitor
        service_manager.chrome_monitor.add_callback.assert_called_once_with('on_chrome_launch', callback)
    
    def test_remove_callback(self, service_manager):
        """Test remove_callback method."""
        # Create test callback
        callback = MagicMock()
        
        # Add callback
        service_manager.add_callback('on_chrome_launch', callback)
        
        # Remove callback
        service_manager.remove_callback('on_chrome_launch', callback)
        
        # Verify callback was removed
        assert callback not in service_manager.callbacks['on_chrome_launch']
        
        # Verify callback was removed from chrome_monitor
        service_manager.chrome_monitor.remove_callback.assert_called_once_with('on_chrome_launch', callback)


@pytest.mark.unit
class TestPasswordExtractor:
    """Test the PasswordExtractor class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of PasswordExtractor."""
        # Create password extractor
        extractor = PasswordExtractor(mock_config_manager)
        
        # Verify properties
        assert extractor.config_manager == mock_config_manager
    
    @patch('os.path.exists')
    @patch('shutil.copy2')
    @patch('src.utils.security.secure_delete_file')
    def test_extract_passwords_direct_access(self, mock_delete, mock_copy, mock_exists, 
                                            password_extractor, mock_config_manager):
        """Test extracting passwords using direct database access."""
        # Mock SQLite connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Set up mock cursor to return test password data
        mock_cursor.fetchall.return_value = [
            ('https://example.com', 'https://example.com/login', 'test_user', b'encrypted_password', 0, 0)
        ]
        
        # Mock sqlite3.connect to return mock connection
        with patch('sqlite3.connect', return_value=mock_conn):
            # Mock win32crypt.CryptUnprotectData to decrypt password
            with patch('win32crypt.CryptUnprotectData', return_value=(None, b'test_password')):
                # Mock path existence
                mock_exists.return_value = True
                
                # Call extract_passwords
                passwords = password_extractor.extract_passwords()
                
                # Verify passwords were extracted correctly
                assert len(passwords) == 1
                assert passwords[0].origin_url == 'https://example.com'
                assert passwords[0].username == 'test_user'
                assert passwords[0].password == 'test_password'
                assert passwords[0].action_url == 'https://example.com/login'
    
    def test_chrome_password_object(self):
        """Test ChromePassword data class."""
        # Create ChromePassword instance
        password = ChromePassword(
            origin_url='https://example.com',
            username='test_user',
            password='test_password',
            action_url='https://example.com/login',
            date_created=12345,
            date_last_used=67890
        )
        
        # Verify properties
        assert password.origin_url == 'https://example.com'
        assert password.username == 'test_user'
        assert password.password == 'test_password'
        assert password.action_url == 'https://example.com/login'
        assert password.date_created == 12345
        assert password.date_last_used == 67890
        
        # Verify string representation
        assert str(password) == "ChromePassword(origin_url='https://example.com', username='test_user')"
        
        # Verify dictionary conversion
        data_dict = password.to_dict()
        assert data_dict['origin_url'] == 'https://example.com'
        assert data_dict['username'] == 'test_user'
        assert data_dict['password'] == 'test_password'
        assert data_dict['action_url'] == 'https://example.com/login'
        assert data_dict['date_created'] == 12345
        assert data_dict['date_last_used'] == 67890


@pytest.mark.unit
class TestBookmarkExtractor:
    """Test the BookmarkExtractor class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of BookmarkExtractor."""
        # Create bookmark extractor
        extractor = BookmarkExtractor(mock_config_manager)
        
        # Verify properties
        assert extractor.config_manager == mock_config_manager
    
    @patch('os.path.exists')
    def test_extract_bookmarks(self, mock_exists, bookmark_extractor, mock_config_manager):
        """Test extracting bookmarks."""
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock reading bookmarks file
        test_bookmarks_data = {
            'roots': {
                'bookmark_bar': {
                    'children': [
                        {
                            'name': 'Example',
                            'type': 'url',
                            'url': 'https://example.com',
                            'date_added': '13000000000000',
                            'date_modified': '13000000000000'
                        },
                        {
                            'name': 'Folder',
                            'type': 'folder',
                            'children': [
                                {
                                    'name': 'Nested Example',
                                    'type': 'url',
                                    'url': 'https://nested.example.com',
                                    'date_added': '13100000000000',
                                    'date_modified': '13100000000000'
                                }
                            ],
                            'date_added': '13000000000000',
                            'date_modified': '13100000000000'
                        }
                    ]
                },
                'other': {
                    'children': [
                        {
                            'name': 'Other Example',
                            'type': 'url',
                            'url': 'https://other.example.com',
                            'date_added': '13200000000000',
                            'date_modified': '13200000000000'
                        }
                    ]
                }
            }
        }
        
        # Mock open to return bookmarks data
        mock_open = MagicMock()
        mock_open.__enter__.return_value.read.return_value = json.dumps(test_bookmarks_data)
        
        # Call extract_bookmarks with mock open
        with patch('builtins.open', return_value=mock_open):
            bookmarks = bookmark_extractor.extract_bookmarks()
            
            # Verify bookmarks were extracted correctly
            assert len(bookmarks) == 3
            
            # Verify top-level bookmark
            assert bookmarks[0].title == 'Example'
            assert bookmarks[0].url == 'https://example.com'
            assert bookmarks[0].folder_path == ['Bookmarks Bar']
            
            # Verify nested bookmark
            assert bookmarks[1].title == 'Nested Example'
            assert bookmarks[1].url == 'https://nested.example.com'
            assert bookmarks[1].folder_path == ['Bookmarks Bar', 'Folder']
            
            # Verify other bookmark
            assert bookmarks[2].title == 'Other Example'
            assert bookmarks[2].url == 'https://other.example.com'
            assert bookmarks[2].folder_path == ['Other']
    
    def test_chrome_bookmark_object(self):
        """Test ChromeBookmark data class."""
        # Create ChromeBookmark instance
        bookmark = ChromeBookmark(
            title='Example Bookmark',
            url='https://example.com',
            date_added=13000000000000,
            date_modified=13000000000000,
            folder_path=['Bookmarks Bar', 'Folder']
        )
        
        # Verify properties
        assert bookmark.title == 'Example Bookmark'
        assert bookmark.url == 'https://example.com'
        assert bookmark.date_added == 13000000000000
        assert bookmark.date_modified == 13000000000000
        assert bookmark.folder_path == ['Bookmarks Bar', 'Folder']
        
        # Verify string representation
        assert str(bookmark) == "ChromeBookmark(title='Example Bookmark', url='https://example.com', folder='Bookmarks Bar/Folder')"
        
        # Verify dictionary conversion
        data_dict = bookmark.to_dict()
        assert data_dict['title'] == 'Example Bookmark'
        assert data_dict['url'] == 'https://example.com'
        assert data_dict['date_added'] == 13000000000000
        assert data_dict['date_modified'] == 13000000000000
        assert data_dict['folder_path'] == ['Bookmarks Bar', 'Folder']


@pytest.mark.unit
class TestHistoryExtractor:
    """Test the HistoryExtractor class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of HistoryExtractor."""
        # Create history extractor
        extractor = HistoryExtractor(mock_config_manager)
        
        # Verify properties
        assert extractor.config_manager == mock_config_manager
    
    @patch('os.path.exists')
    @patch('shutil.copy2')
    @patch('src.utils.security.secure_delete_file')
    def test_extract_history(self, mock_delete, mock_copy, mock_exists, 
                           history_extractor, mock_config_manager):
        """Test extracting browsing history."""
        # Mock SQLite connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Set up mock cursor to return test history data
        mock_cursor.fetchall.return_value = [
            ('https://example.com', 'Example Page', 13000000000000, 1, 13000000000000, 0, 0),
            ('https://another.com', 'Another Page', 13100000000000, 2, 13100000000000, 1, 0)
        ]
        
        # Mock sqlite3.connect to return mock connection
        with patch('sqlite3.connect', return_value=mock_conn):
            # Mock path existence
            mock_exists.return_value = True
            
            # Call extract_history
            history_items = history_extractor.extract_history(days=30)
            
            # Verify history items were extracted correctly
            assert len(history_items) == 2
            
            # Verify first item
            assert history_items[0].url == 'https://example.com'
            assert history_items[0].title == 'Example Page'
            assert history_items[0].visit_time == 13000000000000
            assert history_items[0].visit_count == 1
            assert history_items[0].last_visit_time == 13000000000000
            assert history_items[0].typed_count == 0
            assert history_items[0].hidden == False
            
            # Verify second item
            assert history_items[1].url == 'https://another.com'
            assert history_items[1].title == 'Another Page'
            assert history_items[1].visit_time == 13100000000000
            assert history_items[1].visit_count == 2
            assert history_items[1].last_visit_time == 13100000000000
            assert history_items[1].typed_count == 1
            assert history_items[1].hidden == False
    
    def test_chrome_history_item_object(self):
        """Test ChromeHistoryItem data class."""
        # Create ChromeHistoryItem instance
        history_item = ChromeHistoryItem(
            url='https://example.com',
            title='Example Page',
            visit_time=13000000000000,
            visit_count=1,
            last_visit_time=13000000000000,
            typed_count=0,
            hidden=False
        )
        
        # Verify properties
        assert history_item.url == 'https://example.com'
        assert history_item.title == 'Example Page'
        assert history_item.visit_time == 13000000000000
        assert history_item.visit_count == 1
        assert history_item.last_visit_time == 13000000000000
        assert history_item.typed_count == 0
        assert history_item.hidden == False
        
        # Verify string representation
        assert str(history_item) == "ChromeHistoryItem(title='Example Page', url='https://example.com')"
        
        # Verify dictionary conversion
        data_dict = history_item.to_dict()
        assert data_dict['url'] == 'https://example.com'
        assert data_dict['title'] == 'Example Page'
        assert data_dict['visit_time'] == 13000000000000
        assert data_dict['visit_count'] == 1
        assert data_dict['last_visit_time'] == 13000000000000
        assert data_dict['typed_count'] == 0
        assert data_dict['hidden'] == False


@pytest.mark.unit
class TestProfileDetector:
    """Test the ProfileDetector class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of ProfileDetector."""
        # Create profile detector
        detector = ProfileDetector(mock_config_manager)
        
        # Verify properties
        assert detector.config_manager == mock_config_manager
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_get_profiles(self, mock_listdir, mock_exists, profile_detector):
        """Test getting browser profiles."""
        # Mock path existence
        mock_exists.return_value = True
        
        # Mock directory listing
        mock_listdir.return_value = ['default', 'profile1', 'profile2']
        
        # Mock isdir to identify directories
        with patch('os.path.isdir', return_value=True):
            # Call get_profiles
            profiles = profile_detector.get_profiles()
            
            # Verify profiles were detected correctly
            assert len(profiles) == 3
            
            # Verify default profile
            assert profiles[0].name == 'default'
            assert profiles[0].is_default == True
            
            # Verify other profiles
            assert profiles[1].name == 'profile1'
            assert profiles[1].is_default == False
            assert profiles[2].name == 'profile2'
            assert profiles[2].is_default == False
    
    @patch('os.path.exists')
    def test_get_default_profile(self, mock_exists, profile_detector):
        """Test getting default browser profile."""
        # Mock path existence
        mock_exists.return_value = True
        
        # Mock get_profiles to return test profiles
        test_profiles = [
            ZenProfile(name='default', path='C:\\test\\default', is_default=True, is_active=True),
            ZenProfile(name='profile1', path='C:\\test\\profile1', is_default=False, is_active=False)
        ]
        profile_detector.get_profiles = MagicMock(return_value=test_profiles)
        
        # Call get_default_profile
        default_profile = profile_detector.get_default_profile()
        
        # Verify default profile was returned
        assert default_profile == test_profiles[0]
    
    def test_zen_profile_object(self):
        """Test ZenProfile data class."""
        # Create ZenProfile instance
        profile = ZenProfile(
            name='default',
            path='C:\\test\\default',
            is_default=True,
            is_active=True
        )
        
        # Verify properties
        assert profile.name == 'default'
        assert profile.path == 'C:\\test\\default'
        assert profile.is_default == True
        assert profile.is_active == True
        
        # Verify string representation
        assert str(profile) == "ZenProfile(name='default', is_default=True)"


@pytest.mark.unit
class TestPasswordImporter:
    """Test the PasswordImporter class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of PasswordImporter."""
        # Create password importer
        importer = PasswordImporter(mock_config_manager)
        
        # Verify properties
        assert importer.config_manager == mock_config_manager
    
    @patch('selenium.webdriver.Chrome')
    def test_import_passwords(self, mock_chrome, password_importer, mock_chrome_password):
        """Test importing passwords."""
        # Mock selenium webdriver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Call import_passwords with test password
        with patch('time.sleep'):
            result = password_importer.import_passwords([mock_chrome_password])
            
            # Verify result
            assert result == True
            
            # Verify selenium interactions
            mock_driver.get.assert_called_once_with('https://example.com/login')
            mock_driver.find_element.assert_any_call('name', 'username')
            mock_driver.find_element.assert_any_call('name', 'password')


@pytest.mark.unit
class TestBookmarkImporter:
    """Test the BookmarkImporter class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of BookmarkImporter."""
        # Create bookmark importer
        importer = BookmarkImporter(mock_config_manager)
        
        # Verify properties
        assert importer.config_manager == mock_config_manager
    
    @patch('os.path.exists')
    def test_import_bookmarks(self, mock_exists, bookmark_importer, mock_chrome_bookmark):
        """Test importing bookmarks."""
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock json load to return existing bookmarks
        test_bookmarks_data = {
            'roots': {
                'bookmark_bar': {
                    'children': [],
                    'name': 'Bookmarks Bar'
                },
                'other': {
                    'children': [],
                    'name': 'Other'
                }
            }
        }
        
        # Mock open to return/write bookmarks data
        mock_read = MagicMock()
        mock_read.__enter__.return_value.read.return_value = json.dumps(test_bookmarks_data)
        
        mock_write = MagicMock()
        
        # Call import_bookmarks with mock file operations
        with patch('builtins.open', side_effect=[mock_read, mock_write]):
            result = bookmark_importer.import_bookmarks([mock_chrome_bookmark])
            
            # Verify result
            assert result == True
            
            # Verify bookmarks file was updated
            mock_write.__enter__.return_value.write.assert_called_once()
            write_data = json.loads(mock_write.__enter__.return_value.write.call_args[0][0])
            
            # Verify bookmark was added to bookmarks bar
            assert len(write_data['roots']['bookmark_bar']['children']) == 1
            assert write_data['roots']['bookmark_bar']['children'][0]['name'] == 'Example Bookmark'
            assert write_data['roots']['bookmark_bar']['children'][0]['url'] == 'https://example.com'


@pytest.mark.unit
class TestHistoryImporter:
    """Test the HistoryImporter class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of HistoryImporter."""
        # Create history importer
        importer = HistoryImporter(mock_config_manager)
        
        # Verify properties
        assert importer.config_manager == mock_config_manager
    
    @patch('os.path.exists')
    @patch('sqlite3.connect')
    def test_import_history(self, mock_connect, mock_exists, history_importer, mock_chrome_history_item):
        """Test importing browsing history."""
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock SQLite connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Call import_history
        result = history_importer.import_history([mock_chrome_history_item])
        
        # Verify result
        assert result == True
        
        # Verify database interactions
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
