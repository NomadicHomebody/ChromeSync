"""
Security utilities for ChromeSync.

This module provides security-related utilities, including secure file deletion,
encryption/decryption, user authentication, and other security operations.
"""

import os
import hmac
import uuid
import base64
import random
import shutil
import hashlib
import logging
import ctypes
import ctypes.wintypes
from typing import Optional, Tuple, Any, Dict, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import win32security
import win32api
import win32con

# Set up logging
logger = logging.getLogger(__name__)

# Windows DPAPI constants and functions
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', ctypes.wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_char))
    ]

# Get CryptProtectData and CryptUnprotectData functions from crypt32.dll
_crypt_protect_data = ctypes.windll.crypt32.CryptProtectData
_crypt_unprotect_data = ctypes.windll.crypt32.CryptUnprotectData

def secure_delete_file(file_path: str, passes: int = 3) -> bool:
    """
    Securely delete a file by overwriting it multiple times before removal.
    
    Args:
        file_path: Path to the file to delete
        passes: Number of overwrite passes (default: 3)
    
    Returns:
        bool: True if file was deleted successfully, False otherwise
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.warning(f"File not found for secure deletion: {file_path}")
        return False
    
    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Open file for binary writing
        for _ in range(passes):
            with open(file_path, 'wb') as f:
                # Pass 1: Overwrite with zeros
                f.write(b'\x00' * file_size)
                f.flush()
                os.fsync(f.fileno())
            
            with open(file_path, 'wb') as f:
                # Pass 2: Overwrite with ones
                f.write(b'\xFF' * file_size)
                f.flush()
                os.fsync(f.fileno())
            
            with open(file_path, 'wb') as f:
                # Pass 3: Overwrite with random data
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Finally, delete the file
        os.remove(file_path)
        logger.debug(f"File securely deleted: {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to securely delete file {file_path}: {str(e)}")
        
        # Attempt standard deletion as fallback
        try:
            os.remove(file_path)
            logger.warning(f"File deleted using standard method after secure deletion failed: {file_path}")
            return True
        except Exception as e2:
            logger.error(f"Failed to delete file {file_path} using standard method: {str(e2)}")
            return False

def secure_delete_directory(dir_path: str, passes: int = 3) -> bool:
    """
    Securely delete a directory and all its contents.
    
    Args:
        dir_path: Path to the directory to delete
        passes: Number of overwrite passes (default: 3)
    
    Returns:
        bool: True if directory was deleted successfully, False otherwise
    """
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        logger.warning(f"Directory not found for secure deletion: {dir_path}")
        return False
    
    try:
        # Walk the directory tree and securely delete all files
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for file in files:
                secure_delete_file(os.path.join(root, file), passes)
            
            # Remove empty directories
            for dir in dirs:
                try:
                    os.rmdir(os.path.join(root, dir))
                except Exception as e:
                    logger.error(f"Failed to remove directory {os.path.join(root, dir)}: {str(e)}")
        
        # Finally, remove the root directory
        os.rmdir(dir_path)
        logger.debug(f"Directory securely deleted: {dir_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to securely delete directory {dir_path}: {str(e)}")
        
        # Attempt standard deletion as fallback
        try:
            shutil.rmtree(dir_path)
            logger.warning(f"Directory deleted using standard method after secure deletion failed: {dir_path}")
            return True
        except Exception as e2:
            logger.error(f"Failed to delete directory {dir_path} using standard method: {str(e2)}")
            return False

def encrypt_data(data: Union[str, bytes], password: Optional[str] = None) -> str:
    """
    Encrypt data using Fernet symmetric encryption or Windows DPAPI.
    
    Args:
        data: Data to encrypt (string or bytes)
        password: Optional password for encryption (if None, uses DPAPI)
    
    Returns:
        str: Base64-encoded encrypted data
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    try:
        if password:
            # Derive a key from the password
            salt = b'ChromeSync_Static_Salt'  # In production, consider using a secure per-user salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            # Encrypt with Fernet
            f = Fernet(key)
            encrypted_data = f.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode()
        else:
            # Use Windows DPAPI
            data_in = DATA_BLOB(len(data), ctypes.cast(data, ctypes.POINTER(ctypes.c_char)))
            data_out = DATA_BLOB()
            
            if _crypt_protect_data(
                ctypes.byref(data_in),
                None,  # description
                None,  # entropy
                None,  # reserved
                None,  # prompt_struct
                0,     # flags
                ctypes.byref(data_out)
            ):
                encrypted_data = ctypes.string_at(data_out.pbData, data_out.cbData)
                ctypes.windll.kernel32.LocalFree(data_out.pbData)
                return base64.urlsafe_b64encode(encrypted_data).decode()
            else:
                raise RuntimeError("DPAPI encryption failed")
    
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise

