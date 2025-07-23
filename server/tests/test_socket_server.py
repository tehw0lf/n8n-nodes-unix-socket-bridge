"""
Unit tests for ConfigurableSocketServer class
"""
import pytest
import json
import subprocess
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

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
    
    def test_init_with_invalid_config(self, invalid_config_file):
        """Test server initialization fails with invalid configuration"""
        with pytest.raises(SystemExit):
            ConfigurableSocketServer(invalid_config_file)
    
    def test_load_config_validates_required_fields(self, sample_config):
        """Test that load_config validates all required fields"""
        # Create server instance for testing load_config method
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f)
            temp_config = f.name
        
        try:
            server = ConfigurableSocketServer(temp_config)
            config = server.config
            
            # Check all required fields are present
            assert "name" in config
            assert "socket_path" in config
            assert "commands" in config
        finally:
            os.unlink(temp_config)
    
    def test_load_config_validates_command_structure(self):
        """Test that load_config validates command structure"""
        invalid_command_config = {
            "name": "Test Server",
            "socket_path": "/tmp/test.sock",
            "commands": {
                "broken_command": {
                    # Missing 'executable' field
                    "description": "A broken command"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_command_config, f)
            temp_config = f.name
        
        try:
            with pytest.raises(SystemExit):
                ConfigurableSocketServer(temp_config)
        finally:
            os.unlink(temp_config)

class TestRequestValidation:
    """Test cases for request validation"""
    
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
    
    def test_validate_request_unknown_command(self, config_file):
        """Test validation fails for unknown commands"""
        server = ConfigurableSocketServer(config_file)
        
        is_valid, error = server.validate_request({"command": "unknown_command"})
        assert not is_valid
        assert "Unknown command" in error
        assert "echo" in error  # Should list available commands
    
    def test_validate_request_with_valid_command(self, config_file):
        """Test validation passes for valid commands"""
        server = ConfigurableSocketServer(config_file)
        
        request = {
            "command": "echo",
            "parameters": {
                "message": "test message"
            }
        }
        
        is_valid, error = server.validate_request(request)
        assert is_valid
        assert error == ""
    
    def test_validate_request_missing_required_parameter(self, config_file):
        """Test validation fails when required parameters are missing"""
        server = ConfigurableSocketServer(config_file)
        
        request = {"command": "echo"}  # Missing required 'message' parameter
        
        is_valid, error = server.validate_request(request)
        assert not is_valid
        assert "Missing required parameter: message" in error
    
    def test_validate_request_with_optional_parameters(self, config_file):
        """Test validation passes with optional parameters"""
        server = ConfigurableSocketServer(config_file)
        
        request = {
            "command": "with-flags",
            "parameters": {
                "long": True,
                "path": "/tmp"
            }
        }
        
        is_valid, error = server.validate_request(request)
        assert is_valid
        assert error == ""

class TestParameterValidation:
    """Test cases for parameter validation"""
    
    def test_validate_parameter_value_string_type(self, config_file):
        """Test string parameter validation"""
        server = ConfigurableSocketServer(config_file)
        
        # Valid string
        param_config = {"type": "string"}
        assert server.validate_parameter_value("valid string", param_config)
        
        # Invalid type
        assert not server.validate_parameter_value(123, param_config)
    
    def test_validate_parameter_value_number_type(self, config_file):
        """Test number parameter validation"""
        server = ConfigurableSocketServer(config_file)
        
        param_config = {"type": "number"}
        
        # Valid numbers
        assert server.validate_parameter_value(123, param_config)
        assert server.validate_parameter_value(123.45, param_config)
        
        # Invalid type
        assert not server.validate_parameter_value("not a number", param_config)
    
    def test_validate_parameter_value_boolean_type(self, config_file):
        """Test boolean parameter validation"""
        server = ConfigurableSocketServer(config_file)
        
        param_config = {"type": "boolean"}
        
        # Valid booleans
        assert server.validate_parameter_value(True, param_config)
        assert server.validate_parameter_value(False, param_config)
        
        # Invalid type
        assert not server.validate_parameter_value("true", param_config)
        assert not server.validate_parameter_value(1, param_config)
    
    def test_validate_parameter_value_pattern_matching(self, config_file):
        """Test pattern validation for string parameters"""
        server = ConfigurableSocketServer(config_file)
        
        param_config = {
            "type": "string",
            "pattern": "^[a-zA-Z0-9/._-]+$"
        }
        
        # Valid patterns
        assert server.validate_parameter_value("valid_path123", param_config)
        assert server.validate_parameter_value("/tmp/test.sock", param_config)
        
        # Invalid patterns
        assert not server.validate_parameter_value("invalid@path!", param_config)
        assert not server.validate_parameter_value("spaces not allowed", param_config)
    
    def test_validate_parameter_value_enum_validation(self, config_file):
        """Test enum validation"""
        server = ConfigurableSocketServer(config_file)
        
        param_config = {
            "type": "string",
            "enum": ["option1", "option2", "option3"]
        }
        
        # Valid enum values
        assert server.validate_parameter_value("option1", param_config)
        assert server.validate_parameter_value("option2", param_config)
        
        # Invalid enum value
        assert not server.validate_parameter_value("invalid_option", param_config)

class TestIntrospection:
    """Test cases for server introspection"""
    
    def test_handle_introspection(self, config_file):
        """Test introspection returns correct server information"""
        server = ConfigurableSocketServer(config_file)
        
        result = server.handle_introspection()
        
        assert result["success"] == True
        assert "server_info" in result
        
        server_info = result["server_info"]
        assert server_info["name"] == "Test Server"
        assert server_info["description"] == "A test server for unit testing"
        assert server_info["version"] == "1.0.0"
        assert "commands" in server_info
        
        # Check command information
        commands = server_info["commands"]
        assert "echo" in commands
        assert "description" in commands["echo"]
        assert "parameters" in commands["echo"]

class TestCommandExecution:
    """Test cases for command execution"""
    
    def test_execute_ping_command(self, config_file):
        """Test execution of __ping__ command"""
        server = ConfigurableSocketServer(config_file)
        
        request = {"command": "__ping__"}
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert result["message"] == "pong"
    
    def test_execute_introspect_command(self, config_file):
        """Test execution of __introspect__ command"""
        server = ConfigurableSocketServer(config_file)
        
        request = {"command": "__introspect__"}
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert "server_info" in result
        assert result["server_info"]["name"] == "Test Server"
    
    @patch('subprocess.run')
    def test_execute_simple_command(self, mock_subprocess, config_file):
        """Test execution of simple command without parameters"""
        server = ConfigurableSocketServer(config_file)
        
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "hello"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        request = {"command": "simple"}
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert result["command"] == "simple"
        assert result["returncode"] == 0
        assert result["stdout"] == "hello"
        assert result["stderr"] == ""
        
        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["echo", "hello"]  # executable
    
    @patch('subprocess.run')
    def test_execute_command_with_parameters(self, mock_subprocess, config_file):
        """Test execution of command with parameters"""
        server = ConfigurableSocketServer(config_file)
        
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test message"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        request = {
            "command": "echo",
            "parameters": {
                "message": "test message"
            }
        }
        
        result = server.execute_command(request)
        
        assert result["success"] == True
        assert result["stdout"] == "test message"
        
        # Verify subprocess was called with correct parameters
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["echo", "test message"]  # executable with argument
    
    @patch('subprocess.run')
    def test_execute_command_with_flag_parameters(self, mock_subprocess, config_file):
        """Test execution of command with flag-style parameters"""
        server = ConfigurableSocketServer(config_file)
        
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file listing"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        request = {
            "command": "with-flags",
            "parameters": {
                "long": True,
                "path": "/tmp"
            }
        }
        
        result = server.execute_command(request)
        
        assert result["success"] == True
        
        # Verify subprocess was called with correct flags
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        executable = call_args[0][0]
        
        # Should contain ls command with flags
        assert "ls" in executable
        assert "--long" in executable or "-l" in executable or "True" in executable
        assert "/tmp" in executable
    
    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_subprocess, config_file):
        """Test handling of command execution failure"""
        server = ConfigurableSocketServer(config_file)
        
        # Mock failed subprocess execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "command failed"
        mock_subprocess.return_value = mock_result
        
        request = {"command": "simple"}
        result = server.execute_command(request)
        
        assert result["success"] == False
        assert result["returncode"] == 1
        assert result["stderr"] == "command failed"
    
    @patch('subprocess.run')
    def test_execute_command_timeout(self, mock_subprocess, config_file):
        """Test handling of command timeout"""
        server = ConfigurableSocketServer(config_file)
        
        # Mock timeout exception
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["echo", "hello"], timeout=5
        )
        
        request = {"command": "simple"}
        result = server.execute_command(request)
        
        assert result["success"] == False
        assert "timeout" in result["error"].lower()
    
    @patch('subprocess.run')
    def test_execute_command_with_security_restrictions(self, mock_subprocess, config_file):
        """Test that commands are executed with security restrictions"""
        server = ConfigurableSocketServer(config_file)
        
        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "hello"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        request = {"command": "simple"}
        server.execute_command(request)
        
        # Verify security restrictions were applied
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        
        # Check restricted environment
        assert "env" in call_kwargs
        env = call_kwargs["env"]
        assert "PATH" in env
        assert env["PATH"] == "/usr/bin:/bin"  # Restricted PATH
        
        # Check safe working directory
        assert call_kwargs.get("cwd") == "/"