#!/usr/bin/env python3
"""
Debug test script for authentication rate limiting
"""

import socket
import json
import os
import time
import subprocess

def send_request(socket_path: str, request: dict) -> dict:
    """Send a request to the Unix socket server"""
    try:
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.connect(socket_path)
        
        # Send request
        request_json = json.dumps(request)
        client_socket.send(request_json.encode())
        
        # Receive response
        response_data = client_socket.recv(4096)
        response = json.loads(response_data.decode())
        
        client_socket.close()
        return response
        
    except Exception as e:
        return {'success': False, 'error': f'Connection error: {str(e)}'}

def main():
    """Debug rate limiting"""
    test_token = "test-secret-token-123"
    
    # Start server with auth enabled and low rate limit
    env = os.environ.copy()
    env['AUTH_ENABLED'] = 'true'
    env['AUTH_TOKEN'] = test_token
    env['AUTH_MAX_ATTEMPTS'] = '3'
    env['AUTH_WINDOW_SECONDS'] = '60'
    env['AUTH_BLOCK_DURATION'] = '5'
    
    server_proc = subprocess.Popen([
        'python3', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'socket-server.py'), os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'examples', 'playerctl.json')
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give server time to start
    time.sleep(1)
    
    try:
        # Make failed attempts and observe responses
        for i in range(5):
            response = send_request('/tmp/playerctl.sock', {
                'command': '__ping__',
                'auth_token': 'wrong-token'
            })
            print(f"Attempt {i+1}: {response}")
            time.sleep(0.1)  # Small delay between attempts
        
    finally:
        server_proc.terminate()
        server_proc.wait()

if __name__ == '__main__':
    main()