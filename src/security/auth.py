"""
Authentication module for ChromeSync.

This module provides user authentication functionality to ensure
only authorized users can perform sensitive operations.
"""

import os
import json
import time
import base64
import logging
import tempfile
from typing import Optional, Dict, Any, Tuple, Union

import win32security
import win32api
import win32con
import win32cred

from ..config import ConfigManager
from ..utils.security import (
    encrypt_data, decrypt_data, secure_delete_file,
    verify_windows_user, create_secure_token, is_admin
)

# Set up logging
logger = logging.getLogger(__name__)

class AuthenticationManager:
    """
    Manages user authentication and access control.
    
    This class provides functionality to authenticate users,
    create and validate tokens, and manage access control.
    """
    
    # Token validity duration in seconds (default: 1 hour)
    TOKEN_VALIDITY_DURATION = 60 * 60
    
    # Credential target name for Windows Credential Manager
    CRED_TARGET_NAME = "ChromeSync_Auth"
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the authentication manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.require_auth = config_manager.get('security', {}).get('require_auth_for_sensitive_ops', True)
        self.current_token = None
        self.token_expiry = 0
        
        # Credential storage path (in case Credential Manager is not available)
        self.temp_dir = config_manager.get('storage', {}).get('temp_dir', tempfile.gettempdir())
        self.cred_file_path = os.path.join(self.temp_dir, ".chromesync_auth")
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def is_authentication_required(self) -> bool:
        """
        Check if authentication is required.
        
        Returns:
            bool: True if authentication is required, False otherwise
        """
        return self.require_auth
    
    def authenticate_user(self, password: Optional[str] = None) -> bool:
        """
        Authenticate the user.
        
        Args:
            password: Optional password for authentication (if None, uses Windows authentication)
        
        Returns:
            bool: True if authentication succeeded, False otherwise
        """
        if not self.is_authentication_required():
            return True
        
        try:
            if password:
                # Authenticate using provided password
                stored_hash = self._get_stored_password_hash()
                if not stored_hash:
                    # No stored hash; this might be first-time setup
                    self._store_password_hash(password)
                    logger.info("Password set for future authentication")
                    result = True
                else:
                    # Verify password
                    salt, hash_value = stored_hash.split(":", 1)
                    salt_bytes = base64.b64decode(salt)
                    hash_bytes = base64.b64decode(hash_value)
                    
                    # Verify password against stored hash
                    import hashlib
                    derived_key = hashlib.pbkdf2_hmac(
                        'sha256', 
                        password.encode(), 
                        salt_bytes, 
                        100000,
                        dklen=32
                    )
                    
                    result = derived_key == hash_bytes
            else:
                # Authenticate using Windows user verification
                result = verify_windows_user()
            
            if result:
                # Create and store authentication token
                self._create_auth_token()
                logger.info("User authenticated successfully")
            else:
                logger.warning("Authentication failed")
            
            return result
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def validate_token(self) -> bool:
        """
        Validate the current authentication token.
        
        Returns:
            bool: True if the token is valid, False otherwise
        """
        if not self.is_authentication_required():
            return True
        
        if not self.current_token or time.time() > self.token_expiry:
            logger.warning("Authentication token is invalid or expired")
            return False
        
        return True
    
    def require_authentication(self, operation_name: str) -> bool:
        """
        Check if an operation requires authentication.
        
        Args:
            operation_name: Name of the operation to check
        
        Returns:
            bool: True if the operation requires authentication, False otherwise
        """
        # List of operations that always require authentication
        sensitive_operations = [
            'password_sync',
            'config_export',
            'config_import',
            'secure_delete',
            'profile_create',
            'profile_delete'
        ]
        
        if operation_name in sensitive_operations:
            return True
        
        # Check configuration for general authentication requirement
        return self.is_authentication_required()
    
    def is_authenticated_for(self, operation_name: str) -> bool:
        """
        Check if the user is authenticated for a specific operation.
        
        Args:
            operation_name: Name of the operation to check
        
        Returns:
            bool: True if the user is authenticated for the operation, False otherwise
        """
        if not self.require_authentication(operation_name):
            return True
        
        return self.validate_token()
    
    def logout(self) -> bool:
        """
        Log the user out by invalidating the current token.
        
        Returns:
            bool: True if logout succeeded, False otherwise
        """
        try:
            self.current_token = None
            self.token_expiry = 0
            logger.info("User logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False
    
    def _create_auth_token(self) -> None:
        """Create a new authentication token."""
        self.current_token = create_secure_token()
        self.token_expiry = time.time() + self.TOKEN_VALIDITY_DURATION
    
    def _store_password_hash(self, password: str) -> bool:
        """
        Store a hashed password for future authentication.
        
        Args:
            password: Password to hash and store
        
        Returns:
            bool: True if the password was stored successfully, False otherwise
        """
        try:
            # Generate a salt and hash the password
            import hashlib, os
            salt = os.urandom(16)
            hash_value = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode(), 
                salt, 
                100000,
                dklen=32
            )
            
            # Create a string representation
            credential = f"{base64.b64encode(salt).decode()}:{base64.b64encode(hash_value).decode()}"
            
            # Try to store in Windows Credential Manager first
            try:
                credential_blob = credential.encode()
                cred = {
                    'Type': win32cred.CRED_TYPE_GENERIC,
                    'TargetName': self.CRED_TARGET_NAME,
                    'CredentialBlob': credential_blob,
                    'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE
                }
                win32cred.CredWrite(cred, 0)
                logger.debug("Credential stored in Windows Credential Manager")
                return True
            except Exception as e:
                logger.warning(f"Failed to store credential in Windows Credential Manager: {str(e)}")
                
                # Fall back to file-based storage with encryption
                encrypted_data = encrypt_data(credential)
                with open(self.cred_file_path, 'w') as f:
                    f.write(encrypted_data)
                
                logger.debug("Credential stored in encrypted file")
                return True
        
        except Exception as e:
            logger.error(f"Failed to store password hash: {str(e)}")
            return False
    
    def _get_stored_password_hash(self) -> Optional[str]:
        """
        Get the stored password hash.
        
        Returns:
            str: The stored password hash, or None if not found
        """
        try:
            # Try to get from Windows Credential Manager first
            try:
                cred = win32cred.CredRead(self.CRED_TARGET_NAME, win32cred.CRED_TYPE_GENERIC, 0)
                credential = cred['CredentialBlob'].decode()
                logger.debug("Credential retrieved from Windows Credential Manager")
                return credential
            except Exception:
                logger.debug("Credential not found in Windows Credential Manager")
                
                # Fall back to file-based storage
                if os.path.exists(self.cred_file_path):
                    with open(self.cred_file_path, 'r') as f:
                        encrypted_data = f.read()
                    
                    credential = decrypt_data(encrypted_data).decode()
                    logger.debug("Credential retrieved from encrypted file")
                    return credential
                
                return None
        
        except Exception as e:
            logger.error(f"Failed to get stored password hash: {str(e)}")
            return None
    
    def check_operation_privileges(self, operation_name: str) -> Tuple[bool, str]:
        """
        Check if the user has sufficient privileges for an operation.
        
        Args:
            operation_name: Name of the operation to check
        
        Returns:
            tuple: (has_privileges, error_message)
        """
        # Operations that require administrator privileges
        admin_operations = [
            'auto_startup_config',
            'system_config',
            'service_install'
        ]
        
        # Check for authenticated operations
        if self.require_authentication(operation_name) and not self.validate_token():
            return False, "Authentication required for this operation"
        
        # Check for admin operations
        if operation_name in admin_operations and not is_admin():
            return False, "Administrator privileges required for this operation"
        
        return True, ""
