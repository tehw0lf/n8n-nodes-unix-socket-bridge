# Unix Socket Bridge for n8n

A powerful n8n community node that enables communication with Unix domain sockets, allowing you to integrate command-line tools and system services directly into your n8n workflows.

## 🚀 Features

- **Auto-Discovery**: Automatically discovers available commands from running socket servers
- **Easy Integration**: Simple dropdown selection of available commands in n8n
- **Parameter Validation**: Built-in validation ensures correct command execution
- **Flexible Configuration**: Works with any system command via JSON configuration
- **Production Ready**: Includes systemd service examples and security controls

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

# Install server and example configurations
sudo cp server/socket-server.py /usr/local/bin/unix-socket-server
sudo chmod +x /usr/local/bin/unix-socket-server
sudo mkdir -p /etc/socket-bridge
sudo cp examples/* /etc/socket-bridge/
```

## 📖 Quick Start

### 1. Start a Socket Server

Use one of the included example configurations:

```bash
# For media player control
python3 /usr/local/bin/unix-socket-server /etc/socket-bridge/playerctl.json

# For system monitoring
python3 /usr/local/bin/unix-socket-server /etc/socket-bridge/system-control.json
```

### 2. Use in n8n

1. **Add the Unix Socket Bridge node** to your workflow
2. **Configure the socket path**: `/tmp/playerctl.sock` (or your custom path)
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
  "socket_path": "/tmp/my-service.sock",
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

### PlayerCtl Media Control
Control media players on your system:
```json
{
  "name": "PlayerCtl Media Control",
  "socket_path": "/tmp/playerctl.sock",
  "commands": {
    "play-pause": {
      "description": "Toggle play/pause",
      "executable": ["playerctl", "play-pause"]
    },
    "next": {
      "description": "Next track",
      "executable": ["playerctl", "next"]
    }
  }
}
```

### System Monitoring
Monitor system resources:
```json
{
  "name": "System Monitor",
  "socket_path": "/tmp/system.sock",
  "commands": {
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

## 🔐 Running as a System Service

For production use, run the socket server as a systemd service:

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
User=www-data

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

## 🔒 Security Notes

- **Command Allowlisting**: Only commands defined in your configuration can be executed
- **Input Validation**: All parameters are validated against your configuration
- **Sandboxed Execution**: Commands run with restricted environment variables
- **User Separation**: Consider running socket servers with limited user privileges

## 📝 License

MIT License - see LICENSE file for details

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/unix-socket-bridge/issues)
- **Examples**: Check the `examples/` directory for more configurations

---

**Made with ❤️ for the n8n community**

*Transform any command-line tool into an n8n-accessible service!*