"""
Unit tests for ConfigurableSocketServer class
Tests the improved server with rate limiting, size limits, and security features
"""
import pytest
import json
import subprocess
import tempfile
from unittest.mock import Mock, patch
import sys
import os
import time

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from socket-server.py (with hyphen)
import importlib.util
socket_server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "socket-server.py")
spec = importlib.util.spec_from_file_location("socket_server", socket_server_path)
socket_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(socket_server)
ConfigurableSocketServer = socket_server.ConfigurableSocketServer


class TestConfigurableSocketServer:
    """Test cases for ConfigurableSocketServer class"""
    
    def test_init_with_valid_config(self, config_file):
        """Test server initialization with valid configuration"""
        server = ConfigurableSocketServer(config_file)
        
        assert server.config["name"] == "Test Server"
        assert server.config["description"] == "A test server for unit testing"
        assert "commands" in server.config
        assert "echo" in server.config["commands"]
        assert server.running == False
        assert server.server_socket is None
        
        # Test new features
        assert hasattr(server, 'rate_limit')
        assert hasattr(server, 'max_request_size')
        assert hasattr(server, 'max_output_size')
    
    def test_init_with_rate_limiting_config(self, sample_config):
        """Test server initialization with rate limiting configuration"""
        config = sample_config.copy()
        config['enable_rate_limit'] = True
        config['rate_limit'] = {'requests': 10, 'window': 60}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            assert server.rate_limit['requests'] == 10
            assert server.rate_limit['window'] == 60
        finally:
            os.unlink(temp_config)
    
    def test_init_with_size_limits(self, sample_config):
        """Test server initialization with custom size limits"""
        config = sample_config.copy()
        config['max_request_size'] = 2097152  # 2MB
        config['max_output_size'] = 500000    # 500KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            assert server.max_request_size == 2097152
            assert server.max_output_size == 500000
        finally:
            os.unlink(temp_config)
    
    def test_validate_executable_path_security(self, config_file):
        """Test executable path validation for security"""
        server = ConfigurableSocketServer(config_file)
        
        # Valid paths
        assert server.validate_executable_path(['echo']) == True
        assert server.validate_executable_path(['/bin/echo']) == True
        assert server.validate_executable_path(['/usr/bin/ls']) == True
        
        # Invalid paths - security violations
        assert server.validate_executable_path(['/etc/passwd']) == False
        assert server.validate_executable_path(['../../bin/evil']) == False
        assert server.validate_executable_path(['/home/user/script.sh']) == False
        assert server.validate_executable_path([]) == False
    
    def test_rate_limiting_functionality(self, config_file):
        """Test rate limiting with improved implementation"""
        server = ConfigurableSocketServer(config_file)
        server.rate_limit = {'requests': 3, 'window': 2}
        
        client_id = 'test_client_123'
        
        # First 3 requests should pass
        assert server.check_rate_limit(client_id) == True
        assert server.check_rate_limit(client_id) == True
        assert server.check_rate_limit(client_id) == True
        
        # 4th request should fail
        assert server.check_rate_limit(client_id) == False
        
        # After waiting for window, should pass again
        time.sleep(2.1)
        assert server.check_rate_limit(client_id) == True
    
    def test_receive_full_message(self, config_file):
        """Test the receive_full_message method for handling large requests"""
        server = ConfigurableSocketServer(config_file)
        
        # Create mock socket with chunked data
        mock_socket = Mock()
        
        # Simulate receiving data in chunks
        test_message = json.dumps({"command": "test", "data": "x" * 1000})
        chunks = [test_message[i:i+100].encode() for i in range(0, len(test_message), 100)]
        chunks.append(b'')  # End marker
        
        mock_socket.recv.side_effect = chunks
        mock_socket.settimeout = Mock()
        
        # Test receiving full message
        result = server.receive_full_message(mock_socket)
        assert result == test_message
        
    def test_receive_message_size_limit(self, config_file):
        """Test that receive_full_message enforces size limits"""
        server = ConfigurableSocketServer(config_file)
        server.max_request_size = 100  # Very small limit for testing
        
        mock_socket = Mock()
        mock_socket.recv.return_value = b'x' * 200  # Exceeds limit
        mock_socket.settimeout = Mock()
        
        # Should raise ValueError for exceeding size
        with pytest.raises(ValueError) as excinfo:
            server.receive_full_message(mock_socket)
        assert "too large" in str(excinfo.value).lower()


