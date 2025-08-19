#!/usr/bin/env python3
"""
Unix Socket Bridge CLI Client
Command-line interface for interacting with configurable Unix socket servers.
"""

import socket
import json
import argparse
import sys
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import time

class SocketClient:
    def __init__(self, socket_path: str, timeout: int = 10, verbose: bool = False):
        self.socket_path = socket_path
        self.timeout = timeout
        self.verbose = verbose
        self.max_response_size = 1048576  # 1MB default
        
    def receive_full_response(self, client_socket: socket.socket) -> str:
        """Receive complete response from server, handling large messages"""
        data = b""
        
        while True:
            try:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                    
                data += chunk
                
                # Check size limit
                if len(data) > self.max_response_size:
                    raise ValueError(f"Response too large (max {self.max_response_size} bytes)")
                
                # Try to decode and parse as JSON to check if message is complete
                try:
                    json.loads(data.decode('utf-8'))
                    break  # Valid JSON received, message is complete
                except json.JSONDecodeError:
                    # If we haven't received data for a bit, assume we're done
                    client_socket.settimeout(0.1)
                    continue
                except UnicodeDecodeError:
                    raise ValueError("Invalid UTF-8 in response")
                    
            except socket.timeout:
                if data:
                    break  # Use what we have
                raise
                
        if not data:
            raise ValueError("Empty response from server")
            
        return data.decode('utf-8')
        
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the Unix socket server"""
        try:
            # Check if socket exists
            if not os.path.exists(self.socket_path):
                return {'success': False, 'error': f'Socket not found: {self.socket_path}'}
            
            # Check if we have permission to access the socket
            if not os.access(self.socket_path, os.R_OK | os.W_OK):
                return {'success': False, 'error': f'Permission denied: {self.socket_path}'}
            
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(self.timeout)
            
            if self.verbose:
                print(f"📡 Connecting to {self.socket_path}...", file=sys.stderr)
                print(f"📤 Request: {json.dumps(request, indent=2)}", file=sys.stderr)
            
            client.connect(self.socket_path)
            
            # Send request
            request_json = json.dumps(request)
            client.send(request_json.encode())
            
            # Receive response with proper handling for large messages
            response_data = self.receive_full_response(client)
            client.close()
            
            response = json.loads(response_data)
            
            if self.verbose:
                print(f"📥 Response: {json.dumps(response, indent=2)}", file=sys.stderr)
            
            return response
            
        except FileNotFoundError:
            return {'success': False, 'error': f'Socket not found: {self.socket_path}'}
        except PermissionError:
            return {'success': False, 'error': f'Permission denied: {self.socket_path}'}
        except socket.timeout:
            return {'success': False, 'error': f'Request timeout after {self.timeout} seconds'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON response: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Connection failed: {str(e)}'}
    
    def introspect(self) -> Dict[str, Any]:
        """Get server information and available commands"""
        return self.send_request({'command': '__introspect__'})
    
    def ping(self) -> Dict[str, Any]:
        """Ping the server"""
        return self.send_request({'command': '__ping__'})
    
    def execute_command(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a specific command with parameters"""
        request = {'command': command}
        if parameters:
            request['parameters'] = parameters
        return self.send_request(request)

