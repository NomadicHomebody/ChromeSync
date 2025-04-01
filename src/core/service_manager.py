"""
Service management module for ChromeSync.

This module provides functionality to manage the ChromeSync service,
including auto-startup configuration and service state control.
"""

import os
import sys
import logging
import threading
import subprocess
import winreg
from typing import Optional, Dict, Any, Tuple

from ..config import ConfigManager
from .process_monitor import ChromeProcessMonitor

# Set up logging
logger = logging.getLogger(__name__)

class ServiceManager:
    """
    Manages the ChromeSync service.
    
    This class provides functionality to control the Chrome process monitoring
    service, including starting, stopping, and configuring auto-startup.
    """
    
    # Constants for service status
    STATUS_STOPPED = "stopped"
    STATUS_RUNNING = "running"
    STATUS_ERROR = "error"
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the service manager.
        
        Args:
            config_manager (ConfigManager): Configuration manager instance.
        """
        self.config_manager = config_manager
        self.process_monitor: Optional[ChromeProcessMonitor] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self._status = self.STATUS_STOPPED
        self._error_message = ""
        self._callbacks = {}
    
    @property
    def status(self) -> str:
        """Get the current service status."""
        return self._status
    
    @property
    def error_message(self) -> str:
        """Get the current error message, if any."""
        return self._error_message
    
    def start_service(self) -> bool:
        """
        Start the Chrome process monitoring service.
        
        Returns:
            bool: True if service started successfully, False otherwise.
        """
        # Check if service is already running
        if self._status == self.STATUS_RUNNING:
            logger.warning("Service is already running")
            return True
        
        try:
            # Get Chrome path from configuration
            chrome_path = self.config_manager.get('browsers', 'chrome', {}).get('path', '')
            if not chrome_path:
                self._set_error("Chrome path not configured")
                return False
            
            # Get polling interval from configuration
            polling_interval = self.config_manager.get('sync', 'auto_sync', {}).get('delay_seconds', 5) / 10
            
            # Create process monitor
            self.process_monitor = ChromeProcessMonitor(chrome_path, polling_interval)
            
            # Start monitoring
            self.process_monitor.start()
            
            # Create and start monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_thread_func,
                daemon=True
            )
            self.monitor_thread.start()
            
            # Set status to running
            self._status = self.STATUS_RUNNING
            self._error_message = ""
            
            logger.info("Service started successfully")
            return True
        
        except Exception as e:
            self._set_error(f"Failed to start service: {str(e)}")
            return False
    
    def stop_service(self) -> bool:
        """
        Stop the Chrome process monitoring service.
        
        Returns:
            bool: True if service stopped successfully, False otherwise.
        """
        # Check if service is not running
        if self._status != self.STATUS_RUNNING:
            logger.warning("Service is not running")
            return True
        
        try:
            # Stop process monitor
            if self.process_monitor:
                self.process_monitor.stop()
            
            # Set status to stopped
            self._status = self.STATUS_STOPPED
            self._error_message = ""
            
            logger.info("Service stopped successfully")
            return True
        
        except Exception as e:
            self._set_error(f"Failed to stop service: {str(e)}")
            return False
    
    def restart_service(self) -> bool:
        """
        Restart the Chrome process monitoring service.
        
        Returns:
            bool: True if service restarted successfully, False otherwise.
        """
        logger.info("Restarting service")
        
        # Stop service if running
        if self._status == self.STATUS_RUNNING:
            if not self.stop_service():
                return False
        
        # Start service
        return self.start_service()
    
    def configure_auto_startup(self, enable: bool) -> bool:
        """
        Configure the service to start automatically on system startup.
        
        This uses the Windows Task Scheduler to configure automatic startup.
        
        Args:
            enable (bool): Whether to enable or disable auto-startup.
        
        Returns:
            bool: True if auto-startup was configured successfully, False otherwise.
        """
        app_path = os.path.abspath(sys.argv[0])
        app_dir = os.path.dirname(app_path)
        task_name = "ChromeSync"
        
        try:
            if enable:
                # Create task to start application at login
                command = [
                    "schtasks",
                    "/create",
                    "/tn", task_name,
                    "/tr", f'"{app_path}" --background',
                    "/sc", "onlogon",
                    "/rl", "highest",
                    "/f"  # Force creation if already exists
                ]
                
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode != 0:
                    self._set_error(f"Failed to create startup task: {result.stderr}")
                    return False
                
                logger.info("Auto-startup enabled")
                
                # Update configuration
                self.config_manager.set('general', 'auto_start', True)
                self.config_manager.save()
                
                return True
            
            else:
                # Delete task
                command = [
                    "schtasks",
                    "/delete",
                    "/tn", task_name,
                    "/f"  # Force deletion without confirmation
                ]
                
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Consider success even if task doesn't exist
                if result.returncode != 0 and "The system cannot find the file specified" not in result.stderr:
                    self._set_error(f"Failed to remove startup task: {result.stderr}")
                    return False
                
                logger.info("Auto-startup disabled")
                
                # Update configuration
                self.config_manager.set('general', 'auto_start', False)
                self.config_manager.save()
                
                return True
        
        except Exception as e:
            self._set_error(f"Failed to configure auto-startup: {str(e)}")
            return False
    
    def is_auto_startup_enabled(self) -> bool:
        """
        Check if auto-startup is enabled.
        
        Returns:
            bool: True if auto-startup is enabled, False otherwise.
        """
        task_name = "ChromeSync"
        
        try:
            # Check if task exists
            command = [
                "schtasks",
                "/query",
                "/tn", task_name
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Task exists if return code is 0
            return result.returncode == 0
        
        except Exception:
            return False
    
    def add_callback(self, event_type: str, callback) -> bool:
        """
        Add a callback function for a specific event.
        
        Args:
            event_type (str): Type of event (e.g., 'on_chrome_launch').
            callback (callable): Function to call when the event occurs.
        
        Returns:
            bool: True if callback was added successfully, False otherwise.
        """
        if self.process_monitor:
            return self.process_monitor.add_callback(event_type, callback)
        
        # Store callback for when monitor is created
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        
        if callback not in self._callbacks[event_type]:
            self._callbacks[event_type].append(callback)
            return True
        
        return False
    
    def remove_callback(self, event_type: str, callback) -> bool:
        """
        Remove a callback function for a specific event.
        
        Args:
            event_type (str): Type of event (e.g., 'on_chrome_launch').
            callback (callable): Function to remove from callbacks.
        
        Returns:
            bool: True if callback was removed successfully, False otherwise.
        """
        if self.process_monitor:
            return self.process_monitor.remove_callback(event_type, callback)
        
        # Remove callback from stored callbacks
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            return True
        
        return False
    
    def _monitor_thread_func(self):
        """Thread function to run the process monitor polling loop."""
        if self.process_monitor:
            # Register stored callbacks
            for event_type, callbacks in self._callbacks.items():
                for callback in callbacks:
                    self.process_monitor.add_callback(event_type, callback)
            
            # Run polling loop
            self.process_monitor.run_polling_loop()
    
    def _set_error(self, message: str):
        """Set the error message and update status."""
        logger.error(message)
        self._error_message = message
        self._status = self.STATUS_ERROR
