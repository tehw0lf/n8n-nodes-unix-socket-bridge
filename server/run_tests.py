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
            "uv", "run", "--extra", "test", "pytest"
        ], capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"Error running tests with uv: {e}")
        return 1

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
    from socket_server import ConfigurableSocketServer
    from cli_client import SocketClient
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
        
        client = SocketClient('/tmp/test.sock')
        print('✅ SocketClient initialization works')
        
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

def main():
    """Main function"""
    print("🧪 Running Unix Socket Bridge Server Tests")
    print("=" * 50)
    
    if check_uv():
        print("📦 Using uv for dependency management...")
        exit_code = run_tests_with_uv()
    else:
        print("📦 uv not found, running basic tests...")
        exit_code = run_tests_fallback()
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())