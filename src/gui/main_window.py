"""
Main window for the ChromeSync application.

This module provides the main window for the ChromeSync application,
including the menu bar, toolbar, and status bar.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QSystemTrayIcon, QMenu, QAction,
    QDialog, QMessageBox, QTabWidget, QGroupBox, QCheckBox,
    QComboBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QToolBar, QStatusBar, QFileDialog,
    QApplication
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, pyqtSlot, QEvent
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QCloseEvent

from ..config import ConfigManager
from ..core import ServiceManager, ProfileDetector
from ..security import AuthenticationManager
from .utils import get_icon, get_style_sheet, show_message
from .settings_dialog import SettingsDialog
from .sync_history_dialog import SyncHistoryDialog
from .log_viewer_dialog import LogViewerDialog
from .sync_worker import SyncWorker

# Set up logging
logger = logging.getLogger(__name__)

class ChromeSyncApp:
    """
    Main ChromeSync application class for UI.
    
    This class holds the application components and serves as a communication
    bridge between the UI and the business logic.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the ChromeSync application for UI.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Initialize components
        from ..core import (
            ServiceManager, PasswordExtractor, BookmarkExtractor, HistoryExtractor,
            ProfileDetector, PasswordImporter, BookmarkImporter, HistoryImporter
        )
        from ..security import AuthenticationManager
        
        # Initialize configuration
        self.config_manager = ConfigManager(config_path)
        
        # Initialize authentication manager
        self.auth_manager = AuthenticationManager(self.config_manager)
        
        # Initialize service manager
        self.service_manager = ServiceManager(self.config_manager)
        
        # Initialize data extractors and importers
        self.profile_detector = ProfileDetector(self.config_manager)
        
        # Main window reference
        self.main_window = None
        
        # Status variables
        self.sync_in_progress = False
    
    def synchronize(self, progress_callback=None) -> bool:
        """
        Synchronize data between browsers.
        
        Args:
            progress_callback: Optional callback function for reporting progress
        
        Returns:
            bool: True if synchronization was successful, False otherwise
        """
        from .. import ChromeSync
        
        if self.sync_in_progress:
            logger.warning("Synchronization already in progress")
            return False
        
        self.sync_in_progress = True
        
        try:
            # Create main ChromeSync object for synchronization
            chrome_sync = ChromeSync(self.config_manager.config_file)
            
            # Perform synchronization
            result = chrome_sync.synchronize_all(progress_callback)
            
            return result
        
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            if progress_callback:
                progress_callback(0, 100, f"Error: {str(e)}")
            return False
        
        finally:
            self.sync_in_progress = False


