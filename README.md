# Unix Socket Bridge for n8n

A powerful n8n community node that enables communication with Unix domain sockets, allowing you to integrate command-line tools and system services directly into your n8n workflows.

## 🚀 Features

- **Auto-Discovery**: Automatically discovers available commands from running socket servers
- **Easy Integration**: Simple dropdown selection of available commands in n8n
- **Parameter Validation**: Built-in validation ensures correct command execution
- **Flexible Configuration**: Works with any system command via JSON configuration
- **🔐 Secure Authentication**: SHA-256 hashed token authentication (never sends plain text)
- **⚡ Rate Limiting**: Built-in rate limiting to prevent abuse and control resource usage
- **📏 Size Limits**: Configurable request/response size limits for memory safety
- **🛡️ Security Controls**: Command allowlisting, input validation, and sandboxed execution
- **🔒 Environment Security**: Secure token storage via environment variables
- **🧵 Threading Support**: Optional multi-threading for concurrent request handling
- **Production Ready**: Includes systemd service examples and comprehensive security features

## ⚠️ Important Docker Limitation

**This Unix Socket Bridge cannot be used if n8n runs in a Docker container and the socket is on the host machine.** Unix domain sockets are filesystem-based and cannot cross container boundaries by default.

### Supported Configurations:
- ✅ **n8n installed natively on host** + Unix sockets on host (full functionality)
  - Works Linux, macOS (any Unix system with socket support)
- ✅ **n8n in Docker** + Unix sockets **inside the same container** (limited use cases)
- ✅ **Managing Docker containers** from native n8n installation

### Unsupported Configuration:
- ❌ **n8n in Docker container** trying to access Unix sockets on the host filesystem

**Solution**: For full functionality, install n8n natively on the host system to have direct access to Unix domain sockets.

## 📦 Installation

### Install in n8n

1. Open your n8n instance
2. Go to **Settings** → **Community Nodes**
3. Click **Install a community node**
4. Enter: `@tehw0lf/n8n-nodes-unix-socket-bridge`
5. Click **Install**

The node will now appear in your node list under "Unix Socket Bridge"!

### Install the Socket Server

The socket server is a Python script that exposes your system commands to n8n:

```bash
# Download the repository or copy the server files
git clone https://github.com/yourusername/unix-socket-bridge.git
cd unix-socket-bridge

# Install server (and example configurations)
sudo cp server/socket-server.py /usr/local/bin/unix-socket-server
sudo chmod +x /usr/local/bin/unix-socket-server
sudo chown your-username:your-group /usr/local/bin/unix-socket-server
sudo mkdir -p /etc/socket-bridge
sudo cp examples/* /etc/socket-bridge/ # optional
sudo chown -R your-username:your-group /etc/socket-bridge
```

## 📖 Quick Start

### 1. Start a Socket Server

Use one of the example configurations from the `examples/` directory:

```bash
# For media player control
python3 /usr/local/bin/unix-socket-server examples/playerctl.json

# For system monitoring  
python3 /usr/local/bin/unix-socket-server examples/system-control.json
```

### 2. Use in n8n

1. **Add the Unix Socket Bridge node** to your workflow
2. **Configure the socket path**: The path from your config (e.g., `/tmp/socket-bridge/playerctl.sock`)
3. **Select a command** from the auto-populated dropdown
4. **Configure parameters** if needed
5. **Execute your workflow!** 🎉

### 3. Test Connection (Optional)

You can test if your server is working using the included CLI client:

```bash
# Copy the CLI client
sudo cp server/cli-client.py /usr/local/bin/unix-socket-client
sudo chmod +x /usr/local/bin/unix-socket-client

# Test the connection
unix-socket-client /tmp/playerctl.sock ping

# See available commands
unix-socket-client /tmp/playerctl.sock introspect
```

## 🔐 Security Configuration

### Authentication

