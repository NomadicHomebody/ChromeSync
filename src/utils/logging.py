"""
Logging module for ChromeSync.

This module provides a comprehensive logging system with different verbosity levels,
secure logging (no sensitive data), log rotation, and user-friendly error messages.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

# Define log levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Sensitive keywords for filtering
SENSITIVE_KEYWORDS = [
    'password', 'token', 'secret', 'key', 'auth', 'credential',
    'private', 'sensitive', 'hash', 'salt'
]

class SensitiveDataFilter(logging.Filter):
    """
    Filter sensitive data from log records.
    
    This filter masks sensitive data like passwords, tokens, and keys
    in log messages to prevent security leaks.
    """
    
    def __init__(self, keywords: Optional[List[str]] = None):
        """
        Initialize the filter with sensitive keywords.
        
        Args:
            keywords: Optional list of sensitive keywords to filter
        """
        super().__init__()
        self.sensitive_keywords = keywords or SENSITIVE_KEYWORDS
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to mask sensitive data.
        
        Args:
            record: Log record to filter
        
        Returns:
            bool: Always True (the record is always logged, just modified)
        """
        # Check if message is a string
        if isinstance(record.msg, str):
            # Replace sensitive data in the message
            for keyword in self.sensitive_keywords:
                # Look for patterns like password="123" or password: "123" or "password": "123"
                patterns = [
                    f'{keyword}="{{',  # For password="{"abc"}"
                    f'{keyword}="',  # For password="abc"
                    f'{keyword}:["\'\\s]+',  # For password: "abc" or "password": "abc"
                ]
                
                for pattern in patterns:
                    if pattern.startswith(f'{keyword}="{{'):
                        # Handle JSON-like values with more complex structure
                        import re
                        for match in re.finditer(f'{keyword}="({{.*?}})"', record.msg):
                            try:
                                # Try to handle JSON objects
                                json_value = match.group(1)
                                record.msg = record.msg.replace(
                                    f'{keyword}="{json_value}"',
                                    f'{keyword}="*****"'
                                )
                            except:
                                pass
                    elif pattern.startswith(f'{keyword}="'):
                        # Simple replacement for quotes
                        import re
                        for match in re.finditer(f'{keyword}="(.*?)"', record.msg):
                            record.msg = record.msg.replace(
                                f'{keyword}="{match.group(1)}"',
                                f'{keyword}="*****"'
                            )
                    else:
                        # Handle JSON-style keys with quoted or non-quoted values
                        import re
                        for match in re.finditer(f'["\']?{keyword}["\']?\\s*:\\s*["\']?(.*?)["\']?[,\\s}}]', record.msg):
                            value = match.group(1)
                            record.msg = record.msg.replace(
                                value, 
                                "*****"
                            )
        
        # Check if args contain sensitive data
        if record.args:
            try:
                # Create a copy of the args
                args_list = list(record.args)
                
                # Check each arg
                for i, arg in enumerate(args_list):
                    # If it's a string, check for sensitive keywords
                    if isinstance(arg, str):
                        for keyword in self.sensitive_keywords:
                            if keyword in arg.lower():
                                args_list[i] = "*****"
                    # If it's a dict, check for sensitive keys
                    elif isinstance(arg, dict):
                        for key, value in list(arg.items()):
                            if any(keyword in str(key).lower() for keyword in self.sensitive_keywords):
                                arg[key] = "*****"
                
                # Update the record args
                record.args = tuple(args_list)
            except:
                # If there's an error, just mask all args to be safe
                record.args = ("*****",) * len(record.args)
        
        return True

