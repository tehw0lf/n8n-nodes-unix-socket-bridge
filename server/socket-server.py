#!/usr/bin/env python3
"""
Generic Unix Socket Server
Configurable socket server that can execute predefined commands based on JSON configuration.
"""

import socket
import subprocess
import json
import os
import argparse
import logging
import signal
import sys
from typing import Dict, Any, List, Tuple
import re
from collections import defaultdict
from time import time
import threading
import secrets
import hashlib

class AuthRateLimiter:
    """Rate limiter for authentication attempts"""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60, block_duration: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_duration = block_duration
        self.failed_attempts = defaultdict(list)  # client_id -> [timestamps]
        self.blocked_clients = defaultdict(float)  # client_id -> block_until_timestamp
        self.logger = logging.getLogger(__name__)
        
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client is allowed to attempt authentication"""
        now = time()
        
        # Check if client is currently blocked
        if client_id in self.blocked_clients:
            if now < self.blocked_clients[client_id]:
                return False  # Still blocked
            else:
                # Block expired, remove from blocked list
                del self.blocked_clients[client_id]
                if client_id in self.failed_attempts:
                    del self.failed_attempts[client_id]
        
        # Cleanup old entries and check current attempt count
        self.cleanup_old_entries()
        
        return len(self.failed_attempts[client_id]) < self.max_attempts
    
    def record_failure(self, client_id: str):
        """Record a failed authentication attempt"""
        now = time()
        self.failed_attempts[client_id].append(now)
        
        attempt_count = len(self.failed_attempts[client_id])
        self.logger.warning(f"Failed authentication attempt from {client_id} ({attempt_count}/{self.max_attempts})")
        
        # Block client if max attempts reached
        if attempt_count >= self.max_attempts:
            self.blocked_clients[client_id] = now + self.block_duration
            self.logger.error(f"Client {client_id} blocked due to too many failed auth attempts")
    
    def record_success(self, client_id: str):
        """Clear failure counter on successful authentication"""
        if client_id in self.failed_attempts:
            del self.failed_attempts[client_id]
        # Note: Don't clear blocked_clients here - let blocks expire naturally
        self.logger.info(f"Successful authentication from {client_id}")
    
    def cleanup_old_entries(self):
        """Remove old entries to prevent memory growth"""
        now = time()
        
        # Clean up failed attempts outside the window
        for client_id in list(self.failed_attempts.keys()):
            self.failed_attempts[client_id] = [
                t for t in self.failed_attempts[client_id]
                if now - t < self.window_seconds
            ]
            if not self.failed_attempts[client_id]:
                del self.failed_attempts[client_id]
        
        # Clean up expired blocks
        expired_blocks = []
        for client_id, block_until in self.blocked_clients.items():
            if now >= block_until:
                expired_blocks.append(client_id)
        
        for client_id in expired_blocks:
            del self.blocked_clients[client_id]
            if expired_blocks:
                self.logger.debug(f"Cleaned up {len(expired_blocks)} expired rate limit entries")

class ConfigurableSocketServer:
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.socket_path = self.config['socket_path']
        self.running = False
        self.server_socket = None
        
        # Rate limiting
        self.request_times = defaultdict(list)
        self.rate_limit = self.config.get('rate_limit', {'requests': 30, 'window': 60})
        
        # Size limits
        self.max_request_size = self.config.get('max_request_size', 1048576)  # 1MB default
        self.max_output_size = self.config.get('max_output_size', 100000)  # 100KB default
        
        # Authentication setup
        self.auth_enabled = self._load_auth_config()
        self.auth_token_hash = None
        
        if self.auth_enabled:
            # Load hashed token from environment variable or config file
            self.auth_token_hash = self._load_auth_token_hash()
            if not self.auth_token_hash:
                logging.error("Authentication enabled but no hashed token configured")
                logging.error("Set AUTH_TOKEN_HASH environment variable or 'auth_token_hash' in config file")
                logging.error("Use generate-token-hash.py to create secure hashed tokens")
                sys.exit(1)
        
        # Authentication rate limiting
        auth_max_attempts = int(os.getenv('AUTH_MAX_ATTEMPTS', '5'))
        auth_window_seconds = int(os.getenv('AUTH_WINDOW_SECONDS', '60'))
        auth_block_duration = int(os.getenv('AUTH_BLOCK_DURATION', '60'))
        self.auth_rate_limiter = AuthRateLimiter(auth_max_attempts, auth_window_seconds, auth_block_duration)
        
        # Setup logging
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if self.auth_enabled:
            self.logger.info("Auth enabled, using SHA-256 hashed token authentication")
        else:
            self.logger.info("Auth disabled, running in development mode")
    
    def _load_auth_config(self) -> bool:
        """Load authentication configuration from config file or environment variables"""
        # Check config file first (project-specific setting)
        if 'auth_enabled' in self.config:
            return bool(self.config['auth_enabled'])
        
        # Check environment variable as fallback (optional override)
        auth_enabled_env = os.getenv('AUTH_ENABLED')
        if auth_enabled_env is not None:
            return auth_enabled_env.lower() in ('true', '1', 'yes', 'on')
        
        # Default to disabled (secure by explicit configuration)
        return False
    
    def _load_auth_token_hash(self) -> str:
        """Load authentication token hash from environment variables or config file"""
        # Try environment variable first (recommended for production)
        token_hash = os.getenv('AUTH_TOKEN_HASH')
        if token_hash:
            return token_hash
        
        # Try config file (alternative method)
        if 'auth_token_hash' in self.config:
            return self.config['auth_token_hash']
        
        return None
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Generate SHA-256 hash of a token for secure storage"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_token_hash(token: str, token_hash: str) -> bool:
        """Verify a token against its stored hash"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest() == token_hash
    
    def validate_auth(self, request: Dict[str, Any], client_id: str) -> tuple[bool, str]:
        """Validate authentication token from request"""
        # If auth is disabled, always allow
        if not self.auth_enabled:
            return True, ""
        
        # Check if client is currently blocked
        if not self.auth_rate_limiter.check_rate_limit(client_id):
            return False, "rate_limited"
        
        # Extract hashed token from request (secure approach only)
        auth_token_hash = request.get('auth_token_hash')
        
        # Check if hashed token is present and valid
        token_valid = False
        if auth_token_hash:
            # Client sent hashed token - compare directly with stored hash
            token_valid = auth_token_hash == self.auth_token_hash
        
        if not token_valid:
            self.auth_rate_limiter.record_failure(client_id)
            # Check if the client should be blocked after this failure
            if not self.auth_rate_limiter.check_rate_limit(client_id):
                return False, "rate_limited"
            else:
                return False, "auth_failed"
        
        # Even with correct token, check if client is currently blocked
        # This is important for consistent rate limiting behavior
        if not self.auth_rate_limiter.check_rate_limit(client_id):
            return False, "rate_limited"
        
        # Successful authentication - only record if not blocked
        self.auth_rate_limiter.record_success(client_id)
        return True, ""
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ['name', 'socket_path', 'commands']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate commands
            for cmd_name, cmd_config in config['commands'].items():
                if 'executable' not in cmd_config:
                    raise ValueError(f"Command '{cmd_name}' missing 'executable'")
                
                # Validate executable path
                if not self.validate_executable_path(cmd_config['executable'], config):
                    raise ValueError(f"Command '{cmd_name}' has invalid executable path")
                    
            return config
            
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def validate_executable_path(self, executable: List[str], config = None) -> bool:
        """Validate that executable is in allowed paths"""
        if not config:
            config = self.config
        if not executable:
            return False
        if not config:
            return False
        
        binary = executable[0]
        
        # Allow only specific directories for security
        allowed_dirs = config.get('allowed_executable_dirs', [])
        
        # Check if it's an absolute path
        if os.path.isabs(binary):
            # Must be in allowed directories
            if not any(binary.startswith(d) for d in allowed_dirs):
                return False
            return os.path.exists(binary) and os.access(binary, os.X_OK)
        else:
            # Relative path - check if it exists in allowed dirs
            for dir_path in allowed_dirs:
                full_path = os.path.join(dir_path, binary)
                if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                    return True
            return False
            
    def validate_request(self, request: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate incoming request against configuration"""
        if 'command' not in request:
            return False, "Missing 'command' field"
            
        command = request['command']
        
        # Special introspection commands
        if command in ['__introspect__', '__ping__']:
            return True, ""
            
        if command not in self.config['commands']:
            available = list(self.config['commands'].keys())
            return False, f"Unknown command '{command}'. Available: {available}"
            
        cmd_config = self.config['commands'][command]
        
        # Validate parameters if defined
        if 'parameters' in cmd_config:
            for param_name, param_config in cmd_config['parameters'].items():
                param_value = request.get('parameters', {}).get(param_name)
                
                # Check required parameters
                if param_config.get('required', False) and param_value is None:
                    return False, f"Missing required parameter: {param_name}"
                    
                # Validate parameter value
                if param_value is not None:
                    if not self.validate_parameter_value(param_value, param_config):
                        return False, f"Invalid value for parameter '{param_name}'"
                        
        return True, ""
        
    def validate_parameter_value(self, value: Any, param_config: Dict[str, Any]) -> bool:
        """Validate a parameter value against its configuration"""
        param_type = param_config.get('type', 'string')
        
        # Type validation
        if param_type == 'string' and not isinstance(value, str):
            return False
        elif param_type == 'number' and not isinstance(value, (int, float)):
            return False
        elif param_type == 'boolean' and not isinstance(value, bool):
            return False
            
        # Pattern validation for strings
        if param_type == 'string' and 'pattern' in param_config:
            if not re.match(param_config['pattern'], value):
                return False
                
        # Enum validation
        if 'enum' in param_config:
            if value not in param_config['enum']:
                return False
        
        # Length validation for strings
        if param_type == 'string' and 'max_length' in param_config:
            if len(value) > param_config['max_length']:
                return False
                
        return True
    
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        if not self.config.get('enable_rate_limit', True):
            return True
            
        now = time()
        window = self.rate_limit['window']
        
        # Clean old entries
        self.request_times[client_id] = [
            t for t in self.request_times[client_id] 
            if now - t < window
        ]
        
        if len(self.request_times[client_id]) >= self.rate_limit['requests']:
            return False
            
        self.request_times[client_id].append(now)
        return True
        
    def handle_introspection(self) -> Dict[str, Any]:
        """Return server configuration for client introspection"""
        return {
            'success': True,
            'server_info': {
                'name': self.config['name'],
                'description': self.config.get('description', ''),
                'version': self.config.get('version', '1.0.0'),
                'commands': {
                    name: {
                        'description': cmd.get('description', ''),
                        'parameters': cmd.get('parameters', {}),
                        'examples': cmd.get('examples', [])
                    }
                    for name, cmd in self.config['commands'].items()
                }
            }
        }
        
    def execute_command(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command based on the request"""
        command = request['command']
        
        # Handle special commands
        if command == '__introspect__':
            return self.handle_introspection()
        elif command == '__ping__':
            return {'success': True, 'message': 'pong', 'timestamp': time()}
            
        cmd_config = self.config['commands'][command]
        
        # Build command to execute
        executable = cmd_config['executable'].copy()
        
        # Add parameters
        if 'parameters' in cmd_config and 'parameters' in request:
            for param_name, param_value in request['parameters'].items():
                param_config = cmd_config['parameters'].get(param_name)
                if param_config:
                    # Handle different parameter styles
                    style = param_config.get('style', 'flag')
                    if style == 'flag':
                        executable.extend([f"--{param_name}", str(param_value)])
                    elif style == 'argument':
                        executable.append(str(param_value))
                    elif style == 'single_flag':
                        executable.append(f"--{param_name}={param_value}")
                        
        try:
            # Execute with security restrictions
            env = cmd_config.get('env', {'PATH': '/usr/bin:/bin'})  # Allow custom env or use restricted default
            cwd = cmd_config.get('cwd', '/')  # Safe working directory
            timeout = cmd_config.get('timeout', 10)
            
            self.logger.info(f"Executing: {' '.join(executable)}")
            
            result = subprocess.run(
                executable,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=cwd
            )
            
            # Limit output size
            stdout = result.stdout[:self.max_output_size]
            stderr = result.stderr[:self.max_output_size]
            
            if len(result.stdout) > self.max_output_size:
                stdout += "\n... (output truncated)"
            if len(result.stderr) > self.max_output_size:
                stderr += "\n... (output truncated)"
            
            response = {
                'success': result.returncode == 0,
                'command': command,
                'returncode': result.returncode,
                'stdout': stdout.strip(),
                'stderr': stderr.strip()
            }
            
            # Add custom response processing if configured
            if 'response_format' in cmd_config:
                response = self.format_response(response, cmd_config['response_format'])
                
            return response
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"Command timeout after {timeout} seconds",
                'command': command
            }
        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            return {
                'success': False,
                'error': 'Command execution failed',
                'details': str(e) if self.config.get('debug', False) else None,
                'command': command
            }
            
    def format_response(self, response: Dict[str, Any], format_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom response formatting"""
        if format_config.get('parse_json', False) and response['stdout']:
            try:
                response['parsed_output'] = json.loads(response['stdout'])
            except json.JSONDecodeError:
                response['parse_error'] = 'Output is not valid JSON'
                
        return response
    
    def receive_full_message(self, client_socket: socket.socket) -> str:
        """Receive a complete message from client with size limits"""
        client_socket.settimeout(5.0)
        data = b""
        
        while True:
            try:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                    
                data += chunk
                
                # Check size limit
                if len(data) > self.max_request_size:
                    raise ValueError(f"Request too large (max {self.max_request_size} bytes)")
                
                # Try to decode and parse as JSON to check if message is complete
                try:
                    json.loads(data.decode('utf-8'))
                    break  # Valid JSON received, message is complete
                except json.JSONDecodeError:
                    continue  # Keep reading
                except UnicodeDecodeError:
                    raise ValueError("Invalid UTF-8 in request")
                    
            except socket.timeout:
                if data:
                    break  # Use what we have
                else:
                    # No data received after timeout, will fall through to empty check
                    break
                
        if not data:
            raise ValueError("Empty request")
            
        return data.decode('utf-8')
        
    def handle_client(self, client_socket: socket.socket, client_addr: str):
        """Handle a client connection"""
        # For rate limiting, try to get client process info on Linux
        client_id = f"client_{id(client_socket)}"
        try:
            # Try to get peer credentials (Linux-specific)
            import struct
            creds = client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
            pid, uid, gid = struct.unpack('3i', creds)
            auth_client_id = f"process_{pid}"
        except (OSError, AttributeError, ImportError):
            # Fallback to socket ID if peer credentials not available
            auth_client_id = client_id
        
        try:
            # Rate limiting
            if not self.check_rate_limit(client_id):
                error_response = {
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'retry_after': self.rate_limit['window']
                }
                client_socket.send(json.dumps(error_response).encode())
                return
            
            # Receive request with size limits
            data = self.receive_full_message(client_socket)
            
            request = json.loads(data)
            self.logger.debug(f"Received request from {client_id}: {request}")
            
            # Authentication validation
            auth_valid, auth_error = self.validate_auth(request, auth_client_id)
            if not auth_valid:
                if auth_error == "rate_limited":
                    error_response = {
                        'success': False,
                        'error': 'Too many failed authentication attempts. Please try again later.',
                        'request_id': request.get('request_id')
                    }
                else:  # auth_failed
                    error_response = {
                        'success': False,
                        'error': 'Authentication failed',
                        'request_id': request.get('request_id')
                    }
                client_socket.send(json.dumps(error_response).encode())
                return
            
            # Validate request
            valid, error_msg = self.validate_request(request)
            if not valid:
                response = {'success': False, 'error': error_msg}
            else:
                response = self.execute_command(request)
                
            # Add request_id to response if provided
            if 'request_id' in request:
                response['request_id'] = request['request_id']
                
            # Send response
            response_json = json.dumps(response)
            client_socket.send(response_json.encode())
            
        except json.JSONDecodeError as e:
            error_response = {'success': False, 'error': 'Invalid JSON', 'details': str(e)}
            client_socket.send(json.dumps(error_response).encode())
        except socket.timeout:
            error_response = {'success': False, 'error': 'Request timeout'}
            client_socket.send(json.dumps(error_response).encode())
        except ValueError as e:
            error_response = {'success': False, 'error': str(e)}
            client_socket.send(json.dumps(error_response).encode())
        except Exception as e:
            self.logger.error(f"Client handling error: {e}")
            error_response = {'success': False, 'error': 'Internal server error'}
            if self.config.get('debug', False):
                error_response['details'] = str(e)
            client_socket.send(json.dumps(error_response).encode())
        finally:
            try:
                client_socket.close()
            except:
                pass
                
    def start_server(self):
        """Start the Unix socket server"""
        try:
            # Remove existing socket
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
                
            # Create socket
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
            
            # Set permissions
            permissions = self.config.get('socket_permissions', 0o666)
            os.chmod(self.socket_path, permissions)
            
            self.server_socket.listen(5)
            self.running = True
            
            self.logger.info(f"Server '{self.config['name']}' listening on {self.socket_path}")
            self.logger.info(f"Available commands: {list(self.config['commands'].keys())}")
            
            if self.config.get('enable_rate_limit', True):
                self.logger.info(f"Rate limit: {self.rate_limit['requests']} requests per {self.rate_limit['window']} seconds")
            
            if self.auth_enabled:
                self.logger.info(f"Authentication rate limit: {self.auth_rate_limiter.max_attempts} attempts per {self.auth_rate_limiter.window_seconds} seconds")
            
            while self.running:
                try:
                    client, addr = self.server_socket.accept()
                    
                    # Handle client in a thread for concurrent connections
                    if self.config.get('enable_threading', False):
                        client_thread = threading.Thread(
                            target=self.handle_client,
                            args=(client, str(addr))
                        )
                        client_thread.daemon = True
                        client_thread.start()
                    else:
                        self.handle_client(client, str(addr))
                        
                except OSError as e:
                    # Socket was closed (probably by signal handler)
                    if self.running:
                        self.logger.error(f"Socket error: {e}")
                        raise
                    else:
                        self.logger.info("Server socket closed by shutdown signal")
                        break
                        
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except:
                pass
            
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        # Force close the server socket to break out of accept()
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        

def main():
    parser = argparse.ArgumentParser(description='Generic Unix Socket Server')
    parser.add_argument('config', nargs='?', help='Path to configuration file')
    parser.add_argument('--validate', action='store_true', help='Validate config and exit')
    parser.add_argument('--example', action='store_true', help='Show example configuration')
    parser.add_argument('--generate-token', action='store_true', help='Generate a secure authentication token')
    parser.add_argument('--hash-token', type=str, metavar='TOKEN', help='Generate hash for an existing token')
    
    args = parser.parse_args()
    
    # Generate secure token
    if args.generate_token:
        token = secrets.token_urlsafe(32)
        token_hash = ConfigurableSocketServer.hash_token(token)
        
        print(f"Generated secure authentication token:")
        print(f"")
        print(f"🔑 PLAINTEXT TOKEN (store securely, give to clients):")
        print(f"   {token}")
        print(f"")
        print(f"🔒 HASHED TOKEN (store on server, more secure):")
        print(f"   {token_hash}")
        print(f"")
        print(f"📋 Environment variable options:")
        print(f"")
        print(f"   Option 1 - Secure (recommended):")
        print(f"   export AUTH_TOKEN_HASH={token_hash}")
        print(f"")
        print(f"   Option 2 - Simple (less secure):")
        print(f"   export AUTH_TOKEN={token}")
        print(f"")
        print(f"⚠️  SECURITY NOTE:")
        print(f"   - Give the PLAINTEXT token to n8n clients")
        print(f"   - Store the HASHED token on the server for better security")
        print(f"   - Never store plaintext tokens in config files or logs")
        return
    
    # Hash existing token
    if args.hash_token:
        token_hash = ConfigurableSocketServer.hash_token(args.hash_token)
        print(f"Token hash generated:")
        print(f"")
        print(f"🔑 PLAINTEXT TOKEN:")
        print(f"   {args.hash_token}")
        print(f"")
        print(f"🔒 HASHED TOKEN (for server storage):")
        print(f"   {token_hash}")
        print(f"")
        print(f"📋 Use this environment variable:")
        print(f"   export AUTH_TOKEN_HASH={token_hash}")
        return
    
    if not args.config and not args.example and not args.hash_token:
        parser.error("Config file is required unless using --generate-token or --example")
    
    # Show example configuration
    if args.example:
        example_config = {
            "name": "Example Server",
            "description": "Example configuration for Unix Socket Server",
            "socket_path": "/tmp/example.sock",
            "socket_permissions": 438,  # 0o666 in decimal
            "log_level": "INFO",
            "enable_rate_limit": True,
            "rate_limit": {
                "requests": 30,
                "window": 60
            },
            "max_request_size": 1048576,
            "max_output_size": 100000,
            "enable_threading": False,
            "allowed_executable_dirs": [
                "/usr/bin/",
                "/bin/",
                "/usr/local/bin/"
            ],
            "commands": {
                "echo": {
                    "description": "Echo a message",
                    "executable": ["echo"],
                    "timeout": 5,
                    "parameters": {
                        "message": {
                            "description": "Message to echo",
                            "type": "string",
                            "required": True,
                            "style": "argument",
                            "max_length": 1000
                        }
                    }
                },
                "date": {
                    "description": "Get current date",
                    "executable": ["date"],
                    "timeout": 5
                }
            }
        }
        print(json.dumps(example_config, indent=2))
        return
    
    # Validate config
    server = ConfigurableSocketServer(args.config)
    
    if args.validate:
        print(f"✅ Configuration is valid")
        print(f"Server: {server.config['name']}")
        print(f"Socket: {server.config['socket_path']}")
        print(f"Commands: {list(server.config['commands'].keys())}")
        print(f"Rate limiting: {'Enabled' if server.config.get('enable_rate_limit', True) else 'Disabled'}")
        print(f"Threading: {'Enabled' if server.config.get('enable_threading', False) else 'Disabled'}")
        print(f"Authentication: {'Enabled' if server.auth_enabled else 'Disabled'}")
        if server.auth_enabled:
            print(f"Auth mode: SHA-256 hashed token (secure)")
            print(f"Auth token hash loaded: {'Yes' if server.auth_token_hash else 'No'}")
        return
        
    # Setup signal handlers
    signal.signal(signal.SIGINT, server.signal_handler)
    signal.signal(signal.SIGTERM, server.signal_handler)
    
    # Start server
    try:
        server.start_server()
    except KeyboardInterrupt:
        server.logger.info("Server stopped by user")
    except Exception as e:
        server.logger.error(f"Server failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()