# Unix Socket Bridge for n8n

A generic, configurable Unix domain socket communication system for n8n workflows. This package provides both a configurable server that can expose system commands via Unix sockets and a corresponding n8n node for seamless integration.

## 🚀 Features

- **Generic Configuration**: Define any system command as a socket service using JSON configuration
- **Auto-Discovery**: n8n node automatically discovers available commands from servers at runtime
- **Parameter Validation**: Built-in validation for command parameters with type checking and patterns
- **Security**: Sandboxed command execution with restricted environments
- **Production Ready**: Systemd services, proper user separation, and security controls
- **Examples Included**: Ready-to-use configurations for common use cases

## 📦 Package Contents

```
unix-socket-bridge/
├── server/                          # Generic socket server
│   ├── socket-server.py            # Main server implementation
│   └── cli-client.py               # CLI client tool
├── n8n-node/                       # n8n node package
│   ├── package.json
│   ├── nodes/UnixSocketBridge/
│   │   ├── UnixSocketBridge.node.ts
│   │   └── UnixSocketBridge.node.json
│   └── tests/                      # Comprehensive test suite
├── examples/                        # Configuration examples
│   ├── playerctl.json              # Media player control
│   └── system-control.json         # System monitoring
└── README.md
```

## ⚠️ Node Verification Status

This n8n node appears as "unverified" in the n8n interface due to its use of Node.js APIs that are outside n8n's standard allowlist:

- **`net` module**: Required for Unix domain socket communication
- **`setTimeout`/`clearTimeout`**: Used for connection timeout handling

This occurs because the node requires system-level APIs for socket communication. The functionality is stable and the code is open source for review.

**What this means for users:**
- ✅ The node works normally in all n8n versions
- ✅ Code is open source and available for security review
- ⚠️ You'll see an "unverified" badge in the n8n interface
- ⚠️ n8n may show a warning when you first add the node

## 🛠️ Installation

### Prerequisites

- **n8n** (tested with v1.102.4+)
- **Python 3.x** for the socket server
- **Node.js/npm** for the n8n node

### Quick Setup

1. **Install the n8n node via n8n interface (Easiest):**
   - Open n8n in your browser
   - Go to **Settings** → **Community Nodes**
   - Click **Install a community node**
   - Enter: `@tehw0lf/n8n-nodes-unix-socket-bridge`
   - Click **Install**
   - Restart n8n when prompted

2. **Install the n8n node from npm:**
```bash
npm install -g @tehw0lf/n8n-nodes-unix-socket-bridge
```

**Alternative - Install from source:**
```bash
cd n8n-node
npm install
npm run build
npm pack
npm install -g ./n8n-nodes-unix-socket-bridge-1.0.7.tgz
```

**⚠️ Important if installing with npm or from source: Configure n8n to recognize the custom node**

After installing from other sources than within n8n directly, you **must** set these environment variables for n8n to recognize the custom node:

```bash
# Find your installation path
npm list -g @tehw0lf/n8n-nodes-unix-socket-bridge

# Set required environment variables
# Path to your custom node installation
export N8N_CUSTOM_EXTENSIONS=/home/user/.nvm/versions/node/v20.0.0/lib/node_modules/@tehw0lf/n8n-nodes-unix-socket-bridge

# Ensure n8n reinstalls missing packages (recommended for custom nodes)
export N8N_REINSTALL_MISSING_PACKAGES=true

# For multiple custom nodes, separate with colons
# export N8N_CUSTOM_EXTENSIONS=/path/to/node1:/path/to/node2
```

Add these environment variables to your shell profile (`.bashrc`, `.zshrc`, etc.) or your n8n startup script to make them persistent.

2. **Install server components:**
```bash
sudo cp server/socket-server.py /usr/local/bin/unix-socket-server
sudo cp server/cli-client.py /usr/local/bin/unix-socket-client
sudo chmod +x /usr/local/bin/unix-socket-*
sudo mkdir -p /etc/socket-bridge
sudo cp examples/* /etc/socket-bridge/
```

## 📖 Quick Start

### 1. Start a Socket Server

```bash
# Start the playerctl service
python3 /usr/local/bin/unix-socket-server /etc/socket-bridge/playerctl.json

# Or for system monitoring
python3 /usr/local/bin/unix-socket-server /etc/socket-bridge/system-control.json
```

### 2. Use in n8n

