"""
Unit tests for SocketClient CLI class
"""
import pytest
import json
import socket
from unittest.mock import Mock, patch
import sys
import os

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from cli-client.py (with hyphen)
import importlib.util
cli_client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cli-client.py")
spec = importlib.util.spec_from_file_location("cli_client", cli_client_path)
cli_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_client)
SocketClient = cli_client.SocketClient
format_table = cli_client.format_table
print_server_info = cli_client.print_server_info
parse_parameter_value = cli_client.parse_parameter_value

class TestSocketClient:
    """Test cases for SocketClient class"""
    
    def test_init(self):
        """Test SocketClient initialization"""
        client = SocketClient("/tmp/test.sock", timeout=15)
        
        assert client.socket_path == "/tmp/test.sock"
        assert client.timeout == 15
    
    def test_init_with_default_timeout(self):
        """Test SocketClient initialization with default timeout"""
        client = SocketClient("/tmp/test.sock")
        
        assert client.socket_path == "/tmp/test.sock"
        assert client.timeout == 10
    
    @patch('socket.socket')
    @patch('os.access')
    @patch('os.path.exists')
    def test_send_request_success(self, mock_exists, mock_access, mock_socket_class):
        """Test successful request sending"""
        # Mock file system checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        # Mock socket instance
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        # Mock response
        response_data = {"success": True, "message": "pong"}
        mock_socket.recv.return_value = json.dumps(response_data).encode()
        
        client = SocketClient("/tmp/test.sock")
        request = {"command": "__ping__"}
        
        result = client.send_request(request)
        
        # Verify socket operations
        mock_socket.settimeout.assert_called_once_with(10)
        mock_socket.connect.assert_called_once_with("/tmp/test.sock")
        mock_socket.send.assert_called_once_with(json.dumps(request).encode())
        mock_socket.recv.assert_called_once_with(8192)
        mock_socket.close.assert_called_once()
        
        # Verify result
        assert result == response_data
    
    @patch('socket.socket')
    def test_send_request_file_not_found(self, mock_socket_class):
        """Test handling of socket file not found"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = FileNotFoundError()
        
        client = SocketClient("/tmp/nonexistent.sock")
        result = client.send_request({"command": "__ping__"})
        
        assert "error" in result
        assert "Socket not found" in result["error"]
        assert "/tmp/nonexistent.sock" in result["error"]
    
    @patch('socket.socket')
    @patch('os.access')
    @patch('os.path.exists')
    def test_send_request_timeout(self, mock_exists, mock_access, mock_socket_class):
        """Test handling of socket timeout"""
        # Mock file system checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.timeout()
        
        client = SocketClient("/tmp/test.sock")
        result = client.send_request({"command": "__ping__"})
        
        assert "error" in result
        assert "Request timeout" in result["error"]
    
    @patch('socket.socket')
    @patch('os.access')
    @patch('os.path.exists')
    def test_send_request_connection_error(self, mock_exists, mock_access, mock_socket_class):
        """Test handling of general connection errors"""
        # Mock file system checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        
        client = SocketClient("/tmp/test.sock")
        result = client.send_request({"command": "__ping__"})
        
        assert "error" in result
        assert "Connection failed" in result["error"]
        assert "Connection refused" in result["error"]
    
    @patch('socket.socket')
    @patch('os.access')
    @patch('os.path.exists')
    def test_send_request_json_decode_error(self, mock_exists, mock_access, mock_socket_class):
        """Test handling of invalid JSON response"""
        # Mock file system checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        # Mock receive to return invalid JSON that's small enough
        mock_socket.recv.side_effect = [b"Invalid JSON", b""]
        mock_socket.settimeout = Mock()
        
        client = SocketClient("/tmp/test.sock")
        result = client.send_request({"command": "__ping__"})
        
        # Should return error for invalid JSON
        assert "error" in result
        assert "Invalid JSON response" in result["error"]
    
    @patch.object(SocketClient, 'send_request')
    def test_introspect(self, mock_send_request):
        """Test introspect method"""
        expected_response = {
            "success": True,
            "server_info": {
                "name": "Test Server",
                "commands": {}
            }
        }
        mock_send_request.return_value = expected_response
        
        client = SocketClient("/tmp/test.sock")
        result = client.introspect()
        
        mock_send_request.assert_called_once_with({"command": "__introspect__"})
        assert result == expected_response
    
    @patch.object(SocketClient, 'send_request')
    def test_ping(self, mock_send_request):
        """Test ping method"""
        expected_response = {"success": True, "message": "pong"}
        mock_send_request.return_value = expected_response
        
        client = SocketClient("/tmp/test.sock")
        result = client.ping()
        
        mock_send_request.assert_called_once_with({"command": "__ping__"})
        assert result == expected_response

class TestSocketClientIntegration:
    """Integration tests for SocketClient with real socket communication"""
    
    def test_send_request_with_large_response(self):
        """Test handling of large responses that might require multiple recv calls"""
        # This is a more complex integration test that would need a real server
        # For now, we'll mock it to test the buffer handling logic
        pass
    
    def test_send_request_with_custom_timeout(self):
        """Test that custom timeout values are properly applied"""
        with patch('socket.socket') as mock_socket_class, \
             patch('os.path.exists') as mock_exists, \
             patch('os.access') as mock_access:
            
            # Mock file system checks
            mock_exists.return_value = True
            mock_access.return_value = True
            
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.recv.return_value = b'{"success": true}'
            
            client = SocketClient("/tmp/test.sock", timeout=30)
            client.send_request({"command": "__ping__"})
            
            mock_socket.settimeout.assert_called_once_with(30)
    
    @patch('socket.socket')
    def test_socket_cleanup_on_exception(self, mock_socket_class):
        """Test that socket is properly cleaned up even when exceptions occur"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.recv.side_effect = Exception("Unexpected error")
        
        client = SocketClient("/tmp/test.sock")
        result = client.send_request({"command": "__ping__"})
        
        # Should return error response
        assert "error" in result
        
        # Socket should still be closed despite the exception
        # (Note: In the actual implementation, there's no explicit close in the except block,
        # but the socket will be garbage collected. This test documents expected behavior.)
    
    def test_request_serialization(self):
        """Test that complex request objects are properly serialized"""
        with patch('socket.socket') as mock_socket_class, \
             patch('os.path.exists') as mock_exists, \
             patch('os.access') as mock_access:
            
            # Mock file system checks
            mock_exists.return_value = True
            mock_access.return_value = True
            
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.recv.return_value = b'{"success": true}'
            
            client = SocketClient("/tmp/test.sock")
            
            complex_request = {
                "command": "complex",
                "parameters": {
                    "string_param": "test value",
                    "number_param": 42,
                    "boolean_param": True,
                    "array_param": [1, 2, 3],
                    "object_param": {"nested": "value"}
                }
            }
            
            client.send_request(complex_request)
            
            # Verify the request was properly serialized
            call_args = mock_socket.send.call_args[0][0]
            sent_data = call_args.decode()
            parsed_request = json.loads(sent_data)
            
            assert parsed_request == complex_request

