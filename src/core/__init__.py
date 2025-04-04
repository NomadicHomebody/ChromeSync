"""
Core functionality module for ChromeSync.

This package contains the core functionality for ChromeSync,
including process monitoring and service management.
"""

from .process_monitor import ChromeProcessMonitor
from .service_manager import ServiceManager
from .extractors import (
    PasswordExtractor, ChromePassword,
    BookmarkExtractor, ChromeBookmark,
    HistoryExtractor, ChromeHistoryItem
)
from .importers import (
    ProfileDetector, ZenProfile,
    PasswordImporter,
    BookmarkImporter,
    HistoryImporter
)

__all__ = [
    'ChromeProcessMonitor', 
    'ServiceManager',
    'PasswordExtractor', 
    'ChromePassword',
    'BookmarkExtractor', 
    'ChromeBookmark',
    'HistoryExtractor', 
    'ChromeHistoryItem',
    'ProfileDetector',
    'ZenProfile',
    'PasswordImporter',
    'BookmarkImporter',
    'HistoryImporter'
]