1. **Access n8n** at http://localhost:5678
2. **Add "Unix Socket Bridge" node** to your workflow (found in Communication section)
3. **Configure the node:**
   - **Socket Path**: `/tmp/playerctl.sock`
   - **Auto-Discover Commands**: ✅ Enabled (default)
4. **Select a command** from the auto-populated dropdown
5. **Execute!** 🎉

### 3. Test with CLI

```bash
# Test server connectivity
python3 /usr/local/bin/unix-socket-client /tmp/playerctl.sock ping

# Get available commands
python3 /usr/local/bin/unix-socket-client /tmp/playerctl.sock introspect

# Execute a command
python3 /usr/local/bin/unix-socket-client /tmp/playerctl.sock exec play-pause
```

## 🔧 Configuration

### Server Configuration Example

```json
{
  "name": "PlayerCtl Media Control",
  "description": "Control media players using playerctl",
  "socket_path": "/tmp/playerctl.sock",
  "socket_permissions": 438,
  "log_level": "INFO",
  "commands": {
    "play-pause": {
      "description": "Toggle play/pause",
      "executable": ["playerctl", "play-pause"],
      "timeout": 5,
      "parameters": {
        "player": {
          "description": "Specific player to control",
          "type": "string",
          "required": false,
          "style": "flag",
          "pattern": "^[a-zA-Z0-9._-]+$"
        }
      }
    }
  }
}
```

### Parameter Types & Styles

- **Types**: `string`, `number`, `boolean`
- **Styles**: `flag` (`--param value`), `argument` (`value`), `single_flag` (`--param=value`)

## 🎯 Use Cases

- **Media Control**: Control music/video players (PlayerCtl)
- **System Monitoring**: Check disk usage, memory, uptime
- **Docker Management**: Start/stop containers, monitor health
- **Custom Applications**: Any command-line tool integration

## 🔒 Security Features

- **Restricted PATH**: Commands run with limited environment
- **Input validation**: All parameters validated against configuration
- **Timeouts**: Configurable timeouts prevent hanging processes
- **Pattern matching**: Regex validation for string parameters
- **Command allowlisting**: Only predefined commands can be executed

## 🧪 Testing

### Running Tests

```bash
cd n8n-node

# Install dependencies and run tests
npm install
npm test

# Run with coverage
npm run test:coverage

# Run linting
npm run lint
```

### Test Coverage

- **Unit Tests**: Node class methods, parameter handling, response parsing
- **Integration Tests**: Real socket communication with mock servers
- **Error Handling**: Invalid inputs, network failures, timeouts

### Validation

```bash
# Validate server configuration
python3 /usr/local/bin/unix-socket-server config.json --validate

# Test server connectivity
python3 /usr/local/bin/unix-socket-client /tmp/socket.sock ping
```

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Node not appearing in n8n | 1. Check `N8N_CUSTOM_EXTENSIONS` environment variable is set<br>2. Check n8n logs: `sudo journalctl -u n8n -f`<br>3. Verify node installation: `npm list -g @tehw0lf/n8n-nodes-unix-socket-bridge` |
| Auto-discovery not working | Verify server is running and socket path is correct |
| Socket connection errors | Check file permissions and server status |
| Command execution failures | Validate parameters and check server logs |

### Quick Diagnostics

```bash
# Check if server is running
ps aux | grep socket-server

# Test socket manually
python3 /usr/local/bin/unix-socket-client /tmp/socket.sock introspect

# Check n8n node installation
npm list -g @tehw0lf/n8n-nodes-unix-socket-bridge

# Verify environment variables are set
echo "N8N_CUSTOM_EXTENSIONS: $N8N_CUSTOM_EXTENSIONS"
echo "N8N_REINSTALL_MISSING_PACKAGES: $N8N_REINSTALL_MISSING_PACKAGES"
```

## 📚 API Reference

### Introspection Commands

- **`__ping__`**: Health check - returns `{"success": true, "message": "pong"}`
- **`__introspect__`**: Returns server info and available commands

### Command Execution

```json
{
  "command": "command_name",
  "parameters": {
    "param1": "value1",
    "param2": 42
  }
}
```

Response:
```json
{
  "success": true,
  "command": "command_name",
  "returncode": 0,
  "stdout": "command output",
  "stderr": ""
}
```

## 🛠️ Development

### Building

```bash
cd n8n-node
npm install
npm run build
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details.

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Examples**: `examples/` directory

---

**Made with ❤️ for the n8n community**

*Transform any command-line tool into an n8n-accessible service with Unix Socket Bridge!*