def decrypt_data(encrypted_data: str, password: Optional[str] = None) -> bytes:
    """
    Decrypt data using Fernet symmetric encryption or Windows DPAPI.
    
    Args:
        encrypted_data: Base64-encoded encrypted data
        password: Optional password for decryption (if None, uses DPAPI)
    
    Returns:
        bytes: Decrypted data
    """
    try:
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        
        if password:
            # Derive the same key from the password
            salt = b'ChromeSync_Static_Salt'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            # Decrypt with Fernet
            f = Fernet(key)
            return f.decrypt(encrypted_bytes)
        else:
            # Use Windows DPAPI
            data_in = DATA_BLOB(len(encrypted_bytes), ctypes.cast(encrypted_bytes, ctypes.POINTER(ctypes.c_char)))
            data_out = DATA_BLOB()
            
            if _crypt_unprotect_data(
                ctypes.byref(data_in),
                None,  # description
                None,  # entropy
                None,  # reserved
                None,  # prompt_struct
                0,     # flags
                ctypes.byref(data_out)
            ):
                decrypted_data = ctypes.string_at(data_out.pbData, data_out.cbData)
                ctypes.windll.kernel32.LocalFree(data_out.pbData)
                return decrypted_data
            else:
                raise RuntimeError("DPAPI decryption failed")
    
    except Exception as e:
        logger.error(f"Decryption failed: {str(e)}")
        raise

def create_secure_token() -> str:
    """
    Create a secure random token for authentication.
    
    Returns:
        str: Base64-encoded secure token
    """
    token = os.urandom(32)  # 256 bits of randomness
    return base64.urlsafe_b64encode(token).decode()

def is_admin() -> bool:
    """
    Check if the current process has administrator privileges.
    
    Returns:
        bool: True if running with admin privileges, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def verify_windows_user() -> bool:
    """
    Verify the current Windows user's identity.
    
    This function attempts to perform an operation that requires the user
    to be logged in, verifying their identity.
    
    Returns:
        bool: True if verification succeeded, False otherwise
    """
    try:
        # Get the current user's SID
        current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
        
        # Try to get the user's token, which will fail if not authenticated
        win32security.LookupAccountName(None, current_user)
        
        return True
    except Exception as e:
        logger.error(f"Windows user verification failed: {str(e)}")
        return False

def validate_file_integrity(file_path: str, expected_hash: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate the integrity of a file using SHA-256 hash.
    
    Args:
        file_path: Path to the file to validate
        expected_hash: Expected SHA-256 hash (if None, just returns the hash)
    
    Returns:
        tuple: (is_valid, actual_hash)
    """
    if not os.path.exists(file_path):
        return False, ""
    
    try:
        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_hash = sha256_hash.hexdigest()
        
        if expected_hash is None:
            return True, actual_hash
        
        return hmac.compare_digest(actual_hash, expected_hash), actual_hash
    
    except Exception as e:
        logger.error(f"File integrity check failed: {str(e)}")
        return False, ""

def get_user_confirmation(message: str, default: bool = False) -> bool:
    """
    Get confirmation from the user via console input.
    
    Args:
        message: Message to display to the user
        default: Default value if user just presses Enter
    
    Returns:
        bool: True if user confirmed, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    response = input(f"{message} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response.startswith('y')
