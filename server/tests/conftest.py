"""
Test configuration and fixtures for Unix Socket Server tests
"""
import pytest
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any

@pytest.fixture
def temp_socket_path():
    """Create a temporary socket path for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test.sock")

@pytest.fixture
def sample_config():
    """Sample server configuration for testing"""
    return {
        "name": "Test Server",
        "description": "A test server for unit testing",
        "version": "1.0.0",
        "socket_path": "/tmp/test.sock",
        "socket_permissions": 438,
        "log_level": "INFO",
        "allowed_executable_dirs": [
            "/usr/bin/",
            "/bin/",
            "/usr/local/bin/"
        ],
        "commands": {
            "echo": {
                "description": "Echo back the input",
                "executable": ["echo"],
                "timeout": 5,
                "parameters": {
                    "message": {
                        "description": "Message to echo",
                        "type": "string",
                        "required": True,
                        "style": "argument"
                    }
                }
            },
            "simple": {
                "description": "Simple command with no parameters",
                "executable": ["echo", "hello"],
                "timeout": 5
            },
            "with-flags": {
                "description": "Command with flag parameters",
                "executable": ["ls"],
                "timeout": 10,
                "parameters": {
                    "long": {
                        "description": "Long listing format",
                        "type": "boolean",
                        "required": False,
                        "style": "flag"
                    },
                    "path": {
                        "description": "Path to list",
                        "type": "string",
                        "required": False,
                        "style": "argument",
                        "pattern": "^[a-zA-Z0-9/._-]+$"
                    }
                }
            }
        }
    }

@pytest.fixture
def config_file(sample_config, temp_socket_path):
    """Create a temporary config file with sample configuration"""
    # Update socket path to use temp path
    config = sample_config.copy()
    config["socket_path"] = temp_socket_path
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name
    
    yield config_path
    
    # Cleanup
    try:
        os.unlink(config_path)
    except:
        pass

@pytest.fixture
def invalid_config_file():
    """Create a temporary config file with invalid configuration"""
    invalid_config = {
        "name": "Invalid Config",
        # Missing required fields: socket_path, commands
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_config, f, indent=2)
        config_path = f.name
    
    yield config_path
    
    # Cleanup
    try:
        os.unlink(config_path)
    except:
        pass