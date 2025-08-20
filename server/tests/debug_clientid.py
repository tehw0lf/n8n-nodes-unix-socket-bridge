#!/usr/bin/env python3
"""
Debug client ID behavior
"""

import socket
import json
import os
import time
import subprocess

def send_request_with_same_socket(socket_path: str, requests: list) -> list:
    """Send multiple requests using the same socket connection"""
    results = []
    
    try:
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.connect(socket_path)
        
        for i, request in enumerate(requests):
            # Send request
            request_json = json.dumps(request)
            client_socket.send(request_json.encode())
            
            # Receive response
            response_data = client_socket.recv(4096)
            response = json.loads(response_data.decode())
            results.append(response)
            print(f"Request {i+1}: {response}")
            
            if i < len(requests) - 1:  # Don't close after last request
                client_socket.close()
                time.sleep(0.1)
                client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client_socket.connect(socket_path)
        
        client_socket.close()
        return results
        
    except Exception as e:
        return [{'success': False, 'error': f'Connection error: {str(e)}'}]

def main():
    """Debug client ID behavior"""
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
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Give server time to start
    time.sleep(1)
    
    try:
        requests = []
        # 5 failed attempts
        for i in range(5):
            requests.append({
                'command': '__ping__',
                'auth_token': 'wrong-token'
            })
        
        # Then correct token
        requests.append({
            'command': '__ping__',
            'auth_token': test_token
        })
        
        results = send_request_with_same_socket('/tmp/playerctl.sock', requests)
        
        # Print server output
        server_output, _ = server_proc.communicate(timeout=1)
        print("\nServer output:")
        print(server_output.decode())
        
    except subprocess.TimeoutExpired:
        server_proc.terminate()
        server_proc.wait()

if __name__ == '__main__':
    main()