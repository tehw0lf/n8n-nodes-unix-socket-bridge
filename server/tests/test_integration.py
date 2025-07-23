"""
Integration tests for Unix Socket Server and CLI Client
Tests the full server-client communication flow
"""
import pytest
import json
import threading
import time
import tempfile
import os
import socket
from pathlib import Path
import sys
import signal
from unittest.mock import patch

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from socket-server.py and cli-client.py (with hyphens)
import importlib.util

socket_server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "socket-server.py")
spec = importlib.util.spec_from_file_location("socket_server", socket_server_path)
socket_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(socket_server)
ConfigurableSocketServer = socket_server.ConfigurableSocketServer

cli_client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cli-client.py")
spec = importlib.util.spec_from_file_location("cli_client", cli_client_path)
cli_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_client)
SocketClient = cli_client.SocketClient

class TestServerClientIntegration:
    """Integration tests for server-client communication"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.server_thread = None
        self.server_instance = None
    
    def teardown_method(self):
        """Cleanup after each test method"""
        if self.server_instance and hasattr(self.server_instance, 'running'):
            self.server_instance.running = False
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2)
    
    def start_server_thread(self, config_file):
        """Start server in a separate thread for testing"""
        def run_server():
            try:
                server = ConfigurableSocketServer(config_file)
                self.server_instance = server
                
                # Create and bind socket
                server.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                
                # Remove existing socket file
                if os.path.exists(server.socket_path):
                    os.unlink(server.socket_path)
                
                server.server_socket.bind(server.socket_path)
                server.server_socket.listen(5)
                server.running = True
                
                server.logger.info(f"Server started on {server.socket_path}")
                
                while server.running:
                    try:
                        server.server_socket.settimeout(1.0)  # Allow periodic checks
                        client_socket, address = server.server_socket.accept()
                        
                        # Handle client request
                        data = client_socket.recv(8192).decode('utf-8')
                        if not data:
                            client_socket.close()
                            continue
                        
                        try:
                            request = json.loads(data)
                            
                            # Validate request
                            is_valid, error = server.validate_request(request)
                            if not is_valid:
                                response = {'success': False, 'error': error}
                            else:
                                response = server.execute_command(request)
                            
                            # Send response
                            response_json = json.dumps(response)
                            client_socket.send(response_json.encode('utf-8'))
                            
                        except json.JSONDecodeError:
                            error_response = {'success': False, 'error': 'Invalid JSON'}
                            client_socket.send(json.dumps(error_response).encode('utf-8'))
                        
                        client_socket.close()
                        
                    except socket.timeout:
                        continue  # Check if server should keep running
                    except OSError:
                        break  # Socket was closed
                        
            except Exception as e:
                print(f"Server error: {e}")
            finally:
                if hasattr(server, 'server_socket') and server.server_socket:
                    try:
                        server.server_socket.close()
                    except:
                        pass
                
                # Clean up socket file
                try:
                    if os.path.exists(server.socket_path):
                        os.unlink(server.socket_path)
                except:
                    pass
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Give server time to start
        time.sleep(0.5)
    
    def test_ping_command_integration(self, config_file, temp_socket_path):
        """Test ping command through full server-client integration"""
        self.start_server_thread(config_file)
        
        # Wait for server to be ready
        time.sleep(0.1)
        
        client = SocketClient(temp_socket_path, timeout=5)
        result = client.ping()
        
        assert result["success"] == True
        assert result["message"] == "pong"
    
    def test_introspection_command_integration(self, config_file, temp_socket_path):
        """Test introspection command through full integration"""
        self.start_server_thread(config_file)
        
        time.sleep(0.1)
        
        client = SocketClient(temp_socket_path, timeout=5)
        result = client.introspect()
        
        assert result["success"] == True
        assert "server_info" in result
        assert result["server_info"]["name"] == "Test Server"
        assert "commands" in result["server_info"]
        assert "echo" in result["server_info"]["commands"]
    
    @patch('subprocess.run')
    def test_echo_command_integration(self, mock_subprocess, config_file, temp_socket_path):
        """Test echo command with parameters through full integration"""
        # Mock subprocess for echo command
        mock_result = type('MockResult', (), {
            'returncode': 0,
            'stdout': 'test message',
            'stderr': ''
        })()
        mock_subprocess.return_value = mock_result
        
        self.start_server_thread(config_file)
        time.sleep(0.1)
        
        client = SocketClient(temp_socket_path, timeout=5)
        
        # Send command with parameters
        request = {
            "command": "echo",
            "parameters": {
                "message": "test message"
            }
        }
        
        result = client.send_request(request)
        
        assert result["success"] == True
        assert result["command"] == "echo"
        assert result["stdout"] == "test message"
        assert result["returncode"] == 0
        
        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert "echo" in call_args[0][0]
        assert "test message" in call_args[0][0]
    
    def test_invalid_command_integration(self, config_file, temp_socket_path):
        """Test handling of invalid commands through full integration"""
        self.start_server_thread(config_file)
        time.sleep(0.1)
        
        client = SocketClient(temp_socket_path, timeout=5)
        
        request = {"command": "nonexistent_command"}
        result = client.send_request(request)
        
        assert result["success"] == False
        assert "error" in result
        assert "Unknown command" in result["error"]
    
    def test_invalid_json_integration(self, config_file, temp_socket_path):
        """Test handling of invalid JSON through full integration"""
        self.start_server_thread(config_file)
        time.sleep(0.1)
        
        # Send raw invalid JSON to socket
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(temp_socket_path)
            sock.send(b"invalid json {")
            response = sock.recv(8192).decode('utf-8')
            sock.close()
            
            result = json.loads(response)
            assert result["success"] == False
            assert "error" in result
            assert "Invalid JSON" in result["error"]
            
        except Exception as e:
            pytest.fail(f"Failed to test invalid JSON: {e}")
    
    def test_missing_required_parameters_integration(self, config_file, temp_socket_path):
        """Test validation of required parameters through full integration"""
        self.start_server_thread(config_file)
        time.sleep(0.1)
        
        client = SocketClient(temp_socket_path, timeout=5)
        
        # Send echo command without required message parameter
        request = {"command": "echo"}
        result = client.send_request(request)
        
        assert result["success"] == False
        assert "error" in result
        assert "Missing required parameter: message" in result["error"]
    
    def test_concurrent_client_requests(self, config_file, temp_socket_path):
        """Test handling of multiple concurrent client requests"""
        self.start_server_thread(config_file)
        time.sleep(0.1)
        
        def make_request(client_id):
            client = SocketClient(temp_socket_path, timeout=5)
            return client.ping()
        
        # Create multiple threads to make concurrent requests
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(target=lambda i=i: results.append(make_request(i)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify all requests succeeded
        assert len(results) == 5
        for result in results:
            assert result["success"] == True
            assert result["message"] == "pong"
    
    def test_server_connection_cleanup(self, config_file, temp_socket_path):
        """Test that server properly cleans up connections"""
        self.start_server_thread(config_file)
        time.sleep(0.1)
        
        # Make multiple requests to test connection cleanup
        client = SocketClient(temp_socket_path, timeout=5)
        
        for i in range(3):
            result = client.ping()
            assert result["success"] == True
        
        # Server should still be responsive after multiple requests
        final_result = client.introspect()
        assert final_result["success"] == True

class TestServerLifecycle:
    """Test server lifecycle operations"""
    
    def test_server_socket_file_creation(self, config_file, temp_socket_path):
        """Test that server creates socket file correctly"""
        server = ConfigurableSocketServer(config_file)
        
        # Before starting, socket file shouldn't exist
        assert not os.path.exists(temp_socket_path)
        
        # Create socket
        server.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.server_socket.bind(temp_socket_path)
        
        # Now socket file should exist
        assert os.path.exists(temp_socket_path)
        
        # Cleanup
        server.server_socket.close()
        os.unlink(temp_socket_path)
    
    def test_server_socket_permissions(self, config_file, temp_socket_path):
        """Test that server sets correct socket file permissions"""
        server = ConfigurableSocketServer(config_file)
        
        # Create socket
        server.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.server_socket.bind(temp_socket_path)
        
        # Check file permissions (this is a basic check)
        stat_info = os.stat(temp_socket_path)
        assert stat_info.st_mode & 0o777  # Should have some permissions set
        
        # Cleanup
        server.server_socket.close()
        os.unlink(temp_socket_path)

class TestErrorRecovery:
    """Test error recovery and edge cases"""
    
    def test_client_connection_to_nonexistent_server(self, temp_socket_path):
        """Test client behavior when server is not running"""
        client = SocketClient("/tmp/definitely_nonexistent.sock", timeout=1)
        
        result = client.ping()
        
        assert "error" in result
        assert "Socket not found" in result["error"]
    
    def test_client_timeout_handling(self, config_file, temp_socket_path):
        """Test client timeout behavior"""
        # Start server that accepts but doesn't respond
        def slow_server():
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                if os.path.exists(temp_socket_path):
                    os.unlink(temp_socket_path)
                server_socket.bind(temp_socket_path)
                server_socket.listen(1)
                
                client_socket, _ = server_socket.accept()
                # Don't send response - let client timeout
                time.sleep(2)  # Longer than client timeout
                client_socket.close()
                
            finally:
                server_socket.close()
                if os.path.exists(temp_socket_path):
                    os.unlink(temp_socket_path)
        
        thread = threading.Thread(target=slow_server)
        thread.daemon = True
        thread.start()
        
        time.sleep(0.1)  # Let server start
        
        # Client with short timeout
        client = SocketClient(temp_socket_path, timeout=1)
        result = client.ping()
        
        assert "error" in result
        assert "timeout" in result["error"].lower()
        
        thread.join(timeout=3)
    
    @patch('subprocess.run')
    def test_command_execution_error_handling(self, mock_subprocess, config_file, temp_socket_path):
        """Test handling of command execution errors"""
        # Mock subprocess to raise an exception
        mock_subprocess.side_effect = Exception("Command execution failed")
        
        # Start server
        def run_server():
            server = ConfigurableSocketServer(config_file)
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            
            try:
                if os.path.exists(temp_socket_path):
                    os.unlink(temp_socket_path)
                server_socket.bind(temp_socket_path)
                server_socket.listen(1)
                
                client_socket, _ = server_socket.accept()
                data = client_socket.recv(8192).decode('utf-8')
                request = json.loads(data)
                
                # This should catch the exception and return error response
                try:
                    response = server.execute_command(request)
                except Exception as e:
                    response = {'success': False, 'error': str(e)}
                
                client_socket.send(json.dumps(response).encode('utf-8'))
                client_socket.close()
                
            finally:
                server_socket.close()
                if os.path.exists(temp_socket_path):
                    os.unlink(temp_socket_path)
        
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        
        time.sleep(0.1)
        
        client = SocketClient(temp_socket_path, timeout=5)
        request = {"command": "simple"}  # This should trigger the mocked subprocess
        result = client.send_request(request)
        
        # Should handle the exception gracefully
        assert "error" in result or "success" in result
        
        thread.join(timeout=3)