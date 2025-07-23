#!/usr/bin/env python3
"""
Unix Socket Bridge CLI Client
Command-line interface for interacting with configurable Unix socket servers.
"""

import socket
import json
import argparse
import sys
from typing import Dict, Any, Optional

class SocketClient:
    def __init__(self, socket_path: str, timeout: int = 10):
        self.socket_path = socket_path
        self.timeout = timeout
        
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the Unix socket server"""
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(self.timeout)
            client.connect(self.socket_path)
            
            # Send request
            request_json = json.dumps(request)
            client.send(request_json.encode())
            
            # Receive response
            response_data = client.recv(8192).decode('utf-8')
            client.close()
            
            return json.loads(response_data)
            
        except FileNotFoundError:
            return {'error': f'Socket not found: {self.socket_path}'}
        except socket.timeout:
            return {'error': 'Request timeout'}
        except Exception as e:
            return {'error': f'Connection failed: {str(e)}'}
    
    def introspect(self) -> Dict[str, Any]:
        """Get server information and available commands"""
        return self.send_request({'command': '__introspect__'})
    
    def ping(self) -> Dict[str, Any]:
        """Ping the server"""
        return self.send_request({'command': '__ping__'})

def print_server_info(info: Dict[str, Any]):
    """Pretty print server information"""
    if not info.get('success'):
        print(f"❌ Error: {info.get('error', 'Unknown error')}")
        return
    
    server_info = info['server_info']
    print(f"📡 Server: {server_info['name']}")
    print(f"📝 Description: {server_info.get('description', 'No description')}")
    print(f"🏷️  Version: {server_info.get('version', 'Unknown')}")
    print()
    
    commands = server_info.get('commands', {})
    if commands:
        print("📋 Available Commands:")
        for cmd_name, cmd_info in commands.items():
            print(f"  • {cmd_name}: {cmd_info.get('description', 'No description')}")
            
            # Show parameters
            params = cmd_info.get('parameters', {})
            if params:
                print("    Parameters:")
                for param_name, param_info in params.items():
                    required = " (required)" if param_info.get('required') else ""
                    param_type = param_info.get('type', 'string')
                    print(f"      - {param_name} ({param_type}){required}: {param_info.get('description', '')}")
            
            # Show examples
            examples = cmd_info.get('examples', [])
            if examples:
                print("    Examples:")
                for example in examples:
                    print(f"      {example.get('description', 'Example')}")
                    print(f"      Request: {json.dumps(example.get('request', {}), indent=8)}")
            print()

def main():
    parser = argparse.ArgumentParser(description='Unix Socket Bridge CLI Client')
    parser.add_argument('socket_path', help='Path to Unix socket')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    
    subparsers = parser.add_subparsers(dest='action', help='Available actions')
    
    # Introspect command
    subparsers.add_parser('introspect', help='Get server information and available commands')
    
    # Ping command
    subparsers.add_parser('ping', help='Ping the server')
    
    # Execute command
    exec_parser = subparsers.add_parser('exec', help='Execute a command')
    exec_parser.add_argument('command', help='Command to execute')
    exec_parser.add_argument('--param', action='append', nargs=2, metavar=('NAME', 'VALUE'),
                           help='Add parameter (can be used multiple times)')
    exec_parser.add_argument('--json', action='store_true', help='Output response as JSON')
    
    # List commands
    subparsers.add_parser('list', help='List available commands')
    
    args = parser.parse_args()
    
    if not args.action:
        parser.print_help()
        sys.exit(1)
    
    client = SocketClient(args.socket_path, args.timeout)
    
    if args.action == 'introspect':
        info = client.introspect()
        if args.json if hasattr(args, 'json') else False:
            print(json.dumps(info, indent=2))
        else:
            print_server_info(info)
    
    elif args.action == 'ping':
        response = client.ping()
        if response.get('success'):
            print("✅ Server is responding")
        else:
            print(f"❌ {response.get('error', 'Server not responding')}")
    
    elif args.action == 'list':
        info = client.introspect()
        if info.get('success'):
            commands = info['server_info'].get('commands', {})
            for cmd_name in commands.keys():
                print(cmd_name)
        else:
            print(f"❌ Error: {info.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
    
    elif args.action == 'exec':
        request = {'command': args.command}
        
        # Add parameters
        if args.param:
            request['parameters'] = {}
            for name, value in args.param:
                # Try to parse as JSON, fallback to string
                try:
                    request['parameters'][name] = json.loads(value)
                except json.JSONDecodeError:
                    request['parameters'][name] = value
        
        response = client.send_request(request)
        
        if hasattr(args, 'json') and args.json:
            print(json.dumps(response, indent=2))
        else:
            if response.get('success'):
                output = response.get('stdout', response.get('output', ''))
                if output:
                    print(output)
                else:
                    print("✅ Command executed successfully")
            else:
                error = response.get('error', response.get('stderr', 'Unknown error'))
                print(f"❌ Error: {error}", file=sys.stderr)
                sys.exit(1)

if __name__ == '__main__':
    main()
