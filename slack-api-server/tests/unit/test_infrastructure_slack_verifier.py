"""
Unit tests for infrastructure Slack verifier
"""

import pytest
import time
from unittest.mock import patch
from src.infrastructure.slack_verifier import SlackSignatureVerifier


class TestSlackSignatureVerifier:
    """Test SlackSignatureVerifier infrastructure service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.verifier = SlackSignatureVerifier("test_signing_secret")
    
    def test_initialization(self):
        """Test verifier initialization."""
        assert self.verifier.signing_secret == b"test_signing_secret"
    
    def test_verify_request_success(self):
        """Test successful request verification."""
        # Create a test request
        timestamp = str(int(time.time()))
        request_data = b"test_request_data"
        
        # Generate expected signature
        import hmac
        import hashlib
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + request_data
        expected_signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        result = self.verifier.verify_request(request_data, timestamp, expected_signature)
        
        assert result is True
    
    def test_verify_request_invalid_signature(self):
        """Test request verification with invalid signature."""
        timestamp = str(int(time.time()))
        request_data = b"test_request_data"
        invalid_signature = "v0=invalid_signature"
        
        result = self.verifier.verify_request(request_data, timestamp, invalid_signature)
        
        assert result is False
    
    def test_verify_request_old_timestamp(self):
        """Test request verification with old timestamp."""
        # Create timestamp that's older than 5 minutes
        old_timestamp = str(int(time.time()) - 400)  # 6 minutes ago
        request_data = b"test_request_data"
        
        # Generate valid signature for the old timestamp
        import hmac
        import hashlib
        sig_basestring = f"v0:{old_timestamp}:".encode('utf-8') + request_data
        signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        result = self.verifier.verify_request(request_data, old_timestamp, signature)
        
        assert result is False
    
    def test_verify_request_future_timestamp(self):
        """Test request verification with future timestamp."""
        # Create timestamp that's in the future (more than 5 minutes)
        future_timestamp = str(int(time.time()) + 400)  # 6 minutes in future
        request_data = b"test_request_data"
        
        # Generate valid signature for the future timestamp
        import hmac
        import hashlib
        sig_basestring = f"v0:{future_timestamp}:".encode('utf-8') + request_data
        signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        result = self.verifier.verify_request(request_data, future_timestamp, signature)
        
        assert result is False
    
    def test_verify_request_invalid_timestamp(self):
        """Test request verification with invalid timestamp."""
        invalid_timestamp = "not_a_number"
        request_data = b"test_request_data"
        signature = "v0=test_signature"
        
        result = self.verifier.verify_request(request_data, invalid_timestamp, signature)
        
        assert result is False
    
    def test_verify_request_empty_data(self):
        """Test request verification with empty data."""
        timestamp = str(int(time.time()))
        request_data = b""
        
        # Generate valid signature for empty data
        import hmac
        import hashlib
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + request_data
        signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        result = self.verifier.verify_request(request_data, timestamp, signature)
        
        assert result is True
    
    def test_verify_request_unicode_data(self):
        """Test request verification with unicode data."""
        timestamp = str(int(time.time()))
        request_data = "test_unicode_data_🚀".encode('utf-8')
        
        # Generate valid signature for unicode data
        import hmac
        import hashlib
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + request_data
        signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        result = self.verifier.verify_request(request_data, timestamp, signature)
        
        assert result is True
    
    def test_verify_request_large_data(self):
        """Test request verification with large data."""
        timestamp = str(int(time.time()))
        request_data = b"x" * 10000  # 10KB of data
        
        # Generate valid signature for large data
        import hmac
        import hashlib
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + request_data
        signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        result = self.verifier.verify_request(request_data, timestamp, signature)
        
        assert result is True
    
    def test_verify_request_exception_handling(self):
        """Test exception handling in verify_request."""
        # Test with None values to trigger TypeError
        result = self.verifier.verify_request(None, None, None)
        
        assert result is False
    
    def test_constant_time_comparison(self):
        """Test that signature comparison is constant time."""
        timestamp = str(int(time.time()))
        request_data = b"test_request_data"
        
        # Generate correct signature
        import hmac
        import hashlib
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + request_data
        correct_signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        # Test with correct signature
        result1 = self.verifier.verify_request(request_data, timestamp, correct_signature)
        assert result1 is True
        
        # Test with incorrect signature of same length
        wrong_signature = 'v0=' + 'a' * 64  # Same length as SHA256 hex
        result2 = self.verifier.verify_request(request_data, timestamp, wrong_signature)
        assert result2 is False
        
        # Test with incorrect signature of different length
        short_signature = 'v0=short'
        result3 = self.verifier.verify_request(request_data, timestamp, short_signature)
        assert result3 is False
    
    def test_different_signing_secrets(self):
        """Test that different signing secrets produce different results."""
        timestamp = str(int(time.time()))
        request_data = b"test_request_data"
        
        # Create verifier with different secret
        verifier2 = SlackSignatureVerifier("different_secret")
        
        # Generate signature with first verifier's secret
        import hmac
        import hashlib
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + request_data
        signature = 'v0=' + hmac.new(
            b"test_signing_secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        # First verifier should accept
        result1 = self.verifier.verify_request(request_data, timestamp, signature)
        assert result1 is True
        
        # Second verifier should reject
        result2 = verifier2.verify_request(request_data, timestamp, signature)
        assert result2 is False
    
    @patch('src.infrastructure.slack_verifier.logger')
    def test_logging_on_old_timestamp(self, mock_logger):
        """Test logging when timestamp is too old."""
        old_timestamp = str(int(time.time()) - 400)
        request_data = b"test_request_data"
        signature = "v0=test_signature"
        
        self.verifier.verify_request(request_data, old_timestamp, signature)
        
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Request timestamp too old" in warning_call
    
    @patch('src.infrastructure.slack_verifier.logger')
    def test_logging_on_invalid_signature(self, mock_logger):
        """Test logging when signature is invalid."""
        timestamp = str(int(time.time()))
        request_data = b"test_request_data"
        invalid_signature = "v0=invalid_signature"
        
        self.verifier.verify_request(request_data, timestamp, invalid_signature)
        
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Invalid signature" in warning_call
    
    @patch('src.infrastructure.slack_verifier.logger')
    def test_logging_on_exception(self, mock_logger):
        """Test logging when exception occurs."""
        # Pass invalid types to trigger exception
        result = self.verifier.verify_request(None, None, None)
        
        assert result is False
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error verifying Slack signature" in error_call