def format_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format data as a simple ASCII table"""
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Build table
    lines = []
    
    # Header
    header_line = " │ ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("─┼─".join("─" * w for w in col_widths))
    
    # Rows
    for row in rows:
        row_line = " │ ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        lines.append(row_line)
    
    return "\n".join(lines)

def print_server_info(info: Dict[str, Any], detailed: bool = True):
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
        if detailed:
            print("📋 Available Commands:")
            for cmd_name, cmd_info in commands.items():
                print(f"\n  🔸 {cmd_name}")
                desc = cmd_info.get('description', 'No description')
                print(f"     {desc}")
                
                # Show parameters
                params = cmd_info.get('parameters', {})
                if params:
                    print("     Parameters:")
                    param_rows = []
                    for param_name, param_info in params.items():
                        required = "Yes" if param_info.get('required') else "No"
                        param_type = param_info.get('type', 'string')
                        desc = param_info.get('description', '-')
                        param_rows.append([param_name, param_type, required, desc])
                    
                    if param_rows:
                        table = format_table(["Name", "Type", "Required", "Description"], param_rows)
                        for line in table.split('\n'):
                            print(f"       {line}")
                
                # Show examples
                examples = cmd_info.get('examples', [])
                if examples:
                    print("     Examples:")
                    for i, example in enumerate(examples, 1):
                        print(f"       Example {i}: {example.get('description', 'No description')}")
                        if 'request' in example:
                            print(f"       └─ Request: {json.dumps(example['request'])}")
        else:
            # Simple list view
            print("📋 Available Commands:")
            cmd_list = []
            for cmd_name, cmd_info in commands.items():
                desc = cmd_info.get('description', 'No description')
                cmd_list.append([cmd_name, desc])
            
            table = format_table(["Command", "Description"], cmd_list)
            print(table)

def parse_parameter_value(value_str: str) -> Any:
    """Parse parameter value, trying to infer the type"""
    # Try to parse as JSON first (handles numbers, booleans, arrays, objects)
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        # Check for boolean strings
        if value_str.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value_str.lower() in ('false', 'no', 'off', '0'):
            return False
        # Default to string
        return value_str

def main():
    parser = argparse.ArgumentParser(
        description='Unix Socket Bridge CLI Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /tmp/server.sock ping
  %(prog)s /tmp/server.sock list
  %(prog)s /tmp/server.sock exec echo --param message "Hello World"
  %(prog)s /tmp/server.sock exec disk-usage --json
  %(prog)s /tmp/server.sock introspect --simple
        """
    )
    
    parser.add_argument('socket_path', help='Path to Unix socket')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed request/response information')
    
    subparsers = parser.add_subparsers(dest='action', help='Available actions')
    
    # Introspect command
    intro_parser = subparsers.add_parser('introspect', help='Get server information and available commands')
    intro_parser.add_argument('--json', action='store_true', help='Output as JSON')
    intro_parser.add_argument('--simple', action='store_true', help='Simple command list without details')
    
    # Ping command
    ping_parser = subparsers.add_parser('ping', help='Ping the server')
    ping_parser.add_argument('--json', action='store_true', help='Output as JSON')
    ping_parser.add_argument('--count', '-c', type=int, default=1, help='Number of pings to send')
    
    # Execute command
    exec_parser = subparsers.add_parser('exec', help='Execute a command')
    exec_parser.add_argument('command', help='Command to execute')
    exec_parser.add_argument('--param', '-p', action='append', nargs=2, metavar=('NAME', 'VALUE'),
                           help='Add parameter (can be used multiple times)')
    exec_parser.add_argument('--params-json', type=str, metavar='JSON',
                           help='Parameters as JSON object')
    exec_parser.add_argument('--json', action='store_true', help='Output response as JSON')
    exec_parser.add_argument('--output-only', action='store_true', 
                           help='Only show stdout, no status messages')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List available commands')
    list_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Test command - run basic connectivity tests
    test_parser = subparsers.add_parser('test', help='Run connectivity and functionality tests')
    test_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if not args.action:
        parser.print_help()
        sys.exit(1)
    
    client = SocketClient(args.socket_path, args.timeout, args.verbose)
    
    if args.action == 'introspect':
        info = client.introspect()
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print_server_info(info, detailed=not args.simple)
    
    elif args.action == 'ping':
        if args.count > 1:
            # Multiple pings with timing
            results = []
            for i in range(args.count):
                start_time = time.time()
                response = client.ping()
                elapsed = (time.time() - start_time) * 1000  # ms
                
                if not args.json:
                    if response.get('success'):
                        print(f"✅ Ping {i+1}/{args.count}: Server responding (time={elapsed:.2f}ms)")
                    else:
                        print(f"❌ Ping {i+1}/{args.count}: {response.get('error', 'No response')}")
                
                results.append({
                    'ping': i+1,
                    'success': response.get('success', False),
                    'time_ms': elapsed,
                    'response': response
                })
                
                if i < args.count - 1:
                    time.sleep(1)
            
            if args.json:
                print(json.dumps(results, indent=2))
            elif any(r['success'] for r in results):
                avg_time = sum(r['time_ms'] for r in results if r['success']) / sum(1 for r in results if r['success'])
                success_rate = sum(1 for r in results if r['success']) / len(results) * 100
                print(f"\n📊 Stats: {success_rate:.0f}% success, avg time: {avg_time:.2f}ms")
        else:
            # Single ping
            response = client.ping()
            if args.json:
                print(json.dumps(response, indent=2))
            else:
                if response.get('success'):
                    print("✅ Server is responding")
                    if 'timestamp' in response:
                        print(f"   Timestamp: {response['timestamp']}")
                else:
                    print(f"❌ {response.get('error', 'Server not responding')}")
                    sys.exit(1)
    
    elif args.action == 'list':
        info = client.introspect()
        if info.get('success'):
            commands = list(info['server_info'].get('commands', {}).keys())
            if args.json:
                print(json.dumps(commands, indent=2))
            else:
                for cmd_name in sorted(commands):
                    print(cmd_name)
        else:
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"❌ Error: {info.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
    
    elif args.action == 'exec':
        # Build parameters
        parameters = {}
        
        if args.params_json:
            try:
                parameters = json.loads(args.params_json)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in --params-json: {e}", file=sys.stderr)
                sys.exit(1)
        
        if args.param:
            for name, value in args.param:
                parameters[name] = parse_parameter_value(value)
        
        # Execute command
        response = client.execute_command(args.command, parameters if parameters else None)
        
        if args.json:
            print(json.dumps(response, indent=2))
        elif args.output_only:
            # Only print stdout, useful for scripting
            if response.get('success'):
                output = response.get('stdout', '')
                if output:
                    print(output, end='')
            else:
                print(response.get('stderr', response.get('error', '')), file=sys.stderr)
                sys.exit(1)
        else:
            if response.get('success'):
                print("✅ Command executed successfully")
                if response.get('stdout'):
                    print("\n📤 Output:")
                    print(response['stdout'])
                if response.get('stderr'):
                    print("\n⚠️  Stderr:")
                    print(response['stderr'], file=sys.stderr)
            else:
                print(f"❌ Command failed")
                if response.get('error'):
                    print(f"   Error: {response['error']}")
                if response.get('stderr'):
                    print(f"   Stderr: {response['stderr']}")
                if response.get('details'):
                    print(f"   Details: {response['details']}")
                sys.exit(1)
    
    elif args.action == 'test':
        print(f"🧪 Testing connection to {args.socket_path}\n")
        
        tests = []
        
        # Test 1: Socket exists
        test_result = {'test': 'Socket exists', 'success': os.path.exists(args.socket_path)}
        tests.append(test_result)
        if not args.json:
            status = "✅" if test_result['success'] else "❌"
            print(f"{status} Socket file exists: {test_result['success']}")
        
        if test_result['success']:
            # Test 2: Socket accessible
            test_result = {'test': 'Socket accessible', 
                          'success': os.access(args.socket_path, os.R_OK | os.W_OK)}
            tests.append(test_result)
            if not args.json:
                status = "✅" if test_result['success'] else "❌"
                print(f"{status} Socket is accessible: {test_result['success']}")
            
            # Test 3: Ping
            start_time = time.time()
            ping_response = client.ping()
            ping_time = (time.time() - start_time) * 1000
            test_result = {
                'test': 'Ping response', 
                'success': ping_response.get('success', False),
                'response_time_ms': ping_time
            }
            tests.append(test_result)
            if not args.json:
                status = "✅" if test_result['success'] else "❌"
                print(f"{status} Server responds to ping: {test_result['success']} ({ping_time:.2f}ms)")
            
            # Test 4: Introspection
            intro_response = client.introspect()
            test_result = {'test': 'Introspection', 'success': intro_response.get('success', False)}
            if intro_response.get('success'):
                test_result['commands_count'] = len(intro_response.get('server_info', {}).get('commands', {}))
                test_result['server_name'] = intro_response.get('server_info', {}).get('name', 'Unknown')
            tests.append(test_result)
            if not args.json:
                status = "✅" if test_result['success'] else "❌"
                print(f"{status} Server introspection works: {test_result['success']}")
                if test_result['success']:
                    print(f"   Server: {test_result.get('server_name', 'Unknown')}")
                    print(f"   Commands: {test_result.get('commands_count', 0)}")
            
            # Test 5: Execute a simple command if available
            if intro_response.get('success'):
                commands = intro_response.get('server_info', {}).get('commands', {})
                # Look for a safe test command
                test_cmd = None
                for cmd in ['echo', 'date', 'uptime', 'ping']:
                    if cmd in commands:
                        test_cmd = cmd
                        break
                
                if test_cmd:
                    test_exec = client.execute_command(test_cmd, {'message': 'test'} if test_cmd == 'echo' else None)
                    test_result = {
                        'test': f'Execute command ({test_cmd})',
                        'success': test_exec.get('success', False)
                    }
                    tests.append(test_result)
                    if not args.json:
                        status = "✅" if test_result['success'] else "❌"
                        print(f"{status} Command execution works: {test_result['success']}")
        
        if args.json:
            print(json.dumps({
                'socket_path': args.socket_path,
                'tests': tests, 
                'success': all(t['success'] for t in tests),
                'passed': sum(1 for t in tests if t['success']),
                'failed': sum(1 for t in tests if not t['success']),
                'total': len(tests)
            }, indent=2))
        else:
            passed = sum(1 for t in tests if t['success'])
            print(f"\n📊 Test Summary: {passed}/{len(tests)} tests passed")
            if passed == len(tests):
                print("✨ All tests passed! Server is healthy.")
            else:
                print("⚠️  Some tests failed. Check server configuration.")
            
            if not all(t['success'] for t in tests):
                sys.exit(1)

if __name__ == '__main__':
    main()