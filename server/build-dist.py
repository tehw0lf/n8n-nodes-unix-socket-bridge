#!/usr/bin/env python3
"""
Build script for Unix Socket Bridge server distribution.

Creates a clean production distribution with only the necessary files
for deployment and operation.
"""

import os
import shutil
import sys
from pathlib import Path


def main():
    """Build the distribution package."""
    # Get the project root directory
    server_dir = Path(__file__).parent
    project_root = server_dir.parent
    dist_dir = server_dir / "dist"
    
    print("Building Unix Socket Bridge server distribution...")
    
    # Clean existing dist directory
    if dist_dir.exists():
        print(f"Removing existing dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    # Create dist directory structure
    print(f"Creating dist directory: {dist_dir}")
    dist_dir.mkdir()
    
    # Create subdirectories
    (dist_dir / "examples").mkdir()
    (dist_dir / "systemd").mkdir()
    
    # Copy core server files
    print("Copying core server files...")
    core_files = [
        "socket-server.py",
        "cli-client.py", 
        "generate-token-hash.py"
    ]
    
    for file in core_files:
        src = server_dir / file
        if src.exists():
            dst = dist_dir / file
            shutil.copy2(src, dst)
            print(f"  Copied: {file}")
        else:
            print(f"  Warning: {file} not found, skipping")
    
    # Copy examples
    print("Copying example configurations...")
    examples_src = project_root / "examples"
    if examples_src.exists():
        for example_file in examples_src.glob("*.json"):
            dst = dist_dir / "examples" / example_file.name
            shutil.copy2(example_file, dst)
            print(f"  Copied: examples/{example_file.name}")
    
    # Copy systemd service files
    print("Copying systemd service files...")
    systemd_src = project_root / "systemd"
    if systemd_src.exists():
        for service_file in systemd_src.glob("*"):
            if service_file.is_file():
                dst = dist_dir / "systemd" / service_file.name
                shutil.copy2(service_file, dst)
                print(f"  Copied: systemd/{service_file.name}")
    
    # Copy documentation files
    print("Copying documentation...")
    doc_files = ["README.md", "LICENSE", "SECURITY.md"]
    for doc_file in doc_files:
        src = project_root / doc_file
        if src.exists():
            dst = dist_dir / doc_file
            shutil.copy2(src, dst)
            print(f"  Copied: {doc_file}")
    
    # Create installation script
    print("Creating installation script...")
    install_script = dist_dir / "install.sh"
    install_content = """#!/bin/bash
set -e

echo "Installing Unix Socket Bridge Server..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root for system installation"
   echo "Usage: sudo ./install.sh"
   exit 1
fi

# Install Python files
echo "Installing server components..."
cp socket-server.py /usr/local/bin/unix-socket-server
cp cli-client.py /usr/local/bin/unix-socket-client
cp generate-token-hash.py /usr/local/bin/unix-socket-generate-hash
chmod +x /usr/local/bin/unix-socket-*

# Install systemd service
echo "Installing systemd service..."
cp systemd/socket-bridge@.service /etc/systemd/system/
systemctl daemon-reload

# Create configuration directory
mkdir -p /etc/unix-socket-bridge
cp examples/*.json /etc/unix-socket-bridge/

echo "Installation complete!"
echo ""
echo "Usage:"
echo "  1. Configure your service in /etc/unix-socket-bridge/"
echo "  2. Enable and start: sudo systemctl enable --now socket-bridge@<config-name>"
echo "  3. Example: sudo systemctl enable --now socket-bridge@playerctl"
echo ""
echo "For more information, see README.md"
"""
    
    with open(install_script, 'w') as f:
        f.write(install_content)
    install_script.chmod(0o755)
    print(f"  Created: install.sh")
    
    # Create uninstall script
    print("Creating uninstall script...")
    uninstall_script = dist_dir / "uninstall.sh"
    uninstall_content = """#!/bin/bash
set -e

echo "Uninstalling Unix Socket Bridge Server..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root for system uninstallation"
   echo "Usage: sudo ./uninstall.sh"
   exit 1
fi

# Stop and disable services
echo "Stopping services..."
systemctl stop 'socket-bridge@*' 2>/dev/null || true
systemctl disable 'socket-bridge@*' 2>/dev/null || true

# Remove systemd service
echo "Removing systemd service..."
rm -f /etc/systemd/system/socket-bridge@.service
systemctl daemon-reload

# Remove binaries
echo "Removing server components..."
rm -f /usr/local/bin/unix-socket-server
rm -f /usr/local/bin/unix-socket-client
rm -f /usr/local/bin/unix-socket-generate-hash

# Remove configuration directory (with confirmation)
if [ -d "/etc/unix-socket-bridge" ]; then
    echo "Configuration directory /etc/unix-socket-bridge exists."
    read -p "Remove configuration directory? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf /etc/unix-socket-bridge
        echo "Configuration directory removed."
    else
        echo "Configuration directory preserved."
    fi
fi

echo "Uninstallation complete!"
"""
    
    with open(uninstall_script, 'w') as f:
        f.write(uninstall_content)
    uninstall_script.chmod(0o755)
    print(f"  Created: uninstall.sh")
    
    # Create simple deployment README
    print("Creating deployment README...")
    deploy_readme = dist_dir / "DEPLOY.md"
    deploy_content = """# Unix Socket Bridge Server Deployment

This distribution contains everything needed to deploy the Unix Socket Bridge server.

## Quick Installation

1. Extract this distribution to a temporary directory
2. Run the installation script as root:
   ```bash
   sudo ./install.sh
   ```

## Manual Installation

### Install Server Components
```bash
sudo cp socket-server.py /usr/local/bin/unix-socket-server
sudo cp cli-client.py /usr/local/bin/unix-socket-client
sudo cp generate-token-hash.py /usr/local/bin/unix-socket-generate-hash
sudo chmod +x /usr/local/bin/unix-socket-*
```

### Install Systemd Service
```bash
sudo cp systemd/socket-bridge@.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Configure Services
```bash
sudo mkdir -p /etc/unix-socket-bridge
sudo cp examples/*.json /etc/unix-socket-bridge/
```

## Usage

1. Configure your service in `/etc/unix-socket-bridge/`
2. Enable and start the service:
   ```bash
   sudo systemctl enable --now socket-bridge@<config-name>
   ```

### Example: Media Control Service
```bash
sudo systemctl enable --now socket-bridge@playerctl
```

## Testing

Test the service with the CLI client:
```bash
unix-socket-client /tmp/playerctl.sock ping
unix-socket-client /tmp/playerctl.sock introspect
```

## Uninstallation

Run the uninstall script:
```bash
sudo ./uninstall.sh
```

## Security

For production use with authentication, generate secure token hashes:
```bash
unix-socket-generate-hash
```

Then update your configuration files with the generated hash.

## Support

See the main README.md for detailed configuration and troubleshooting information.
"""
    
    with open(deploy_readme, 'w') as f:
        f.write(deploy_content)
    print(f"  Created: DEPLOY.md")
    
    # Print summary
    print("\n" + "="*60)
    print("Distribution build complete!")
    print(f"Location: {dist_dir}")
    print("\nContents:")
    for item in sorted(dist_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(dist_dir)
            print(f"  {rel_path}")
    
    print(f"\nTotal files: {len(list(dist_dir.rglob('*')))}")
    print("\nTo create a tarball:")
    print(f"  cd {server_dir}")
    print("  tar -czf unix-socket-bridge-server.tar.gz dist/")


if __name__ == "__main__":
    main()