The Unix Socket Bridge supports secure token-based authentication. You can configure authentication in two ways:

#### Method 1: Configuration File (Recommended)
Add authentication directly to your config file:
```json
{
  "auth_enabled": true,
  "auth_token_hash": "e06b5a4f194b95775ffd36453d8abaea0226a1d8b127ad9ce96357d9eda64b51",
  "commands": { ... }
}
```

#### Method 2: Environment Variables
```bash
export AUTH_ENABLED=true
export AUTH_TOKEN_HASH=e06b5a4f194b95775ffd36453d8abaea0226a1d8b127ad9ce96357d9eda64b51
python3 /usr/local/bin/unix-socket-server /path/to/config.json
```

#### Generate Secure Token Hash
```bash
# Use the included generator (recommended)
python3 server/generate-token-hash.py

# Or manually generate
echo -n "your-secret-token" | sha256sum
```

#### Configure n8n Node
In your n8n workflow:
- Set the **Auth Token** field to your original plaintext token
- The node automatically hashes it for secure transmission

### Rate Limiting

Control request frequency to prevent abuse:

```bash
# Configure rate limiting (30 requests per 60 seconds by default)
export AUTH_MAX_ATTEMPTS=5        # Max failed auth attempts
export AUTH_WINDOW_SECONDS=60     # Time window for rate limiting
export AUTH_BLOCK_DURATION=60     # Block duration after max attempts
```

### Advanced Security Options

Add to your server configuration file:

```json
{
  "name": "Secure Service",
  "socket_path": "/tmp/socket-bridge/secure.sock",
  "socket_permissions": 666,
  "max_request_size": 1048576,
  "max_output_size": 100000,
  "enable_rate_limit": true,
  "rate_limit": {
    "requests": 30,
    "window": 60
  },
  "allowed_executable_dirs": ["/usr/bin/", "/usr/local/bin/"],
  "commands": {
    "safe-command": {
      "description": "A secure command",
      "executable": ["echo", "hello"],
      "timeout": 10
    }
  }
}
```

## 🎯 Example Use Cases

### Media Control
Control your media players directly from n8n workflows:
- Play/pause music based on calendar events
- Skip tracks via webhook triggers
- Create custom media automation flows

### System Monitoring
Monitor and react to system metrics:
- Send alerts when disk space is low
- Track memory usage over time
- Automate system maintenance tasks

### Docker Management
Integrate Docker operations into workflows:
- Start/stop containers based on schedules
- Monitor container health
- Automate deployment processes

### Custom Integrations
Connect any command-line tool to n8n:
- Database backups
- File processing
- Custom scripts and applications

## 🔧 Creating Custom Socket Services

Create a JSON configuration file for your commands:

```json
{
  "name": "My Custom Service",
  "description": "Description of your service",
  "socket_path": "/tmp/socket-bridge/my-service.sock",
  "commands": {
    "my-command": {
      "description": "What this command does",
      "executable": ["command", "arg1"],
      "parameters": {
        "param1": {
          "description": "Parameter description",
          "type": "string",
          "required": false
        }
      }
    }
  }
}
```

Start your custom server:
```bash
python3 /usr/local/bin/unix-socket-server /path/to/your/config.json
```

## 📚 Configuration Examples

### Version 1.3.0 Security Enhancements

All example configurations in the `examples/` directory have been updated with:

- **🔒 Strict Parameter Validation**: Enhanced input validation with length limits
- **📁 Runtime Directory Templating**: `{RUNTIME_DIR}` for user-specific socket paths  
- **🛡️ Reduced Socket Permissions**: Changed from 438 to 420 for better security
- **📏 Optimized Size Limits**: 4KB request limits for better resource management
- **🚫 No Shell Execution**: Direct command execution without `bash -c` wrappers

### Available Examples