class TestRequestValidation:
    """Test cases for request validation"""
    
    def test_validate_request_with_parameter_max_length(self, sample_config):
        """Test validation of parameter max_length"""
        config = sample_config.copy()
        config['commands']['test_length'] = {
            'executable': ['echo'],
            'parameters': {
                'text': {
                    'type': 'string',
                    'max_length': 10
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Valid length
            request = {'command': 'test_length', 'parameters': {'text': 'short'}}
            valid, error = server.validate_request(request)
            assert valid == True
            
            # Exceeds max length
            request = {'command': 'test_length', 'parameters': {'text': 'x' * 20}}
            valid, error = server.validate_request(request)
            assert valid == False
            assert "Invalid value" in error
        finally:
            os.unlink(temp_config)
    
    def test_validate_request_missing_command(self, config_file):
        """Test validation fails when command field is missing"""
        server = ConfigurableSocketServer(config_file)
        
        is_valid, error = server.validate_request({})
        assert not is_valid
        assert "Missing 'command' field" in error
    
    def test_validate_request_introspection_commands(self, config_file):
        """Test validation passes for introspection commands"""
        server = ConfigurableSocketServer(config_file)
        
        # Test __introspect__ command
        is_valid, error = server.validate_request({"command": "__introspect__"})
        assert is_valid
        assert error == ""
        
        # Test __ping__ command
        is_valid, error = server.validate_request({"command": "__ping__"})
        assert is_valid
        assert error == ""


class TestCommandExecution:
    """Test cases for command execution with improved features"""
    
    def test_execute_ping_with_timestamp(self, config_file):
        """Test that ping command includes timestamp"""
        server = ConfigurableSocketServer(config_file)
        
        request = {"command": "__ping__"}
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert result["message"] == "pong"
        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)
    
    @patch('subprocess.run')
    def test_execute_command_with_output_truncation(self, mock_subprocess, config_file):
        """Test that large output is truncated"""
        server = ConfigurableSocketServer(config_file)
        server.max_output_size = 100  # Small limit for testing
        
        # Mock large output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "x" * 200  # Exceeds limit
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        request = {"command": "simple"}
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert len(result["stdout"]) <= server.max_output_size + 50  # Allow for truncation message
        assert "truncated" in result["stdout"]
    
    @patch('subprocess.run')
    def test_execute_command_with_custom_env(self, mock_subprocess, sample_config):
        """Test command execution with custom environment variables"""
        config = sample_config.copy()
        config['commands']['custom_env'] = {
            'executable': ['printenv'],
            'env': {'CUSTOM_VAR': 'custom_value', 'PATH': '/custom/path'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            request = {"command": "custom_env"}
            result = server.execute_command(request)
            
            # Verify custom env was used
            mock_subprocess.assert_called_once()
            call_kwargs = mock_subprocess.call_args[1]
            assert call_kwargs['env']['CUSTOM_VAR'] == 'custom_value'
            assert call_kwargs['env']['PATH'] == '/custom/path'
        finally:
            os.unlink(temp_config)
    
    @patch('subprocess.run')
    def test_execute_command_with_debug_mode(self, mock_subprocess, sample_config):
        """Test that debug mode provides detailed error information"""
        config = sample_config.copy()
        config['debug'] = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Mock exception
            mock_subprocess.side_effect = Exception("Detailed error message")
            
            request = {"command": "simple"}
            result = server.execute_command(request)
            
            assert result["success"] == False
            assert "details" in result
            assert "Detailed error message" in result["details"]
        finally:
            os.unlink(temp_config)


class TestParameterValidation:
    """Test cases for enhanced parameter validation"""
    
    def test_validate_parameter_all_types(self, config_file):
        """Test validation of all parameter types"""
        server = ConfigurableSocketServer(config_file)
        
        # String type
        assert server.validate_parameter_value("text", {"type": "string"}) == True
        assert server.validate_parameter_value(123, {"type": "string"}) == False
        
        # Number type
        assert server.validate_parameter_value(42, {"type": "number"}) == True
        assert server.validate_parameter_value(3.14, {"type": "number"}) == True
        assert server.validate_parameter_value("not_number", {"type": "number"}) == False
        
        # Boolean type
        assert server.validate_parameter_value(True, {"type": "boolean"}) == True
        assert server.validate_parameter_value(False, {"type": "boolean"}) == True
        assert server.validate_parameter_value("true", {"type": "boolean"}) == False


class TestConcurrency:
    """Test cases for concurrent request handling"""
    
    def test_threading_configuration(self, sample_config):
        """Test that threading can be enabled via configuration"""
        config = sample_config.copy()
        config['enable_threading'] = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            assert server.config.get('enable_threading') == True
        finally:
            os.unlink(temp_config)


class TestEnhancedRateLimiting:
    """Test cases for enhanced rate limiting features"""
    
    def test_rate_limiting_with_disabled_config(self, sample_config):
        """Test that rate limiting can be completely disabled"""
        config = sample_config.copy()
        config['enable_rate_limit'] = False
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            client_id = 'test_client_unlimited'
            
            # Should allow unlimited requests when disabled
            for _ in range(100):
                assert server.check_rate_limit(client_id) == True
        finally:
            os.unlink(temp_config)
    
    def test_rate_limiting_multiple_clients(self, config_file):
        """Test rate limiting works independently for different clients"""
        server = ConfigurableSocketServer(config_file)
        server.rate_limit = {'requests': 2, 'window': 60}
        
        client1 = 'client_1'
        client2 = 'client_2'
        
        # Each client should have independent rate limits
        assert server.check_rate_limit(client1) == True
        assert server.check_rate_limit(client1) == True
        assert server.check_rate_limit(client1) == False  # Exceeded for client1
        
        # Client2 should still be allowed
        assert server.check_rate_limit(client2) == True
        assert server.check_rate_limit(client2) == True
        assert server.check_rate_limit(client2) == False  # Exceeded for client2
    
    def test_rate_limiting_window_expiration(self, config_file):
        """Test that rate limit window properly expires old requests"""
        server = ConfigurableSocketServer(config_file)
        server.rate_limit = {'requests': 2, 'window': 1}  # 1 second window
        
        client_id = 'test_client_window'
        
        # Use up the rate limit
        assert server.check_rate_limit(client_id) == True
        assert server.check_rate_limit(client_id) == True
        assert server.check_rate_limit(client_id) == False
        
        # Wait for window to expire
        time.sleep(1.2)
        
        # Should be allowed again
        assert server.check_rate_limit(client_id) == True


class TestEnhancedSizeLimits:
    """Test cases for enhanced size limit features"""
    
    def test_custom_request_size_limits(self, sample_config):
        """Test custom request size limits"""
        config = sample_config.copy()
        config['max_request_size'] = 500  # Very small for testing
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            assert server.max_request_size == 500
            
            # Test that the limit is enforced in receive_full_message
            mock_socket = Mock()
            large_data = 'x' * 600  # Exceeds limit
            mock_socket.recv.return_value = large_data.encode()
            mock_socket.settimeout = Mock()
            
            with pytest.raises(ValueError) as excinfo:
                server.receive_full_message(mock_socket)
            assert "too large" in str(excinfo.value).lower()
        finally:
            os.unlink(temp_config)
    
    def test_custom_output_size_limits(self, sample_config):
        """Test custom output size limits"""
        config = sample_config.copy()
        config['max_output_size'] = 50  # Very small for testing
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            assert server.max_output_size == 50
        finally:
            os.unlink(temp_config)
    
    @patch('subprocess.run')
    def test_output_truncation_with_message(self, mock_subprocess, config_file):
        """Test that output truncation includes helpful message"""
        server = ConfigurableSocketServer(config_file)
        server.max_output_size = 20  # Very small for testing
        
        # Mock large output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "x" * 50  # Exceeds limit
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        request = {"command": "simple"}
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert len(result["stdout"]) <= server.max_output_size + 50  # Allow for truncation message
        assert "truncated" in result["stdout"]


class TestEnhancedSecurity:
    """Test cases for enhanced security features"""
    
    def test_executable_path_validation_with_allowed_dirs(self, sample_config):
        """Test executable path validation with allowed directories"""
        config = sample_config.copy()
        config['allowed_executable_dirs'] = ['/usr/bin/', '/bin/', '/usr/local/bin/']
        config['commands']['secure_test'] = {
            'executable': ['/usr/bin/echo'],
            'timeout': 5
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Valid paths
            assert server.validate_executable_path(['/usr/bin/echo']) == True
            assert server.validate_executable_path(['/bin/ls']) == True
            assert server.validate_executable_path(['echo']) == True  # Relative path in allowed dir
            
            # Invalid paths
            assert server.validate_executable_path(['/tmp/malicious']) == False
            assert server.validate_executable_path(['/etc/passwd']) == False
            assert server.validate_executable_path(['../../bin/evil']) == False
            
        finally:
            os.unlink(temp_config)
    
    def test_executable_path_validation_without_allowed_dirs(self, sample_config):
        """Test that validation fails gracefully without allowed_executable_dirs"""
        config = sample_config.copy()
        # Remove allowed_executable_dirs to test fallback behavior
        if 'allowed_executable_dirs' in config:
            del config['allowed_executable_dirs']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            # Server initialization should fail due to invalid executable paths
            with pytest.raises(SystemExit):
                ConfigurableSocketServer(temp_config)
            
        finally:
            os.unlink(temp_config)
    
    def test_security_config_validation_on_startup(self, sample_config):
        """Test that invalid executables are caught during config loading"""
        config = sample_config.copy()
        config['allowed_executable_dirs'] = ['/usr/bin/']
        config['commands']['invalid_cmd'] = {
            'executable': ['/tmp/evil_script'],  # Not in allowed dirs
            'timeout': 5
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            with pytest.raises(SystemExit):
                # Should fail during initialization
                ConfigurableSocketServer(temp_config)
        finally:
            os.unlink(temp_config)


class TestEnhancedParameterValidation:
    """Test cases for enhanced parameter validation"""
    
    def test_parameter_max_length_validation(self, sample_config):
        """Test parameter max_length validation"""
        config = sample_config.copy()
        config['commands']['length_test'] = {
            'executable': ['echo'],
            'parameters': {
                'short_text': {
                    'type': 'string',
                    'max_length': 5
                },
                'long_text': {
                    'type': 'string',
                    'max_length': 100
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Valid lengths
            request = {'command': 'length_test', 'parameters': {'short_text': 'hi'}}
            valid, error = server.validate_request(request)
            assert valid == True
            
            # Invalid length
            request = {'command': 'length_test', 'parameters': {'short_text': 'toolong'}}
            valid, error = server.validate_request(request)
            assert valid == False
            assert "Invalid value" in error
            
        finally:
            os.unlink(temp_config)
    
    def test_parameter_enum_validation(self, sample_config):
        """Test parameter enum validation"""
        config = sample_config.copy()
        config['commands']['enum_test'] = {
            'executable': ['echo'],
            'parameters': {
                'level': {
                    'type': 'string',
                    'enum': ['debug', 'info', 'warning', 'error']
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Valid enum value
            request = {'command': 'enum_test', 'parameters': {'level': 'info'}}
            valid, error = server.validate_request(request)
            assert valid == True
            
            # Invalid enum value
            request = {'command': 'enum_test', 'parameters': {'level': 'invalid'}}
            valid, error = server.validate_request(request)
            assert valid == False
            
        finally:
            os.unlink(temp_config)
    
    def test_parameter_pattern_validation(self, sample_config):
        """Test parameter regex pattern validation"""
        config = sample_config.copy()
        config['commands']['pattern_test'] = {
            'executable': ['echo'],
            'parameters': {
                'email': {
                    'type': 'string',
                    'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Valid email
            request = {'command': 'pattern_test', 'parameters': {'email': 'test@example.com'}}
            valid, error = server.validate_request(request)
            assert valid == True
            
            # Invalid email
            request = {'command': 'pattern_test', 'parameters': {'email': 'not_an_email'}}
            valid, error = server.validate_request(request)
            assert valid == False
            
        finally:
            os.unlink(temp_config)


class TestThreadingSupport:
    """Test cases for threading support"""
    
    def test_threading_disabled_by_default(self, config_file):
        """Test that threading is disabled by default"""
        server = ConfigurableSocketServer(config_file)
        assert server.config.get('enable_threading', False) == False
    
    def test_threading_configuration(self, sample_config):
        """Test threading configuration"""
        config = sample_config.copy()
        config['enable_threading'] = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            assert server.config.get('enable_threading') == True
        finally:
            os.unlink(temp_config)


class TestDebugMode:
    """Test cases for debug mode functionality"""
    
    @patch('subprocess.run')
    def test_debug_mode_enabled_shows_details(self, mock_subprocess, sample_config):
        """Test that debug mode shows detailed error information"""
        config = sample_config.copy()
        config['debug'] = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Mock exception with detailed message
            mock_subprocess.side_effect = Exception("Detailed debug information")
            
            request = {"command": "simple"}
            result = server.execute_command(request)
            
            assert result["success"] == False
            assert "details" in result
            assert "Detailed debug information" in result["details"]
        finally:
            os.unlink(temp_config)
    
    @patch('subprocess.run')
    def test_debug_mode_disabled_hides_details(self, mock_subprocess, sample_config):
        """Test that production mode hides detailed error information"""
        config = sample_config.copy()
        config['debug'] = False
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Mock exception
            mock_subprocess.side_effect = Exception("Sensitive internal error")
            
            request = {"command": "simple"}
            result = server.execute_command(request)
            
            assert result["success"] == False
            assert result.get("details") is None
            assert "Sensitive internal error" not in str(result)
        finally:
            os.unlink(temp_config)


class TestEnhancedResponseFormatting:
    """Test cases for enhanced response formatting"""
    
    @patch('subprocess.run')
    def test_custom_response_formatting(self, mock_subprocess, sample_config):
        """Test custom response formatting configuration"""
        config = sample_config.copy()
        config['commands']['json_response'] = {
            'executable': ['echo'],
            'response_format': {
                'parse_json': True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Mock JSON output
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = '{"key": "value", "number": 42}'
            mock_result.stderr = ''
            mock_subprocess.return_value = mock_result
            
            request = {"command": "json_response"}
            result = server.execute_command(request)
            
            assert result["success"] == True
            assert "parsed_output" in result
            assert result["parsed_output"]["key"] == "value"
            assert result["parsed_output"]["number"] == 42
        finally:
            os.unlink(temp_config)
    
    @patch('subprocess.run')
    def test_json_parse_error_handling(self, mock_subprocess, sample_config):
        """Test handling of JSON parse errors in response formatting"""
        config = sample_config.copy()
        config['commands']['bad_json'] = {
            'executable': ['echo'],
            'response_format': {
                'parse_json': True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Mock invalid JSON output
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'not valid json {'
            mock_result.stderr = ''
            mock_subprocess.return_value = mock_result
            
            request = {"command": "bad_json"}
            result = server.execute_command(request)
            
            assert result["success"] == True
            assert "parse_error" in result
            assert "not valid JSON" in result["parse_error"]
        finally:
            os.unlink(temp_config)


class TestReceiveFullMessage:
    """Test cases for the enhanced receive_full_message method"""
    
    def test_receive_message_with_timeout(self, config_file):
        """Test receive_full_message timeout handling"""
        server = ConfigurableSocketServer(config_file)
        
        mock_socket = Mock()
        mock_socket.settimeout = Mock()
        # Mock recv to raise socket.timeout (which is TimeoutError)
        mock_socket.recv.side_effect = TimeoutError()
        
        # Should raise ValueError for empty request after timeout
        with pytest.raises(ValueError) as excinfo:
            server.receive_full_message(mock_socket)
        assert "Empty request" in str(excinfo.value)
    
    def test_receive_message_with_unicode_error(self, config_file):
        """Test receive_full_message Unicode decode error handling"""
        server = ConfigurableSocketServer(config_file)
        
        mock_socket = Mock()
        mock_socket.settimeout = Mock()
        mock_socket.recv.return_value = b'\xff\xfe'  # Invalid UTF-8
        
        with pytest.raises(ValueError) as excinfo:
            server.receive_full_message(mock_socket)
        assert "Invalid UTF-8" in str(excinfo.value)
    
    def test_receive_message_chunked_json(self, config_file):
        """Test receive_full_message with chunked JSON data"""
        server = ConfigurableSocketServer(config_file)
        
        test_message = json.dumps({"command": "test", "data": "x" * 500})
        chunks = [test_message[i:i+50].encode() for i in range(0, len(test_message), 50)]
        chunks.append(b'')  # End marker
        
        mock_socket = Mock()
        mock_socket.settimeout = Mock()
        mock_socket.recv.side_effect = chunks
        
        result = server.receive_full_message(mock_socket)
        assert result == test_message
        parsed = json.loads(result)
        assert parsed["command"] == "test"


class TestErrorHandling:
    """Test cases for improved error handling"""
    
    @patch('subprocess.run')
    def test_command_timeout_with_custom_timeout(self, mock_subprocess, sample_config):
        """Test command timeout with custom timeout value"""
        config = sample_config.copy()
        config['commands']['slow'] = {
            'executable': ['sleep', '10'],
            'timeout': 1  # Very short timeout
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            
            # Mock timeout
            mock_subprocess.side_effect = subprocess.TimeoutExpired(
                cmd=['sleep', '10'], timeout=1
            )
            
            request = {"command": "slow"}
            result = server.execute_command(request)
            
            assert result["success"] == False
            assert "timeout" in result["error"].lower()
            assert "1 seconds" in result["error"]
        finally:
            os.unlink(temp_config)