"""
Utility modules for ChromeSync.

This package contains various utility modules used throughout the application,
including logging, security functions, and other helper utilities.
"""

from .logging import (
    setup_logging, log_exception, get_user_friendly_error_message, 
    ErrorHandler, LOG_LEVELS, SensitiveDataFilter
)
from .security import (
    secure_delete_file, secure_delete_directory, encrypt_data, decrypt_data,
    create_secure_token, is_admin, verify_windows_user, validate_file_integrity,
    get_user_confirmation
)

__all__ = [
    # Logging
    'setup_logging', 'log_exception', 'get_user_friendly_error_message',
    'ErrorHandler', 'LOG_LEVELS', 'SensitiveDataFilter',
    
    # Security
    'secure_delete_file', 'secure_delete_directory', 'encrypt_data', 'decrypt_data',
    'create_secure_token', 'is_admin', 'verify_windows_user', 'validate_file_integrity',
    'get_user_confirmation'
]
