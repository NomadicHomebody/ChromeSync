"""
GUI utilities for ChromeSync.

This module provides utility functions for the ChromeSync GUI,
including icon loading, stylesheet loading, and message boxes.
"""

import os
import logging
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize

# Set up logging
logger = logging.getLogger(__name__)

# Icon cache
_icon_cache = {}

def get_icon(name: str) -> QIcon:
    """
    Get an icon by name.
    
    Args:
        name: Name of the icon
    
    Returns:
        QIcon: Icon object
    """
    global _icon_cache
    
    # Check if icon is already cached
    if name in _icon_cache:
        return _icon_cache[name]
    
    # Define icon paths
    icon_paths = {
        # Application icons
        'app_icon': 'resources/icons/app_icon.png',
        
        # Action icons
        'settings': 'resources/icons/settings.png',
        'logs': 'resources/icons/logs.png',
        'about': 'resources/icons/about.png',
        'sync': 'resources/icons/sync.png',
        'cancel': 'resources/icons/cancel.png',
        'start': 'resources/icons/start.png',
        'stop': 'resources/icons/stop.png',
        'refresh': 'resources/icons/refresh.png',
        'export': 'resources/icons/export.png',
        'import': 'resources/icons/import.png',
        'close': 'resources/icons/close.png',
        'clear': 'resources/icons/clear.png',
        'folder': 'resources/icons/folder.png',
        'history': 'resources/icons/history.png',
        
        # Status icons
        'success': 'resources/icons/success.png',
        'error': 'resources/icons/error.png',
        'warning': 'resources/icons/warning.png',
        'info': 'resources/icons/info.png',
        
        # Browser icons
        'chrome': 'resources/icons/chrome.png',
        'zen': 'resources/icons/zen.png',
    }
    
    # Get icon path
    icon_path = icon_paths.get(name, '')
    
    # Check if icon exists
    if icon_path and os.path.exists(icon_path):
        # Load icon
        icon = QIcon(icon_path)
    else:
        # Log missing icon file
        logger.debug(f"Icon file not found: {icon_path}, using system fallback")
        
        # Use fallback icon from Qt
        icon = QIcon.fromTheme(name)
        
        # If no theme icon, use system icon
        if icon.isNull():
            icon = _get_system_icon(name)
    
    # Cache icon
    _icon_cache[name] = icon
    
    return icon

def _get_system_icon(name: str) -> QIcon:
    """
    Get a system icon by name.
    
    Args:
        name: Name of the icon
    
    Returns:
        QIcon: Icon object
    """
    # Map names to standard style icons
    from PyQt5.QtWidgets import QStyle, QApplication
    
    style = QApplication.style()
    icon_map = {
        'settings': QStyle.SP_FileDialogDetailedView,
        'logs': QStyle.SP_FileIcon,
        'about': QStyle.SP_MessageBoxInformation,
        'sync': QStyle.SP_BrowserReload,
        'cancel': QStyle.SP_DialogCancelButton,
        'start': QStyle.SP_MediaPlay,
        'stop': QStyle.SP_MediaStop,
        'refresh': QStyle.SP_BrowserReload,
        'export': QStyle.SP_FileLinkIcon,
        'import': QStyle.SP_FileLinkIcon,
        'close': QStyle.SP_DialogCloseButton,
        'clear': QStyle.SP_DialogResetButton,
        'folder': QStyle.SP_DirIcon,
        'history': QStyle.SP_FileDialogBack,
        'success': QStyle.SP_DialogApplyButton,
        'error': QStyle.SP_MessageBoxCritical,
        'warning': QStyle.SP_MessageBoxWarning,
        'info': QStyle.SP_MessageBoxInformation
    }
    
    # Get standard icon
    standard_icon = icon_map.get(name, QStyle.SP_CustomBase)
    if standard_icon != QStyle.SP_CustomBase:
        return style.standardIcon(standard_icon)
    
    # Return empty icon
    return QIcon()

def get_style_sheet(theme: str) -> str:
    """
    Get stylesheet for the specified theme.
    
    Args:
        theme: Theme name ('light', 'dark')
    
    Returns:
        str: Stylesheet CSS
    """
    # Define stylesheets
    stylesheets = {
        'light': """
            QMainWindow, QDialog {
                background-color: #f0f0f0;
            }
            QWidget {
                color: #202020;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: #202020;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 3px;
            }
            QGroupBox {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin-top: 1em;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QProgressBar {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2080c0;
            }
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: #f8f8f8;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                border: 1px solid #c0c0c0;
                border-bottom-color: #c0c0c0;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 5px 10px;
            }
            QTabBar::tab:selected {
                background-color: #f8f8f8;
                border-bottom-color: #f8f8f8;
            }
            QTableWidget {
                alternate-background-color: #e8e8e8;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 4px;
                border: 1px solid #c0c0c0;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
        """,
        'dark': """
            QMainWindow, QDialog {
                background-color: #2c2c2c;
            }
            QWidget {
                color: #f0f0f0;
            }
            QPushButton {
                background-color: #505050;
                color: #f0f0f0;
                border: 1px solid #606060;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #606060;
                border-radius: 4px;
                padding: 3px;
                background-color: #404040;
                color: #f0f0f0;
            }
            QGroupBox {
                border: 1px solid #606060;
                border-radius: 4px;
                margin-top: 1em;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QProgressBar {
                border: 1px solid #606060;
                border-radius: 4px;
                text-align: center;
                color: #f0f0f0;
                background-color: #404040;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
            QTabWidget::pane {
                border: 1px solid #606060;
                background-color: #383838;
            }
            QTabBar::tab {
                background-color: #505050;
                border: 1px solid #606060;
                border-bottom-color: #606060;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 5px 10px;
            }
            QTabBar::tab:selected {
                background-color: #383838;
                border-bottom-color: #383838;
            }
            QTableWidget {
                alternate-background-color: #383838;
                background-color: #2c2c2c;
                color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #505050;
                padding: 4px;
                border: 1px solid #606060;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QScrollBar:vertical {
                border: 1px solid #606060;
                background: #404040;
                width: 15px;
                margin: 15px 0 15px 0;
            }
            QScrollBar::handle:vertical {
                background: #606060;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical {
                border: 1px solid #606060;
                background: #505050;
                height: 15px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical {
                border: 1px solid #606060;
                background: #505050;
                height: 15px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QScrollBar:horizontal {
                border: 1px solid #606060;
                background: #404040;
                height: 15px;
                margin: 0 15px 0 15px;
            }
            QScrollBar::handle:horizontal {
                background: #606060;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal {
                border: 1px solid #606060;
                background: #505050;
                width: 15px;
                subcontrol-position: right;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:horizontal {
                border: 1px solid #606060;
                background: #505050;
                width: 15px;
                subcontrol-position: left;
                subcontrol-origin: margin;
            }
        """
    }
    
    # Return the stylesheet for the specified theme
    return stylesheets.get(theme, '')

def show_message(parent: QWidget, title: str, message: str, icon: QMessageBox.Icon) -> None:
    """
    Show a message box.
    
    Args:
        parent: Parent widget
        title: Message box title
        message: Message box message
        icon: Message box icon
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(icon)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()
