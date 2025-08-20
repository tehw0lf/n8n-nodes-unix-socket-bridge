"""
Tests for authentication functionality including hashed tokens
"""

import pytest
import hashlib
import os
import json
import tempfile
import socket
import threading
import time
from unittest.mock import patch, MagicMock

# Import the server module using importlib for hyphenated filename
import sys
import importlib.util
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

socket_server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "socket-server.py")
spec = importlib.util.spec_from_file_location("socket_server", socket_server_path)
socket_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(socket_server)
ConfigurableSocketServer = socket_server.ConfigurableSocketServer
AuthRateLimiter = socket_server.AuthRateLimiter


class TestTokenHashing:
    """Test token hashing utilities"""

    def test_hash_token_basic(self):
        """Test basic token hashing"""
        token = "test-token-123"
        expected_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        
        actual_hash = ConfigurableSocketServer.hash_token(token)
        
        assert actual_hash == expected_hash
        assert len(actual_hash) == 64  # SHA-256 produces 64-character hex string

    def test_hash_token_different_inputs(self):
        """Test that different inputs produce different hashes"""
        token1 = "token1"
        token2 = "token2"
        
        hash1 = ConfigurableSocketServer.hash_token(token1)
        hash2 = ConfigurableSocketServer.hash_token(token2)
        
        assert hash1 != hash2

    def test_hash_token_consistent(self):
        """Test that same input always produces same hash"""
        token = "consistent-token"
        
        hash1 = ConfigurableSocketServer.hash_token(token)
        hash2 = ConfigurableSocketServer.hash_token(token)
        
        assert hash1 == hash2

    def test_verify_token_hash_valid(self):
        """Test token verification with valid hash"""
        token = "verify-test-token"
        token_hash = ConfigurableSocketServer.hash_token(token)
        
        is_valid = ConfigurableSocketServer.verify_token_hash(token, token_hash)
        
        assert is_valid is True

    def test_verify_token_hash_invalid(self):
        """Test token verification with invalid hash"""
        token = "verify-test-token"
        wrong_hash = "invalid-hash-value"
        
        is_valid = ConfigurableSocketServer.verify_token_hash(token, wrong_hash)
        
        assert is_valid is False

    def test_verify_token_hash_wrong_token(self):
        """Test token verification with wrong token"""
        token = "correct-token"
        wrong_token = "wrong-token"
        token_hash = ConfigurableSocketServer.hash_token(token)
        
        is_valid = ConfigurableSocketServer.verify_token_hash(wrong_token, token_hash)
        
        assert is_valid is False


class TestAuthenticationModes:
    """Test different authentication modes"""

    def create_test_config(self):
        """Create a minimal test configuration"""
        return {
            "name": "Test Server",
            "socket_path": "/tmp/test-auth.sock",
            "allowed_executable_dirs": ["/usr/bin/", "/bin/", "/usr/local/bin/"],
            "commands": {
                "ping": {
                    "description": "Test ping",
                    "executable": ["echo", "pong"],
                    "timeout": 5
                }
            }
        }

    def test_auth_disabled_mode(self):
        """Test server initialization with auth disabled"""
        config = self.create_test_config()
        
        with patch.dict(os.environ, {'AUTH_ENABLED': 'false'}):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            try:
                server = ConfigurableSocketServer(config_path)
                
                assert server.auth_enabled is False
                assert server.auth_token_hash is None
                
            finally:
                os.unlink(config_path)

    def test_plaintext_token_mode(self):
        """Test server initialization with plaintext token - should fail because only hashed tokens are supported"""
        config = self.create_test_config()
        test_token = "test-plaintext-token"
        
        with patch.dict(os.environ, {'AUTH_ENABLED': 'true', 'AUTH_TOKEN': test_token}):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            try:
                # This should raise SystemExit because no hashed token is configured
                with pytest.raises(SystemExit):
                    ConfigurableSocketServer(config_path)
                
            finally:
                os.unlink(config_path)

    def test_hashed_token_mode(self):
        """Test server initialization with hashed token"""
        config = self.create_test_config()
        test_token = "test-hashed-token"
        test_hash = ConfigurableSocketServer.hash_token(test_token)
        
        with patch.dict(os.environ, {'AUTH_ENABLED': 'true', 'AUTH_TOKEN_HASH': test_hash}):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            try:
                server = ConfigurableSocketServer(config_path)
                
                assert server.auth_enabled is True
                assert server.auth_token_hash == test_hash
                
            finally:
                os.unlink(config_path)

    def test_hashed_token_priority_over_plaintext(self):
        """Test that hashed token takes priority over plaintext"""
        config = self.create_test_config()
        test_token = "test-token"
        test_hash = ConfigurableSocketServer.hash_token(test_token)
        
        env = {
            'AUTH_ENABLED': 'true',
            'AUTH_TOKEN': test_token,
            'AUTH_TOKEN_HASH': test_hash
        }
        
        with patch.dict(os.environ, env):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            try:
                server = ConfigurableSocketServer(config_path)
                
                assert server.auth_enabled is True
                assert server.auth_token_hash == test_hash
                
            finally:
                os.unlink(config_path)