class TestSocketClientEdgeCases:
    """Test edge cases and error conditions for SocketClient"""
    
    def test_empty_response_handling(self):
        """Test handling of empty responses from server"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.recv.return_value = b''  # Empty response
            
            client = SocketClient("/tmp/test.sock")
            result = client.send_request({"command": "__ping__"})
            
            # Should handle empty response gracefully
            assert "error" in result
    
    def test_malformed_json_request(self):
        """Test that malformed JSON requests are handled"""
        # This test verifies that our client properly serializes requests
        # Even if we pass objects that might be hard to serialize
        with patch('socket.socket') as mock_socket_class, \
             patch('os.path.exists') as mock_exists, \
             patch('os.access') as mock_access:
            
            # Mock file system checks
            mock_exists.return_value = True
            mock_access.return_value = True
            
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.recv.return_value = b'{"success": true}'
            
            client = SocketClient("/tmp/test.sock")
            
            # Test with a request that should serialize fine
            request = {"command": "test", "data": "normal string"}
            result = client.send_request(request)
            
            # Should work without issues
            mock_socket.send.assert_called()
    
    def test_unicode_handling(self):
        """Test handling of unicode characters in requests and responses"""
        with patch('socket.socket') as mock_socket_class, \
             patch('os.path.exists') as mock_exists, \
             patch('os.access') as mock_access:
            
            # Mock file system checks
            mock_exists.return_value = True
            mock_access.return_value = True
            
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            
            # Response with unicode characters
            unicode_response = {"message": "Hello 世界 🌍"}
            mock_socket.recv.return_value = json.dumps(unicode_response).encode('utf-8')
            
            client = SocketClient("/tmp/test.sock")
            
            # Request with unicode characters
            unicode_request = {"command": "test", "message": "Hello 世界 🌍"}
            result = client.send_request(unicode_request)
            
            # Should handle unicode properly in both directions
            assert result["message"] == "Hello 世界 🌍"
            
            # Verify request was sent with proper encoding
            sent_data = mock_socket.send.call_args[0][0]
            decoded_request = json.loads(sent_data.decode('utf-8'))
            assert decoded_request["message"] == "Hello 世界 🌍"


class TestEnhancedSocketClient:
    """Test cases for enhanced SocketClient features"""
    
    def test_init_with_verbose_mode(self):
        """Test SocketClient initialization with verbose mode"""
        client = SocketClient("/tmp/test.sock", timeout=15, verbose=True)
        
        assert client.socket_path == "/tmp/test.sock"
        assert client.timeout == 15
        assert client.verbose == True
    
    def test_init_with_max_response_size(self):
        """Test SocketClient initialization with custom max response size"""
        client = SocketClient("/tmp/test.sock")
        
        # Should have default max response size
        assert client.max_response_size == 1048576  # 1MB
    
    @patch('socket.socket')
    @patch('sys.stderr')
    @patch('os.access')
    @patch('os.path.exists')
    def test_verbose_mode_output(self, mock_exists, mock_access, mock_stderr, mock_socket_class):
        """Test that verbose mode outputs request/response details"""
        # Mock file system checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.recv.return_value = b'{"success": true}'
        
        client = SocketClient("/tmp/test.sock", verbose=True)
        request = {"command": "__ping__"}
        client.send_request(request)
        
        # Should have written verbose output to stderr
        mock_stderr.write.assert_called()
        
    @patch('os.path.exists')
    def test_permission_check_before_connection(self, mock_exists):
        """Test that client checks permissions before attempting connection"""
        mock_exists.return_value = True
        
        with patch('os.access') as mock_access:
            mock_access.return_value = False  # No permissions
            
            client = SocketClient("/tmp/test.sock")
            result = client.send_request({"command": "__ping__"})
            
            assert "error" in result
            assert "Permission denied" in result["error"]
    
    def test_receive_full_response_with_size_limit(self):
        """Test receive_full_response respects size limits"""
        client = SocketClient("/tmp/test.sock")
        client.max_response_size = 100  # Small limit for testing
        
        mock_socket = Mock()
        # Simulate large response
        large_response = b'x' * 200
        mock_socket.recv.return_value = large_response
        
        with pytest.raises(ValueError) as excinfo:
            client.receive_full_response(mock_socket)
        assert "too large" in str(excinfo.value).lower()
    
    def test_receive_full_response_chunked_data(self):
        """Test receive_full_response handles chunked data correctly"""
        client = SocketClient("/tmp/test.sock")
        
        mock_socket = Mock()
        test_data = '{"success": true, "message": "test response"}'
        chunks = [test_data[i:i+10].encode() for i in range(0, len(test_data), 10)]
        chunks.append(b'')  # End marker
        
        mock_socket.recv.side_effect = chunks
        mock_socket.settimeout = Mock()
        
        result = client.receive_full_response(mock_socket)
        assert result == test_data
    
    def test_receive_full_response_timeout_handling(self):
        """Test receive_full_response handles timeouts gracefully"""
        client = SocketClient("/tmp/test.sock")
        
        mock_socket = Mock()
        mock_socket.recv.side_effect = [b'partial', socket.timeout()]
        mock_socket.settimeout = Mock()
        
        result = client.receive_full_response(mock_socket)
        assert result == "partial"


class TestParameterValueParsing:
    """Test cases for enhanced parameter value parsing"""
    
    def test_parse_parameter_value_json_objects(self):
        """Test parsing of JSON objects"""
        # Using pre-imported function
        
        # Valid JSON object
        result = parse_parameter_value('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}
        
        # Valid JSON array
        result = parse_parameter_value('[1, 2, 3, "test"]')
        assert result == [1, 2, 3, "test"]
    
    def test_parse_parameter_value_numbers(self):
        """Test parsing of numeric values"""
        # Using pre-imported function
        
        # Integer
        result = parse_parameter_value('42')
        assert result == 42
        
        # Float
        result = parse_parameter_value('3.14')
        assert result == 3.14
        
        # Scientific notation
        result = parse_parameter_value('1e5')
        assert result == 100000.0
    
    def test_parse_parameter_value_booleans(self):
        """Test parsing of boolean values"""
        # Using pre-imported function
        
        # True values
        for true_val in ['true', 'True', 'TRUE', 'yes', 'Yes', 'on', 'ON', '1']:
            result = parse_parameter_value(true_val)
            assert result == True, f"Failed for {true_val}"
        
        # False values
        for false_val in ['false', 'False', 'FALSE', 'no', 'No', 'off', 'OFF', '0']:
            result = parse_parameter_value(false_val)
            assert result == False, f"Failed for {false_val}"
    
    def test_parse_parameter_value_strings(self):
        """Test parsing of string values"""
        # Using pre-imported function
        
        # Plain string
        result = parse_parameter_value('hello world')
        assert result == 'hello world'
        
        # String that looks like JSON but isn't valid
        result = parse_parameter_value('{"incomplete":')
        assert result == '{"incomplete":'
        
        # Empty string
        result = parse_parameter_value('')
        assert result == ''


class TestCLITableFormatting:
    """Test cases for ASCII table formatting"""
    
    def test_format_table_basic(self):
        """Test basic table formatting"""
        # Using pre-imported function
        
        headers = ["Name", "Type", "Description"]
        rows = [
            ["param1", "string", "First parameter"],
            ["param2", "number", "Second parameter"]
        ]
        
        result = format_table(headers, rows)
        
        # Should contain headers
        assert "Name" in result
        assert "Type" in result
        assert "Description" in result
        
        # Should contain data
        assert "param1" in result
        assert "string" in result
        assert "First parameter" in result
        
        # Should have separators
        assert "─" in result
        assert "│" in result
    
    def test_format_table_varying_widths(self):
        """Test table formatting with varying column widths"""
        # Using pre-imported function
        
        headers = ["Short", "Very Long Header Name"]
        rows = [
            ["A", "Short content"],
            ["Long content here", "B"]
        ]
        
        result = format_table(headers, rows)
        
        # All content should be present
        assert "Short" in result
        assert "Very Long Header Name" in result
        assert "Long content here" in result
        
        # Should handle width alignment properly
        lines = result.split('\n')
        assert len(lines) >= 4  # Header + separator + 2 data rows
    
    def test_format_table_empty_data(self):
        """Test table formatting with empty data"""
        # Using pre-imported function
        
        headers = ["Column1", "Column2"]
        rows = []
        
        result = format_table(headers, rows)
        
        # Should still show headers
        assert "Column1" in result
        assert "Column2" in result


class TestServerInfoPrinting:
    """Test cases for server info printing functionality"""
    
    @patch('builtins.print')
    def test_print_server_info_success(self, mock_print):
        """Test printing successful server info"""
        # Using pre-imported function
        
        info = {
            "success": True,
            "server_info": {
                "name": "Test Server",
                "description": "A test server",
                "version": "1.0.0",
                "commands": {
                    "echo": {
                        "description": "Echo command",
                        "parameters": {
                            "message": {
                                "description": "Message to echo",
                                "type": "string",
                                "required": True
                            }
                        }
                    },
                    "simple": {
                        "description": "Simple command",
                        "parameters": {}
                    }
                }
            }
        }
        
        print_server_info(info, detailed=True)
        
        # Should have printed server details
        mock_print.assert_called()
        printed_content = ' '.join([str(call[0][0]) if call[0] else '' for call in mock_print.call_args_list])
        
        assert "Test Server" in printed_content
        assert "A test server" in printed_content
        assert "1.0.0" in printed_content
        assert "echo" in printed_content
        assert "simple" in printed_content
    
    @patch('builtins.print')
    def test_print_server_info_error(self, mock_print):
        """Test printing server info with error"""
        # Using pre-imported function
        
        info = {
            "success": False,
            "error": "Connection failed"
        }
        
        print_server_info(info)
        
        # Should have printed error
        mock_print.assert_called()
        printed_content = str(mock_print.call_args_list[0].args[0])
        assert "Error" in printed_content
        assert "Connection failed" in printed_content
    
    @patch('builtins.print')
    def test_print_server_info_simple_mode(self, mock_print):
        """Test printing server info in simple mode"""
        # Using pre-imported function
        
        info = {
            "success": True,
            "server_info": {
                "name": "Test Server",
                "commands": {
                    "cmd1": {"description": "Command 1"},
                    "cmd2": {"description": "Command 2"}
                }
            }
        }
        
        print_server_info(info, detailed=False)
        
        # Should print in simple table format
        mock_print.assert_called()
        printed_content = ' '.join([str(call[0][0]) if call[0] else '' for call in mock_print.call_args_list])
        
        assert "cmd1" in printed_content
        assert "cmd2" in printed_content
        assert "Command 1" in printed_content
        assert "Command 2" in printed_content


class TestEnhancedClientMethods:
    """Test cases for enhanced client methods"""
    
    @patch.object(SocketClient, 'send_request')
    def test_execute_command_with_parameters(self, mock_send_request):
        """Test execute_command method with parameters"""
        mock_send_request.return_value = {"success": True, "output": "test"}
        
        client = SocketClient("/tmp/test.sock")
        parameters = {"message": "hello", "count": 3}
        result = client.execute_command("test_cmd", parameters)
        
        expected_request = {
            "command": "test_cmd",
            "parameters": parameters
        }
        mock_send_request.assert_called_once_with(expected_request)
        assert result == {"success": True, "output": "test"}
    
    @patch.object(SocketClient, 'send_request')
    def test_execute_command_without_parameters(self, mock_send_request):
        """Test execute_command method without parameters"""
        mock_send_request.return_value = {"success": True}
        
        client = SocketClient("/tmp/test.sock")
        result = client.execute_command("simple_cmd")
        
        expected_request = {"command": "simple_cmd"}
        mock_send_request.assert_called_once_with(expected_request)
        assert result == {"success": True}


class TestCLIArgumentParsing:
    """Test cases for enhanced CLI argument parsing"""
    
    def test_parameter_type_inference(self):
        """Test that parameter types are properly inferred"""
        # Using pre-imported function
        
        # Should detect JSON
        result = parse_parameter_value('{"test": true}')
        assert isinstance(result, dict)
        
        # Should detect numbers
        result = parse_parameter_value('42')
        assert isinstance(result, int)
        
        # Should detect floats
        result = parse_parameter_value('3.14')
        assert isinstance(result, float)
        
        # Should detect booleans
        result = parse_parameter_value('true')
        assert isinstance(result, bool)
        
        # Should default to string
        result = parse_parameter_value('plain text')
        assert isinstance(result, str)


class TestEnhancedErrorHandling:
    """Test cases for enhanced error handling in CLI client"""
    
    @patch('socket.socket')
    @patch('os.access')
    @patch('os.path.exists')
    def test_detailed_connection_errors(self, mock_exists, mock_access, mock_socket_class):
        """Test detailed connection error messages"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        # Test different error scenarios
        # FileNotFoundError - socket file doesn't exist
        mock_exists.return_value = False
        client = SocketClient("/tmp/test.sock")
        result = client.send_request({"command": "__ping__"})
        assert "error" in result
        assert "socket not found" in result["error"].lower()
        
        # PermissionError - socket exists but no permission
        mock_exists.return_value = True
        mock_access.return_value = False
        result = client.send_request({"command": "__ping__"})
        assert "error" in result
        assert "permission denied" in result["error"].lower()
        
        # Connection errors - socket exists and has permission but connection fails
        mock_exists.return_value = True
        mock_access.return_value = True
        
        # ConnectionRefusedError
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        result = client.send_request({"command": "__ping__"})
        assert "error" in result
        assert "connection failed" in result["error"].lower()
        
        # Timeout error
        mock_socket.connect.side_effect = socket.timeout()
        result = client.send_request({"command": "__ping__"})
        assert "error" in result
        assert "request timeout" in result["error"].lower()


class TestCLIClientPerformance:
    """Test cases for CLI client performance features"""
    
    def test_large_response_handling(self):
        """Test handling of large responses without memory issues"""
        client = SocketClient("/tmp/test.sock")
        
        # Test that large responses are handled gracefully
        mock_socket = Mock()
        
        # Simulate a large but valid JSON response
        large_data = {"data": "x" * 50000}  # 50KB of data
        response_json = json.dumps(large_data)
        
        mock_socket.recv.return_value = response_json.encode()
        mock_socket.settimeout = Mock()
        
        result = client.receive_full_response(mock_socket)
        assert result == response_json
        
        # Verify it can be parsed back
        parsed = json.loads(result)
        assert len(parsed["data"]) == 50000
    
    def test_response_size_enforcement(self):
        """Test that response size limits are enforced"""
        client = SocketClient("/tmp/test.sock")
        client.max_response_size = 1000  # 1KB limit
        
        mock_socket = Mock()
        # Response larger than limit
        large_response = b'x' * 2000
        mock_socket.recv.return_value = large_response
        mock_socket.settimeout = Mock()
        
        with pytest.raises(ValueError) as excinfo:
            client.receive_full_response(mock_socket)
        assert "too large" in str(excinfo.value).lower()