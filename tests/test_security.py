"""
Test module for ChromeSync security components.

This module contains unit tests for authentication, encryption,
and other security-related functionality.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import tempfile
import json
import base64
import time
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.security.auth import AuthenticationManager, generate_token, validate_token, encrypt_data, decrypt_data, hash_password


@pytest.mark.unit
class TestAuthManager:
    """Test the AuthenticationManager class."""
    
    def test_initialization(self, mock_config_manager):
        """Test initialization of AuthenticationManager."""
        # Create auth manager
        auth_manager = AuthenticationManager(mock_config_manager)
        
        # Verify properties
        assert auth_manager.config_manager == mock_config_manager
        assert auth_manager.authenticated == False
        assert auth_manager.token is None
        assert auth_manager.token_expiry is None
    
    def test_authenticate_user_success(self, auth_manager, monkeypatch):
        """Test successful user authentication."""
        # Mock verify_windows_user to return True
        monkeypatch.setattr('src.security.auth.verify_windows_user', MagicMock(return_value=True))
        
        # Call authenticate_user
        result = auth_manager.authenticate_user()
        
        # Verify authentication was successful
        assert result == True
        assert auth_manager.authenticated == True
        assert auth_manager.token is not None
        assert auth_manager.token_expiry is not None
        assert auth_manager.token_expiry > datetime.now()
    
    def test_authenticate_user_failure(self, auth_manager, monkeypatch):
        """Test failed user authentication."""
        # Mock verify_windows_user to return False
        monkeypatch.setattr('src.security.auth.verify_windows_user', MagicMock(return_value=False))
        
        # Call authenticate_user
        result = auth_manager.authenticate_user()
        
        # Verify authentication failed
        assert result == False
        assert auth_manager.authenticated == False
        assert auth_manager.token is None
        assert auth_manager.token_expiry is None
    
    def test_validate_token_valid(self, auth_manager):
        """Test validating a valid token."""
        # Authenticate to generate token
        auth_manager.authenticated = True
        auth_manager.token = "valid_token"
        auth_manager.token_expiry = datetime.now() + timedelta(hours=1)
        
        # Call validate_token
        result = auth_manager.validate_token()
        
        # Verify token validation was successful
        assert result == True
    
    def test_validate_token_expired(self, auth_manager):
        """Test validating an expired token."""
        # Set expired token
        auth_manager.authenticated = True
        auth_manager.token = "expired_token"
        auth_manager.token_expiry = datetime.now() - timedelta(minutes=5)
        
        # Call validate_token
        result = auth_manager.validate_token()
        
        # Verify token validation failed
        assert result == False
        assert auth_manager.authenticated == False
        assert auth_manager.token is None
        assert auth_manager.token_expiry is None
    
    def test_validate_token_no_token(self, auth_manager):
        """Test validating when no token exists."""
        # Ensure no token
        auth_manager.authenticated = False
        auth_manager.token = None
        auth_manager.token_expiry = None
        
        # Call validate_token
        result = auth_manager.validate_token()
        
        # Verify token validation failed
        assert result == False
    
    def test_require_authentication(self, auth_manager, mock_config_manager):
        """Test checking if authentication is required for operations."""
        # Set up config manager to require authentication for passwords
        mock_config_manager.get.side_effect = lambda section, key=None, default=None: (
            True if section == 'security' and key == 'require_auth_for_sensitive_ops' else default
        )
        
        # Test for sensitive operations
        result = auth_manager.require_authentication('password_sync')
        assert result == True
        
        # Test for non-sensitive operations
        result = auth_manager.require_authentication('bookmark_sync')
        assert result == False  # Should not require by default
    
    def test_logout(self, auth_manager):
        """Test user logout."""
        # Authenticate first
        auth_manager.authenticated = True
        auth_manager.token = "test_token"
        auth_manager.token_expiry = datetime.now() + timedelta(hours=1)
        
        # Call logout
        auth_manager.logout()
        
        # Verify user is logged out
        assert auth_manager.authenticated == False
        assert auth_manager.token is None
        assert auth_manager.token_expiry is None


@pytest.mark.unit
class TestTokenFunctions:
    """Test token generation and validation functions."""
    
    def test_generate_token(self):
        """Test token generation."""
        # Generate token
        token, expiry = generate_token()
        
        # Verify token format
        assert isinstance(token, str)
        assert len(token) > 10  # Token should be reasonably long
        
        # Verify expiry
        assert isinstance(expiry, datetime)
        assert expiry > datetime.now()
        assert expiry < datetime.now() + timedelta(days=2)  # Should not be too far in the future
    
    def test_validate_token_valid(self):
        """Test validating a valid token."""
        # Generate token with custom expiry
        expiry = datetime.now() + timedelta(minutes=30)
        token = base64.b64encode(f"test_token:{int(expiry.timestamp())}".encode()).decode()
        
        # Validate token
        result = validate_token(token, expiry)
        
        # Verify validation was successful
        assert result == True
    
    def test_validate_token_expired(self):
        """Test validating an expired token."""
        # Generate expired token
        expiry = datetime.now() - timedelta(minutes=5)
        token = base64.b64encode(f"test_token:{int(expiry.timestamp())}".encode()).decode()
        
        # Validate token
        result = validate_token(token, expiry)
        
        # Verify validation failed
        assert result == False
    
    def test_validate_token_invalid_format(self):
        """Test validating a token with invalid format."""
        # Generate invalid token
        token = "invalid_token_format"
        expiry = datetime.now() + timedelta(minutes=30)
        
        # Validate token
        result = validate_token(token, expiry)
        
        # Verify validation failed
        assert result == False
    
    def test_validate_token_no_token(self):
        """Test validating when no token is provided."""
        # Validate with None token
        result = validate_token(None, datetime.now() + timedelta(minutes=30))
        
        # Verify validation failed
        assert result == False


@pytest.mark.unit
class TestEncryptionFunctions:
    """Test encryption and decryption functions."""
    
    def test_encrypt_decrypt_data(self):
        """Test encrypting and decrypting data."""
        # Test data
        test_data = "Sensitive information to encrypt"
        
        # Encrypt data
        encrypted = encrypt_data(test_data)
        
        # Verify encrypted data
        assert encrypted != test_data
        assert isinstance(encrypted, str)
        
        # Decrypt data
        decrypted = decrypt_data(encrypted)
        
        # Verify decrypted data
        assert decrypted == test_data.encode()
    
    def test_encrypt_with_different_inputs(self):
        """Test encrypting different inputs."""
        # Test various input types
        inputs = [
            "Simple text string",
            "Special characters: !@#$%^&*()",
            "Unicode characters: 你好, おはよう, مرحبا",
            json.dumps({"key": "value", "nested": {"key2": "value2"}}),
            "1234567890" * 100  # Long string
        ]
        
        for input_data in inputs:
            # Encrypt data
            encrypted = encrypt_data(input_data)
            
            # Verify encrypted data
            assert encrypted != input_data
            assert isinstance(encrypted, str)
            
            # Decrypt data
            decrypted = decrypt_data(encrypted)
            
            # Verify decryption
            assert decrypted.decode() == input_data
    
    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data."""
        # Invalid encrypted data
        invalid_data = "not_valid_encrypted_data"
        
        # Attempt to decrypt
        with pytest.raises(Exception):
            decrypt_data(invalid_data)
    
    def test_hash_password(self):
        """Test password hashing function."""
        # Test password
        password = "MySecurePassword123"
        
        # Hash password
        hashed = hash_password(password)
        
        # Verify hash
        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 20  # Hash should be reasonably long
        
        # Verify consistent hashing
        hashed2 = hash_password(password)
        assert hashed2 != hashed  # Should use salt, so hashes differ
        
        # Verify different passwords have different hashes
        different_hash = hash_password("DifferentPassword")
        assert different_hash != hashed