class TestAuthenticationValidation:
    """Test authentication validation logic"""

    def create_server_with_auth(self, auth_mode='hashed', token='test-token'):
        """Helper to create server with specific auth configuration"""
        config = {
            "name": "Test Server",
            "socket_path": "/tmp/test-auth.sock",
            "allowed_executable_dirs": ["/usr/bin/", "/bin/", "/usr/local/bin/"],
            "commands": {
                "ping": {"executable": ["echo", "pong"], "timeout": 5}
            }
        }
        
        env_vars = {'AUTH_ENABLED': 'true'}
        # Only hashed tokens are supported now
        env_vars['AUTH_TOKEN_HASH'] = ConfigurableSocketServer.hash_token(token)
            
        with patch.dict(os.environ, env_vars):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            server = ConfigurableSocketServer(config_path)
            # Clean up config file
            os.unlink(config_path)
            return server

    def test_auth_disabled_allows_all(self):
        """Test that disabled auth allows all requests"""
        config = {
            "name": "Test Server",
            "socket_path": "/tmp/test.sock",
            "allowed_executable_dirs": ["/usr/bin/", "/bin/", "/usr/local/bin/"],
            "commands": {"ping": {"executable": ["echo", "pong"]}}
        }
        
        with patch.dict(os.environ, {'AUTH_ENABLED': 'false'}):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            try:
                server = ConfigurableSocketServer(config_path)
                
                # Should allow request without token
                valid, error = server.validate_auth({}, "test_client")
                assert valid is True
                assert error == ""
                
                # Should allow request with token (token ignored)
                valid, error = server.validate_auth({"auth_token": "any-token"}, "test_client")
                assert valid is True
                assert error == ""
                
            finally:
                os.unlink(config_path)

    def test_plaintext_auth_validation(self):
        """Test plaintext token authentication validation - should fail because only hashed tokens are supported"""
        config = {
            "name": "Test Server",
            "socket_path": "/tmp/test-auth.sock",
            "allowed_executable_dirs": ["/usr/bin/", "/bin/", "/usr/local/bin/"],
            "commands": {
                "ping": {"executable": ["echo", "pong"], "timeout": 5}
            }
        }
        
        # Try to create server with only AUTH_TOKEN (no AUTH_TOKEN_HASH) - should fail
        with patch.dict(os.environ, {'AUTH_ENABLED': 'true', 'AUTH_TOKEN': 'plaintext-token'}):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
            
            try:
                # This should raise SystemExit because no AUTH_TOKEN_HASH is provided
                with pytest.raises(SystemExit):
                    ConfigurableSocketServer(config_path)
            finally:
                os.unlink(config_path)

    def test_hashed_auth_validation(self):
        """Test hashed token authentication validation"""
        correct_token = "correct-hashed-token"
        correct_token_hash = ConfigurableSocketServer.hash_token(correct_token)
        server = self.create_server_with_auth('hashed', correct_token)
        
        # Should succeed with correct token hash (client sends hash, server has hash)
        valid, error = server.validate_auth({"auth_token_hash": correct_token_hash}, "test_client")
        assert valid is True
        assert error == ""
        
        # Should fail with wrong token hash
        valid, error = server.validate_auth({"auth_token_hash": "wrong-hash"}, "test_client")
        assert valid is False
        assert error == "auth_failed"
        
        # Should fail with no token
        valid, error = server.validate_auth({}, "test_client")
        assert valid is False
        assert error == "auth_failed"

    def test_auth_rate_limiting_integration(self):
        """Test that rate limiting works with authentication"""
        correct_token = "rate-limit-token"
        server = self.create_server_with_auth('hashed', correct_token)
        
        # First few failures should return auth_failed
        for i in range(2):
            valid, error = server.validate_auth({"auth_token": "wrong-token"}, "test_client")
            assert valid is False
            assert error == "auth_failed"
        
        # After enough failures, should get rate limited
        # The exact number depends on the AUTH_MAX_ATTEMPTS setting
        for i in range(5):
            valid, error = server.validate_auth({"auth_token": "wrong-token"}, "test_client")
            assert valid is False
            # Could be auth_failed or rate_limited depending on attempt number
            assert error in ["auth_failed", "rate_limited"]
        
        # Eventually should get rate_limited
        valid, error = server.validate_auth({"auth_token": "wrong-token"}, "test_client")
        assert valid is False
        # Should be rate limited by now
        assert error == "rate_limited"


class TestAuthRateLimiter:
    """Test the AuthRateLimiter class"""

    def test_rate_limiter_basic(self):
        """Test basic rate limiting functionality"""
        limiter = AuthRateLimiter(max_attempts=3, window_seconds=60, block_duration=60)
        client_id = "test_client"
        
        # Should allow initial attempts
        assert limiter.check_rate_limit(client_id) is True
        
        # Record failures
        limiter.record_failure(client_id)
        assert limiter.check_rate_limit(client_id) is True
        
        limiter.record_failure(client_id)
        assert limiter.check_rate_limit(client_id) is True
        
        limiter.record_failure(client_id)
        # After max attempts, should be blocked
        assert limiter.check_rate_limit(client_id) is False

    def test_rate_limiter_success_reset(self):
        """Test that successful auth resets the counter"""
        limiter = AuthRateLimiter(max_attempts=3, window_seconds=60, block_duration=60)
        client_id = "test_client"
        
        # Make some failures
        limiter.record_failure(client_id)
        limiter.record_failure(client_id)
        
        # Should still be allowed
        assert limiter.check_rate_limit(client_id) is True
        
        # Success should reset counter
        limiter.record_success(client_id)
        
        # Should be able to make more attempts
        assert limiter.check_rate_limit(client_id) is True
        limiter.record_failure(client_id)
        assert limiter.check_rate_limit(client_id) is True

    def test_rate_limiter_cleanup(self):
        """Test that old entries are cleaned up"""
        limiter = AuthRateLimiter(max_attempts=3, window_seconds=1, block_duration=1)
        client_id = "test_client"
        
        # Make failures
        limiter.record_failure(client_id)
        limiter.record_failure(client_id)
        
        # Should have entries
        assert len(limiter.failed_attempts[client_id]) == 2
        
        # Wait for window to pass
        time.sleep(1.1)
        
        # Cleanup should remove old entries
        limiter.cleanup_old_entries()
        assert len(limiter.failed_attempts.get(client_id, [])) == 0


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])