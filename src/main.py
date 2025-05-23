"""
Main application entry point for ChromeSync.

This module initializes and sets up the ChromeSync application, including
configuration, logging, service management, and data synchronization.
"""

import os
import sys
import argparse
import logging
import threading
from typing import Dict, Any, Optional, List

from config import ConfigManager
from core import (
    ServiceManager, 
    PasswordExtractor, BookmarkExtractor, HistoryExtractor,
    ProfileDetector, PasswordImporter, BookmarkImporter, HistoryImporter
)
from security import AuthenticationManager
from utils import setup_logging, log_exception, is_admin

# Initialize logger
logger = logging.getLogger(__name__)

class ChromeSync:
    """
    Main ChromeSync application class.
    
    This class coordinates the various components of the application,
    including configuration, service management, and synchronization.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the ChromeSync application.
        
        Args:
            config_path: Optional path to the configuration file
        """
        try:
            # Initialize configuration
            self.config_manager = ConfigManager(config_path)
            
            # Initialize logging
            self.logger = setup_logging(config_manager=self.config_manager)
            self.logger.info("ChromeSync application initializing")
            
            # Initialize authentication manager
            self.auth_manager = AuthenticationManager(self.config_manager)
            
            # Initialize service manager
            self.service_manager = ServiceManager(self.config_manager)
            
            # Initialize data extractors
            self.password_extractor = PasswordExtractor(self.config_manager)
            self.bookmark_extractor = BookmarkExtractor(self.config_manager)
            self.history_extractor = HistoryExtractor(self.config_manager)
            
            # Initialize profile detector
            self.profile_detector = ProfileDetector(self.config_manager)
            
            # Initialize data importers
            self.password_importer = PasswordImporter(self.config_manager)
            self.bookmark_importer = BookmarkImporter(self.config_manager)
            self.history_importer = HistoryImporter(self.config_manager)
            
            # State flags
            self.running = False
            self.sync_in_progress = False
            
            # Initialize GUI (will be implemented in Phase 7)
            self.gui = None
            
            self.logger.info("ChromeSync application initialized successfully")
        
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                log_exception(e, logger)
            else:
                logger.error(f"Failed to initialize ChromeSync: {str(e)}")
            
            # Re-raise the exception to the caller
            raise
    
    def start(self):
        """
        Start the ChromeSync application.
        
        This method starts the service manager and other background services.
        """
        try:
            if self.running:
                logger.warning("ChromeSync is already running")
                return
            
            logger.info("Starting ChromeSync")
            
            # Set up service callbacks
            self.service_manager.add_callback('on_chrome_launch', self._on_chrome_launch)
            self.service_manager.add_callback('on_chrome_close', self._on_chrome_close)
            
            # Start service
            if not self.service_manager.start_service():
                logger.error(f"Failed to start service: {self.service_manager.error_message}")
                return
            
            # Perform startup synchronization if configured
            if self.config_manager.get('general', 'sync_on_startup', False):
                logger.info("Performing startup synchronization")
                threading.Thread(target=self.synchronize_all, daemon=True).start()
            
            self.running = True
            logger.info("ChromeSync started successfully")
        
        except Exception as e:
            log_exception(e, logger)
            logger.error(f"Failed to start ChromeSync: {str(e)}")
    
    def stop(self):
        """
        Stop the ChromeSync application.
        
        This method stops the service manager and other background services.
        """
        try:
            if not self.running:
                logger.warning("ChromeSync is not running")
                return
            
            logger.info("Stopping ChromeSync")
            
            # Stop service
            if not self.service_manager.stop_service():
                logger.error(f"Failed to stop service: {self.service_manager.error_message}")
            
            self.running = False
            logger.info("ChromeSync stopped successfully")
        
        except Exception as e:
            log_exception(e, logger)
            logger.error(f"Failed to stop ChromeSync: {str(e)}")
    
    def _on_chrome_launch(self):
        """
        Handle Chrome launch event.
        
        This method is called when Chrome is launched and will
        trigger synchronization if configured.
        """
        logger.info("Chrome launched detected")
        
        # Check if auto-sync is enabled
        if self.config_manager.get('sync', 'auto_sync', {}).get('enabled', True) and \
           self.config_manager.get('sync', 'auto_sync', {}).get('trigger_on_chrome_launch', True):
            
            # Get delay before synchronization
            delay_seconds = self.config_manager.get('sync', 'auto_sync', {}).get('delay_seconds', 5)
            
            logger.info(f"Auto-sync enabled. Scheduling synchronization in {delay_seconds} seconds")
            
            # Schedule synchronization with delay
            def delayed_sync():
                import time
                time.sleep(delay_seconds)
                self.synchronize_all()
            
            threading.Thread(target=delayed_sync, daemon=True).start()
    
    def _on_chrome_close(self):
        """
        Handle Chrome close event.
        
        This method is called when Chrome is closed and will
        trigger synchronization if configured.
        """
        logger.info("Chrome close detected")
        
        # Check if auto-sync is enabled
        if self.config_manager.get('sync', 'auto_sync', {}).get('enabled', True) and \
           self.config_manager.get('sync', 'auto_sync', {}).get('trigger_on_chrome_close', False):
            
            logger.info("Auto-sync enabled. Scheduling synchronization")
            
            # Schedule synchronization
            threading.Thread(target=self.synchronize_all, daemon=True).start()
    
    def synchronize_all(self, progress_callback=None):
        """
        Synchronize all data from Chrome to Zen Browser.
        
        Args:
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            bool: True if synchronization was successful, False otherwise
        """
        if self.sync_in_progress:
            logger.warning("Synchronization already in progress")
            return False
        
        self.sync_in_progress = True
        logger.info("Starting full synchronization")
        
        try:
            # Check if authentication is required for password sync
            if self.auth_manager.require_authentication('password_sync') and \
               not self.auth_manager.validate_token():
                logger.warning("Authentication required for password synchronization")
                if progress_callback:
                    progress_callback(0, 100, "Authentication required for password synchronization")
                self.sync_in_progress = False
                return False
            
            # Initialize results
            results = {
                'passwords': False,
                'bookmarks': False,
                'history': False
            }
            
            # Get sync preferences
            sync_passwords = self.config_manager.get('sync', 'data_types', {}).get('passwords', True)
            sync_bookmarks = self.config_manager.get('sync', 'data_types', {}).get('bookmarks', True)
            sync_history = self.config_manager.get('sync', 'data_types', {}).get('history', True)
            
            # Define progress calculation
            total_steps = sum([sync_passwords, sync_bookmarks, sync_history]) * 2  # Extract + Import
            current_step = 0
            
            def update_progress(step_progress, step_total, message):
                nonlocal current_step
                if progress_callback:
                    progress = int(100 * (current_step + step_progress / step_total) / total_steps)
                    progress_callback(progress, 100, message)
            
            # Get Zen Browser profile
            try:
                zen_profile = self.profile_detector.get_default_profile()
                if not zen_profile:
                    error_msg = "No valid Zen Browser profile found"
                    logger.error(error_msg)
                    if progress_callback:
                        progress_callback(0, 100, error_msg)
                    self.sync_in_progress = False
                    return False
                
                logger.info(f"Using Zen Browser profile: {zen_profile.name}")
                if progress_callback:
                    progress_callback(5, 100, f"Using Zen Browser profile: {zen_profile.name}")
            
            except Exception as e:
                error_msg = f"Failed to detect Zen Browser profile: {str(e)}"
                logger.error(error_msg)
                if progress_callback:
                    progress_callback(0, 100, error_msg)
                self.sync_in_progress = False
                return False
            
            # Synchronize passwords
            if sync_passwords:
                try:
                    logger.info("Extracting passwords from Chrome")
                    if progress_callback:
                        progress_callback(10, 100, "Extracting passwords from Chrome")
                    
                    # Extract passwords
                    passwords = self.password_extractor.extract_passwords(
                        lambda p, t, m: update_progress(p, t, m)
                    )
                    
                    current_step += 1
                    
                    logger.info(f"Extracted {len(passwords)} passwords")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            f"Extracted {len(passwords)} passwords"
                        )
                    
                    # Import passwords
                    logger.info("Importing passwords to Zen Browser")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            "Importing passwords to Zen Browser"
                        )
                    
                    # Import passwords
                    result = self.password_importer.import_passwords(
                        passwords,
                        zen_profile,
                        lambda p, t, m: update_progress(p, t, m)
                    )
                    
                    current_step += 1
                    
                    results['passwords'] = result
                    logger.info(f"Password synchronization {'succeeded' if result else 'failed'}")
                
                except Exception as e:
                    log_exception(e, logger)
                    logger.error(f"Password synchronization failed: {str(e)}")
                    results['passwords'] = False
                    current_step += 2  # Skip extract and import steps
            
            # Synchronize bookmarks
            if sync_bookmarks:
                try:
                    logger.info("Extracting bookmarks from Chrome")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            "Extracting bookmarks from Chrome"
                        )
                    
                    # Extract bookmarks
                    bookmarks = self.bookmark_extractor.extract_bookmarks(
                        lambda p, t, m: update_progress(p, t, m)
                    )
                    
                    current_step += 1
                    
                    logger.info(f"Extracted {len(bookmarks)} bookmark folders")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            f"Extracted {len(bookmarks)} bookmark folders"
                        )
                    
                    # Import bookmarks
                    logger.info("Importing bookmarks to Zen Browser")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            "Importing bookmarks to Zen Browser"
                        )
                    
                    # Import bookmarks
                    result = self.bookmark_importer.import_bookmarks(
                        bookmarks,
                        zen_profile,
                        lambda p, t, m: update_progress(p, t, m)
                    )
                    
                    current_step += 1
                    
                    results['bookmarks'] = result
                    logger.info(f"Bookmark synchronization {'succeeded' if result else 'failed'}")
                
                except Exception as e:
                    log_exception(e, logger)
                    logger.error(f"Bookmark synchronization failed: {str(e)}")
                    results['bookmarks'] = False
                    current_step += 2  # Skip extract and import steps
            
            # Synchronize history
            if sync_history:
                try:
                    # Get history days preference
                    history_days = 30  # Default
                    
                    logger.info(f"Extracting browsing history from Chrome (last {history_days} days)")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            f"Extracting browsing history from Chrome (last {history_days} days)"
                        )
                    
                    # Extract history
                    history_items = self.history_extractor.extract_history(
                        days=history_days,
                        progress_callback=lambda p, t, m: update_progress(p, t, m)
                    )
                    
                    current_step += 1
                    
                    logger.info(f"Extracted {len(history_items)} history items")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            f"Extracted {len(history_items)} history items"
                        )
                    
                    # Import history
                    logger.info("Importing browsing history to Zen Browser")
                    if progress_callback:
                        progress_callback(
                            int(100 * current_step / total_steps),
                            100,
                            "Importing browsing history to Zen Browser"
                        )
                    
                    # Import history
                    result = self.history_importer.import_history(
                        history_items,
                        zen_profile,
                        lambda p, t, m: update_progress(p, t, m)
                    )
                    
                    current_step += 1
                    
                    results['history'] = result
                    logger.info(f"History synchronization {'succeeded' if result else 'failed'}")
                
                except Exception as e:
                    log_exception(e, logger)
                    logger.error(f"History synchronization failed: {str(e)}")
                    results['history'] = False
                    current_step += 2  # Skip extract and import steps
            
            # Determine overall success
            overall_success = any(results.values())
            
            if progress_callback:
                progress_callback(
                    100,
                    100,
                    f"Synchronization {'completed successfully' if overall_success else 'completed with errors'}"
                )
            
            logger.info(f"Synchronization completed. Results: {results}")
            return overall_success
        
        except Exception as e:
            log_exception(e, logger)
            logger.error(f"Synchronization failed: {str(e)}")
            if progress_callback:
                progress_callback(0, 100, f"Synchronization failed: {str(e)}")
            return False
        
        finally:
            self.sync_in_progress = False

def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="ChromeSync - Synchronize Chrome data to Zen Browser")
    
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--background',
        action='store_true',
        help='Run in background mode (no GUI)'
    )
    
    parser.add_argument(
        '--sync',
        action='store_true',
        help='Perform one-time synchronization and exit'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level'
    )
    
    parser.add_argument(
        '--version',
        action='store_true',
        help='Show version information and exit'
    )
    
    return parser.parse_args()

def show_version():
    """
    Show version information.
    """
    version = "1.0.0"  # This should come from a version.py file in a production app
    print(f"ChromeSync version {version}")
    print("Copyright © 2025 Jamie Spinner")
    print("Licensed under MIT License")

def main():
    """
    Main application entry point.
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Show version and exit if requested
    if args.version:
        show_version()
        return 0
    
    try:
        # Initialize ChromeSync
        app = ChromeSync(config_path=args.config)
        
        # Perform one-time synchronization and exit if requested
        if args.sync:
            app.synchronize_all()
            return 0
        
        # Run in background mode (service only)
        if args.background:
            app.start()
            
            # Keep the application running
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                app.stop()
            
            return 0
        
        # Run in GUI mode
        from gui import run_gui
        return run_gui(args.config)
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