class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON objects.
    
    This formatter outputs log records as structured JSON objects,
    which is useful for log analysis and machine processing.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            str: JSON-formatted log record
        """
        # Create a dictionary with log data
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

class ColoredConsoleFormatter(logging.Formatter):
    """
    Format log records with colors for console output.
    
    This formatter adds ANSI colors to log records for better visibility
    in terminal/console output.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[38;5;246m',  # Gray
        'INFO': '\033[38;5;39m',    # Blue
        'WARNING': '\033[38;5;208m', # Orange
        'ERROR': '\033[38;5;196m',   # Red
        'CRITICAL': '\033[48;5;196;38;5;231m', # White on Red
        'RESET': '\033[0m'          # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.
        
        Args:
            record: Log record to format
        
        Returns:
            str: Colored log record
        """
        # Get the log level color
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        
        # Format the message
        formatted_message = super().format(record)
        
        # Add color to the log level
        colored_level = f"{level_color}{record.levelname}{self.COLORS['RESET']}"
        
        # Replace the level name with the colored version
        return formatted_message.replace(record.levelname, colored_level)

def setup_logging(
    log_dir: Optional[str] = None,
    log_level: str = 'INFO',
    enable_console: bool = True,
    enable_file: bool = True,
    max_size_mb: int = 10,
    rotation_count: int = 5,
    include_timestamps: bool = True,
    json_format: bool = False,
    config_manager = None
) -> logging.Logger:
    """
    Set up the logging system.
    
    Args:
        log_dir: Directory for log files
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
        max_size_mb: Maximum size of log files in MB
        rotation_count: Number of log files to keep
        include_timestamps: Whether to include timestamps in log messages
        json_format: Whether to use JSON format for log files
        config_manager: Optional configuration manager to get settings from
    
    Returns:
        Logger: Root logger
    """
    # Get settings from config manager if provided
    if config_manager:
        log_dir = config_manager.get('logs', {}).get('dir', log_dir)
        log_level = config_manager.get('logs', {}).get('level', log_level)
        max_size_mb = config_manager.get('logs', {}).get('max_size_mb', max_size_mb)
        rotation_count = config_manager.get('logs', {}).get('rotation_count', rotation_count)
        include_timestamps = config_manager.get('logs', {}).get('include_timestamps', include_timestamps)
    
    # Create log directory if necessary
    if enable_file and log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Get log level
    numeric_level = LOG_LEVELS.get(log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Create ChromeSync logger (which is what the application will use)
    logger = logging.getLogger('chromesync')
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Define the format
    log_format = '%(levelname)s - %(name)s - %(message)s'
    if include_timestamps:
        log_format = '%(asctime)s - ' + log_format
    
    # Create console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Use colored formatter for console
        formatter = ColoredConsoleFormatter(log_format)
        console_handler.setFormatter(formatter)
        
        # Add sensitive data filter
        console_handler.addFilter(SensitiveDataFilter())
        
        root_logger.addHandler(console_handler)
    
    # Create file handlers
    if enable_file and log_dir:
        # Create general log file
        general_log_path = os.path.join(log_dir, 'chromesync.log')
        general_handler = logging.handlers.RotatingFileHandler(
            general_log_path,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=rotation_count
        )
        general_handler.setLevel(numeric_level)
        
        # Set formatter
        if json_format:
            general_handler.setFormatter(JSONFormatter())
        else:
            general_handler.setFormatter(logging.Formatter(log_format))
        
        # Add sensitive data filter
        general_handler.addFilter(SensitiveDataFilter())
        
        root_logger.addHandler(general_handler)
        
        # Create separate error log file
        error_log_path = os.path.join(log_dir, 'chromesync_error.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=rotation_count
        )
        error_handler.setLevel(logging.ERROR)  # Only ERROR and CRITICAL
        
        # Set formatter
        if json_format:
            error_handler.setFormatter(JSONFormatter())
        else:
            error_handler.setFormatter(logging.Formatter(log_format))
        
        # Add sensitive data filter
        error_handler.addFilter(SensitiveDataFilter())
        
        root_logger.addHandler(error_handler)
    
    # Log setup completion
    logger.debug(f"Logging system initialized with level {log_level}")
    
    return logger

def log_exception(e: Exception, logger: Optional[logging.Logger] = None) -> None:
    """
    Log an exception with stack trace.
    
    Args:
        e: Exception to log
        logger: Logger to use (if None, uses the root logger)
    """
    if logger is None:
        logger = logging.getLogger()
    
    logger.error(f"Exception: {type(e).__name__}: {str(e)}", exc_info=True)

def get_user_friendly_error_message(error_code: str, *args, **kwargs) -> str:
    """
    Get a user-friendly error message for an error code.
    
    Args:
        error_code: Error code to get message for
        *args: Positional arguments to format the message with
        **kwargs: Keyword arguments to format the message with
    
    Returns:
        str: User-friendly error message
    """
    # Define error messages
    error_messages = {
        # General errors
        'GENERAL_ERROR': "An error occurred: {0}",
        'PERMISSION_DENIED': "Permission denied. Try running the application as administrator.",
        'FILE_NOT_FOUND': "File not found: {0}",
        'DIRECTORY_NOT_FOUND': "Directory not found: {0}",
        'CONNECTION_ERROR': "Connection error: {0}",
        'TIMEOUT_ERROR': "Operation timed out: {0}",
        
        # Configuration errors
        'CONFIG_INVALID': "Invalid configuration: {0}",
        'CONFIG_LOAD_ERROR': "Failed to load configuration: {0}",
        'CONFIG_SAVE_ERROR': "Failed to save configuration: {0}",
        
        # Browser errors
        'CHROME_NOT_FOUND': "Chrome executable not found. Please check the path in settings.",
        'ZEN_BROWSER_NOT_FOUND': "Zen Browser executable not found. Please check the path in settings.",
        'CHROME_PROFILE_ERROR': "Error accessing Chrome profile: {0}",
        'ZEN_PROFILE_ERROR': "Error accessing Zen Browser profile: {0}",
        
        # Data extraction errors
        'PASSWORD_EXTRACTION_ERROR': "Failed to extract passwords: {0}",
        'BOOKMARK_EXTRACTION_ERROR': "Failed to extract bookmarks: {0}",
        'HISTORY_EXTRACTION_ERROR': "Failed to extract browsing history: {0}",
        
        # Import errors
        'PASSWORD_IMPORT_ERROR': "Failed to import passwords: {0}",
        'BOOKMARK_IMPORT_ERROR': "Failed to import bookmarks: {0}",
        'HISTORY_IMPORT_ERROR': "Failed to import browsing history: {0}",
        
        # Security errors
        'AUTHENTICATION_ERROR': "Authentication failed: {0}",
        'ENCRYPTION_ERROR': "Encryption error: {0}",
        'DECRYPTION_ERROR': "Decryption error: {0}",
        
        # Service errors
        'SERVICE_START_ERROR': "Failed to start service: {0}",
        'SERVICE_STOP_ERROR': "Failed to stop service: {0}",
        'MONITORING_ERROR': "Process monitoring error: {0}"
    }
    
    # Get the error message
    message = error_messages.get(error_code, "Unknown error: {0}")
    
    # Format the message with args and kwargs
    if args:
        message = message.format(*args)
    elif kwargs:
        message = message.format(**kwargs)
    
    return message

class ErrorHandler:
    """
    Handle errors and exceptions with retries and fallbacks.
    
    This class provides functionality to handle errors and exceptions,
    including retries with exponential backoff, fallbacks, and
    graceful degradation.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler.
        
        Args:
            logger: Logger to use (if None, uses the root logger)
        """
        self.logger = logger or logging.getLogger()
    
    def with_retries(self, func, max_retries: int = 3, backoff_factor: float = 2.0,
                    exceptions: Union[Exception, tuple] = Exception, 
                    fallback_func = None, fallback_args: tuple = (), fallback_kwargs: Dict[str, Any] = {}):
        """
        Execute a function with retries and exponential backoff.
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor for exponential backoff
            exceptions: Exception(s) to catch and retry
            fallback_func: Fallback function to call if all retries fail
            fallback_args: Arguments for the fallback function
            fallback_kwargs: Keyword arguments for the fallback function
        
        Returns:
            Result of the function or fallback function
        
        Raises:
            The last exception encountered if all retries fail and no fallback is provided
        """
        import time
        
        retry_count = 0
        last_exception = None
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    self.logger.debug(f"Retry {retry_count}/{max_retries}")
                
                return func()
            
            except exceptions as e:
                retry_count += 1
                last_exception = e
                
                if retry_count <= max_retries:
                    # Calculate backoff time
                    backoff_time = backoff_factor ** (retry_count - 1)
                    
                    self.logger.warning(
                        f"Operation failed with error: {str(e)}. "
                        f"Retrying in {backoff_time:.1f} seconds."
                    )
                    
                    # Wait before retrying
                    time.sleep(backoff_time)
                else:
                    # All retries failed
                    self.logger.error(
                        f"Operation failed after {max_retries} retries. "
                        f"Last error: {str(e)}"
                    )
                    
                    # If a fallback function is provided, call it
                    if fallback_func is not None:
                        self.logger.info("Executing fallback function")
                        return fallback_func(*fallback_args, **fallback_kwargs)
                    
                    # Otherwise, re-raise the exception
                    raise last_exception
