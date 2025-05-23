# Configuration schema
"""
Configuration schema for ChromeSync.

This module defines the schema used to validate configuration settings.
"""

import os
import json
import jsonschema

# Configuration schema definition using JSON Schema format
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "general": {
            "type": "object",
            "properties": {
                "auto_start": {"type": "boolean"},
                "minimize_to_tray": {"type": "boolean"},
                "check_for_updates": {"type": "boolean"},
                "sync_on_startup": {"type": "boolean"},
                "language": {"type": "string", "pattern": "^[a-z]{2}-[A-Z]{2}$"}
            },
            "required": ["auto_start", "minimize_to_tray", "check_for_updates", "sync_on_startup", "language"],
            "additionalProperties": False
        },
        "browsers": {
            "type": "object",
            "properties": {
                "chrome": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "user_data_dir": {"type": "string"},
                        "profile": {"type": "string"},
                        "use_gui_automation": {"type": "boolean"}
                    },
                    "required": ["path", "user_data_dir", "profile", "use_gui_automation"],
                    "additionalProperties": False
                },
                "zen": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "user_data_dir": {"type": "string"},
                        "profile": {"type": "string"}
                    },
                    "required": ["path", "user_data_dir", "profile"],
                    "additionalProperties": False
                }
            },
            "required": ["chrome", "zen"],
            "additionalProperties": False
        },
        "sync": {
            "type": "object",
            "properties": {
                "data_types": {
                    "type": "object",
                    "properties": {
                        "passwords": {"type": "boolean"},
                        "bookmarks": {"type": "boolean"},
                        "history": {"type": "boolean"}
                    },
                    "required": ["passwords", "bookmarks", "history"],
                    "additionalProperties": False
                },
                "schedule": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "interval_hours": {"type": "number", "minimum": 1, "maximum": 168},
                        "specific_time": {"type": "string", "pattern": "^([01]?[0-9]|2[0-3]):[0-5][0-9]$"},
                        "sync_when_idle": {"type": "boolean"},
                        "idle_time_minutes": {"type": "number", "minimum": 1, "maximum": 60}
                    },
                    "required": ["enabled", "interval_hours", "specific_time", "sync_when_idle", "idle_time_minutes"],
                    "additionalProperties": False
                },
                "auto_sync": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "trigger_on_chrome_launch": {"type": "boolean"},
                        "trigger_on_chrome_close": {"type": "boolean"},
                        "delay_seconds": {"type": "number", "minimum": 0, "maximum": 300}
                    },
                    "required": ["enabled", "trigger_on_chrome_launch", "trigger_on_chrome_close", "delay_seconds"],
                    "additionalProperties": False
                }
            },
            "required": ["data_types", "schedule", "auto_sync"],
            "additionalProperties": False
        },
        "security": {
            "type": "object",
            "properties": {
                "encrypt_temp_files": {"type": "boolean"},
                "require_auth_for_sensitive_ops": {"type": "boolean"},
                "secure_delete_temp_files": {"type": "boolean"},
                "log_sensitive_operations": {"type": "boolean"}
            },
            "required": ["encrypt_temp_files", "require_auth_for_sensitive_ops", "secure_delete_temp_files", "log_sensitive_operations"],
            "additionalProperties": False
        },
        "storage": {
            "type": "object",
            "properties": {
                "temp_dir": {"type": "string"},
                "retention_days": {"type": "number", "minimum": 1, "maximum": 30},
                "max_backups": {"type": "number", "minimum": 0, "maximum": 10}
            },
            "required": ["temp_dir", "retention_days", "max_backups"],
            "additionalProperties": False
        },
        "logs": {
            "type": "object",
            "properties": {
                "dir": {"type": "string"},
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "max_size_mb": {"type": "number", "minimum": 1, "maximum": 100},
                "rotation_count": {"type": "number", "minimum": 1, "maximum": 20},
                "include_timestamps": {"type": "boolean"}
            },
            "required": ["dir", "level", "max_size_mb", "rotation_count", "include_timestamps"],
            "additionalProperties": False
        },
        "gui": {
            "type": "object",
            "properties": {
                "theme": {"type": "string", "enum": ["light", "dark", "system"]},
                "start_minimized": {"type": "boolean"},
                "show_notifications": {"type": "boolean"},
                "notification_timeout_sec": {"type": "number", "minimum": 1, "maximum": 30},
                "confirm_actions": {"type": "boolean"}
            },
            "required": ["theme", "start_minimized", "show_notifications", "notification_timeout_sec", "confirm_actions"],
            "additionalProperties": False
        }
    },
    "required": ["general", "browsers", "sync", "security", "storage", "logs", "gui"],
    "additionalProperties": False
}

def validate_config(config):
    """
    Validate configuration against the schema.
    
    Args:
        config (dict): Configuration dictionary to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        jsonschema.validate(instance=config, schema=CONFIG_SCHEMA)
        return True, None
    except jsonschema.exceptions.ValidationError as e:
        return False, str(e)

def validate_path_exists(path, is_file=True):
    """
    Validate that a path exists and is the correct type.
    
    Args:
        path (str): Path to validate
        is_file (bool): Whether path should be a file (True) or directory (False)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not os.path.exists(path):
        return False, f"Path does not exist: {path}"
    
    if is_file and not os.path.isfile(path):
        return False, f"Path is not a file: {path}"
    elif not is_file and not os.path.isdir(path):
        return False, f"Path is not a directory: {path}"
    
    return True, None