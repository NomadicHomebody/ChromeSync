"""
Default configuration settings for ChromeSync.

This module provides the default configuration values used when
no user configuration is present or when configuration is reset.
"""

import os
import pathlib

# User's home directory for default paths
USER_HOME = str(pathlib.Path.home())

# Default Chrome paths based on standard installation locations
DEFAULT_CHROME_PATH = os.path.join(
    os.environ.get('PROGRAMFILES', r'C:\Program Files'),
    r'Google\Chrome\Application\chrome.exe'
)
DEFAULT_CHROME_USER_DATA = os.path.join(
    os.environ.get('LOCALAPPDATA', ''),
    r'Google\Chrome\User Data'
)
DEFAULT_CHROME_PROFILE = 'Default'

# Default Zen Browser paths
DEFAULT_ZEN_PATH = os.path.join(
    os.environ.get('PROGRAMFILES', r'C:\Program Files'),
    r'Zen Browser\zen.exe'
)
DEFAULT_ZEN_USER_DATA = os.path.join(
    os.environ.get('APPDATA', ''),
    r'zen'
)
DEFAULT_ZEN_PROFILE = 'default'

# Default temporary directory for data exchange
DEFAULT_TEMP_DIR = os.path.join(
    os.environ.get('TEMP', os.path.join(USER_HOME, 'AppData', 'Local', 'Temp')),
    'ChromeSync'
)

# Default log directory
DEFAULT_LOG_DIR = os.path.join(USER_HOME, 'AppData', 'Local', 'ChromeSync', 'logs')

# Default configuration
DEFAULT_CONFIG = {
    "general": {
        "auto_start": True,
        "minimize_to_tray": True,
        "check_for_updates": True,
        "sync_on_startup": False,
        "language": "en-US"
    },
    "browsers": {
        "chrome": {
            "path": DEFAULT_CHROME_PATH,
            "user_data_dir": DEFAULT_CHROME_USER_DATA,
            "profile": DEFAULT_CHROME_PROFILE,
            "use_gui_automation": True
        },
        "zen": {
            "path": DEFAULT_ZEN_PATH,
            "user_data_dir": DEFAULT_ZEN_USER_DATA,
            "profile": DEFAULT_ZEN_PROFILE
        }
    },
    "sync": {
        "data_types": {
            "passwords": True,
            "bookmarks": True,
            "history": True
        },
        "schedule": {
            "enabled": False,
            "interval_hours": 24,
            "specific_time": "02:00",
            "sync_when_idle": True,
            "idle_time_minutes": 10
        },
        "auto_sync": {
            "enabled": True,
            "trigger_on_chrome_launch": True,
            "trigger_on_chrome_close": False,
            "delay_seconds": 5
        }
    },
    "security": {
        "encrypt_temp_files": True,
        "require_auth_for_sensitive_ops": True,
        "secure_delete_temp_files": True,
        "log_sensitive_operations": False
    },
    "storage": {
        "temp_dir": DEFAULT_TEMP_DIR,
        "retention_days": 1,
        "max_backups": 3
    },
    "logs": {
        "dir": DEFAULT_LOG_DIR,
        "level": "INFO",
        "max_size_mb": 10,
        "rotation_count": 5,
        "include_timestamps": True
    },
    "gui": {
        "theme": "system",
        "start_minimized": False,
        "show_notifications": True,
        "notification_timeout_sec": 5,
        "confirm_actions": True
    }
}