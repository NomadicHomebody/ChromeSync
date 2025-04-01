"""
Worker class for background synchronization.

This module provides a worker class that can be used to perform synchronization
in the background, without blocking the GUI.
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QMutex, QWaitCondition

from ..config import ConfigManager

# Set up logging
logger = logging.getLogger(__name__)

class SyncThread(QThread):
    """Thread that performs synchronization."""
    
    # Signal for progress updates
    progress = pyqtSignal(int, int, str)
    
    def __init__(self, app, parent=None):
        """
        Initialize the sync thread.
        
        Args:
            app: ChromeSyncApp instance
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.app = app
        self.cancelled = False
        self.mutex = QMutex()
        self.condition = QWaitCondition()
    
    def progress_callback(self, current: int, total: int, message: str):
        """
        Callback for reporting progress.
        
        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message
        """
        # Emit progress signal
        self.progress.emit(current, total, message)
        
        # Check if cancelled
        self.mutex.lock()
        cancelled = self.cancelled
        self.mutex.unlock()
        
        if cancelled:
            # Raise exception to cancel synchronization
            raise Exception("Synchronization cancelled by user")
    
    def run(self):
        """Run the synchronization thread."""
        try:
            # Synchronize
            result = self.app.synchronize(self.progress_callback)
            
            # Update last sync time
            if result:
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.app.config_manager.set('sync', 'last_sync_time', now)
                self.app.config_manager.save()
            
            # Return result
            return result
        
        except Exception as e:
            logger.error(f"Synchronization thread error: {str(e)}")
            return False
    
    def cancel(self):
        """Cancel the synchronization."""
        self.mutex.lock()
        self.cancelled = True
        self.mutex.unlock()
        
        # Wake up the thread if it's waiting
        self.condition.wakeAll()

class SyncWorker(QObject):
    """
    Worker for background synchronization.
    
    This class provides a worker that can be used to perform synchronization
    in the background, without blocking the GUI.
    """
    
    # Signals for progress and completion
    progress = pyqtSignal(int, int, str)
    completed = pyqtSignal(bool)
    
    def __init__(self, app, parent=None):
        """
        Initialize the sync worker.
        
        Args:
            app: ChromeSyncApp instance
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.app = app
        self.sync_thread = None
    
    def is_running(self) -> bool:
        """
        Check if a synchronization is running.
        
        Returns:
            bool: True if a synchronization is running, False otherwise
        """
        return self.sync_thread is not None and self.sync_thread.isRunning()
    
    def start(self):
        """Start a synchronization."""
        # Check if already running
        if self.is_running():
            logger.warning("Sync already in progress")
            return
        
        # Create and start sync thread
        self.sync_thread = SyncThread(self.app)
        self.sync_thread.progress.connect(self.on_progress)
        self.sync_thread.finished.connect(self.on_finished)
        self.sync_thread.start()
    
    def cancel(self):
        """Cancel the current synchronization."""
        # Check if running
        if not self.is_running():
            return
        
        # Cancel sync thread
        self.sync_thread.cancel()
    
    @pyqtSlot(int, int, str)
    def on_progress(self, current: int, total: int, message: str):
        """
        Handle progress update.
        
        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message
        """
        # Emit progress signal
        self.progress.emit(current, total, message)
    
    @pyqtSlot()
    def on_finished(self):
        """Handle sync thread completion."""
        # Get result
        result = self.sync_thread.result()
        
        # Clean up thread
        self.sync_thread.deleteLater()
        self.sync_thread = None
        
        # Emit completed signal
        self.completed.emit(result)
