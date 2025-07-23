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

## 🛠️ Installation

### Prerequisites

- **n8n** (tested with v1.102.4+)
- **Python 3.x** for the socket server
- **Node.js/npm** for the n8n node

### Quick Setup

1. **Install the n8n node:**
```bash
cd n8n-node
npm install
npm run build
npm pack
npm install -g ./n8n-nodes-unix-socket-bridge-1.0.0.tgz
```

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
| Node not appearing in n8n | Check n8n logs: `sudo journalctl -u n8n -f` |
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
npm list -g | grep unix-socket-bridge
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