class MainWindow(QMainWindow):
    """
    Main window for the ChromeSync application.
    
    This class provides the main window UI for the ChromeSync application.
    """
    
    def __init__(self, app: ChromeSyncApp):
        """
        Initialize the main window.
        
        Args:
            app: ChromeSyncApp instance
        """
        super().__init__()
        
        self.app = app
        
        # Initialize UI components
        self.init_ui()
        
        # Initialize system tray icon
        self.init_tray()
        
        # Initialize timers for status updates
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Update every 5 seconds
        
        # Initialize sync worker
        self.sync_worker = SyncWorker(self.app)
        self.sync_worker.progress.connect(self.update_sync_progress)
        self.sync_worker.completed.connect(self.on_sync_completed)
        
        # Set up service callbacks
        self.app.service_manager.add_callback('on_chrome_launch', self.on_chrome_launch)
        self.app.service_manager.add_callback('on_chrome_close', self.on_chrome_close)
        
        # Apply theme
        self.apply_theme()
        
        # Update status initially
        self.update_status()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("ChromeSync")
        self.setWindowIcon(get_icon("app_icon"))
        self.resize(800, 600)
        
        # Create main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status section
        self.create_status_section()
        
        # Create main content
        self.create_main_content()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        # Create menu bar
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Sync action
        sync_action = QAction(get_icon("sync"), "&Sync Now", self)
        sync_action.setShortcut("Ctrl+S")
        sync_action.setStatusTip("Synchronize browsers now")
        sync_action.triggered.connect(self.on_sync_clicked)
        file_menu.addAction(sync_action)
        
        # Settings action
        settings_action = QAction(get_icon("settings"), "S&ettings", self)
        settings_action.setShortcut("Ctrl+E")
        settings_action.setStatusTip("Open settings dialog")
        settings_action.triggered.connect(self.on_settings_clicked)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction(get_icon("close"), "E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        # Sync history action
        history_action = QAction(get_icon("history"), "Sync &History", self)
        history_action.setShortcut("Ctrl+H")
        history_action.setStatusTip("View synchronization history")
        history_action.triggered.connect(self.on_history_clicked)
        tools_menu.addAction(history_action)
        
        # Log viewer action
        logs_action = QAction(get_icon("logs"), "&Logs", self)
        logs_action.setShortcut("Ctrl+L")
        logs_action.setStatusTip("View application logs")
        logs_action.triggered.connect(self.on_logs_clicked)
        tools_menu.addAction(logs_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        # About action
        about_action = QAction(get_icon("about"), "&About", self)
        about_action.setStatusTip("About ChromeSync")
        about_action.triggered.connect(self.on_about_clicked)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the toolbar."""
        # Create toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # Sync action
        sync_action = QAction(get_icon("sync"), "Sync Now", self)
        sync_action.setStatusTip("Synchronize browsers now")
        sync_action.triggered.connect(self.on_sync_clicked)
        self.toolbar.addAction(sync_action)
        
        # Settings action
        settings_action = QAction(get_icon("settings"), "Settings", self)
        settings_action.setStatusTip("Open settings dialog")
        settings_action.triggered.connect(self.on_settings_clicked)
        self.toolbar.addAction(settings_action)
        
        # Add separator
        self.toolbar.addSeparator()
        
        # History action
        history_action = QAction(get_icon("history"), "Sync History", self)
        history_action.setStatusTip("View synchronization history")
        history_action.triggered.connect(self.on_history_clicked)
        self.toolbar.addAction(history_action)
        
        # Logs action
        logs_action = QAction(get_icon("logs"), "Logs", self)
        logs_action.setStatusTip("View application logs")
        logs_action.triggered.connect(self.on_logs_clicked)
        self.toolbar.addAction(logs_action)
    
    def create_status_section(self):
        """Create the status section."""
        # Create status group
        status_group = QGroupBox("Sync Status")
        status_layout = QVBoxLayout(status_group)
        
        # Create chrome status
        chrome_layout = QHBoxLayout()
        self.chrome_status_icon = QLabel()
        self.chrome_status_icon.setPixmap(get_icon("chrome").pixmap(QSize(16, 16)))
        self.chrome_status_label = QLabel("Chrome: Not running")
        chrome_layout.addWidget(self.chrome_status_icon)
        chrome_layout.addWidget(self.chrome_status_label)
        chrome_layout.addStretch()
        status_layout.addLayout(chrome_layout)
        
        # Create zen status
        zen_layout = QHBoxLayout()
        self.zen_status_icon = QLabel()
        self.zen_status_icon.setPixmap(get_icon("zen").pixmap(QSize(16, 16)))
        self.zen_status_label = QLabel("Zen Browser: Not detected")
        zen_layout.addWidget(self.zen_status_icon)
        zen_layout.addWidget(self.zen_status_label)
        zen_layout.addStretch()
        status_layout.addLayout(zen_layout)
        
        # Create service status
        service_layout = QHBoxLayout()
        self.service_status_icon = QLabel()
        self.service_status_icon.setPixmap(get_icon("info").pixmap(QSize(16, 16)))
        self.service_status_label = QLabel("Service: Stopped")
        service_layout.addWidget(self.service_status_icon)
        service_layout.addWidget(self.service_status_label)
        service_layout.addStretch()
        
        # Create service control buttons
        self.start_service_button = QPushButton("Start Service")
        self.start_service_button.setIcon(get_icon("start"))
        self.start_service_button.clicked.connect(self.on_start_service_clicked)
        self.stop_service_button = QPushButton("Stop Service")
        self.stop_service_button.setIcon(get_icon("stop"))
        self.stop_service_button.clicked.connect(self.on_stop_service_clicked)
        self.stop_service_button.setEnabled(False)
        
        service_layout.addWidget(self.start_service_button)
        service_layout.addWidget(self.stop_service_button)
        
        status_layout.addLayout(service_layout)
        
        # Create last sync
        last_sync_layout = QHBoxLayout()
        self.last_sync_icon = QLabel()
        self.last_sync_icon.setPixmap(get_icon("info").pixmap(QSize(16, 16)))
        self.last_sync_label = QLabel("Last Sync: Never")
        last_sync_layout.addWidget(self.last_sync_icon)
        last_sync_layout.addWidget(self.last_sync_label)
        last_sync_layout.addStretch()
        status_layout.addLayout(last_sync_layout)
        
        # Add status group to main layout
        self.main_layout.addWidget(status_group)
    
    def create_main_content(self):
        """Create the main content."""
        # Create sync section
        sync_group = QGroupBox("Synchronization")
        sync_layout = QVBoxLayout(sync_group)
        
        # Create sync status and progress
        sync_status_layout = QHBoxLayout()
        self.sync_status_icon = QLabel()
        self.sync_status_icon.setPixmap(get_icon("info").pixmap(QSize(16, 16)))
        self.sync_status_label = QLabel("Ready to sync")
        sync_status_layout.addWidget(self.sync_status_icon)
        sync_status_layout.addWidget(self.sync_status_label)
        sync_status_layout.addStretch()
        sync_layout.addLayout(sync_status_layout)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        sync_layout.addWidget(self.progress_bar)
        
        # Create sync buttons
        sync_buttons_layout = QHBoxLayout()
        sync_buttons_layout.addStretch()
        
        self.sync_button = QPushButton("Sync Now")
        self.sync_button.setIcon(get_icon("sync"))
        self.sync_button.clicked.connect(self.on_sync_clicked)
        self.sync_button.setMinimumWidth(120)
        sync_buttons_layout.addWidget(self.sync_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setIcon(get_icon("cancel"))
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setMinimumWidth(120)
        sync_buttons_layout.addWidget(self.cancel_button)
        
        sync_layout.addLayout(sync_buttons_layout)
        
        # Add sync group to main layout
        self.main_layout.addWidget(sync_group)
        
        # Add sync options group
        options_group = QGroupBox("Sync Options")
        options_layout = QVBoxLayout(options_group)
        
        # Create data type checkboxes
        data_types_layout = QHBoxLayout()
        
        self.passwords_checkbox = QCheckBox("Passwords")
        self.passwords_checkbox.setChecked(True)
        data_types_layout.addWidget(self.passwords_checkbox)
        
        self.bookmarks_checkbox = QCheckBox("Bookmarks")
        self.bookmarks_checkbox.setChecked(True)
        data_types_layout.addWidget(self.bookmarks_checkbox)
        
        self.history_checkbox = QCheckBox("Browsing History")
        self.history_checkbox.setChecked(True)
        data_types_layout.addWidget(self.history_checkbox)
        
        options_layout.addLayout(data_types_layout)
        
        # Create auto-sync options
        auto_sync_layout = QHBoxLayout()
        
        self.auto_sync_checkbox = QCheckBox("Enable Auto-Sync")
        self.auto_sync_checkbox.setChecked(True)
        self.auto_sync_checkbox.stateChanged.connect(self.on_auto_sync_changed)
        auto_sync_layout.addWidget(self.auto_sync_checkbox)
        
        auto_sync_layout.addWidget(QLabel("Trigger on:"))
        
        self.on_launch_checkbox = QCheckBox("Chrome Launch")
        self.on_launch_checkbox.setChecked(True)
        auto_sync_layout.addWidget(self.on_launch_checkbox)
        
        self.on_close_checkbox = QCheckBox("Chrome Close")
        self.on_close_checkbox.setChecked(False)
        auto_sync_layout.addWidget(self.on_close_checkbox)
        
        options_layout.addLayout(auto_sync_layout)
        
        # Save options button
        save_options_layout = QHBoxLayout()
        save_options_layout.addStretch()
        
        self.save_options_button = QPushButton("Save Options")
        self.save_options_button.clicked.connect(self.on_save_options_clicked)
        save_options_layout.addWidget(self.save_options_button)
        
        options_layout.addLayout(save_options_layout)
        
        # Add options group to main layout
        self.main_layout.addWidget(options_group)
        
        # Add stretch to push everything up
        self.main_layout.addStretch()
    
    def init_tray(self):
        """Initialize the system tray icon."""
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(get_icon("app_icon"))
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show/hide action
        self.show_action = QAction("Show", self)
        self.show_action.triggered.connect(self.show)
        tray_menu.addAction(self.show_action)
        
        # Sync action
        sync_action = QAction("Sync Now", self)
        sync_action.triggered.connect(self.on_sync_clicked)
        tray_menu.addAction(sync_action)
        
        tray_menu.addSeparator()
        
        # Service actions
        start_service_action = QAction("Start Service", self)
        start_service_action.triggered.connect(self.on_start_service_clicked)
        tray_menu.addAction(start_service_action)
        
        stop_service_action = QAction("Stop Service", self)
        stop_service_action.triggered.connect(self.on_stop_service_clicked)
        tray_menu.addAction(stop_service_action)
        
        tray_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.on_settings_clicked)
        tray_menu.addAction(settings_action)
        
        tray_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.on_exit_clicked)
        tray_menu.addAction(exit_action)
        
        # Set tray menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Set tray tooltip
        self.tray_icon.setToolTip("ChromeSync")
        
        # Show tray icon
        self.tray_icon.show()
        
        # Connect activation signal
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def apply_theme(self):
        """Apply the current theme."""
        # Get theme preference
        theme = self.app.config_manager.get('ui', 'theme', 'light')
        
        # Apply stylesheet
        self.setStyleSheet(get_style_sheet(theme))
    
    def update_status(self):
        """Update the status display."""
        # Get service status
        service_status = self.app.service_manager.status
        service_running = service_status == "running"
        
        # Update service status display
        if service_running:
            self.service_status_icon.setPixmap(get_icon("success").pixmap(QSize(16, 16)))
            self.service_status_label.setText("Service: Running")
            self.start_service_button.setEnabled(False)
            self.stop_service_button.setEnabled(True)
        else:
            self.service_status_icon.setPixmap(get_icon("error").pixmap(QSize(16, 16)))
            self.service_status_label.setText("Service: Stopped")
            self.start_service_button.setEnabled(True)
            self.stop_service_button.setEnabled(False)
        
        # Get Chrome status
        chrome_running = self.app.service_manager.is_chrome_running()
        
        # Update Chrome status display
        if chrome_running:
            self.chrome_status_icon.setPixmap(get_icon("success").pixmap(QSize(16, 16)))
            self.chrome_status_label.setText("Chrome: Running")
        else:
            self.chrome_status_icon.setPixmap(get_icon("warning").pixmap(QSize(16, 16)))
            self.chrome_status_label.setText("Chrome: Not running")
        
        # Get Zen Browser status
        try:
            zen_profile = self.app.profile_detector.get_default_profile()
            if zen_profile:
                self.zen_status_icon.setPixmap(get_icon("success").pixmap(QSize(16, 16)))
                self.zen_status_label.setText(f"Zen Browser: {zen_profile.name}")
            else:
                self.zen_status_icon.setPixmap(get_icon("error").pixmap(QSize(16, 16)))
                self.zen_status_label.setText("Zen Browser: Not detected")
        except Exception as e:
            self.zen_status_icon.setPixmap(get_icon("error").pixmap(QSize(16, 16)))
            self.zen_status_label.setText(f"Zen Browser: Error ({str(e)})")
        
        # Get last sync time
        last_sync = self.app.config_manager.get('sync', 'last_sync_time', None)
        if last_sync:
            self.last_sync_icon.setPixmap(get_icon("success").pixmap(QSize(16, 16)))
            self.last_sync_label.setText(f"Last Sync: {last_sync}")
        else:
            self.last_sync_icon.setPixmap(get_icon("info").pixmap(QSize(16, 16)))
            self.last_sync_label.setText("Last Sync: Never")
        
        # Update sync options
        self.update_sync_options()
    
    def update_sync_options(self):
        """Update the sync options from config."""
        # Get sync preferences
        sync_options = self.app.config_manager.get('sync', {})
        
        # Update data types
        data_types = sync_options.get('data_types', {})
        self.passwords_checkbox.setChecked(data_types.get('passwords', True))
        self.bookmarks_checkbox.setChecked(data_types.get('bookmarks', True))
        self.history_checkbox.setChecked(data_types.get('history', True))
        
        # Update auto-sync options
        auto_sync = sync_options.get('auto_sync', {})
        self.auto_sync_checkbox.setChecked(auto_sync.get('enabled', True))
        self.on_launch_checkbox.setChecked(auto_sync.get('trigger_on_chrome_launch', True))
        self.on_close_checkbox.setChecked(auto_sync.get('trigger_on_chrome_close', False))
        
        # Update control states
        self.on_auto_sync_changed(self.auto_sync_checkbox.checkState())
    
    def update_sync_progress(self, current: int, total: int, message: str):
        """
        Update the sync progress display.
        
        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message
        """
        # Update progress bar
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
        # Update status label
        self.sync_status_label.setText(message)
        
        # Update status bar
        self.status_label.setText(message)
        
        # Update tray tooltip
        self.tray_icon.setToolTip(f"ChromeSync - {message}")
        
        # Process events to update UI
        QApplication.processEvents()
    
    def on_sync_completed(self, success: bool):
        """
        Handle sync completion.
        
        Args:
            success: Whether the sync was successful
        """
        # Update UI state
        self.sync_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Update status and progress
        if success:
            self.sync_status_icon.setPixmap(get_icon("success").pixmap(QSize(16, 16)))
            self.sync_status_label.setText("Sync completed successfully")
            self.status_label.setText("Sync completed successfully")
            self.tray_icon.setToolTip("ChromeSync - Sync completed successfully")
            
            # Show notification
            self.tray_icon.showMessage(
                "ChromeSync",
                "Synchronization completed successfully",
                QSystemTrayIcon.Information,
                5000
            )
        else:
            self.sync_status_icon.setPixmap(get_icon("error").pixmap(QSize(16, 16)))
            self.sync_status_label.setText("Sync failed")
            self.status_label.setText("Sync failed")
            self.tray_icon.setToolTip("ChromeSync - Sync failed")
            
            # Show notification
            self.tray_icon.showMessage(
                "ChromeSync",
                "Synchronization failed. Check logs for details.",
                QSystemTrayIcon.Critical,
                5000
            )
        
        # Update last sync time
        self.update_status()
    
    def on_chrome_launch(self):
        """Handle Chrome launch event."""
        logger.info("Chrome launch detected in UI")
        
        # Update status
        self.update_status()
        
        # Check auto-sync settings
        if (self.auto_sync_checkbox.isChecked() and
                self.on_launch_checkbox.isChecked() and
                not self.sync_worker.is_running()):
            
            # Show notification
            self.tray_icon.showMessage(
                "ChromeSync",
                "Chrome launched. Starting automatic synchronization...",
                QSystemTrayIcon.Information,
                5000
            )
            
            # Delay sync for a few seconds
            QTimer.singleShot(5000, self.on_sync_clicked)
    
    def on_chrome_close(self):
        """Handle Chrome close event."""
        logger.info("Chrome close detected in UI")
        
        # Update status
        self.update_status()
        
        # Check auto-sync settings
        if (self.auto_sync_checkbox.isChecked() and
                self.on_close_checkbox.isChecked() and
                not self.sync_worker.is_running()):
            
            # Show notification
            self.tray_icon.showMessage(
                "ChromeSync",
                "Chrome closed. Starting automatic synchronization...",
                QSystemTrayIcon.Information,
                5000
            )
            
            # Start sync immediately
            self.on_sync_clicked()
    
    def on_sync_clicked(self):
        """Handle sync button click."""
        # Check if sync is already in progress
        if self.sync_worker.is_running():
            logger.warning("Sync already in progress")
            return
        
        # Update UI state
        self.sync_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.sync_status_icon.setPixmap(get_icon("info").pixmap(QSize(16, 16)))
        self.sync_status_label.setText("Starting synchronization...")
        self.progress_bar.setValue(0)
        
        # Get sync options
        sync_passwords = self.passwords_checkbox.isChecked()
        sync_bookmarks = self.bookmarks_checkbox.isChecked()
        sync_history = self.history_checkbox.isChecked()
        
        # Check if at least one type is selected
        if not any([sync_passwords, sync_bookmarks, sync_history]):
            logger.warning("No data types selected for sync")
            show_message(
                self,
                "Synchronization",
                "Please select at least one data type to synchronize.",
                QMessageBox.Warning
            )
            
            # Reset UI state
            self.sync_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.sync_status_icon.setPixmap(get_icon("error").pixmap(QSize(16, 16)))
            self.sync_status_label.setText("No data types selected for sync")
            return
        
        # Update config with sync options
        self.app.config_manager.set('sync', 'data_types', {
            'passwords': sync_passwords,
            'bookmarks': sync_bookmarks,
            'history': sync_history
        })
        self.app.config_manager.save()
        
        # Start sync worker
        self.sync_worker.start()
    
    def on_cancel_clicked(self):
        """Handle cancel button click."""
        # Check if sync is in progress
        if not self.sync_worker.is_running():
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Cancel Synchronization",
            "Are you sure you want to cancel the synchronization?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Cancel sync worker
            self.sync_worker.cancel()
            
            # Update UI state
            self.sync_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.sync_status_icon.setPixmap(get_icon("warning").pixmap(QSize(16, 16)))
            self.sync_status_label.setText("Synchronization cancelled")
            self.status_label.setText("Synchronization cancelled")
            self.tray_icon.setToolTip("ChromeSync - Synchronization cancelled")
    
    def on_settings_clicked(self):
        """Handle settings button click."""
        # Create and show settings dialog
        settings_dialog = SettingsDialog(self.app.config_manager, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            # Settings updated, apply changes
            self.apply_theme()
            self.update_status()
    
    def on_history_clicked(self):
        """Handle history button click."""
        # Create and show sync history dialog
        history_dialog = SyncHistoryDialog(self.app.config_manager, self)
        history_dialog.exec_()
    
    def on_logs_clicked(self):
        """Handle logs button click."""
        # Create and show log viewer dialog
        log_dialog = LogViewerDialog(self.app.config_manager, self)
        log_dialog.exec_()
    
    def on_about_clicked(self):
        """Handle about button click."""
        # Get version info
        version = "1.0.0"  # Should come from a version.py file in a production app
        
        # Create and show about message
        about_text = f"""
        <h2>ChromeSync</h2>
        <p>Version {version}</p>
        <p>A tool to synchronize Chrome data to Zen Browser.</p>
        <p>Copyright © 2025 Jamie Spinner</p>
        <p>Licensed under MIT License</p>
        """
        
        QMessageBox.about(self, "About ChromeSync", about_text)
    
    def on_start_service_clicked(self):
        """Handle start service button click."""
        # Start service
        if self.app.service_manager.start_service():
            logger.info("Service started successfully from UI")
            
            # Update UI
            self.update_status()
            
            # Show notification
            self.tray_icon.showMessage(
                "ChromeSync",
                "Service started successfully",
                QSystemTrayIcon.Information,
                5000
            )
        else:
            logger.error(f"Failed to start service from UI: {self.app.service_manager.error_message}")
            
            # Show error message
            show_message(
                self,
                "Service Error",
                f"Failed to start service: {self.app.service_manager.error_message}",
                QMessageBox.Critical
            )
    
    def on_stop_service_clicked(self):
        """Handle stop service button click."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Stop Service",
            "Are you sure you want to stop the service?\n"
            "No automatic synchronization will occur while the service is stopped.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Stop service
            if self.app.service_manager.stop_service():
                logger.info("Service stopped successfully from UI")
                
                # Update UI
                self.update_status()
                
                # Show notification
                self.tray_icon.showMessage(
                    "ChromeSync",
                    "Service stopped successfully",
                    QSystemTrayIcon.Information,
                    5000
                )
            else:
                logger.error(f"Failed to stop service from UI: {self.app.service_manager.error_message}")
                
                # Show error message
                show_message(
                    self,
                    "Service Error",
                    f"Failed to stop service: {self.app.service_manager.error_message}",
                    QMessageBox.Critical
                )
    
    def on_auto_sync_changed(self, state):
        """
        Handle auto-sync checkbox change.
        
        Args:
            state: Checkbox state
        """
        # Enable/disable trigger checkboxes
        enabled = state == Qt.Checked
        self.on_launch_checkbox.setEnabled(enabled)
        self.on_close_checkbox.setEnabled(enabled)
    
    def on_save_options_clicked(self):
        """Handle save options button click."""
        # Get sync options
        sync_passwords = self.passwords_checkbox.isChecked()
        sync_bookmarks = self.bookmarks_checkbox.isChecked()
        sync_history = self.history_checkbox.isChecked()
        
        auto_sync_enabled = self.auto_sync_checkbox.isChecked()
        trigger_on_launch = self.on_launch_checkbox.isChecked()
        trigger_on_close = self.on_close_checkbox.isChecked()
        
        # Update config
        self.app.config_manager.set('sync', 'data_types', {
            'passwords': sync_passwords,
            'bookmarks': sync_bookmarks,
            'history': sync_history
        })
        
        self.app.config_manager.set('sync', 'auto_sync', {
            'enabled': auto_sync_enabled,
            'trigger_on_chrome_launch': trigger_on_launch,
            'trigger_on_chrome_close': trigger_on_close
        })
        
        # Save config
        self.app.config_manager.save()
        
        # Show confirmation
        self.status_label.setText("Sync options saved")
        self.tray_icon.showMessage(
            "ChromeSync",
            "Synchronization options saved",
            QSystemTrayIcon.Information,
            3000
        )
    
    def on_tray_activated(self, reason):
        """
        Handle tray icon activation.
        
        Args:
            reason: Activation reason
        """
        # Handle double click
        if reason == QSystemTrayIcon.DoubleClick:
            # Show/hide window
            if self.isVisible():
                self.hide()
                self.show_action.setText("Show")
            else:
                self.show()
                self.show_action.setText("Hide")
    
    def on_exit_clicked(self):
        """Handle exit button click."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Exit Confirmation",
            "Are you sure you want to exit ChromeSync?\n"
            "No automatic synchronization will occur while the application is closed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Exit application
            self.close()
    
    def closeEvent(self, event: QCloseEvent):
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        # Check if minimizing to tray is enabled
        minimize_to_tray = self.app.config_manager.get('ui', 'minimize_to_tray', True)
        
        # Handle close event
        if minimize_to_tray and event.spontaneous():
            # Minimize to tray instead of closing
            event.ignore()
            self.hide()
            self.show_action.setText("Show")
            
            # Show notification
            self.tray_icon.showMessage(
                "ChromeSync",
                "ChromeSync is still running in the background.",
                QSystemTrayIcon.Information,
                3000
            )
        else:
            # Stop service
            if self.app.service_manager.status == "running":
                self.app.service_manager.stop_service()
            
            # Accept close event
            event.accept()
