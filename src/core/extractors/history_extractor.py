"""
Chrome history extraction module for ChromeSync.

This module provides functionality to extract browsing history from Google Chrome
and convert it to a format compatible with Zen Browser.
"""

import os
import csv
import time
import shutil
import sqlite3
import logging
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from ...config import ConfigManager
from ...utils.security import secure_delete_file

# Set up logging
logger = logging.getLogger(__name__)

class ChromeHistoryItem:
    """Class representing a Chrome history entry."""
    
    def __init__(self, url: str, title: str, visit_time: int,
                 visit_count: int = 1, last_visit_time: int = 0,
                 typed_count: int = 0, hidden: bool = False):
        """
        Initialize a Chrome history entry.
        
        Args:
            url: The URL of the page
            title: The page title
            visit_time: The visit timestamp (microseconds since 1601-01-01 UTC)
            visit_count: Number of visits to this URL
            last_visit_time: Time of last visit (microseconds since 1601-01-01 UTC)
            typed_count: Number of times the URL was typed
            hidden: Whether the URL is hidden
        """
        self.url = url
        self.title = title
        self.visit_time = visit_time
        self.visit_count = visit_count
        self.last_visit_time = last_visit_time or visit_time
        self.typed_count = typed_count
        self.hidden = hidden
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'url': self.url,
            'title': self.title,
            'visit_time': self.visit_time,
            'visit_count': self.visit_count,
            'last_visit_time': self.last_visit_time,
            'typed_count': self.typed_count,
            'hidden': self.hidden
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChromeHistoryItem':
        """Create from dictionary."""
        return cls(
            url=data.get('url', ''),
            title=data.get('title', ''),
            visit_time=data.get('visit_time', 0),
            visit_count=data.get('visit_count', 1),
            last_visit_time=data.get('last_visit_time', 0),
            typed_count=data.get('typed_count', 0),
            hidden=data.get('hidden', False)
        )
    
    @property
    def datetime(self) -> datetime:
        """Convert Chrome timestamp to datetime object."""
        # Chrome timestamp is microseconds since Jan 1, 1601 UTC
        # To convert to Unix time (seconds since Jan 1, 1970 UTC), we need to:
        # 1. Divide by 1000000 to get seconds
        # 2. Subtract the difference between 1601 and 1970 (11644473600 seconds)
        chrome_to_unix_epoch_diff = 11644473600
        unix_timestamp = self.visit_time / 1000000 - chrome_to_unix_epoch_diff
        
        # Handle negative values (before 1970) or other issues
        if unix_timestamp < 0:
            unix_timestamp = 0
        
        return datetime.fromtimestamp(unix_timestamp)
    
    @property
    def datetime_str(self) -> str:
        """Get formatted date/time string."""
        return self.datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    def __str__(self) -> str:
        """String representation of the history item."""
        return f"{self.title} ({self.url}) - {self.datetime_str}"


