"""
Log viewer dialog for ChromeSync.

This module provides a dialog for viewing application logs.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QComboBox, QFileDialog, QCheckBox,
    QDialogButtonBox, QApplication, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor

from ..config import ConfigManager
from .utils import get_icon, show_message

# Set up logging
logger = logging.getLogger(__name__)

class LogViewerDialog(QDialog):
    """
    Dialog for viewing application logs.
    
    This dialog displays the contents of log files and provides
    options for filtering and refreshing log data.
    """
    
    # Colors for different log levels
    LOG_LEVEL_COLORS = {
        'DEBUG': QColor(150, 150, 150),  # Gray
        'INFO': QColor(0, 0, 0),         # Black
        'WARNING': QColor(255, 165, 0),  # Orange
        'ERROR': QColor(255, 0, 0),      # Red
        'CRITICAL': QColor(153, 0, 0)    # Dark Red
    }
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize the log viewer dialog.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Get log directory
        self.log_dir = self.config_manager.get('logs', {}).get(
            'dir',
            os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ChromeSync', 'logs')
        )
        
        # Auto-refresh timer
        self.refresh_timer = None
        
        # Set up the UI
        self.init_ui()
        
        # Load log files
        self.load_log_files()
        
        # Load selected log file
        self.on_log_file_changed(0)
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Log Viewer")
        self.setWindowIcon(get_icon("logs"))
        self.resize(800, 600)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create top controls
        top_layout = QHBoxLayout()
        
        # Create log file combo box
        self.log_file_label = QLabel("Log File:")
        self.log_file_combo = QComboBox()
        self.log_file_combo.setMinimumWidth(300)
        self.log_file_combo.currentIndexChanged.connect(self.on_log_file_changed)
        
        top_layout.addWidget(self.log_file_label)
        top_layout.addWidget(self.log_file_combo)
        
        # Add spacer
        top_layout.addStretch()
        
        # Create level filter combo box
        self.level_label = QLabel("Filter Level:")
        self.level_combo = QComboBox()
        self.level_combo.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentIndexChanged.connect(self.apply_filters)
        
        top_layout.addWidget(self.level_label)
        top_layout.addWidget(self.level_combo)
        
        main_layout.addLayout(top_layout)
        
        # Create text edit for displaying logs
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text_edit.setFont(QFont("Courier New", 10))
        
        main_layout.addWidget(self.log_text_edit)
        
        # Create bottom controls
        bottom_layout = QHBoxLayout()
        
        # Create search controls
        self.search_label = QLabel("Search:")
        self.search_text_edit = QTextEdit()
        self.search_text_edit.setMaximumHeight(28)
        self.search_text_edit.textChanged.connect(self.apply_filters)
        
        self.case_sensitive_checkbox = QCheckBox("Case Sensitive")
        self.case_sensitive_checkbox.toggled.connect(self.apply_filters)
        
        bottom_layout.addWidget(self.search_label)
        bottom_layout.addWidget(self.search_text_edit)
        bottom_layout.addWidget(self.case_sensitive_checkbox)
        
        # Add spacer
        bottom_layout.addStretch()
        
        # Create auto-refresh checkbox and refresh button
        self.auto_refresh_checkbox = QCheckBox("Auto-Refresh")
        self.auto_refresh_checkbox.toggled.connect(self.on_auto_refresh_toggled)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setIcon(get_icon("refresh"))
        self.refresh_button.clicked.connect(self.on_refresh)
        
        bottom_layout.addWidget(self.auto_refresh_checkbox)
        bottom_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(bottom_layout)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Create buttons
        self.open_dir_button = QPushButton("Open Log Directory")
        self.open_dir_button.setIcon(get_icon("folder"))
        self.open_dir_button.clicked.connect(self.on_open_dir)
        
        self.export_button = QPushButton("Export")
        self.export_button.setIcon(get_icon("export"))
        self.export_button.clicked.connect(self.on_export)
        
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.setIcon(get_icon("clear"))
        self.clear_button.clicked.connect(self.on_clear)
        
        self.close_button = QPushButton("Close")
        self.close_button.setIcon(get_icon("close"))
        self.close_button.clicked.connect(self.accept)
        
        # Add buttons to layout
        button_layout.addWidget(self.open_dir_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
    
    def load_log_files(self):
        """Load available log files."""
        try:
            # Check if log directory exists
            if not os.path.exists(self.log_dir):
                logger.warning(f"Log directory not found: {self.log_dir}")
                return
            
            # Get log files
            log_files = []
            for file in os.listdir(self.log_dir):
                if file.endswith('.log'):
                    log_files.append(file)
            
            # Sort log files (main log first, then by name)
            log_files.sort()
            if 'chromesync.log' in log_files:
                log_files.remove('chromesync.log')
                log_files.insert(0, 'chromesync.log')
            if 'chromesync_error.log' in log_files:
                log_files.remove('chromesync_error.log')
                log_files.insert(1, 'chromesync_error.log')
            
            # Update combo box
            self.log_file_combo.clear()
            for file in log_files:
                self.log_file_combo.addItem(file)
            
            logger.debug(f"Found {len(log_files)} log files")
        
        except Exception as e:
            logger.error(f"Failed to load log files: {str(e)}")
    
    def on_log_file_changed(self, index):
        """
        Handle log file selection change.
        
        Args:
            index: Index of the selected log file
        """
        if index < 0:
            return
        
        # Get selected log file
        log_file = self.log_file_combo.currentText()
        
        # Load log file
        self.load_log_file(log_file)
    
    def load_log_file(self, log_file: str):
        """
        Load and display a log file.
        
        Args:
            log_file: Name of the log file to load
        """
        try:
            # Get full path
            log_path = os.path.join(self.log_dir, log_file)
            
            # Check if file exists
            if not os.path.exists(log_path):
                self.log_text_edit.clear()
                self.log_text_edit.setPlainText(f"Log file not found: {log_path}")
                return
            
            # Load file contents
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Display log content
            self.log_text_edit.clear()
            
            # Parse and colorize log entries
            self.parse_and_display_log(log_content)
            
            # Scroll to the end
            cursor = self.log_text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text_edit.setTextCursor(cursor)
            
            logger.debug(f"Loaded log file: {log_file}")
        
        except Exception as e:
            logger.error(f"Failed to load log file: {str(e)}")
            self.log_text_edit.clear()
            self.log_text_edit.setPlainText(f"Error loading log file: {str(e)}")
    
    def parse_and_display_log(self, log_content: str):
        """
        Parse and display log content with coloring.
        
        Args:
            log_content: Raw log content to parse and display
        """
        # Get current text edit cursor
        cursor = self.log_text_edit.textCursor()
        
        # Split log content into lines
        lines = log_content.splitlines()
        
        # Get filter settings
        filter_level = self.level_combo.currentText()
        search_text = self.search_text_edit.toPlainText()
        case_sensitive = self.case_sensitive_checkbox.isChecked()
        
        # Process each line
        for line in lines:
            # Check if line matches level filter
            if filter_level != "All" and filter_level not in line:
                continue
            
            # Check if line matches search filter
            if search_text:
                if case_sensitive:
                    if search_text not in line:
                        continue
                else:
                    if search_text.lower() not in line.lower():
                        continue
            
            # Set color based on log level
            color = QColor(0, 0, 0)  # Default black
            for level, level_color in self.LOG_LEVEL_COLORS.items():
                if level in line:
                    color = level_color
                    break
            
            # Set text color for this line
            cursor.insertText(line + '\n', self.get_colored_format(color))
    
    def get_colored_format(self, color: QColor):
        """
        Get a text format with the specified color.
        
        Args:
            color: Text color
        
        Returns:
            QTextCharFormat: Text format with the specified color
        """
        from PyQt5.QtGui import QTextCharFormat
        format = QTextCharFormat()
        format.setForeground(color)
        return format
    
    def apply_filters(self):
        """Apply filters to the log display."""
        # Reload the current log file with filters
        log_file = self.log_file_combo.currentText()
        if log_file:
            self.load_log_file(log_file)
    
    def on_refresh(self):
        """Handle the Refresh button click."""
        # Reload the current log file
        log_file = self.log_file_combo.currentText()
        if log_file:
            self.load_log_file(log_file)
    
    def on_auto_refresh_toggled(self, checked: bool):
        """
        Handle auto-refresh checkbox toggle.
        
        Args:
            checked: Whether auto-refresh is enabled
        """
        if checked:
            # Create timer if it doesn't exist
            if not self.refresh_timer:
                self.refresh_timer = QTimer(self)
                self.refresh_timer.timeout.connect(self.on_refresh)
            
            # Start timer
            self.refresh_timer.start(2000)  # Refresh every 2 seconds
        else:
            # Stop timer
            if self.refresh_timer:
                self.refresh_timer.stop()
    
    def on_open_dir(self):
        """Handle the Open Log Directory button click."""
        try:
            # Create directory if it doesn't exist
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
                logger.info(f"Created log directory: {self.log_dir}")
            
            # Open directory
            import subprocess
            subprocess.Popen(f'explorer "{self.log_dir}"')
            
            logger.debug(f"Opened log directory: {self.log_dir}")
        
        except Exception as e:
            logger.error(f"Failed to open log directory: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Error",
                f"Failed to open log directory: {str(e)}",
                QMessageBox.Critical
            )
    
    def on_export(self):
        """Handle the Export button click."""
        # Get current log file
        log_file = self.log_file_combo.currentText()
        if not log_file:
            return
        
        # Ask for file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            os.path.join(os.path.expanduser('~'), 'Documents', log_file),
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get full path of source file
                log_path = os.path.join(self.log_dir, log_file)
                
                # Copy file
                shutil.copy2(log_path, file_path)
                
                logger.info(f"Exported log file to {file_path}")
                
                # Show success message
                show_message(
                    self,
                    "Export Successful",
                    f"Log file has been exported to:\n{file_path}",
                    QMessageBox.Information
                )
            
            except Exception as e:
                logger.error(f"Failed to export log file: {str(e)}")
                
                # Show error message
                show_message(
                    self,
                    "Export Error",
                    f"Failed to export log file: {str(e)}",
                    QMessageBox.Critical
                )
    
    def on_clear(self):
        """Handle the Clear Log button click."""
        # Get current log file
        log_file = self.log_file_combo.currentText()
        if not log_file:
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Clear Log",
            f"Are you sure you want to clear the log file?\n{log_file}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Get full path
                log_path = os.path.join(self.log_dir, log_file)
                
                # Clear file
                with open(log_path, 'w') as f:
                    pass
                
                logger.info(f"Cleared log file: {log_file}")
                
                # Reload file
                self.load_log_file(log_file)
                
                # Show success message
                show_message(
                    self,
                    "Log Cleared",
                    f"Log file has been cleared:\n{log_file}",
                    QMessageBox.Information
                )
            
            except Exception as e:
                logger.error(f"Failed to clear log file: {str(e)}")
                
                # Show error message
                show_message(
                    self,
                    "Error",
                    f"Failed to clear log file: {str(e)}",
                    QMessageBox.Critical
                )
    
    def closeEvent(self, event):
        """
        Handle dialog close event.
        
        Args:
            event: Close event
        """
        # Stop refresh timer
        if self.refresh_timer and self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        # Accept event
        event.accept()
