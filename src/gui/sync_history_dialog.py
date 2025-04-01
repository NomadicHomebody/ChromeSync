"""
Synchronization history dialog for ChromeSync.

This module provides a dialog for viewing the synchronization history.
"""

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QComboBox, QMenu, QAction
)
from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtGui import QIcon, QColor, QCursor

from ..config import ConfigManager
from .utils import get_icon, show_message

# Set up logging
logger = logging.getLogger(__name__)

class SyncHistoryDialog(QDialog):
    """
    Dialog for viewing synchronization history.
    
    This dialog displays the history of synchronizations performed by the
    application, with timestamps, results, and details.
    """
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize the sync history dialog.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Get history file path
        self.history_dir = self.config_manager.get('logs', {}).get(
            'dir',
            os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ChromeSync', 'logs')
        )
        self.history_file = os.path.join(self.history_dir, 'sync_history.json')
        
        # Initialize UI
        self.init_ui()
        
        # Load history
        self.load_history()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Synchronization History")
        self.setWindowIcon(get_icon("history"))
        self.resize(800, 600)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create table widget
        self.table = QTableWidget(0, 5)  # 0 rows, 5 columns
        self.table.setHorizontalHeaderLabels([
            "Date & Time",
            "Type",
            "Status",
            "Duration",
            "Details"
        ])
        
        # Configure table
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(100)
        self.table.verticalHeader().setVisible(False)
        
        # Connect context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add table to layout
        main_layout.addWidget(self.table)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Filter combo boxes
        filter_layout = QHBoxLayout()
        
        # Type filter
        filter_layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Auto", "Manual", "Startup"])
        self.type_filter.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.type_filter)
        
        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Success", "Failed", "Cancelled"])
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.status_filter)
        
        # Add filter layout
        button_layout.addLayout(filter_layout)
        
        # Add spacer
        button_layout.addStretch()
        
        # Create buttons
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setIcon(get_icon("refresh"))
        self.refresh_button.clicked.connect(self.load_history)
        button_layout.addWidget(self.refresh_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.setIcon(get_icon("export"))
        self.export_button.clicked.connect(self.export_history)
        button_layout.addWidget(self.export_button)
        
        self.clear_button = QPushButton("Clear History")
        self.clear_button.setIcon(get_icon("clear"))
        self.clear_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.clear_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.setIcon(get_icon("close"))
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
    
    def load_history(self):
        """Load synchronization history."""
        try:
            # Check if history file exists
            if not os.path.exists(self.history_file):
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
                
                # Create empty history file
                with open(self.history_file, 'w') as f:
                    json.dump([], f)
                
                # Clear table
                self.table.setRowCount(0)
                
                # Log
                logger.debug("Created empty sync history file")
                return
            
            # Load history
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Clear table
            self.table.setRowCount(0)
            
            # Fill table with history items
            for item in history:
                self.add_history_item(item)
            
            # Sort by date (newest first)
            self.table.sortItems(0, Qt.DescendingOrder)
            
            # Apply filters
            self.apply_filters()
            
            # Log
            logger.debug(f"Loaded {len(history)} history items")
        
        except Exception as e:
            logger.error(f"Failed to load sync history: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Error",
                f"Failed to load synchronization history: {str(e)}",
                QMessageBox.Critical
            )
    
    def add_history_item(self, item: Dict[str, Any]):
        """
        Add a history item to the table.
        
        Args:
            item: History item dictionary
        """
        # Get item data
        timestamp = item.get('timestamp', '')
        sync_type = item.get('type', 'Manual')
        status = item.get('status', 'Unknown')
        duration = item.get('duration', 0)
        details = item.get('details', 'No details')
        
        # Format duration
        if isinstance(duration, (int, float)):
            duration_str = f"{duration:.1f}s"
        else:
            duration_str = str(duration)
        
        # Insert row
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Create items
        timestamp_item = QTableWidgetItem(timestamp)
        timestamp_item.setData(Qt.UserRole, item)  # Store full item for reference
        
        type_item = QTableWidgetItem(sync_type)
        status_item = QTableWidgetItem(status)
        duration_item = QTableWidgetItem(duration_str)
        details_item = QTableWidgetItem(details)
        
        # Set item alignment
        timestamp_item.setTextAlignment(Qt.AlignCenter)
        type_item.setTextAlignment(Qt.AlignCenter)
        status_item.setTextAlignment(Qt.AlignCenter)
        duration_item.setTextAlignment(Qt.AlignCenter)
        
        # Set icons
        if sync_type == 'Auto':
            type_item.setIcon(get_icon("sync"))
        elif sync_type == 'Manual':
            type_item.setIcon(get_icon("sync"))
        elif sync_type == 'Startup':
            type_item.setIcon(get_icon("start"))
        
        if status == 'Success':
            status_item.setIcon(get_icon("success"))
            status_item.setForeground(QColor(0, 128, 0))  # Green
        elif status == 'Failed':
            status_item.setIcon(get_icon("error"))
            status_item.setForeground(QColor(255, 0, 0))  # Red
        elif status == 'Cancelled':
            status_item.setIcon(get_icon("cancel"))
            status_item.setForeground(QColor(255, 128, 0))  # Orange
        
        # Add items to table
        self.table.setItem(row, 0, timestamp_item)
        self.table.setItem(row, 1, type_item)
        self.table.setItem(row, 2, status_item)
        self.table.setItem(row, 3, duration_item)
        self.table.setItem(row, 4, details_item)
    
    def apply_filters(self):
        """Apply filters to the table."""
        # Get filter values
        type_filter = self.type_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        # Hide rows that don't match the filters
        for row in range(self.table.rowCount()):
            # Get row values
            type_value = self.table.item(row, 1).text()
            status_value = self.table.item(row, 2).text()
            
            # Check if row matches filters
            type_match = type_filter == 'All' or type_value == type_filter
            status_match = status_filter == 'All' or status_value == status_filter
            
            # Show or hide row
            self.table.setRowHidden(row, not (type_match and status_match))
    
    def export_history(self):
        """Export synchronization history to a file."""
        try:
            # Ask for file path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Synchronization History",
                os.path.join(os.path.expanduser('~'), 'Documents', 'sync_history.json'),
                "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Load history
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Export based on file extension
            if file_path.lower().endswith('.json'):
                # Export as JSON
                with open(file_path, 'w') as f:
                    json.dump(history, f, indent=2)
            
            elif file_path.lower().endswith('.csv'):
                # Export as CSV
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    writer.writerow(['Timestamp', 'Type', 'Status', 'Duration', 'Details'])
                    
                    # Write data
                    for item in history:
                        writer.writerow([
                            item.get('timestamp', ''),
                            item.get('type', ''),
                            item.get('status', ''),
                            item.get('duration', ''),
                            item.get('details', '')
                        ])
            
            else:
                # Default to JSON
                with open(file_path, 'w') as f:
                    json.dump(history, f, indent=2)
            
            # Log
            logger.info(f"Exported sync history to {file_path}")
            
            # Show success message
            show_message(
                self,
                "Export Successful",
                f"Synchronization history has been exported to:\n{file_path}",
                QMessageBox.Information
            )
        
        except Exception as e:
            logger.error(f"Failed to export sync history: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Export Error",
                f"Failed to export synchronization history: {str(e)}",
                QMessageBox.Critical
            )
    
    def clear_history(self):
        """Clear synchronization history."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear the synchronization history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Clear history file
            with open(self.history_file, 'w') as f:
                json.dump([], f)
            
            # Clear table
            self.table.setRowCount(0)
            
            # Log
            logger.info("Cleared sync history")
            
            # Show success message
            show_message(
                self,
                "Clear Successful",
                "Synchronization history has been cleared.",
                QMessageBox.Information
            )
        
        except Exception as e:
            logger.error(f"Failed to clear sync history: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Clear Error",
                f"Failed to clear synchronization history: {str(e)}",
                QMessageBox.Critical
            )
    
    def show_context_menu(self, position):
        """
        Show context menu for the table.
        
        Args:
            position: Position to show the menu
        """
        # Get selected row
        indexes = self.table.selectedIndexes()
        if not indexes:
            return
        
        # Create menu
        menu = QMenu(self)
        
        # Create actions
        view_details_action = QAction("View Details", self)
        view_details_action.triggered.connect(self.view_details)
        menu.addAction(view_details_action)
        
        menu.addSeparator()
        
        delete_action = QAction("Delete Entry", self)
        delete_action.triggered.connect(self.delete_entry)
        menu.addAction(delete_action)
        
        # Show menu
        menu.exec_(QCursor.pos())
    
    def view_details(self):
        """View details of the selected history entry."""
        # Get selected row
        indexes = self.table.selectedIndexes()
        if not indexes:
            return
        
        # Get item data
        row = indexes[0].row()
        item = self.table.item(row, 0).data(Qt.UserRole)
        
        # Format details
        details = f"""
        <h3>Synchronization Details</h3>
        <p><b>Date & Time:</b> {item.get('timestamp', 'Unknown')}</p>
        <p><b>Type:</b> {item.get('type', 'Unknown')}</p>
        <p><b>Status:</b> {item.get('status', 'Unknown')}</p>
        <p><b>Duration:</b> {item.get('duration', 0):.1f} seconds</p>
        <p><b>Details:</b> {item.get('details', 'No details')}</p>
        """
        
        # Add data types
        data_types = item.get('data_types', {})
        if data_types:
            details += "<p><b>Data Types:</b></p><ul>"
            for key, value in data_types.items():
                details += f"<li>{key.capitalize()}: {'Yes' if value else 'No'}</li>"
            details += "</ul>"
        
        # Add errors
        errors = item.get('errors', [])
        if errors:
            details += "<p><b>Errors:</b></p><ul>"
            for error in errors:
                details += f"<li>{error}</li>"
            details += "</ul>"
        
        # Show details
        QMessageBox.information(self, "Synchronization Details", details)
    
    def delete_entry(self):
        """Delete the selected history entry."""
        # Get selected row
        indexes = self.table.selectedIndexes()
        if not indexes:
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Delete Entry",
            "Are you sure you want to delete this history entry?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Get row and item
            row = indexes[0].row()
            item = self.table.item(row, 0).data(Qt.UserRole)
            
            # Load history
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Find and remove item
            for i, history_item in enumerate(history):
                if (history_item.get('timestamp') == item.get('timestamp') and
                        history_item.get('type') == item.get('type') and
                        history_item.get('status') == item.get('status')):
                    history.pop(i)
                    break
            
            # Save history
            with open(self.history_file, 'w') as f:
                json.dump(history, f)
            
            # Remove row from table
            self.table.removeRow(row)
            
            # Log
            logger.info("Deleted sync history entry")
        
        except Exception as e:
            logger.error(f"Failed to delete sync history entry: {str(e)}")
            
            # Show error message
            show_message(
                self,
                "Delete Error",
                f"Failed to delete history entry: {str(e)}",
                QMessageBox.Critical
            )