- **`examples/playerctl.json`** - Media player control (play, pause, metadata, etc.)
- **`examples/playerctl-secure.json`** - Same as above with authentication enabled  
- **`examples/system-control.json`** - System monitoring (disk, memory, network, etc.)

### Deployment Patterns

**For systemd user services (recommended):**
- Copy configs to `~/.config/socket-bridge/`
- Use the user service template for automatic startup
- Clean separation from system configs

**For manual/testing:**
- Use configs directly from `examples/`
- Sockets created in `/tmp/socket-bridge/`

### Basic Configuration Structure
```json
{
  "name": "Your Service Name",
  "socket_path": "/tmp/socket-bridge/service.sock",
  "allowed_executable_dirs": ["/usr/bin/", "/bin/", "/usr/local/bin/"],
  "auth_enabled": false,
  "commands": {
    "command-name": {
      "description": "What this command does",
      "executable": ["command", "arg1", "arg2"],
      "timeout": 10
    }
  }
}
```

### Parameter Validation System

Commands can include parameters with comprehensive validation to ensure security and correctness:

```json
{
  "name": "Service With Parameters",
  "socket_path": "/tmp/socket-bridge/service.sock",
  "allowed_executable_dirs": ["/usr/bin/", "/bin/", "/usr/local/bin/"],
  "commands": {
    "example-command": {
      "description": "Command demonstrating parameter validation",
      "executable": ["echo"],
      "timeout": 10,
      "parameters": {
        "message": {
          "description": "Message to display",
          "type": "string",
          "required": true,
          "style": "argument",
          "pattern": "^[a-zA-Z0-9._\\-\\s!?,]+$",
          "max_length": 100
        },
        "verbose": {
          "description": "Enable verbose output",
          "type": "boolean", 
          "required": false,
          "style": "flag"
        },
        "player": {
          "description": "Specific player to control",
          "type": "string",
          "required": false,
          "style": "single_flag",
          "pattern": "^[a-zA-Z0-9._-]+$",
          "max_length": 50
        }
      }
    }
  }
}
```

#### Parameter Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `description` | string | Yes | Human-readable description of the parameter |
| `type` | string | Yes | Parameter type: `string`, `number`, `boolean`, `json`, `auto` |
| `required` | boolean | Yes | Whether the parameter is required |
| `style` | string | Yes | How the parameter is passed to the command |
| `pattern` | string | No | Regex pattern for validation (string types only) |
| `max_length` | number | No | Maximum length validation |
| `min_value` | number | No | Minimum value (number types only) |
| `max_value` | number | No | Maximum value (number types only) |

#### Parameter Styles

| Style | Description | Example Output |
|-------|-------------|----------------|
| `argument` | Passed as a positional argument | `command value` |
| `flag` | Passed as `--name value` | `command --verbose true` |
| `single_flag` | Passed as `--name=value` | `command --player=spotify` |

#### Parameter Types

- **`string`**: Text values with optional regex pattern validation
- **`number`**: Numeric values with optional min/max validation  
- **`boolean`**: True/false values (converted to strings for commands)
- **`json`**: Complex objects passed as JSON strings
- **`auto`**: Automatic type detection based on input

#### Security Features

- **Regex Validation**: All string parameters can enforce regex patterns
- **Length Limits**: Prevent oversized inputs with `max_length`
- **Type Safety**: Parameters are validated and converted to correct types
- **Required Validation**: Missing required parameters are rejected
- **Pattern Enforcement**: Invalid patterns are blocked before execution

## 🔐 Running as a System Service

### User Services (Recommended)

For user-specific services (when you need access to user sessions like DBUS), use the included user service template:

