"""
Chrome process monitoring module.

This module provides functionality to detect and monitor Chrome browser processes.
"""

import os
import time
import logging
import psutil
from typing import List, Optional, Callable, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

class ChromeProcessMonitor:
    """
    Monitors Chrome browser processes.
    
    This class provides the ability to detect when Chrome is launched or closed,
    and trigger callback functions accordingly.
    """
    
    def __init__(self, chrome_path: str, polling_interval: float = 1.0):
        """
        Initialize the Chrome process monitor.
        
        Args:
            chrome_path (str): Path to the Chrome executable.
            polling_interval (float): Interval in seconds for checking processes.
        """
        self.chrome_path = chrome_path
        self.polling_interval = polling_interval
        self.running = False
        self.chrome_detected = False
        self._callbacks: Dict[str, List[Callable[..., Any]]] = {
            'on_chrome_launch': [],
            'on_chrome_close': []
        }
    
    def add_callback(self, event_type: str, callback: Callable[..., Any]):
        """
        Add a callback function for a specific event.
        
        Args:
            event_type (str): Type of event ('on_chrome_launch' or 'on_chrome_close').
            callback (Callable): Function to call when the event occurs.
        
        Returns:
            bool: True if callback was added successfully, False otherwise.
        """
        if event_type not in self._callbacks:
            logger.error(f"Invalid event type: {event_type}")
            return False
        
        if callback not in self._callbacks[event_type]:
            self._callbacks[event_type].append(callback)
            logger.debug(f"Added callback for {event_type}: {callback.__name__}")
            return True
        
        return False
    
    def remove_callback(self, event_type: str, callback: Callable[..., Any]):
        """
        Remove a callback function for a specific event.
        
        Args:
            event_type (str): Type of event ('on_chrome_launch' or 'on_chrome_close').
            callback (Callable): Function to remove from callbacks.
        
        Returns:
            bool: True if callback was removed successfully, False otherwise.
        """
        if event_type not in self._callbacks:
            logger.error(f"Invalid event type: {event_type}")
            return False
        
        if callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            logger.debug(f"Removed callback for {event_type}: {callback.__name__}")
            return True
        
        return False
    
    def is_chrome_running(self) -> bool:
        """
        Check if Chrome is currently running.
        
        Returns:
            bool: True if Chrome is running, False otherwise.
        """
        chrome_exes = ['chrome.exe']
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                # Check if the process name matches Chrome
                if proc.info['name'] and proc.info['name'].lower() in chrome_exes:
                    # Verify it's the correct Chrome installation if exe path is available
                    if proc.info['exe'] and os.path.normpath(self.chrome_path) in os.path.normpath(proc.info['exe']):
                        return True
                    # If exe path isn't available but name matches, consider it Chrome
                    elif not proc.info['exe']:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return False
    
    def _trigger_callbacks(self, event_type: str):
        """
        Trigger all callbacks for a specific event.
        
        Args:
            event_type (str): Type of event to trigger callbacks for.
        """
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in callback {callback.__name__}: {str(e)}")
    
    def start(self):
        """
        Start monitoring for Chrome processes.
        """
        if self.running:
            logger.warning("Process monitor is already running")
            return
        
        self.running = True
        self.chrome_detected = self.is_chrome_running()
        
        logger.info("Chrome process monitor started")
        if self.chrome_detected:
            logger.info("Chrome was already running when monitor started")
    
    def stop(self):
        """
        Stop monitoring for Chrome processes.
        """
        self.running = False
        logger.info("Chrome process monitor stopped")
    
    def poll_once(self):
        """
        Check for Chrome processes once and trigger callbacks if needed.
        
        Returns:
            bool: True if Chrome status changed, False otherwise.
        """
        if not self.running:
            return False
        
        chrome_running = self.is_chrome_running()
        
        # If state changed from not running to running
        if chrome_running and not self.chrome_detected:
            logger.info("Chrome launched")
            self.chrome_detected = True
            self._trigger_callbacks('on_chrome_launch')
            return True
        
        # If state changed from running to not running
        elif not chrome_running and self.chrome_detected:
            logger.info("Chrome closed")
            self.chrome_detected = False
            self._trigger_callbacks('on_chrome_close')
            return True
        
        return False
    
    def run_polling_loop(self):
        """
        Run the monitoring loop continuously until stopped.
        """
        self.start()
        
        try:
            while self.running:
                self.poll_once()
                time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            logger.info("Process monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Error in process monitoring loop: {str(e)}")
        finally:
            self.stop()
