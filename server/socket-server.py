#!/usr/bin/env python3
"""
Generic Unix Socket Server
Configurable socket server that can execute predefined commands based on JSON configuration.
"""

import socket
import subprocess
import json
import os
import stat
import argparse
import logging
import signal
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
import re

class ConfigurableSocketServer:
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.socket_path = self.config['socket_path']
        self.running = False
        self.server_socket = None
        
        # Setup logging
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
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
                    
            return config
            
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
            
    def validate_request(self, request: Dict[str, Any]) -> tuple[bool, str]:
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
            return {'success': True, 'message': 'pong'}
            
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
            env = {'PATH': '/usr/bin:/bin'}  # Restricted PATH
            cwd = '/'  # Safe working directory
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
            
            response = {
                'success': result.returncode == 0,
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip()
            }
            
            # Add custom response processing if configured
            if 'response_format' in cmd_config:
                response = self.format_response(response, cmd_config['response_format'])
                
            return response
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"Command timeout after {timeout} seconds"
            }
        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            return {
                'success': False,
                'error': 'Command execution failed'
            }
            
    def format_response(self, response: Dict[str, Any], format_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom response formatting"""
        if format_config.get('parse_json', False) and response['stdout']:
            try:
                response['parsed_output'] = json.loads(response['stdout'])
            except json.JSONDecodeError:
                pass
                
        return response
        
    def handle_client(self, client_socket: socket.socket):
        """Handle a client connection"""
        try:
            client_socket.settimeout(5.0)
            
            # Receive request
            data = client_socket.recv(4096).decode('utf-8')
            if not data.strip():
                client_socket.send(json.dumps({'error': 'Empty request'}).encode())
                return
                
            request = json.loads(data)
            self.logger.debug(f"Received request: {request}")
            
            # Validate request
            valid, error_msg = self.validate_request(request)
            if not valid:
                response = {'success': False, 'error': error_msg}
            else:
                response = self.execute_command(request)
                
            # Send response
            response_json = json.dumps(response)
            client_socket.send(response_json.encode())
            
        except json.JSONDecodeError:
            client_socket.send(json.dumps({'error': 'Invalid JSON'}).encode())
        except socket.timeout:
            client_socket.send(json.dumps({'error': 'Request timeout'}).encode())
        except Exception as e:
            self.logger.error(f"Client handling error: {e}")
            client_socket.send(json.dumps({'error': 'Internal server error'}).encode())
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
            
            while self.running:
                try:
                    client, addr = self.server_socket.accept()
                    self.handle_client(client)
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
            self.server_socket.close()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Received shutdown signal")
        self.running = False
        # Force close the server socket to break out of accept()
        if self.server_socket:
            self.server_socket.close()
        

def main():
    parser = argparse.ArgumentParser(description='Generic Unix Socket Server')
    parser.add_argument('config', help='Path to configuration file')
    parser.add_argument('--validate', action='store_true', help='Validate config and exit')
    
    args = parser.parse_args()
    
    # Validate config
    server = ConfigurableSocketServer(args.config)
    
    if args.validate:
        print(f"✅ Configuration is valid")
        print(f"Server: {server.config['name']}")
        print(f"Socket: {server.config['socket_path']}")
        print(f"Commands: {list(server.config['commands'].keys())}")
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