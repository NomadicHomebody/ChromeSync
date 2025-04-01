"""
Test module for ChromeSync GUI components.

This module contains unit tests for GUI components, ensuring proper
functionality and error handling.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import tempfile
import json

# Skip tests if PyQt5 is not available
pytest.importorskip("PyQt5.QtWidgets")

from PyQt5.QtCore import Qt, QEvent, QSize
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.QtTest import QTest

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.gui.main_window import MainWindow, ChromeSyncApp
from src.gui.settings_dialog import SettingsDialog
from src.gui.sync_history_dialog import SyncHistoryDialog
from src.gui.log_viewer_dialog import LogViewerDialog
from src.gui.sync_worker import SyncWorker, SyncThread
from src.gui.utils import get_icon, get_style_sheet, show_message


@pytest.mark.gui
class TestMainWindow:
    """Test the MainWindow class."""

    def test_initialization(self, main_window, chrome_sync_app):
        """Test initialization of MainWindow."""
        # Verify window properties
        assert main_window.windowTitle() == "ChromeSync"
        assert main_window.app == chrome_sync_app
        
        # Verify UI components were created
        assert main_window.central_widget is not None
        assert main_window.status_bar is not None
        assert main_window.toolbar is not None
        assert main_window.tray_icon is not None
        
        # Verify status components
        assert main_window.chrome_status_label is not None
        assert main_window.zen_status_label is not None
        assert main_window.service_status_label is not None
        assert main_window.last_sync_label is not None
        
        # Verify sync components
        assert main_window.sync_button is not None
        assert main_window.cancel_button is not None
        assert main_window.progress_bar is not None
        
        # Verify sync options
        assert main_window.passwords_checkbox is not None
        assert main_window.bookmarks_checkbox is not None
        assert main_window.history_checkbox is not None
        assert main_window.auto_sync_checkbox is not None
        
        # Verify service was not started automatically
        chrome_sync_app.service_manager.start_service.assert_not_called()

    def test_sync_button_click(self, main_window, chrome_sync_app, monkeypatch):
        """Test sync button click."""
        # Mock the sync worker
        mock_worker = MagicMock()
        monkeypatch.setattr(main_window, 'sync_worker', mock_worker)
        mock_worker.is_running.return_value = False
        
        # Click the sync button
        QTest.mouseClick(main_window.sync_button, Qt.LeftButton)
        
        # Verify sync worker was started
        mock_worker.start.assert_called_once()
        
        # Verify UI state changes
        assert main_window.sync_button.isEnabled() == False
        assert main_window.cancel_button.isEnabled() == True
    
    def test_sync_button_click_with_no_data_types(self, main_window, chrome_sync_app, monkeypatch):
        """Test sync button click with no data types selected."""
        # Mock the sync worker
        mock_worker = MagicMock()
        monkeypatch.setattr(main_window, 'sync_worker', mock_worker)
        mock_worker.is_running.return_value = False
        
        # Uncheck all data types
        main_window.passwords_checkbox.setChecked(False)
        main_window.bookmarks_checkbox.setChecked(False)
        main_window.history_checkbox.setChecked(False)
        
        # Mock show_message to avoid message box
        monkeypatch.setattr('src.gui.main_window.show_message', MagicMock())
        
        # Click the sync button
        QTest.mouseClick(main_window.sync_button, Qt.LeftButton)
        
        # Verify sync worker was not started
        mock_worker.start.assert_not_called()
        
        # Verify UI state didn't change
        assert main_window.sync_button.isEnabled() == True
        assert main_window.cancel_button.isEnabled() == False
    
    def test_cancel_button_click(self, main_window, chrome_sync_app, monkeypatch):
        """Test cancel button click."""
        # Mock the sync worker
        mock_worker = MagicMock()
        monkeypatch.setattr(main_window, 'sync_worker', mock_worker)
        mock_worker.is_running.return_value = True
        
        # Enable cancel button
        main_window.cancel_button.setEnabled(True)
        
        # Mock QMessageBox.question to return QMessageBox.Yes
        monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.question', 
                         MagicMock(return_value=QMessageBox.Yes))
        
        # Click the cancel button
        QTest.mouseClick(main_window.cancel_button, Qt.LeftButton)
        
        # Verify sync worker was cancelled
        mock_worker.cancel.assert_called_once()
    
    def test_auto_sync_checkbox(self, main_window):
        """Test auto sync checkbox functionality."""
        # Test checking the box
        main_window.auto_sync_checkbox.setChecked(True)
        assert main_window.on_launch_checkbox.isEnabled() == True
        assert main_window.on_close_checkbox.isEnabled() == True
        
        # Test unchecking the box
        main_window.auto_sync_checkbox.setChecked(False)
        assert main_window.on_launch_checkbox.isEnabled() == False
        assert main_window.on_close_checkbox.isEnabled() == False
    
    def test_on_sync_completed_success(self, main_window, monkeypatch):
        """Test sync completion handler with success."""
        # Mock tray icon showMessage to avoid notifications
        monkeypatch.setattr(main_window.tray_icon, 'showMessage', MagicMock())
        
        # Call on_sync_completed with success=True
        main_window.on_sync_completed(True)
        
        # Verify UI state
        assert main_window.sync_button.isEnabled() == True
        assert main_window.cancel_button.isEnabled() == False
        assert "successfully" in main_window.sync_status_label.text()
        
        # Verify notification was shown
        main_window.tray_icon.showMessage.assert_called_once()
    
    def test_on_sync_completed_failure(self, main_window, monkeypatch):
        """Test sync completion handler with failure."""
        # Mock tray icon showMessage to avoid notifications
        monkeypatch.setattr(main_window.tray_icon, 'showMessage', MagicMock())
        
        # Call on_sync_completed with success=False
        main_window.on_sync_completed(False)
        
        # Verify UI state
        assert main_window.sync_button.isEnabled() == True
        assert main_window.cancel_button.isEnabled() == False
        assert "failed" in main_window.sync_status_label.text()
        
        # Verify notification was shown
        main_window.tray_icon.showMessage.assert_called_once()
    
    def test_update_sync_progress(self, main_window, monkeypatch):
        """Test progress update handler."""
        # Mock QApplication.processEvents to avoid UI updates
        monkeypatch.setattr('PyQt5.QtWidgets.QApplication.processEvents', MagicMock())
        
        # Call update_sync_progress
        main_window.update_sync_progress(50, 100, "Testing progress")
        
        # Verify UI updates
        assert main_window.progress_bar.value() == 50
        assert main_window.progress_bar.maximum() == 100
        assert main_window.sync_status_label.text() == "Testing progress"
        assert main_window.status_label.text() == "Testing progress"
        assert "Testing progress" in main_window.tray_icon.toolTip()
    
    def test_tray_icon_activation(self, main_window, monkeypatch):
        """Test tray icon activation."""
        # Mock isVisible to return True
        monkeypatch.setattr(main_window, 'isVisible', MagicMock(return_value=True))
        monkeypatch.setattr(main_window, 'hide', MagicMock())
        
        # Call on_tray_activated with DoubleClick
        main_window.on_tray_activated(QSystemTrayIcon.DoubleClick)
        
        # Verify window was hidden
        main_window.hide.assert_called_once()
        
        # Now test for when window is not visible
        main_window.hide.reset_mock()
        monkeypatch.setattr(main_window, 'isVisible', MagicMock(return_value=False))
        monkeypatch.setattr(main_window, 'show', MagicMock())
        
        # Call on_tray_activated again
        main_window.on_tray_activated(QSystemTrayIcon.DoubleClick)
        
        # Verify window was shown
        main_window.show.assert_called_once()


@pytest.mark.gui
class TestSettingsDialog:
    """Test the SettingsDialog class."""

    def test_initialization(self, settings_dialog, mock_config_manager):
        """Test initialization of SettingsDialog."""
        # Verify window properties
        assert settings_dialog.windowTitle() == "Settings"
        assert settings_dialog.config_manager == mock_config_manager
        
        # Verify tab widget
        assert settings_dialog.tab_widget is not None
        assert settings_dialog.tab_widget.count() == 5  # General, Sync, Security, UI, Advanced
        
        # Verify original config was stored
        assert settings_dialog.original_config is not None
    
    def test_load_settings(self, settings_dialog, mock_config_manager):
        """Test loading settings from config."""
        # Set up expected values
        mock_config_manager.get_all.return_value = {
            'general': {
                'auto_start': True,
                'sync_on_startup': True,
                'start_minimized': True
            },
            'logs': {
                'level': 'DEBUG',
                'dir': 'C:\\test\\logs',
                'max_size_mb': 20
            },
            'sync': {
                'data_types': {'passwords': False, 'bookmarks': True, 'history': False},
                'auto_sync': {'enabled': False, 'trigger_on_chrome_launch': False, 'trigger_on_chrome_close': True},
                'history_days': 60
            },
            'security': {
                'authentication': {'require_for_passwords': False, 'require_for_ui': True},
                'encryption': {'algorithm': 'ChaCha20'},
                'credentials': {'use_credential_manager': False}
            },
            'ui': {
                'theme': 'dark',
                'minimize_to_tray': False,
                'show_notifications': False
            },
            'advanced': {
                'browsers': {'chrome_path': 'C:\\test\\chrome.exe', 'zen_path': 'C:\\test\\zen.exe'},
                'storage': {'data_dir': 'C:\\test\\data'},
                'performance': {'thread_count': 8}
            }
        }
        
        # Call load_settings
        settings_dialog.load_settings()
        
        # Verify settings were loaded
        assert settings_dialog.auto_start_checkbox.isChecked() == True
        assert settings_dialog.sync_on_startup_checkbox.isChecked() == True
        assert settings_dialog.start_minimized_checkbox.isChecked() == True
        
        assert settings_dialog.log_level_combo.currentText() == "DEBUG"
        assert settings_dialog.log_dir_edit.text() == "C:\\test\\logs"
        assert settings_dialog.log_max_size_spinbox.value() == 20
        
        assert settings_dialog.passwords_checkbox.isChecked() == False
        assert settings_dialog.bookmarks_checkbox.isChecked() == True
        assert settings_dialog.history_checkbox.isChecked() == False
        
        assert settings_dialog.auto_sync_checkbox.isChecked() == False
        assert settings_dialog.on_launch_checkbox.isChecked() == False
        assert settings_dialog.on_close_checkbox.isChecked() == True
        assert settings_dialog.history_days_spinbox.value() == 60
        
        assert settings_dialog.auth_for_passwords_checkbox.isChecked() == False
        assert settings_dialog.auth_for_ui_checkbox.isChecked() == True
        assert settings_dialog.encryption_algo_combo.currentText() == "ChaCha20"
        assert settings_dialog.use_credential_manager_checkbox.isChecked() == False
        
        assert settings_dialog.theme_combo.currentText() == "Dark"
        assert settings_dialog.minimize_to_tray_checkbox.isChecked() == False
        assert settings_dialog.show_notifications_checkbox.isChecked() == False
        
        assert settings_dialog.chrome_path_edit.text() == "C:\\test\\chrome.exe"
        assert settings_dialog.zen_path_edit.text() == "C:\\test\\zen.exe"
        assert settings_dialog.data_dir_edit.text() == "C:\\test\\data"
        assert settings_dialog.thread_count_spinbox.value() == 8
    
    def test_gather_settings(self, settings_dialog):
        """Test gathering settings from UI."""
        # Set UI values
        settings_dialog.auto_start_checkbox.setChecked(False)
        settings_dialog.sync_on_startup_checkbox.setChecked(True)
        settings_dialog.start_minimized_checkbox.setChecked(True)
        
        settings_dialog.log_level_combo.setCurrentText("ERROR")
        settings_dialog.log_dir_edit.setText("C:\\custom\\logs")
        settings_dialog.log_max_size_spinbox.setValue(15)
        
        settings_dialog.passwords_checkbox.setChecked(True)
        settings_dialog.bookmarks_checkbox.setChecked(False)
        settings_dialog.history_checkbox.setChecked(True)
        
        settings_dialog.auto_sync_checkbox.setChecked(True)
        settings_dialog.on_launch_checkbox.setChecked(False)
        settings_dialog.on_close_checkbox.setChecked(True)
        settings_dialog.delay_spinbox.setValue(10)
        settings_dialog.history_days_spinbox.setValue(45)
        
        settings_dialog.auth_for_passwords_checkbox.setChecked(True)
        settings_dialog.auth_for_ui_checkbox.setChecked(False)
        settings_dialog.encryption_algo_combo.setCurrentText("Blowfish")
        settings_dialog.use_credential_manager_checkbox.setChecked(True)
        
        settings_dialog.theme_combo.setCurrentText("Dark")
        settings_dialog.minimize_to_tray_checkbox.setChecked(True)
        settings_dialog.show_notifications_checkbox.setChecked(False)
        
        settings_dialog.chrome_path_edit.setText("C:\\custom\\chrome.exe")
        settings_dialog.zen_path_edit.setText("C:\\custom\\zen.exe")
        settings_dialog.data_dir_edit.setText("C:\\custom\\data")
        settings_dialog.thread_count_spinbox.setValue(6)
        
        # Call gather_settings
        config = settings_dialog.gather_settings()
        
        # Verify settings were gathered correctly
        assert config['general']['auto_start'] == False
        assert config['general']['sync_on_startup'] == True
        assert config['general']['start_minimized'] == True
        
        assert config['logs']['level'] == "ERROR"
        assert config['logs']['dir'] == "C:\\custom\\logs"
        assert config['logs']['max_size_mb'] == 15
        
        assert config['sync']['data_types']['passwords'] == True
        assert config['sync']['data_types']['bookmarks'] == False
        assert config['sync']['data_types']['history'] == True
        
        assert config['sync']['auto_sync']['enabled'] == True
        assert config['sync']['auto_sync']['trigger_on_chrome_launch'] == False
        assert config['sync']['auto_sync']['trigger_on_chrome_close'] == True
        assert config['sync']['auto_sync']['delay_seconds'] == 10
        assert config['sync']['history_days'] == 45
        
        assert config['security']['authentication']['require_for_passwords'] == True
        assert config['security']['authentication']['require_for_ui'] == False
        assert config['security']['encryption']['algorithm'] == "Blowfish"
        assert config['security']['credentials']['use_credential_manager'] == True
        
        assert config['ui']['theme'] == "dark"
        assert config['ui']['minimize_to_tray'] == True
        assert config['ui']['show_notifications'] == False
        
        assert config['advanced']['browsers']['chrome_path'] == "C:\\custom\\chrome.exe"
        assert config['advanced']['browsers']['zen_path'] == "C:\\custom\\zen.exe"
        assert config['advanced']['storage']['data_dir'] == "C:\\custom\\data"
        assert config['advanced']['performance']['thread_count'] == 6
    
    def test_apply_settings(self, settings_dialog, mock_config_manager, monkeypatch):
        """Test applying settings."""
        # Mock dependencies
        monkeypatch.setattr(settings_dialog, 'gather_settings', MagicMock(return_value={'test': 'settings'}))
        monkeypatch.setattr('src.gui.settings_dialog.show_message', MagicMock())
        
        # Call apply_settings
        settings_dialog.apply_settings()
        
        # Verify config was updated and saved
        mock_config_manager.update.assert_called_once_with({'test': 'settings'})
        mock_config_manager.save.assert_called_once()
    
    def test_reset_settings(self, settings_dialog, mock_config_manager, monkeypatch):
        """Test resetting settings."""
        # Mock dependencies
        settings_dialog.original_config = {'original': 'config'}
        monkeypatch.setattr(settings_dialog, 'load_settings', MagicMock())
        monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.question', 
                         MagicMock(return_value=QMessageBox.Yes))
        monkeypatch.setattr('src.gui.settings_dialog.show_message', MagicMock())
        
        # Call reset_settings
        settings_dialog.reset_settings()
        
        # Verify config was reset
        mock_config_manager.update.assert_called_once_with({'original': 'config'})
        settings_dialog.load_settings.assert_called_once()


@pytest.mark.gui
class TestSyncHistoryDialog:
    """Test the SyncHistoryDialog class."""

    def test_initialization(self, sync_history_dialog, mock_config_manager, monkeypatch):
        """Test initialization of SyncHistoryDialog."""
        # Verify window properties
        assert sync_history_dialog.windowTitle() == "Synchronization History"
        assert sync_history_dialog.config_manager == mock_config_manager
        
        # Verify UI components
        assert sync_history_dialog.table is not None
        assert sync_history_dialog.type_filter is not None
        assert sync_history_dialog.status_filter is not None
        
        # Verify table configuration
        assert sync_history_dialog.table.columnCount() == 5
        assert sync_history_dialog.table.horizontalHeaderItem(0).text() == "Date & Time"
        assert sync_history_dialog.table.horizontalHeaderItem(1).text() == "Type"
        assert sync_history_dialog.table.horizontalHeaderItem(2).text() == "Status"
        assert sync_history_dialog.table.horizontalHeaderItem(3).text() == "Duration"
        assert sync_history_dialog.table.horizontalHeaderItem(4).text() == "Details"
    
    def test_add_history_item(self, sync_history_dialog):
        """Test adding a history item to the table."""
        # Create test item
        test_item = {
            'timestamp': '2025-03-30 14:30:00',
            'type': 'Manual',
            'status': 'Success',
            'duration': 5.2,
            'details': 'Test sync operation',
            'data_types': {'passwords': True, 'bookmarks': False, 'history': True},
            'errors': []
        }
        
        # Add item to table
        sync_history_dialog.add_history_item(test_item)
        
        # Verify item was added correctly
        assert sync_history_dialog.table.rowCount() == 1
        assert sync_history_dialog.table.item(0, 0).text() == '2025-03-30 14:30:00'
        assert sync_history_dialog.table.item(0, 1).text() == 'Manual'
        assert sync_history_dialog.table.item(0, 2).text() == 'Success'
        assert sync_history_dialog.table.item(0, 3).text() == '5.2s'
        assert sync_history_dialog.table.item(0, 4).text() == 'Test sync operation'
        
        # Verify stored data
        stored_item = sync_history_dialog.table.item(0, 0).data(Qt.UserRole)
        assert stored_item == test_item
    
    def test_apply_filters(self, sync_history_dialog):
        """Test applying filters to the table."""
        # Add test items
        sync_history_dialog.add_history_item({
            'timestamp': '2025-03-30 14:30:00',
            'type': 'Manual',
            'status': 'Success',
            'duration': 5.2,
            'details': 'Test manual success'
        })
        
        sync_history_dialog.add_history_item({
            'timestamp': '2025-03-30 14:35:00',
            'type': 'Auto',
            'status': 'Failed',
            'duration': 3.1,
            'details': 'Test auto failed'
        })
        
        sync_history_dialog.add_history_item({
            'timestamp': '2025-03-30 14:40:00',
            'type': 'Manual',
            'status': 'Failed',
            'duration': 2.5,
            'details': 'Test manual failed'
        })
        
        # Test 'All' filter (should show all rows)
        sync_history_dialog.type_filter.setCurrentText("All")
        sync_history_dialog.status_filter.setCurrentText("All")
        sync_history_dialog.apply_filters()
        
        assert not sync_history_dialog.table.isRowHidden(0)
        assert not sync_history_dialog.table.isRowHidden(1)
        assert not sync_history_dialog.table.isRowHidden(2)
        
        # Test type filter
        sync_history_dialog.type_filter.setCurrentText("Manual")
        sync_history_dialog.status_filter.setCurrentText("All")
        sync_history_dialog.apply_filters()
        
        assert not sync_history_dialog.table.isRowHidden(0)  # Manual
        assert sync_history_dialog.table.isRowHidden(1)      # Auto (hidden)
        assert not sync_history_dialog.table.isRowHidden(2)  # Manual
        
        # Test status filter
        sync_history_dialog.type_filter.setCurrentText("All")
        sync_history_dialog.status_filter.setCurrentText("Failed")
        sync_history_dialog.apply_filters()
        
        assert sync_history_dialog.table.isRowHidden(0)      # Success (hidden)
        assert not sync_history_dialog.table.isRowHidden(1)  # Failed
        assert not sync_history_dialog.table.isRowHidden(2)  # Failed
        
        # Test combined filters
        sync_history_dialog.type_filter.setCurrentText("Manual")
        sync_history_dialog.status_filter.setCurrentText("Failed")
        sync_history_dialog.apply_filters()
        
        assert sync_history_dialog.table.isRowHidden(0)      # Manual Success (hidden)
        assert sync_history_dialog.table.isRowHidden(1)      # Auto Failed (hidden)
        assert not sync_history_dialog.table.isRowHidden(2)  # Manual Failed


@pytest.mark.gui
class TestLogViewerDialog:
    """Test the LogViewerDialog class."""

    def test_initialization(self, log_viewer_dialog, mock_config_manager):
        """Test initialization of LogViewerDialog."""
        # Verify window properties
        assert log_viewer_dialog.windowTitle() == "Log Viewer"
        assert log_viewer_dialog.config_manager == mock_config_manager
        
        # Verify UI components
        assert log_viewer_dialog.log_text is not None
        assert log_viewer_dialog.log_level_combo is not None
        assert log_viewer_dialog.search_box is not None
        
        # Verify buttons
        assert log_viewer_dialog.refresh_button is not None
        assert log_viewer_dialog.clear_button is not None
        assert log_viewer_dialog.export_button is not None
        assert log_viewer_dialog.close_button is not None


@pytest.mark.gui
class TestSyncWorker:
    """Test the SyncWorker class."""

    def test_initialization(self, sync_worker, chrome_sync_app):
        """Test initialization of SyncWorker."""
        assert sync_worker.app == chrome_sync_app
        assert sync_worker.sync_thread is None
        
        # Verify signals exist
        assert hasattr(sync_worker, 'progress')
        assert hasattr(sync_worker, 'completed')
    
    def test_is_running(self, sync_worker):
        """Test is_running method."""
        # When sync_thread is None
        assert sync_worker.is_running() == False
        
        # When sync_thread exists but is not running
        sync_worker.sync_thread = MagicMock()
        sync_worker.sync_thread.isRunning.return_value = False
        assert sync_worker.is_running() == False
        
        # When sync_thread is running
        sync_worker.sync_thread.isRunning.return_value = True
        assert sync_worker.is_running() == True
    
    def test_start(self, sync_worker, chrome_sync_app, monkeypatch):
        """Test start method."""
        # Mock SyncThread
        mock_thread = MagicMock()
        monkeypatch.setattr('src.gui.sync_worker.SyncThread', MagicMock(return_value=mock_thread))
        
        # Call start
        sync_worker.start()
        
        # Verify thread was created and started
        assert sync_worker.sync_thread == mock_thread
        mock_thread.progress.connect.assert_called_once()
        mock_thread.finished.connect.assert_called_once()
        mock_thread.start.assert_called_once()
    
    def test_start_already_running(self, sync_worker, monkeypatch):
        """Test start method when already running."""
        # Mock is_running to return True
        monkeypatch.setattr(sync_worker, 'is_running', MagicMock(return_value=True))
        monkeypatch.setattr('src.gui.sync_worker.logger', MagicMock())
        
        # Call start
        sync_worker.start()
        
        # Verify SyncThread was not created
        assert sync_worker.sync_thread is None
    
    def test_cancel(self, sync_worker):
        """Test cancel method."""
        # Set up mock thread
        mock_thread = MagicMock()
        sync_worker.sync_thread = mock_thread
        
        # Call cancel
        sync_worker.cancel()
        
        # Verify thread was cancelled
        mock_thread.cancel.assert_called_once()
    
    def test_cancel_not_running(self, sync_worker, monkeypatch):
        """Test cancel method when not running."""
        # Mock is_running to return False
        monkeypatch.setattr(sync_worker, 'is_running', MagicMock(return_value=False))
        
        # Call cancel
        sync_worker.cancel()
        
        # Nothing should happen (no exceptions)
        pass
    
    def test_on_progress(self, sync_worker, monkeypatch):
        """Test on_progress method."""
        # Set up mock progress signal
        mock_progress = MagicMock()
        monkeypatch.setattr(sync_worker, 'progress', mock_progress)
        
        # Call on_progress
        sync_worker.on_progress(50, 100, "Test progress")
        
        # Verify progress signal was emitted
        mock_progress.emit.assert_called_once_with(50, 100, "Test progress")
    
    def test_on_finished(self, sync_worker, monkeypatch):
        """Test on_finished method."""
        # Set up mock completed signal
        mock_completed = MagicMock()
        monkeypatch.setattr(sync_worker, 'completed', mock_completed)
        
        # Set up mock thread
        mock_thread = MagicMock()
        mock_thread.result.return_value = True
        sync_worker.sync_thread = mock_thread
        
        # Call on_finished
        sync_worker.on_finished()
        
        # Verify completed signal was emitted
        mock_completed.emit.assert_called_once_with(True)
        
        # Verify thread was cleaned up
        mock_thread.deleteLater.assert_called_once()
        assert sync_worker.sync_thread is None


@pytest.mark.gui
class TestSyncThread:
    """Test the SyncThread class."""

    def test_initialization(self, chrome_sync_app):
        """Test initialization of SyncThread."""
        # Create SyncThread
        sync_thread = SyncThread(chrome_sync_app)
        
        # Verify properties
        assert sync_thread.app == chrome_sync_app
        assert sync_thread.cancelled == False
        assert sync_thread.mutex is not None
        assert sync_thread.condition is not None
        
        # Verify signal exists
        assert hasattr(sync_thread, 'progress')
    
    def test_progress_callback(self, chrome_sync_app, monkeypatch):
        """Test progress_callback method."""
        # Create SyncThread
        sync_thread = SyncThread(chrome_sync_app)
        
        # Set up mock progress signal
        mock_progress = MagicMock()
        monkeypatch.setattr(sync_thread, 'progress', mock_progress)
        
        # Call progress_callback
        sync_thread.progress_callback(50, 100, "Test progress")
        
        # Verify progress signal was emitted
        mock_progress.emit.assert_called_once_with(50, 100, "Test progress")
    
    def test_progress_callback_cancelled(self, chrome_sync_app, monkeypatch):
        """Test progress_callback method when cancelled."""
        # Create SyncThread
        sync_thread = SyncThread(chrome_sync_app)
        
        # Set cancelled to True
        sync_thread.cancelled = True
        
        # Set up mock progress signal
        mock_progress = MagicMock()
        monkeypatch.setattr(sync_thread, 'progress', mock_progress)
        
        # Call progress_callback, should raise exception due to cancellation
        with pytest.raises(Exception, match="Synchronization cancelled by user"):
            sync_thread.progress_callback(50, 100, "Test progress")
        
        # Verify progress signal was still emitted
        mock_progress.emit.assert_called_once_with(50, 100, "Test progress")
    
    def test_cancel(self, chrome_sync_app):
        """Test cancel method."""
        # Create SyncThread
        sync_thread = SyncThread(chrome_sync_app)
        
        # Call cancel
        sync_thread.cancel()
        
        # Verify cancelled flag was set
        assert sync_thread.cancelled == True
