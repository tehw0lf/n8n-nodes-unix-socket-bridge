# n8n-nodes-unix-socket-bridge

![n8n.io - Workflow Automation](https://raw.githubusercontent.com/n8n-io/n8n/master/assets/n8n-logo.png)

An n8n community node that enables generic Unix domain socket communication with configurable servers for system automation and command execution.

[n8n](https://n8n.io/) is a [fair-code licensed](https://docs.n8n.io/reference/license/) workflow automation platform.

### Global Installation

To install globally, run the following in your n8n installation directory:

```bash
npm install -g @tehw0lf/n8n-nodes-unix-socket-bridge
```


### Local Installation

To install locally, run the following in your n8n installation directory:

```bash
npm install @tehw0lf/n8n-nodes-unix-socket-bridge
```

## Operations

The Unix Socket Bridge node provides seamless communication with Unix domain socket servers:

- **Auto-Discovery**: Automatically discovers available commands from servers at runtime
- **Raw Communication**: Send raw messages to Unix sockets  
- **JSON Commands**: Send structured JSON commands with parameter validation
- **Flexible Response Handling**: Auto-detect JSON responses or handle as plain text

## Node Reference

### Socket Path
Path to the Unix domain socket file (e.g., `/tmp/socket.sock`)

### Auto-Discover Commands
When enabled, the node automatically discovers available commands from the server using introspection. This provides a user-friendly dropdown of available operations.

### Operation Modes

#### Auto-Discovery Mode (Recommended)
- Automatically loads available commands from the server
- Provides dropdown selection of commands
- Validates parameters based on server configuration
- Handles parameter types and formatting automatically

#### Manual Modes  
- **Send JSON Command**: Manually specify command name and parameters
- **Send Raw Message**: Send arbitrary text messages to the socket

### Parameters
When using JSON commands, parameters can be provided as key-value pairs. The node handles:
- **String parameters**: Text values
- **Number parameters**: Numeric values  
- **Boolean parameters**: True/false flags
- **Parameter validation**: Based on server-defined patterns and types

### Response Handling
- **Auto-Detect** (default): Automatically detects JSON responses, falls back to text
- **JSON**: Forces JSON parsing of responses
- **Text**: Returns raw text responses

## Configuration Example

### Server Setup
First, set up a Unix socket server using the provided server component:

```json
{
  "name": "System Control",
  "description": "Basic system monitoring commands",
  "socket_path": "/tmp/system.sock",
  "commands": {
    "uptime": {
      "description": "Get system uptime",
      "executable": ["uptime"],
      "timeout": 5
    },
    "disk-usage": {
      "description": "Check disk usage",
      "executable": ["df", "-h"],
      "timeout": 10,
      "parameters": {
        "path": {
          "description": "Specific path to check",
          "type": "string",
          "required": false,
          "style": "argument"
        }
      }
    }
  }
}
```

### n8n Workflow Usage
1. Add the Unix Socket Bridge node to your workflow
2. Configure the socket path: `/tmp/system.sock`
3. Enable auto-discovery (recommended)
4. Select a command from the dropdown (e.g., "uptime")
5. Add parameters if needed
6. Execute the workflow

## Use Cases

- **System Monitoring**: Check disk usage, memory, CPU, uptime
- **Media Control**: Control music/video players via playerctl
- **Docker Management**: Start/stop containers, health checks
- **Custom Applications**: Integrate any command-line tool with n8n
- **System Administration**: Automate routine system tasks
- **Development Tools**: Integrate build tools, test runners, deployment scripts

## Server Component

This n8n node works with the Unix Socket Bridge server, which provides:

- **Configurable Commands**: Define any system command via JSON configuration
- **Parameter Validation**: Built-in type checking and pattern validation
- **Security**: Sandboxed execution with restricted environments
- **Introspection**: Auto-discovery of available commands

For complete server setup and configuration examples, see the [main repository](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge).

## Security

- Commands are allowlisted in server configuration
- Input validation prevents command injection
- Configurable timeouts prevent hanging processes
- Restricted execution environment
- Socket file permissions control access

## Compatibility

- **Node.js**: >=16.0.0
- **n8n**: 1.0.0+ (tested with 1.102.4+)
- **Operating Systems**: Linux, macOS (Unix systems with socket support)

## Resources

- [n8n community nodes documentation](https://docs.n8n.io/integrations/community-nodes/)
- [GitHub Repository](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge)
- [Configuration Examples](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge/tree/main/examples)

## License

[MIT](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge/blob/main/LICENSE)

## Support

- **Issues**: [GitHub Issues](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge/issues)
- **Documentation**: [Repository README](https://github.com/tehw0lf/n8n-nodes-unix-socket-bridge#readme)