```bash
# Install the user service template
sudo cp systemd/socket-bridge-user@.service /etc/systemd/user/
sudo systemctl daemon-reload

# Create user configuration directory
mkdir -p ~/.config/socket-bridge

# Copy example configurations
cp examples/playerctl.json ~/.config/socket-bridge/
cp examples/system-control.json ~/.config/socket-bridge/

# Enable and start user services
systemctl --user enable socket-bridge-user@playerctl.service
systemctl --user start socket-bridge-user@playerctl.service

systemctl --user enable socket-bridge-user@system-control.service  
systemctl --user start socket-bridge-user@system-control.service

# Check status
systemctl --user status socket-bridge-user@playerctl.service
journalctl --user -u socket-bridge-user@playerctl.service -f
```

The user service template (`socket-bridge-user@.service`) provides:
- **User-specific execution**: Runs as your user with access to your DBUS session
- **Enhanced security**: `NoNewPrivileges`, `ProtectSystem=strict`
- **User isolation**: `ProtectHome=read-only` for security
- **Automatic restart**: Service restarts on failure

### System Services (Alternative)

For system-wide services (requires configuring User= to match the user with required access):

```bash
# Create service file
sudo nano /etc/systemd/system/socket-bridge-playerctl.service
```

```ini
[Unit]
Description=Unix Socket Bridge - PlayerCtl
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/unix-socket-server /etc/socket-bridge/playerctl.json
Restart=always
User=your-username  # Must be user with access to playerctl/DBUS
# Essential for DBUS/playerctl access in systemd context
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
Environment=AUTH_ENABLED=true
Environment=AUTH_TOKEN_HASH=your-hashed-token-here

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl enable socket-bridge-playerctl
sudo systemctl start socket-bridge-playerctl
```

## 🆘 Troubleshooting

### Node not appearing in n8n?
- Make sure you've restarted n8n after installation
- Check the n8n logs for any error messages

### Commands not showing in dropdown?
- Verify the socket server is running: `ps aux | grep socket-server`
- Check if the socket file exists: `ls -la /tmp/*.sock`
- Test the connection: `unix-socket-client /tmp/your-socket.sock ping`

### Permission denied errors?
- Make sure n8n can access the socket file
- Check socket file permissions: `ls -la /tmp/your-socket.sock`
- Consider running the socket server as the same user as n8n

## 💻 Platform Compatibility

- **Linux**: Full support for all features
- **macOS**: Full support for all features (tested and confirmed)
- **Windows**: Not supported (Unix domain sockets not available)

## 🔒 Security

⚠️ **For comprehensive security guidance, see [SECURITY.md](SECURITY.md)**

### Quick Security Setup

1. **Generate secure token**: `python3 server/generate-token-hash.py --random`
2. **Enable auth in config**: Add `"auth_enabled": true` to your config.json
3. **Configure server**: `export AUTH_TOKEN_HASH="your-hash"`  
4. **Configure n8n**: Use "HTTP Header Auth" credentials with plain text token
5. **Security**: Plain text tokens are hashed before transmission (SHA-256)

## 🔒 Security Notes

- **🔐 Secure Authentication**: SHA-256 hashed tokens only - no plain text transmission
- **⚡ Rate Limiting**: Built-in protection against abuse with configurable limits
- **📏 Size Limits**: Request and response size limits prevent memory exhaustion attacks
- **🛡️ Security-First**: Plain text token support removed - credentials required
- **✅ Command Allowlisting**: Only commands defined in your configuration can be executed
- **🔍 Input Validation**: All parameters validated against patterns and types
- **🗂️ Path Restrictions**: Executables must be in predefined allowed directories
- **⏱️ Timeout Protection**: Commands have configurable timeouts to prevent hanging
- **🔒 File Permissions**: Socket files created with restrictive permissions (600 by default)
- **👤 User Separation**: Run socket servers with limited user privileges (www-data recommended)
- **🏖️ Sandboxed Execution**: Commands run with restricted environment variables

## 📝 License

MIT License - see LICENSE file for details

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/unix-socket-bridge/issues)
- **Examples**: Check the `examples/` directory for more configurations

---

**Made with ❤️ for the n8n community**

*Transform any command-line tool into an n8n-accessible service!*