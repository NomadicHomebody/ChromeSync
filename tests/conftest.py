"""
Configuration and fixtures for pytest.

This module provides fixtures and configuration for pytest,
allowing for easy setup and teardown of test environments.
"""

import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import ConfigManager
from src.core import (
    ServiceManager, 
    PasswordExtractor, BookmarkExtractor, HistoryExtractor,
    ProfileDetector, PasswordImporter, BookmarkImporter, HistoryImporter
)
from src.security import AuthenticationManager

# PyQt fixtures for GUI testing
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtTest import QTest
    from PyQt5.QtCore import Qt, QTimer, QEvent
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    shutil.rmtree(temp_dir)

@pytest.fixture
def config_path(temp_dir):
    """Create a temporary config path for testing."""
    return os.path.join(temp_dir, 'test_config.json')

@pytest.fixture
def config_manager(config_path):
    """Create a ConfigManager instance for testing."""
    return ConfigManager(config_path)

@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager for testing."""
    config_manager = MagicMock()
    
    # Set up default return values
    def get_side_effect(*args, **kwargs):
        if len(args) >= 2:
            if args[0] == 'browsers' and args[1] == 'chrome':
                return {
                    'path': 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                    'user_data_dir': '%LOCALAPPDATA%\\Google\\Chrome\\User Data',
                    'profile': 'Default',
                    'use_gui_automation': True
                }
            elif args[0] == 'browsers' and args[1] == 'zen':
                return {
                    'path': 'C:\\Program Files\\Zen Browser\\zen.exe',
                    'user_data_dir': '%APPDATA%\\zen',
                    'profile': 'default'
                }
            elif args[0] == 'storage' and args[1] == 'temp_dir':
                return tempfile.gettempdir()
            elif args[0] == 'security' and args[1] == 'require_auth_for_sensitive_ops':
                return True
            elif args[0] == 'sync' and args[1] == 'data_types':
                return {'passwords': True, 'bookmarks': True, 'history': True}
            elif args[0] == 'sync' and args[1] == 'auto_sync':
                return {'enabled': True, 'trigger_on_chrome_launch': True, 'delay_seconds': 5}
            elif args[0] == 'general' and args[1] == 'sync_on_startup':
                return False
            elif args[0] == 'ui' and args[1] == 'theme':
                return 'light'
            elif args[0] == 'ui' and args[1] == 'minimize_to_tray':
                return True
            elif args[0] == 'ui' and args[1] == 'show_notifications':
                return True
        
        # Default return an empty dict for section, None for key
        if len(args) == 1:
            return {}
        elif len(args) >= 2:
            return None
    
    config_manager.get.side_effect = get_side_effect
    config_manager.get_all.return_value = {
        'general': {
            'auto_start': True,
            'sync_on_startup': False,
            'start_minimized': False
        },
        'sync': {
            'data_types': {'passwords': True, 'bookmarks': True, 'history': True},
            'auto_sync': {'enabled': True, 'trigger_on_chrome_launch': True, 'delay_seconds': 5}
        },
        'ui': {
            'theme': 'light',
            'minimize_to_tray': True,
            'show_notifications': True
        }
    }
    return config_manager

@pytest.fixture
def service_manager(mock_config_manager):
    """Create a ServiceManager instance for testing."""
    with pytest.MonkeyPatch.context() as mp:
        # Patch dependencies
        mp.setattr('src.core.service_manager.ChromeProcessMonitor', MagicMock())
        mp.setattr('threading.Thread', MagicMock())
        
        service_manager = ServiceManager(mock_config_manager)
        yield service_manager

@pytest.fixture
def auth_manager(mock_config_manager):
    """Create an AuthenticationManager instance for testing."""
    with pytest.MonkeyPatch.context() as mp:
        # Patch dependencies
        mp.setattr('src.security.auth.verify_windows_user', MagicMock(return_value=True))
        mp.setattr('src.security.auth.encrypt_data', MagicMock(return_value='encrypted_data'))
        mp.setattr('src.security.auth.decrypt_data', MagicMock(return_value=b'decrypted_data'))
        
        auth_manager = AuthenticationManager(mock_config_manager)
        yield auth_manager

@pytest.fixture
def password_extractor(mock_config_manager):
    """Create a PasswordExtractor instance for testing."""
    with pytest.MonkeyPatch.context() as mp:
        # Patch dependencies
        mp.setattr('os.path.exists', MagicMock(return_value=True))
        mp.setattr('shutil.copy2', MagicMock())
        mp.setattr('src.utils.security.secure_delete_file', MagicMock())
        
        password_extractor = PasswordExtractor(mock_config_manager)
        yield password_extractor

@pytest.fixture
def bookmark_extractor(mock_config_manager):
    """Create a BookmarkExtractor instance for testing."""
    bookmark_extractor = BookmarkExtractor(mock_config_manager)
    return bookmark_extractor

@pytest.fixture
def history_extractor(mock_config_manager):
    """Create a HistoryExtractor instance for testing."""
    with pytest.MonkeyPatch.context() as mp:
        # Patch dependencies
        mp.setattr('os.path.exists', MagicMock(return_value=True))
        mp.setattr('shutil.copy2', MagicMock())
        mp.setattr('src.utils.security.secure_delete_file', MagicMock())
        mp.setattr('sqlite3.connect', MagicMock())
        
        history_extractor = HistoryExtractor(mock_config_manager)
        yield history_extractor

@pytest.fixture
def profile_detector(mock_config_manager):
    """Create a ProfileDetector instance for testing."""
    with pytest.MonkeyPatch.context() as mp:
        # Patch dependencies
        mp.setattr('os.path.exists', MagicMock(return_value=True))
        mp.setattr('os.listdir', MagicMock(return_value=['default']))
        
        profile_detector = ProfileDetector(mock_config_manager)
        yield profile_detector

@pytest.fixture
def password_importer(mock_config_manager):
    """Create a PasswordImporter instance for testing."""
    password_importer = PasswordImporter(mock_config_manager)
    return password_importer

@pytest.fixture
def bookmark_importer(mock_config_manager):
    """Create a BookmarkImporter instance for testing."""
    bookmark_importer = BookmarkImporter(mock_config_manager)
    return bookmark_importer

@pytest.fixture
def history_importer(mock_config_manager):
    """Create a HistoryImporter instance for testing."""
    history_importer = HistoryImporter(mock_config_manager)
    return history_importer

@pytest.fixture
def mock_chrome_password():
    """Create a mock ChromePassword instance for testing."""
    from src.core.extractors import ChromePassword
    return ChromePassword(
        origin_url='https://example.com',
        username='test_user',
        password='test_password',
        action_url='https://example.com/login',
        date_created=0,
        date_last_used=0
    )

@pytest.fixture
def mock_chrome_bookmark():
    """Create a mock ChromeBookmark instance for testing."""
    from src.core.extractors import ChromeBookmark
    bookmark = ChromeBookmark(
        title='Example Bookmark',
        url='https://example.com',
        date_added=13000000000000,  # Chrome timestamp
        date_modified=13000000000000,
        folder_path=['Bookmarks Bar']
    )
    return bookmark

@pytest.fixture
def mock_chrome_history_item():
    """Create a mock ChromeHistoryItem instance for testing."""
    from src.core.extractors import ChromeHistoryItem
    return ChromeHistoryItem(
        url='https://example.com',
        title='Example Page',
        visit_time=13000000000000,  # Chrome timestamp
        visit_count=1,
        last_visit_time=13000000000000,
        typed_count=0,
        hidden=False
    )

@pytest.fixture
def mock_zen_profile():
    """Create a mock ZenProfile instance for testing."""
    from src.core.importers import ZenProfile
    return ZenProfile(
        name='default',
        path='C:\\Users\\test\\AppData\\Roaming\\zen\\default',
        is_default=True,
        is_active=True
    )

# GUI testing fixtures
if HAS_PYQT:
    @pytest.fixture
    def qapp():
        """Create a QApplication instance for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        
        # Ensure app is cleaned up
        # This allows separate tests to create new QApplication instances
        # while respecting PyQt's requirement that QApplication be a singleton
        if QApplication.instance() is app:
            app.closeAllWindows()
        
    @pytest.fixture
    def chrome_sync_app(mock_config_manager):
        """Create a ChromeSyncApp instance for GUI testing."""
        from src.gui.main_window import ChromeSyncApp
        
        with patch('src.gui.main_window.ConfigManager', return_value=mock_config_manager):
            app = ChromeSyncApp()
            yield app
        
    @pytest.fixture
    def main_window(qapp, chrome_sync_app):
        """Create a MainWindow instance for testing."""
        from src.gui.main_window import MainWindow
        
        with patch('src.gui.main_window.get_icon', return_value=MagicMock()):
            window = MainWindow(chrome_sync_app)
            window.show()
            QApplication.processEvents()
            yield window
            window.close()
            QApplication.processEvents()
    
    @pytest.fixture
    def settings_dialog(qapp, mock_config_manager):
        """Create a SettingsDialog instance for testing."""
        from src.gui.settings_dialog import SettingsDialog
        
        with patch('src.gui.settings_dialog.get_icon', return_value=MagicMock()):
            dialog = SettingsDialog(mock_config_manager)
            yield dialog
            dialog.close()
            QApplication.processEvents()
    
    @pytest.fixture
    def sync_history_dialog(qapp, mock_config_manager):
        """Create a SyncHistoryDialog instance for testing."""
        from src.gui.sync_history_dialog import SyncHistoryDialog
        
        with patch('src.gui.sync_history_dialog.get_icon', return_value=MagicMock()), \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs'):
            dialog = SyncHistoryDialog(mock_config_manager)
            yield dialog
            dialog.close()
            QApplication.processEvents()
    
    @pytest.fixture
    def log_viewer_dialog(qapp, mock_config_manager):
        """Create a LogViewerDialog instance for testing."""
        from src.gui.log_viewer_dialog import LogViewerDialog
        
        with patch('src.gui.log_viewer_dialog.get_icon', return_value=MagicMock()), \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs'):
            dialog = LogViewerDialog(mock_config_manager)
            yield dialog
            dialog.close()
            QApplication.processEvents()
    
    @pytest.fixture
    def sync_worker(chrome_sync_app):
        """Create a SyncWorker instance for testing."""
        from src.gui.sync_worker import SyncWorker
        
        worker = SyncWorker(chrome_sync_app)
        yield worker
