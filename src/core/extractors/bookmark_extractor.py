"""
Chrome bookmark extraction module for ChromeSync.

This module provides functionality to extract bookmarks from Google Chrome
and convert them to a format compatible with Zen Browser.
"""

import os
import json
import time
import logging
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ...config import ConfigManager

# Set up logging
logger = logging.getLogger(__name__)

class ChromeBookmark:
    """Class representing a Chrome bookmark entry."""
    
    def __init__(self, title: str, url: str = "", 
                 date_added: int = 0, date_modified: int = 0,
                 folder_path: List[str] = None):
        """
        Initialize a Chrome bookmark entry.
        
        Args:
            title: The bookmark title
            url: The bookmark URL (empty for folders)
            date_added: The creation timestamp (microseconds since 1601-01-01 UTC)
            date_modified: The modification timestamp (microseconds since 1601-01-01 UTC)
            folder_path: List of parent folder names
        """
        self.title = title
        self.url = url
        self.date_added = date_added
        self.date_modified = date_modified
        self.folder_path = folder_path or []
        self.is_folder = not bool(url)
        self.children: List[ChromeBookmark] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'title': self.title,
            'url': self.url,
            'date_added': self.date_added,
            'date_modified': self.date_modified,
            'folder_path': self.folder_path,
            'is_folder': self.is_folder
        }
        
        if self.is_folder:
            result['children'] = [child.to_dict() for child in self.children]
        
        return result

    def add_child(self, bookmark: 'ChromeBookmark'):
        """Add a child bookmark (for folders)."""
        self.children.append(bookmark)

    @property
    def full_path(self) -> str:
        """Get the full folder path as a string."""
        return " > ".join(self.folder_path)

    def __str__(self) -> str:
        """String representation of the bookmark."""
        path_str = f" ({self.full_path})" if self.folder_path else ""
        return f"{self.title}{path_str}" + (f" - {self.url}" if self.url else " [Folder]")


class BookmarkExtractor:
    """
    Extracts bookmarks from Google Chrome.
    
    This class reads the Chrome Bookmarks JSON file and converts it to
    a format compatible with Zen Browser.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the bookmark extractor.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.chrome_path = config_manager.get('browsers', 'chrome', {}).get('path', '')
        self.user_data_dir = config_manager.get('browsers', 'chrome', {}).get('user_data_dir', '')
        self.profile = config_manager.get('browsers', 'chrome', {}).get('profile', 'Default')
        self.temp_dir = config_manager.get('storage', {}).get('temp_dir', tempfile.gettempdir())
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def extract_bookmarks(self, progress_callback=None) -> List[ChromeBookmark]:
        """
        Extract bookmarks from Chrome.
        
        Args:
            progress_callback: Optional callback function to report progress
                The callback should accept parameters (current, total, status_message)
        
        Returns:
            List of ChromeBookmark objects
        
        Raises:
            RuntimeError: If extraction fails
        """
        # Locate the Bookmarks file
        bookmarks_path = os.path.join(
            os.path.expandvars(self.user_data_dir),
            self.profile,
            "Bookmarks"
        )
        
        if not os.path.exists(bookmarks_path):
            error_msg = f"Bookmarks file not found: {bookmarks_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        if progress_callback:
            progress_callback(10, 100, "Located Chrome bookmarks file")
        
        try:
            # Read the bookmarks file
            with open(bookmarks_path, 'r', encoding='utf-8') as f:
                bookmarks_data = json.load(f)
            
            if progress_callback:
                progress_callback(30, 100, "Loaded bookmarks data")
            
            # Parse the bookmarks
            bookmarks = self._parse_bookmarks_data(bookmarks_data, progress_callback)
            
            if progress_callback:
                progress_callback(100, 100, f"Extracted {len(bookmarks)} bookmarks")
            
            return bookmarks
        
        except Exception as e:
            error_msg = f"Failed to extract bookmarks: {str(e)}"
            logger.error(error_msg)
            if progress_callback:
                progress_callback(0, 100, error_msg)
            
            raise RuntimeError(error_msg)
    
    def _parse_bookmarks_data(self, data: Dict[str, Any], progress_callback=None) -> List[ChromeBookmark]:
        """
        Parse Chrome bookmarks data.
        
        Args:
            data: Chrome bookmarks JSON data
            progress_callback: Optional callback function to report progress
        
        Returns:
            List of ChromeBookmark objects
        """
        if 'roots' not in data:
            raise ValueError("Invalid bookmarks data: 'roots' not found")
        
        roots = data['roots']
        bookmarks = []
        
        # Process each root bookmark category
        for i, (category, root) in enumerate(roots.items()):
            if progress_callback:
                progress = 30 + int(60 * ((i + 1) / len(roots)))
                progress_callback(progress, 100, f"Parsing {category} bookmarks")
            
            # Skip sync_transaction_version and other non-bookmark entries
            if not isinstance(root, dict) or 'children' not in root:
                continue
            
            # Parse the bookmark tree
            category_bookmark = ChromeBookmark(
                title=root.get('name', category),
                date_added=root.get('date_added', 0),
                date_modified=root.get('date_modified', 0),
                folder_path=[]
            )
            
            # Extract each bookmark in this category
            self._extract_bookmarks_recursive(root, category_bookmark, [category_bookmark.title])
            
            bookmarks.append(category_bookmark)
        
        return bookmarks
    
    def _extract_bookmarks_recursive(self, node: Dict[str, Any], parent: ChromeBookmark, 
                                     folder_path: List[str]) -> None:
        """
        Recursively extract bookmarks from a node.
        
        Args:
            node: Bookmark node (folder or bookmark)
            parent: Parent ChromeBookmark object
            folder_path: Current folder path
        """
        if 'children' not in node:
            return
        
        for child in node['children']:
            # Check if it's a folder or bookmark
            if child.get('type') == 'folder':
                # Create folder bookmark
                folder = ChromeBookmark(
                    title=child.get('name', ''),
                    date_added=child.get('date_added', 0),
                    date_modified=child.get('date_modified', 0),
                    folder_path=folder_path.copy()
                )
                
                # Add to parent
                parent.add_child(folder)
                
                # Process children recursively
                new_path = folder_path + [folder.title]
                self._extract_bookmarks_recursive(child, folder, new_path)
            
            elif child.get('type') == 'url':
                # Create URL bookmark
                bookmark = ChromeBookmark(
                    title=child.get('name', ''),
                    url=child.get('url', ''),
                    date_added=child.get('date_added', 0),
                    date_modified=child.get('date_modified', 0),
                    folder_path=folder_path.copy()
                )
                
                # Add to parent
                parent.add_child(bookmark)
    
    def save_to_html(self, bookmarks: List[ChromeBookmark], output_path: str = None) -> str:
        """
        Save bookmarks to HTML file compatible with Zen Browser import.
        
        Args:
            bookmarks: List of ChromeBookmark objects
            output_path: Path to save the HTML file (optional)
        
        Returns:
            Path to the saved HTML file
        """
        if not output_path:
            output_path = os.path.join(self.temp_dir, f"chrome_bookmarks_{int(time.time())}.html")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write HTML header
                f.write("""<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
     It will be read and overwritten.
     DO NOT EDIT! -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
