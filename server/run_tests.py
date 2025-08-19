#!/usr/bin/env python3
"""
Test runner script for Unix Socket Bridge Server
Uses uv to manage virtual environment and dependencies
"""
import subprocess
import sys
import os
from pathlib import Path

def check_uv():
    """Check if uv is available"""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_tests_with_uv():
    """Run tests using uv to manage dependencies"""
    server_dir = Path(__file__).parent
    os.chdir(server_dir)
    
    try:
        # Use uv to run pytest with test dependencies
        result = subprocess.run([
            "uv", "run", "--extra", "test", "pytest", 
            "-v",  # Verbose output
            "--tb=short",  # Short traceback
            "conftest.py",
            "test_socket_server.py",
            "test_cli_client.py", 
            "test_integration.py"
        ], capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"Error running tests with uv: {e}")
        return 1

def run_tests_with_pytest():
    """Run tests using pytest directly if available"""
    try:
        import pytest
        # Run pytest with the test files
        exit_code = pytest.main([
            "-v",
            "--tb=short",
            "conftest.py",
            "test_socket_server.py",
            "test_cli_client.py",
            "test_integration.py"
        ])
        return exit_code
    except ImportError:
        print("⚠️  pytest not found, falling back to basic tests")
        return run_tests_fallback()

def run_tests_fallback():
    """Fallback to running basic tests without external dependencies"""
    print("⚠️  Running basic tests without pytest (limited functionality)")
    
    server_dir = Path(__file__).parent
    os.chdir(server_dir)
    
    # Run Python's built-in unittest on a simple test
    try:
        result = subprocess.run([
            sys.executable, "-c", """
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, '..')

# Basic smoke test
try:
    # Import with hyphens (actual filenames)
    import importlib.util
    
    socket_server_path = os.path.join('..', 'socket-server.py')
    if not os.path.exists(socket_server_path):
        socket_server_path = os.path.join('..', 'socket_server.py')
    
    spec = importlib.util.spec_from_file_location("socket_server", socket_server_path)
    socket_server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(socket_server)
    ConfigurableSocketServer = socket_server.ConfigurableSocketServer
    
    cli_client_path = os.path.join('..', 'cli-client.py')
    if not os.path.exists(cli_client_path):
        cli_client_path = os.path.join('..', 'cli_client.py')
    
    spec = importlib.util.spec_from_file_location("cli_client", cli_client_path)
    cli_client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli_client)
    SocketClient = cli_client.SocketClient
    
    print('✅ Modules import successfully')
    
    # Test config loading
    import tempfile
    import json
    
    sample_config = {
        'name': 'Test Server',
        'socket_path': '/tmp/test.sock', 
        'commands': {
            'test': {'executable': ['echo', 'hello']}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_config, f)
        config_path = f.name
    
    try:
        server = ConfigurableSocketServer(config_path)
        print('✅ ConfigurableSocketServer initialization works')
        
        # Test new features
        if hasattr(server, 'rate_limit'):
            print('✅ Rate limiting support detected')
        if hasattr(server, 'max_request_size'):
            print('✅ Size limits support detected')
        
        client = SocketClient('/tmp/test.sock')
        print('✅ SocketClient initialization works')
        
        # Test improved client features
        if hasattr(client, 'verbose'):
            print('✅ Verbose mode support detected')
        
        print('\\n🎉 Basic smoke tests passed!')
        print('💡 For full test suite, install uv: pip install uv')
        
    finally:
        os.unlink(config_path)
        
except Exception as e:
    print(f'❌ Basic tests failed: {e}')
    sys.exit(1)
"""
        ], capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"Error running fallback tests: {e}")
        return 1

def run_specific_test_file(test_file):
    """Run a specific test file"""
    print(f"🎯 Running specific test: {test_file}")
    
    if check_uv():
        result = subprocess.run([
            "uv", "run", "--extra", "test", "pytest", 
            "-v", test_file
        ], capture_output=False)
        return result.returncode
    else:
        try:
            import pytest
            return pytest.main(["-v", test_file])
        except ImportError:
            print("❌ pytest not available and uv not found")
            return 1

def main():
    """Main function"""
    print("🧪 Running Unix Socket Bridge Server Tests")
    print("=" * 50)
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Test runner for Unix Socket Bridge Server')
    parser.add_argument('test_file', nargs='?', help='Specific test file to run')
    parser.add_argument('--no-uv', action='store_true', help='Skip uv and use pytest directly')
    parser.add_argument('--fallback', action='store_true', help='Use fallback tests only')
    args = parser.parse_args()
    
    if args.test_file:
        # Run specific test file
        exit_code = run_specific_test_file(args.test_file)
    elif args.fallback:
        # Force fallback tests
        exit_code = run_tests_fallback()
    elif args.no_uv:
        # Skip uv, try pytest directly
        print("📦 Skipping uv, using pytest directly...")
        exit_code = run_tests_with_pytest()
    elif check_uv():
        print("📦 Using uv for dependency management...")
        exit_code = run_tests_with_uv()
    else:
        print("📦 uv not found, trying pytest directly...")
        exit_code = run_tests_with_pytest()
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())