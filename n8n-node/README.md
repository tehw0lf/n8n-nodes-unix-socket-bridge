# n8n-nodes-unix-socket-bridge

![n8n.io - Workflow Automation](https://raw.githubusercontent.com/n8n-io/n8n/master/assets/n8n-logo.png)

An n8n community node that enables Unix domain socket communication for system automation and command execution.

[n8n](https://n8n.io/) is a [fair-code licensed](https://docs.n8n.io/reference/license/) workflow automation platform.

## Installation

Open your n8n instance and install directly through the UI:

1. Go to **Settings** → **Community Nodes**
2. Click **Install a community node**
3. Enter: `@tehw0lf/n8n-nodes-unix-socket-bridge`
4. Click **Install**

The node will appear in your node list as "Unix Socket Bridge"!

## ⚠️ Docker Compatibility Warning

**Important**: This node cannot access Unix domain sockets on the host if n8n is running inside a Docker container. Unix sockets are filesystem-based and do not cross container boundaries.

### Compatibility Matrix:
- ✅ **n8n native installation** → Host Unix sockets (recommended)
- ✅ **n8n in Docker** → Unix sockets inside the same container
- ✅ **Docker container management** from native n8n
- ❌ **n8n in Docker** → Host Unix sockets (not supported)

**For full functionality**: Install n8n natively on your host system to access Unix domain sockets.

## Features

- **Auto-Discovery**: Automatically discovers available commands from socket servers
- **Easy Configuration**: Simple dropdown selection of available operations
- **Parameter Validation**: Built-in validation ensures correct command execution
- **Flexible Response Handling**: Auto-detect JSON responses or handle as plain text
- **🔐 Authentication Support**: Secure token-based authentication for protected services
- **⚡ Rate Limiting Protection**: Built-in rate limiting prevents abuse and overload
- **📏 Size Controls**: Configurable response size limits for memory safety
- **🛡️ Security Features**: Input validation, command allowlisting, and timeout protection
- **Production Ready**: Works with systemd services and Docker deployments

## Quick Start

### 1. Set Up a Socket Server

Create a configuration file for your commands (e.g., `system-monitor.json`):

```json
{
  "name": "System Monitor",
  "socket_path": "/tmp/system.sock",
  "commands": {
    "uptime": {
      "description": "Get system uptime",
      "executable": ["uptime"]
    },
    "disk-usage": {
      "description": "Check disk usage",
      "executable": ["df", "-h"]
    },
    "memory": {
      "description": "Check memory usage",
      "executable": ["free", "-h"]
    }
  }
}
```

Start the server:
```bash
python3 socket-server.py system-monitor.json
```

### 2. Use in n8n

1. Add the **Unix Socket Bridge** node to your workflow
2. Set **Socket Path**: `/tmp/system.sock`
3. Enable **Auto-Discover Commands** (recommended)
4. Select a command from the dropdown
5. Execute your workflow! 🎉

## Node Configuration

### Socket Path
Path to the Unix domain socket file (e.g., `/tmp/socket.sock`)

### Auto-Discover Commands (Recommended)
When enabled, automatically loads available commands from the server and provides a dropdown for easy selection.

### Authentication
For servers with authentication enabled:
- **Auth Token**: Enter your authentication token
- The node automatically handles authentication with the server
- Leave empty for servers without authentication

### Advanced Options
- **Max Response Size**: Limit response size for memory safety (default: 1MB)
- **Include Metadata**: Include execution metadata in responses
- **Timeout**: Connection timeout in milliseconds (default: 5000ms)

### Operation Modes

#### With Auto-Discovery
- Select commands from dropdown menu
- Automatic parameter validation
- Type-safe parameter handling

#### Manual Modes
- **Send JSON Command**: Manually specify command and parameters
- **Send Raw Message**: Send arbitrary text messages

### Response Handling
- **Auto-Detect** (default): Automatically detects JSON or text
- **JSON**: Forces JSON parsing
- **Text**: Returns raw text

## Example Use Cases

### System Monitoring
Monitor and automate based on system metrics:
- Send alerts when disk space is low
- Track memory usage over time
- Monitor system uptime

### Media Control
Control media players (using playerctl):
```json
{
  "name": "Media Control",
  "socket_path": "/tmp/playerctl.sock",
  "commands": {
    "play-pause": {
      "description": "Toggle play/pause",
      "executable": ["playerctl", "play-pause"]
    },
    "next": {
      "description": "Next track",
      "executable": ["playerctl", "next"]
    },
    "current": {
      "description": "Current track info",
      "executable": ["playerctl", "metadata", "--format", "{{artist}} - {{title}}"]
    }
  }
}
```

### Docker Management
Integrate Docker operations:
```json
{
  "name": "Docker Control",
  "socket_path": "/tmp/docker.sock",
  "commands": {
    "list": {
      "description": "List containers",
      "executable": ["docker", "ps", "--format", "json"]
    },
    "restart": {
      "description": "Restart a container",
      "executable": ["docker", "restart"],
      "parameters": {
        "container": {
          "description": "Container name or ID",
          "type": "string",
          "required": true,
          "style": "argument"
        }
      }
    }
  }
}
```

### Custom Scripts
Run any custom script or command:
```json
{
  "name": "Custom Scripts",
  "socket_path": "/tmp/scripts.sock",
  "commands": {
    "backup": {
      "description": "Run backup script",
      "executable": ["/usr/local/bin/backup.sh"]
    },
    "deploy": {
      "description": "Deploy application",
      "executable": ["/usr/local/bin/deploy.sh"],
      "parameters": {
        "environment": {
          "description": "Target environment",
          "type": "string",
          "required": true,
          "pattern": "^(dev|staging|prod)$"
        }
      }
    }
  }
}
```

## Server Component

This node requires the Unix Socket Bridge server to be running. The server:

- Exposes system commands via Unix sockets
- Provides command introspection for auto-discovery
- Validates parameters and handles execution
- Returns structured responses

Get the server from the [main repository](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge).

## Production Setup

For production use, run the socket server as a systemd service with authentication:

```ini
[Unit]
Description=Unix Socket Bridge
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/socket-server.py /etc/socket-bridge/config.json
Restart=always
User=www-data
Environment=AUTH_ENABLED=true
Environment=AUTH_TOKEN_HASH=your-hashed-token-here
Environment=AUTH_MAX_ATTEMPTS=5
Environment=AUTH_WINDOW_SECONDS=60

[Install]
WantedBy=multi-user.target
```

### Security Configuration

Generate a secure token hash:
```bash
echo -n "your-secret-token" | sha256sum
```

Use the hash in your systemd service and the plaintext token in your n8n node configuration.

## Troubleshooting

### Node not appearing in n8n?
- Ensure you've restarted n8n after installation
- Check n8n logs for any errors

### Commands not showing in dropdown?
- Verify the socket server is running: `ps aux | grep socket-server`
- Check if the socket file exists: `ls -la /tmp/*.sock`
- Test the connection with the CLI client

### Connection errors?
- Check socket file permissions
- Ensure n8n can access the socket path
- Verify the server configuration

### Authentication failures?
- Verify your auth token is correct
- Check if the server has authentication enabled
- Ensure token hash matches on the server side
- Check server logs for authentication errors

## Compatibility

- **n8n**: 1.0.0 and above
- **Operating Systems**: Linux, macOS (any Unix system with socket support)
- **Requirements**: Python 3.x for the socket server

## Resources

- [GitHub Repository](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge)
- [Configuration Examples](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge/tree/main/examples)
- [n8n Community Nodes Documentation](https://docs.n8n.io/integrations/community-nodes/)

## License

[MIT](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge/blob/main/LICENSE)

## Support

- **Issues**: [GitHub Issues](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge/issues)
- **Examples**: Check the repository for more configuration examples

---

**Made with ❤️ for the n8n community**

*Transform any command-line tool into an n8n-accessible service!*