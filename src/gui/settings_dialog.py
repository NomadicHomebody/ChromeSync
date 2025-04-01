"""
Settings dialog for ChromeSync.

This module provides a dialog for editing the application settings.
"""

import os
import logging
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QWidget, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QComboBox, QGroupBox, QFileDialog, QMessageBox,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

from ..config import ConfigManager
from .utils import get_icon, get_style_sheet, show_message

# Set up logging
logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """
    Dialog for editing application settings.
    
    This dialog allows the user to edit various settings of the ChromeSync
    application, including general settings, synchronization settings,
    security settings, and UI settings.
    """
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize the settings dialog.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Original config for reset
        self.original_config = self.config_manager.get_all()
        
        # Initialize UI
        self.init_ui()
        
        # Load settings
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Settings")
        self.setWindowIcon(get_icon("settings"))
        self.resize(600, 500)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.general_tab = QWidget()
        self.sync_tab = QWidget()
        self.security_tab = QWidget()
        self.ui_tab = QWidget()
        self.advanced_tab = QWidget()
        
        # Initialize tab contents
        self.init_general_tab()
        self.init_sync_tab()
        self.init_security_tab()
        self.init_ui_tab()
        self.init_advanced_tab()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.general_tab, get_icon("info"), "General")
        self.tab_widget.addTab(self.sync_tab, get_icon("sync"), "Synchronization")
        self.tab_widget.addTab(self.security_tab, get_icon("error"), "Security")
        self.tab_widget.addTab(self.ui_tab, get_icon("app_icon"), "UI")
        self.tab_widget.addTab(self.advanced_tab, get_icon("settings"), "Advanced")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.Reset
        )
        
        # Connect button signals
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_settings)
        
        # Add button box to main layout
        main_layout.addWidget(button_box)
    
    def init_general_tab(self):
        """Initialize the general tab."""
        # Create layout
        layout = QVBoxLayout(self.general_tab)
        
        # Create startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)
        
        # Auto start on application launch
        self.auto_start_checkbox = QCheckBox("Automatically start service on application launch")
        startup_layout.addWidget(self.auto_start_checkbox)
        
        # Sync on startup
        self.sync_on_startup_checkbox = QCheckBox("Synchronize on startup")
        startup_layout.addWidget(self.sync_on_startup_checkbox)
        
        # Start minimized
        self.start_minimized_checkbox = QCheckBox("Start minimized to system tray")
        startup_layout.addWidget(self.start_minimized_checkbox)
        
        # Add startup group to layout
        layout.addWidget(startup_group)
        
        # Create logging group
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        
        # Log level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        # Log directory
        log_dir_layout = QHBoxLayout()
        self.log_dir_edit = QLineEdit()
        self.log_dir_edit.setReadOnly(True)
        self.log_dir_button = QPushButton("Browse...")
        self.log_dir_button.clicked.connect(self.browse_log_dir)
        log_dir_layout.addWidget(self.log_dir_edit)
        log_dir_layout.addWidget(self.log_dir_button)
        logging_layout.addRow("Log Directory:", log_dir_layout)
        
        # Log file max size
        self.log_max_size_spinbox = QSpinBox()
        self.log_max_size_spinbox.setRange(1, 100)
        self.log_max_size_spinbox.setSuffix(" MB")
        logging_layout.addRow("Max Log File Size:", self.log_max_size_spinbox)
        
        # Add logging group to layout
        layout.addWidget(logging_group)
        
        # Add spacer
        layout.addStretch()
    
    def init_sync_tab(self):
        """Initialize the synchronization tab."""
        # Create layout
        layout = QVBoxLayout(self.sync_tab)
        
        # Create data types group
        data_types_group = QGroupBox("Data Types")
        data_types_layout = QVBoxLayout(data_types_group)
        
        # Password sync
        self.passwords_checkbox = QCheckBox("Passwords")
        data_types_layout.addWidget(self.passwords_checkbox)
        
        # Bookmark sync
        self.bookmarks_checkbox = QCheckBox("Bookmarks")
        data_types_layout.addWidget(self.bookmarks_checkbox)
        
        # History sync
        self.history_checkbox = QCheckBox("Browsing History")
        data_types_layout.addWidget(self.history_checkbox)
        
        # Add data types group to layout
        layout.addWidget(data_types_group)
        
        # Create auto sync group
        auto_sync_group = QGroupBox("Automatic Synchronization")
        auto_sync_layout = QVBoxLayout(auto_sync_group)
        
        # Enable auto sync
        self.auto_sync_checkbox = QCheckBox("Enable automatic synchronization")
        self.auto_sync_checkbox.stateChanged.connect(self.on_auto_sync_changed)
        auto_sync_layout.addWidget(self.auto_sync_checkbox)
        
        # Trigger events
        self.trigger_group = QGroupBox("Trigger Events")
        trigger_layout = QVBoxLayout(self.trigger_group)
        
        # On Chrome launch
        self.on_launch_checkbox = QCheckBox("When Chrome is launched")
        trigger_layout.addWidget(self.on_launch_checkbox)
        
        # On Chrome close
        self.on_close_checkbox = QCheckBox("When Chrome is closed")
        trigger_layout.addWidget(self.on_close_checkbox)
        
        # Add trigger group to auto sync layout
        auto_sync_layout.addWidget(self.trigger_group)
        
        # Delay seconds
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay before sync:"))
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 60)
        self.delay_spinbox.setSuffix(" seconds")
        delay_layout.addWidget(self.delay_spinbox)
        delay_layout.addStretch()
        auto_sync_layout.addLayout(delay_layout)
        
        # Add auto sync group to layout
        layout.addWidget(auto_sync_group)
        
        # Create history group
        history_group = QGroupBox("History")
        history_layout = QFormLayout(history_group)
        
        # Max days of history to sync
        self.history_days_spinbox = QSpinBox()
        self.history_days_spinbox.setRange(1, 365)
        self.history_days_spinbox.setSuffix(" days")
        history_layout.addRow("Sync browsing history for the last:", self.history_days_spinbox)
        
        # Add history group to layout
        layout.addWidget(history_group)
        
        # Add spacer
        layout.addStretch()
    
    def init_security_tab(self):
        """Initialize the security tab."""
        # Create layout
        layout = QVBoxLayout(self.security_tab)
        
        # Create authentication group
        auth_group = QGroupBox("Authentication")
        auth_layout = QVBoxLayout(auth_group)
        
        # Require auth for password sync
        self.auth_for_passwords_checkbox = QCheckBox("Require authentication for password synchronization")
        auth_layout.addWidget(self.auth_for_passwords_checkbox)
        
        # Require auth for UI
        self.auth_for_ui_checkbox = QCheckBox("Require authentication to open application")
        auth_layout.addWidget(self.auth_for_ui_checkbox)
        
        # Add auth group to layout
        layout.addWidget(auth_group)
        
        # Create encryption group
        encryption_group = QGroupBox("Encryption")
        encryption_layout = QFormLayout(encryption_group)
        
        # Encryption algorithm
        self.encryption_algo_combo = QComboBox()
        self.encryption_algo_combo.addItems(["AES-256", "ChaCha20", "Blowfish"])
        encryption_layout.addRow("Encryption Algorithm:", self.encryption_algo_combo)
        
        # Add encryption group to layout
        layout.addWidget(encryption_group)
        
        # Create credentials group
        creds_group = QGroupBox("Credentials Storage")
        creds_layout = QVBoxLayout(creds_group)
        
        # Use Windows Credential Manager
        self.use_credential_manager_checkbox = QCheckBox("Use Windows Credential Manager")
        creds_layout.addWidget(self.use_credential_manager_checkbox)
        
        # Add credentials group to layout
        layout.addWidget(creds_group)
        
        # Add spacer
        layout.addStretch()
    
    def init_ui_tab(self):
        """Initialize the UI tab."""
        # Create layout
        layout = QVBoxLayout(self.ui_tab)
        
        # Create appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        appearance_layout.addRow("Theme:", self.theme_combo)
        
        # Add appearance group to layout
        layout.addWidget(appearance_group)
        
        # Create tray group
        tray_group = QGroupBox("System Tray")
        tray_layout = QVBoxLayout(tray_group)
        
        # Minimize to tray
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to system tray when closed")
        tray_layout.addWidget(self.minimize_to_tray_checkbox)
        
        # Show notifications
        self.show_notifications_checkbox = QCheckBox("Show system tray notifications")
        tray_layout.addWidget(self.show_notifications_checkbox)
        
        # Add tray group to layout
        layout.addWidget(tray_group)
        
        # Add spacer
        layout.addStretch()
    
    def init_advanced_tab(self):
        """Initialize the advanced tab."""
        # Create layout
        layout = QVBoxLayout(self.advanced_tab)
        
        # Create browser paths group
        browser_group = QGroupBox("Browser Paths")
        browser_layout = QFormLayout(browser_group)
        
        # Chrome path
        chrome_path_layout = QHBoxLayout()
        self.chrome_path_edit = QLineEdit()
        self.chrome_path_button = QPushButton("Browse...")
        self.chrome_path_button.clicked.connect(self.browse_chrome_path)
        chrome_path_layout.addWidget(self.chrome_path_edit)
        chrome_path_layout.addWidget(self.chrome_path_button)
        browser_layout.addRow("Chrome Path:", chrome_path_layout)
        
        # Zen Browser path
        zen_path_layout = QHBoxLayout()
        self.zen_path_edit = QLineEdit()
        self.zen_path_button = QPushButton("Browse...")
        self.zen_path_button.clicked.connect(self.browse_zen_path)
        zen_path_layout.addWidget(self.zen_path_edit)
        zen_path_layout.addWidget(self.zen_path_button)
        browser_layout.addRow("Zen Browser Path:", zen_path_layout)
        
        # Add browser group to layout
        layout.addWidget(browser_group)
        
        # Create data storage group
        storage_group = QGroupBox("Data Storage")
        storage_layout = QFormLayout(storage_group)
        
        # Data directory
        data_dir_layout = QHBoxLayout()
        self.data_dir_edit = QLineEdit()
        self.data_dir_button = QPushButton("Browse...")
        self.data_dir_button.clicked.connect(self.browse_data_dir)
        data_dir_layout.addWidget(self.data_dir_edit)
        data_dir_layout.addWidget(self.data_dir_button)
        storage_layout.addRow("Data Directory:", data_dir_layout)
        
        # Add storage group to layout
        layout.addWidget(storage_group)
        
        # Create performance group
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout(performance_group)
        
        # Thread count
        self.thread_count_spinbox = QSpinBox()
        self.thread_count_spinbox.setRange(1, 16)
        performance_layout.addRow("Worker Threads:", self.thread_count_spinbox)
        
        # Add performance group to layout
        layout.addWidget(performance_group)
        
        # Add spacer
        layout.addStretch()
    
    def load_settings(self):
        """Load settings from config."""
        # Get config
        config = self.config_manager.get_all()
        
        # Load general settings
        general = config.get('general', {})
        self.auto_start_checkbox.setChecked(general.get('auto_start', True))
        self.sync_on_startup_checkbox.setChecked(general.get('sync_on_startup', False))
        self.start_minimized_checkbox.setChecked(general.get('start_minimized', False))
        
        # Load logging settings
        logs = config.get('logs', {})
        self.log_level_combo.setCurrentText(logs.get('level', 'INFO').upper())
        self.log_dir_edit.setText(logs.get('dir', os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ChromeSync', 'logs')))
        self.log_max_size_spinbox.setValue(logs.get('max_size_mb', 10))
        
        # Load sync settings
        sync = config.get('sync', {})
        
        # Data types
        data_types = sync.get('data_types', {})
        self.passwords_checkbox.setChecked(data_types.get('passwords', True))
        self.bookmarks_checkbox.setChecked(data_types.get('bookmarks', True))
        self.history_checkbox.setChecked(data_types.get('history', True))
        
        # Auto sync
        auto_sync = sync.get('auto_sync', {})
        self.auto_sync_checkbox.setChecked(auto_sync.get('enabled', True))
        self.on_launch_checkbox.setChecked(auto_sync.get('trigger_on_chrome_launch', True))
        self.on_close_checkbox.setChecked(auto_sync.get('trigger_on_chrome_close', False))
        self.delay_spinbox.setValue(auto_sync.get('delay_seconds', 5))
        
        # Update control states
        self.on_auto_sync_changed(Qt.Checked if auto_sync.get('enabled', True) else Qt.Unchecked)
        
        # History settings
        self.history_days_spinbox.setValue(sync.get('history_days', 30))
        
        # Load security settings
        security = config.get('security', {})
        
        # Authentication
        auth = security.get('authentication', {})
        self.auth_for_passwords_checkbox.setChecked(auth.get('require_for_passwords', True))
        self.auth_for_ui_checkbox.setChecked(auth.get('require_for_ui', False))
        
        # Encryption
        encryption = security.get('encryption', {})
        algo = encryption.get('algorithm', 'AES-256')
        index = self.encryption_algo_combo.findText(algo)
        if index >= 0:
            self.encryption_algo_combo.setCurrentIndex(index)
        
        # Credentials
        creds = security.get('credentials', {})
        self.use_credential_manager_checkbox.setChecked(creds.get('use_credential_manager', True))
        
        # Load UI settings
        ui = config.get('ui', {})
        
        # Theme
        theme = ui.get('theme', 'light').capitalize()
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        # Tray
        self.minimize_to_tray_checkbox.setChecked(ui.get('minimize_to_tray', True))
        self.show_notifications_checkbox.setChecked(ui.get('show_notifications', True))
        
        # Load advanced settings
        advanced = config.get('advanced', {})
        
        # Browser paths
        browsers = advanced.get('browsers', {})
        self.chrome_path_edit.setText(browsers.get('chrome_path', ''))
        self.zen_path_edit.setText(browsers.get('zen_path', ''))
        
        # Data storage
        storage = advanced.get('storage', {})
        self.data_dir_edit.setText(storage.get('data_dir', os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ChromeSync', 'data')))
        
        # Performance
        performance = advanced.get('performance', {})
        self.thread_count_spinbox.setValue(performance.get('thread_count', 4))
    
    def gather_settings(self) -> Dict[str, Any]:
        """
        Gather settings from UI.
        
        Returns:
            Dict[str, Any]: Settings dictionary
        """
        config = {}
        
        # General settings
        config['general'] = {
            'auto_start': self.auto_start_checkbox.isChecked(),
            'sync_on_startup': self.sync_on_startup_checkbox.isChecked(),
            'start_minimized': self.start_minimized_checkbox.isChecked()
        }
        
        # Logging settings
        config['logs'] = {
            'level': self.log_level_combo.currentText(),
            'dir': self.log_dir_edit.text(),
            'max_size_mb': self.log_max_size_spinbox.value()
        }
        
        # Sync settings
        config['sync'] = {
            'data_types': {
                'passwords': self.passwords_checkbox.isChecked(),
                'bookmarks': self.bookmarks_checkbox.isChecked(),
                'history': self.history_checkbox.isChecked()
            },
            'auto_sync': {
                'enabled': self.auto_sync_checkbox.isChecked(),
                'trigger_on_chrome_launch': self.on_launch_checkbox.isChecked(),
                'trigger_on_chrome_close': self.on_close_checkbox.isChecked(),
                'delay_seconds': self.delay_spinbox.value()
            },
            'history_days': self.history_days_spinbox.value()
        }
        
        # Security settings
        config['security'] = {
            'authentication': {
                'require_for_passwords': self.auth_for_passwords_checkbox.isChecked(),
                'require_for_ui': self.auth_for_ui_checkbox.isChecked()
            },
            'encryption': {
                'algorithm': self.encryption_algo_combo.currentText()
            },
            'credentials': {
                'use_credential_manager': self.use_credential_manager_checkbox.isChecked()
            }
        }
        
        # UI settings
        config['ui'] = {
            'theme': self.theme_combo.currentText().lower(),
            'minimize_to_tray': self.minimize_to_tray_checkbox.isChecked(),
            'show_notifications': self.show_notifications_checkbox.isChecked()
        }
        
        # Advanced settings
        config['advanced'] = {
            'browsers': {
                'chrome_path': self.chrome_path_edit.text(),
                'zen_path': self.zen_path_edit.text()
            },
            'storage': {
                'data_dir': self.data_dir_edit.text()
            },
            'performance': {
                'thread_count': self.thread_count_spinbox.value()
            }
        }
        
        return config
    
    def on_auto_sync_changed(self, state):
        """
        Handle auto sync checkbox change.
        
        Args:
            state: Checkbox state
        """
        # Enable/disable trigger group
        enabled = state == Qt.Checked
        self.trigger_group.setEnabled(enabled)
        self.delay_spinbox.setEnabled(enabled)
    
    def browse_log_dir(self):
        """Browse for log directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Log Directory",
            self.log_dir_edit.text()
        )
        
        if directory:
            self.log_dir_edit.setText(directory)
    
    def browse_chrome_path(self):
        """Browse for Chrome executable path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Chrome Executable",
            self.chrome_path_edit.text(),
            "Executables (*.exe);;All Files (*)"
        )
        
        if file_path:
            self.chrome_path_edit.setText(file_path)
    
    def browse_zen_path(self):
        """Browse for Zen Browser executable path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Zen Browser Executable",
            self.zen_path_edit.text(),
            "Executables (*.exe);;All Files (*)"
        )
        
        if file_path:
            self.zen_path_edit.setText(file_path)
    
    def browse_data_dir(self):
        """Browse for data directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Data Directory",
            self.data_dir_edit.text()
        )
        
        if directory:
            self.data_dir_edit.setText(directory)
    
    def apply_settings(self):
        """Apply settings without closing the dialog."""
        # Gather settings
        config = self.gather_settings()
        
        try:
            # Update config
            self.config_manager.update(config)
            
            # Save config
            self.config_manager.save()
            
            # Update original config for reset
            self.original_config = self.config_manager.get_all()
            
            # Log
            logger.info("Settings saved")
            
            # Show success message
            show_message(
                self,
                "Settings Saved",
                "Settings have been saved successfully.",
                QMessageBox.Information
            )
        
        except Exception as e:
            logger.error(f"Failed to save settings: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}",
                QMessageBox.Critical
            )
    
    def reset_settings(self):
        """Reset settings to original values."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their original values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Restore original config
            self.config_manager.update(self.original_config)
            
            # Reload settings
            self.load_settings()
            
            # Log
            logger.info("Settings reset")
            
            # Show success message
            show_message(
                self,
                "Settings Reset",
                "Settings have been reset to their original values.",
                QMessageBox.Information
            )
        
        except Exception as e:
            logger.error(f"Failed to reset settings: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Reset Error",
                f"Failed to reset settings: {str(e)}",
                QMessageBox.Critical
            )
    
    def accept(self):
        """Handle dialog acceptance."""
        # Apply settings
        self.apply_settings()
        
        # Accept the dialog
        super().accept()
