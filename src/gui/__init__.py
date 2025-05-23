"""
GUI package for ChromeSync.

This package provides the graphical user interface for ChromeSync,
including the main window, dialogs, and utilities.
"""

import sys
import logging
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from .main_window import MainWindow, ChromeSyncApp
from .settings_dialog import SettingsDialog
from .sync_history_dialog import SyncHistoryDialog
from .log_viewer_dialog import LogViewerDialog
from .sync_worker import SyncWorker
from .utils import get_icon, get_style_sheet, show_message

__all__ = [
    'MainWindow',
    'ChromeSyncApp',
    'SettingsDialog',
    'SyncHistoryDialog',
    'LogViewerDialog',
    'SyncWorker',
    'get_icon',
    'get_style_sheet',
    'show_message',
    'run_gui'
]

# Set up logging
logger = logging.getLogger(__name__)

def run_gui(config_path: Optional[str] = None) -> int:
    """
    Run the ChromeSync GUI application.
    
    Args:
        config_path: Optional path to configuration file
    
    Returns:
        int: Exit code
    """
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ChromeSync")
    app.setOrganizationName("ChromeSync")
    
    try:
        # Set application icon
        app_icon = get_icon("app_icon")
        app.setWindowIcon(app_icon)
        
        # Create and initialize ChromeSync application
        chrome_sync_app = ChromeSyncApp(config_path)
        
        # Create main window
        main_window = MainWindow(chrome_sync_app)
        chrome_sync_app.main_window = main_window
        
        # Show the main window
        main_window.show()
        
        # Start auto startup if configured
        if chrome_sync_app.config_manager.get('general', 'auto_start', True):
            chrome_sync_app.service_manager.start_service()
        
        # Run the application
        exit_code = app.exec_()
        
        # Clean up and stop services
        if chrome_sync_app.service_manager.status == "running":
            chrome_sync_app.service_manager.stop_service()
        
        return exit_code
    
    except Exception as e:
        logger.error(f"Failed to start GUI: {str(e)}", exc_info=True)
        
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "ChromeSync Error",
            f"Failed to start ChromeSync GUI: {str(e)}"
        )
        
        return 1