""")
                
                # Write bookmark data
                for bookmark in bookmarks:
                    self._write_bookmark_html(f, bookmark, 1)
                
                # Write HTML footer
                f.write("</DL><p>")
            
            logger.info(f"Saved bookmarks to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to save bookmarks to HTML: {str(e)}")
            raise
    
    def _write_bookmark_html(self, file, bookmark: ChromeBookmark, indent_level: int):
        """
        Write a bookmark as HTML to the file.
        
        Args:
            file: File object to write to
            bookmark: ChromeBookmark object
            indent_level: Current indentation level
        """
        indent = "    " * indent_level
        
        # Convert Chrome timestamp (microseconds since 1601-01-01 UTC) to Unix timestamp
        # Chrome timestamp is microseconds since Jan 1, 1601 UTC
        # To convert to Unix time (seconds since Jan 1, 1970 UTC), we need to:
        # 1. Divide by 1000000 to get seconds
        # 2. Subtract the difference between 1601 and 1970 (11644473600 seconds)
        chrome_to_unix_epoch_diff = 11644473600
        date_added_unix = int(bookmark.date_added / 1000000 - chrome_to_unix_epoch_diff)
        date_added_str = datetime.fromtimestamp(max(0, date_added_unix)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if bookmark.is_folder:
            # Write folder
            file.write(f'{indent}<DT><H3 ADD_DATE="{date_added_unix}" LAST_MODIFIED="{int(bookmark.date_modified / 1000000 - chrome_to_unix_epoch_diff)}">{bookmark.title}</H3>\n')
            file.write(f'{indent}<DL><p>\n')
            
            # Write children
            for child in bookmark.children:
                self._write_bookmark_html(file, child, indent_level + 1)
            
            file.write(f'{indent}</DL><p>\n')
        else:
            # Write bookmark
            file.write(f'{indent}<DT><A HREF="{bookmark.url}" ADD_DATE="{date_added_unix}">{bookmark.title}</A>\n')
