# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a Unix Socket Bridge system consisting of two main components:

1. **Python Socket Server** (`server/socket-server.py`): Generic configurable server that exposes system commands via Unix domain sockets
2. **n8n Node Package** (`n8n-node/`): TypeScript-based n8n community node for seamless workflow integration

### Key Components

- **UnixSocketBridge.node.ts**: Main n8n node implementation with auto-discovery and parameter validation
- **socket-server.py**: Python server with JSON configuration-driven command execution
- **Configuration Examples**: `examples/playerctl.json` and `examples/system-control.json` demonstrate different use cases

### Communication Flow

1. n8n node connects to Unix domain socket
2. Sends JSON commands with optional parameters
3. Server validates and executes predefined commands
4. Returns structured JSON responses with stdout/stderr/returncode

## Development Commands

### n8n Node Development

```bash
cd n8n-node

# Install dependencies
npm install

# Build the TypeScript code
npm run build

# Run tests with Jest
npm test

# Run tests with coverage report
npm run test:coverage

# Run tests in watch mode (for development)
npm run test:watch

# Lint TypeScript code
npm run lint

# Package for distribution
npm pack
```

### Pre-commit Validation

Always run these commands before committing:

```bash
cd n8n-node && npm run lint && npm run test && npm run build
```

### Python Server Testing

```bash
# Validate server configuration
python3 server/socket-server.py examples/playerctl.json --validate

# Test server connectivity with CLI client
python3 server/cli-client.py /tmp/playerctl.sock ping
python3 server/cli-client.py /tmp/playerctl.sock introspect
```

### Installation and Deployment

```bash
# Install n8n node globally
cd n8n-node
npm run build && npm pack
npm install -g ./n8n-nodes-unix-socket-bridge-*.tgz

# Install server components system-wide
sudo cp server/socket-server.py /usr/local/bin/unix-socket-server
sudo cp server/cli-client.py /usr/local/bin/unix-socket-client
sudo chmod +x /usr/local/bin/unix-socket-*
```

## Code Architecture

### n8n Node Structure

The UnixSocketBridge node implements:

- **Auto-discovery**: Introspects server capabilities via `__introspect__` command
- **Dynamic UI**: Populates command dropdown based on server configuration
- **Parameter Handling**: Supports typed parameters with validation patterns
- **Response Parsing**: Auto-detects JSON vs text responses
- **Error Handling**: Graceful degradation with continue-on-fail support

Key methods:
- `getAvailableCommands()`: Loads command options dynamically (n8n-node/nodes/UnixSocketBridge/UnixSocketBridge.node.ts:212)
- `execute()`: Main execution logic with parameter processing (n8n-node/nodes/UnixSocketBridge/UnixSocketBridge.node.ts:337)
- `sendToUnixSocket()`: Helper function for socket communication (n8n-node/nodes/UnixSocketBridge/UnixSocketBridge.node.ts:507)

### Python Server Architecture

The ConfigurableSocketServer class provides:

- **JSON Configuration**: Commands defined with executable paths, parameters, and validation
- **Parameter Types**: Support for string, number, boolean with different styles (flag, argument, single_flag)
- **Security**: Input validation, command allowlisting, and timeout enforcement
- **Introspection**: Built-in commands for health checks and capability discovery

### Configuration Schema

Server configurations must include:
- `name`: Human-readable server description
- `socket_path`: Unix socket file location
- `commands`: Dictionary of available commands with:
  - `description`: User-friendly command description
  - `executable`: Array of command and arguments
  - `timeout`: Maximum execution time
  - `parameters`: Optional typed parameters with validation

## Testing Strategy

### Test Coverage Areas

- **Unit Tests**: Node class methods, parameter validation, response parsing
- **Integration Tests**: Real socket communication with mock servers
- **Socket Communication**: Connection handling, timeouts, error scenarios
- **Parameter Processing**: Type conversion, validation, command building

### Test Files

- `tests/UnixSocketBridge.test.ts`: Core node functionality
- `tests/UnixSocketBridge.simple.test.ts`: Basic operation tests
- `tests/socketCommunication.test.ts`: Socket-specific testing
- `tests/integration.test.ts`: End-to-end scenarios

## Security Considerations

- Commands are allowlisted in server configuration
- Parameters validated against regex patterns
- Timeout enforcement prevents hanging processes
- Restricted PATH environment for command execution
- Socket file permissions configurable (default 438/0o666)

## Common Development Tasks

### Adding New Commands

1. Update server JSON configuration with command definition
2. Define parameters with proper types and validation
3. Test command execution via CLI client
4. Verify n8n node auto-discovery picks up new commands

### Debugging Connection Issues

1. Check socket file exists and has correct permissions
2. Verify server is running: `ps aux | grep socket-server`
3. Test with CLI client: `python3 server/cli-client.py /tmp/socket.sock ping`
4. Check n8n logs for detailed error messages