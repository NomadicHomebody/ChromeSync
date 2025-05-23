"""
Configuration package for ChromeSync.

This package handles all configuration-related functionality
including loading, saving, and validating configuration settings.
"""

from .config_manager import ConfigManager
from .config_defaults import DEFAULT_CONFIG

__all__ = ['ConfigManager', 'DEFAULT_CONFIG']