class HistoryExtractor:
    """
    Extracts browsing history from Google Chrome.
    
    This class accesses the Chrome History SQLite database and extracts
    browsing history data for import into Zen Browser.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the history extractor.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.chrome_path = config_manager.get('browsers', 'chrome', {}).get('path', '')
        self.user_data_dir = config_manager.get('browsers', 'chrome', {}).get('user_data_dir', '')
        self.profile = config_manager.get('browsers', 'chrome', {}).get('profile', 'Default')
        self.temp_dir = config_manager.get('storage', {}).get('temp_dir', tempfile.gettempdir())
        self.secure_delete = config_manager.get('security', {}).get('secure_delete_temp_files', True)
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def extract_history(self, days: int = 30, max_items: int = 5000, 
                        progress_callback=None) -> List[ChromeHistoryItem]:
        """
        Extract browsing history from Chrome.
        
        Args:
            days: Number of days of history to extract (default: 30)
            max_items: Maximum number of history items to extract (default: 5000)
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            List of ChromeHistoryItem objects
        
        Raises:
            RuntimeError: If extraction fails
        """
        # Locate the History file
        history_path = os.path.join(
            os.path.expandvars(self.user_data_dir),
            self.profile,
            "History"
        )
        
        if not os.path.exists(history_path):
            error_msg = f"History file not found: {history_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        if progress_callback:
            progress_callback(10, 100, "Located Chrome history database")
        
        # Create a temporary copy of the database
        temp_db_path = os.path.join(self.temp_dir, f"chrome_history_{int(time.time())}.db")
        shutil.copy2(history_path, temp_db_path)
        
        try:
            # Calculate the cutoff date in Chrome timestamp format
            cutoff_date = datetime.now() - timedelta(days=days)
            unix_cutoff = int((cutoff_date.timestamp() + 11644473600) * 1000000)
            
            # Connect to the database
            history_items = []
            with sqlite3.connect(temp_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if progress_callback:
                    progress_callback(20, 100, "Connected to history database")
                
                # Get total count for progress reporting
                cursor.execute("""
                    SELECT COUNT(*) FROM urls 
                    JOIN visits ON urls.id = visits.url
                    WHERE visits.visit_time > ? 
                    ORDER BY visits.visit_time DESC
                """, (unix_cutoff,))
                total_count = min(cursor.fetchone()[0], max_items)
                
                if progress_callback:
                    progress_callback(30, 100, f"Found {total_count} history items")
                
                # Get history items
                cursor.execute("""
                    SELECT urls.url, urls.title, visits.visit_time, 
                           urls.visit_count, urls.last_visit_time, 
                           urls.typed_count, urls.hidden
                    FROM urls 
                    JOIN visits ON urls.id = visits.url
                    WHERE visits.visit_time > ? 
                    ORDER BY visits.visit_time DESC
                    LIMIT ?
                """, (unix_cutoff, max_items))
                
                # Process rows
                for i, row in enumerate(cursor.fetchall()):
                    # Report progress
                    if progress_callback and total_count > 0:
                        progress = 30 + int(60 * ((i + 1) / total_count))
                        progress_callback(progress, 100, f"Processing history item {i+1}/{total_count}")
                    
                    # Create history item
                    history_item = ChromeHistoryItem(
                        url=row['url'],
                        title=row['title'] or row['url'],  # Use URL as title if title is empty
                        visit_time=row['visit_time'],
                        visit_count=row['visit_count'],
                        last_visit_time=row['last_visit_time'],
                        typed_count=row['typed_count'],
                        hidden=bool(row['hidden'])
                    )
                    
                    history_items.append(history_item)
            
            if progress_callback:
                progress_callback(95, 100, f"Extracted {len(history_items)} history items")
            
            return history_items
        
        except Exception as e:
            error_msg = f"Failed to extract history: {str(e)}"
            logger.error(error_msg)
            if progress_callback:
                progress_callback(0, 100, error_msg)
            
            raise RuntimeError(error_msg)
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_db_path):
                if self.secure_delete:
                    secure_delete_file(temp_db_path)
                else:
                    os.remove(temp_db_path)
    
    def save_to_sqlite(self, history_items: List[ChromeHistoryItem], output_path: str = None) -> str:
        """
        Save history items to a SQLite database file for import into Zen Browser.
        
        Args:
            history_items: List of ChromeHistoryItem objects
            output_path: Path to save the SQLite file (optional)
        
        Returns:
            Path to the saved SQLite file
        """
        if not output_path:
            output_path = os.path.join(self.temp_dir, f"chrome_history_{int(time.time())}.sqlite")
        
        try:
            # Create a new SQLite database
            with sqlite3.connect(output_path) as conn:
                cursor = conn.cursor()
                
                # Create tables similar to Firefox/Zen Browser structure
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS moz_places (
                        id INTEGER PRIMARY KEY,
                        url TEXT NOT NULL,
                        title TEXT,
                        rev_host TEXT,
                        visit_count INTEGER,
                        hidden INTEGER DEFAULT 0,
                        typed INTEGER DEFAULT 0,
                        frecency INTEGER,
                        last_visit_date INTEGER,
                        guid TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS moz_historyvisits (
                        id INTEGER PRIMARY KEY,
                        from_visit INTEGER,
                        place_id INTEGER,
                        visit_date INTEGER,
                        visit_type INTEGER,
                        session INTEGER
                    )
                """)
                
                # Convert history items to Firefox/Zen Browser format
                for i, item in enumerate(history_items):
                    # Insert place
                    rev_host = ''.join(reversed(item.url.split('/')[2])) + '.'
                    cursor.execute("""
                        INSERT INTO moz_places (
                            url, title, rev_host, visit_count, hidden, typed, 
                            frecency, last_visit_date, guid
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.url,
                        item.title,
                        rev_host,
                        item.visit_count,
                        1 if item.hidden else 0,
                        item.typed_count,
                        100,  # Default frecency
                        item.last_visit_time,
                        f"chrome-import-{i}"  # Generated GUID
                    ))
                    
                    place_id = cursor.lastrowid
                    
                    # Insert visit
                    cursor.execute("""
                        INSERT INTO moz_historyvisits (
                            from_visit, place_id, visit_date, visit_type, session
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        0,  # from_visit (0 for direct navigation)
                        place_id,
                        item.visit_time,
                        1,  # visit_type (1 for LINK)
                        0   # session (0 for default)
                    ))
                
                # Create indices for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS url_idx ON moz_places (url)")
                cursor.execute("CREATE INDEX IF NOT EXISTS place_id_idx ON moz_historyvisits (place_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS visit_date_idx ON moz_historyvisits (visit_date)")
            
            logger.info(f"Saved {len(history_items)} history items to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to save history to SQLite: {str(e)}")
            raise
    
    def save_to_csv(self, history_items: List[ChromeHistoryItem], output_path: str = None) -> str:
        """
        Save history items to a CSV file (for debugging or alternative import).
        
        Args:
            history_items: List of ChromeHistoryItem objects
            output_path: Path to save the CSV file (optional)
        
        Returns:
            Path to the saved CSV file
        """
        if not output_path:
            output_path = os.path.join(self.temp_dir, f"chrome_history_{int(time.time())}.csv")
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'url', 'title', 'visit_time', 'visit_count', 
                    'last_visit_time', 'typed_count', 'hidden'
                ])
                
                # Write history data
                for item in history_items:
                    writer.writerow([
                        item.url,
                        item.title,
                        item.visit_time,
                        item.visit_count,
                        item.last_visit_time,
                        item.typed_count,
                        1 if item.hidden else 0
                    ])
            
            logger.info(f"Saved {len(history_items)} history items to CSV: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to save history to CSV: {str(e)}")
            raise
