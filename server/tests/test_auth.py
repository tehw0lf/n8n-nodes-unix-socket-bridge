#!/usr/bin/env python3
"""
Test script for Unix Socket Bridge authentication
"""

import socket
import json
import os
import time
import subprocess
import sys
from typing import Dict, Any

def send_request(socket_path: str, request: Dict[str, Any]) -> Dict[str, Any]:
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

def test_auth_disabled():
    """Test authentication when disabled"""
    print("=== Testing AUTH_ENABLED=false ===")
    
    # Start server with auth disabled
    env = os.environ.copy()
    env['AUTH_ENABLED'] = 'false'
    server_proc = subprocess.Popen([
        'python3', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'socket-server.py'), os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'examples', 'playerctl.json')
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give server time to start
    time.sleep(1)
    
    try:
        # Test without token - should work
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__'
        })
        print(f"Request without token: {response}")
        assert response['success'] == True, "Request should succeed when auth disabled"
        
        # Test with token - should also work (token ignored)
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': 'any-token'
        })
        print(f"Request with token: {response}")
        assert response['success'] == True, "Request should succeed when auth disabled"
        
        print("✅ AUTH_ENABLED=false tests passed")
        
    finally:
        server_proc.terminate()
        server_proc.wait()

def test_auth_enabled():
    """Test authentication when enabled"""
    print("\n=== Testing AUTH_ENABLED=true ===")
    
    test_token = "test-secret-token-123"
    
    # Start server with auth enabled
    env = os.environ.copy()
    env['AUTH_ENABLED'] = 'true'
    env['AUTH_TOKEN'] = test_token
    server_proc = subprocess.Popen([
        'python3', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'socket-server.py'), os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'examples', 'playerctl.json')
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give server time to start
    time.sleep(1)
    
    try:
        # Test without token - should fail
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__'
        })
        print(f"Request without token: {response}")
        assert response['success'] == False, "Request should fail without token"
        assert 'Authentication failed' in response['error'], "Should get auth error"
        
        # Test with wrong token - should fail
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': 'wrong-token'
        })
        print(f"Request with wrong token: {response}")
        assert response['success'] == False, "Request should fail with wrong token"
        assert 'Authentication failed' in response['error'], "Should get auth error"
        
        # Test with correct token - should work
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': test_token
        })
        print(f"Request with correct token: {response}")
        assert response['success'] == True, "Request should succeed with correct token"
        
        print("✅ AUTH_ENABLED=true tests passed")
        
    finally:
        server_proc.terminate()
        server_proc.wait()

def test_rate_limiting():
    """Test authentication rate limiting"""
    print("\n=== Testing Authentication Rate Limiting ===")
    
    test_token = "test-secret-token-123"
    
    # Start server with auth enabled and low rate limit
    env = os.environ.copy()
    env['AUTH_ENABLED'] = 'true'
    env['AUTH_TOKEN'] = test_token
    env['AUTH_MAX_ATTEMPTS'] = '3'
    env['AUTH_WINDOW_SECONDS'] = '60'
    env['AUTH_BLOCK_DURATION'] = '5'  # Short block for testing
    
    server_proc = subprocess.Popen([
        'python3', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'socket-server.py'), os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'examples', 'playerctl.json')
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give server time to start
    time.sleep(1)
    
    try:
        # Make 2 failed attempts (within limit)
        for i in range(2):
            response = send_request('/tmp/playerctl.sock', {
                'command': '__ping__',
                'auth_token': 'wrong-token'
            })
            print(f"Failed attempt {i+1}: {response}")
            assert response['success'] == False, "Should fail with wrong token"
            assert 'Authentication failed' in response['error'], "Should get auth error"
        
        # 3rd attempt should trigger rate limiting
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': 'wrong-token'
        })
        print(f"3rd attempt (triggers rate limit): {response}")
        assert response['success'] == False, "Should be rate limited"
        assert 'Too many failed' in response['error'], "Should get rate limit error"
        
        # 4th attempt should also be rate limited
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': 'wrong-token'
        })
        print(f"4th attempt (still rate limited): {response}")
        assert response['success'] == False, "Should be rate limited"
        assert 'Too many failed' in response['error'], "Should get rate limit error"
        
        # Even correct token should be blocked now
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': test_token
        })
        print(f"Correct token while blocked: {response}")
        assert response['success'] == False, "Should be blocked even with correct token"
        
        # Wait for block to expire and try again
        print("Waiting for rate limit to expire...")
        time.sleep(6)  # Wait for block to expire
        
        response = send_request('/tmp/playerctl.sock', {
            'command': '__ping__',
            'auth_token': test_token
        })
        print(f"After rate limit expires: {response}")
        assert response['success'] == True, "Should work after rate limit expires"
        
        print("✅ Rate limiting tests passed")
        
    finally:
        server_proc.terminate()
        server_proc.wait()

def main():
    """Run all authentication tests"""
    try:
        test_auth_disabled()
        test_auth_enabled() 
        test_rate_limiting()
        print("\n🎉 All authentication tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()