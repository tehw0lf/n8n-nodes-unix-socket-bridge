# End-to-End Tests for Unix Socket Bridge

This directory contains comprehensive end-to-end tests that verify the complete integration between the n8n Unix Socket Bridge node and a Python socket server.

## Overview

The E2E tests provide:

- **Real Integration Testing**: Tests actual communication between the n8n node and Python server
- **Server Lifecycle Management**: Automated Python server startup/shutdown
- **Comprehensive Test Coverage**: Command execution, parameter handling, error scenarios, and concurrency
- **Resource Management**: Automatic cleanup of sockets, processes, and temporary files
- **Health Checks**: Server readiness detection with retry logic

## Architecture

### Components

1. **`UnixSocketBridge.e2e.test.ts`** - Main test suite with comprehensive scenarios
2. **`python-server-manager.ts`** - Python server process lifecycle management
3. **`test-config.json`** - Safe test server configuration
4. **`utils/`** - Supporting utilities:
   - `health-check.ts` - Server readiness detection
   - `cleanup.ts` - Resource management and cleanup
   - `mock-context.ts` - n8n execution context mocking

### Test Configuration

The E2E tests use a dedicated test server configuration (`test-config.json`) with safe commands:

- **`ping`** - Health check command
- **`echo`** - Text echo with optional message parameter
- **`sleep`** - Timed operation with duration parameter
- **`count`** - Counting with reverse boolean parameter
- **`parameter_test`** - Multi-parameter validation
- **`fail`** - Controlled failure scenario
- **`timeout_test`** - Timeout handling test

## Running the Tests

### Prerequisites

1. **Python 3** must be installed and available as `python3`
2. **Python socket server** must be available at `../../server/socket-server.py`
3. **n8n node build** must be completed (`npm run build`)

### Commands

```bash
# Run all E2E tests
npm run test:e2e

# Run specific test file
npx jest tests/e2e/UnixSocketBridge.e2e.test.ts

# Run with verbose output
npx jest tests/e2e/UnixSocketBridge.e2e.test.ts --verbose

# Run single test case
npx jest tests/e2e/UnixSocketBridge.e2e.test.ts -t "should successfully ping"
```

### Configuration

E2E tests use a dedicated Jest configuration (`jest.e2e.config.js`) with:

- **60 second timeout** for server startup and complex operations
- **Serial execution** (maxWorkers: 1) to avoid socket conflicts
- **Specific test pattern** matching only E2E test files

## Test Scenarios

### 1. Server Health and Introspection

- **Ping Test**: Basic server connectivity
- **Introspection Test**: Command discovery and server metadata

### 2. Command Execution

- **Basic Commands**: Echo without parameters
- **String Parameters**: Echo with custom message
- **Numeric Parameters**: Sleep with duration
- **Boolean Parameters**: Count with reverse flag
- **Multi-Parameter**: Complex parameter validation

### 3. Error Handling

- **Command Failures**: Graceful handling of failed commands
- **Timeouts**: Server unresponsiveness scenarios
- **Invalid Commands**: Non-existent command handling
- **Socket Errors**: Invalid socket path handling

### 4. Response Format Handling

- **Auto-Detection**: JSON vs text response parsing
- **Explicit JSON**: Structured response parsing
- **Plain Text**: Text response handling

### 5. Concurrent Operations

- **Multiple Requests**: Simultaneous command execution
- **Resource Isolation**: No interference between concurrent requests

### 6. Dynamic Command Discovery

- **Command Loading**: n8n dropdown population via introspection
- **Server Metadata**: Command descriptions and parameters

## Test Structure

Each test follows this pattern:

```typescript
test('should perform specific action', async () => {
  // 1. Create mock n8n execution context
  const mockContext = createMockExecuteFunctions({
    socketPath: TEST_SOCKET_PATH,
    command: 'test_command',
    parameters: { parameter: [{ name: 'param', value: 'value' }] }
  });

  // 2. Execute the n8n node
  const result = await unixSocketBridge.execute.call(mockContext);

  // 3. Validate the response structure
  expect(result).toHaveLength(1);
  expect(result[0]).toHaveLength(1);
  expect(result[0][0].json.success).toBe(true);
  
  // 4. Validate specific response content
  expect(result[0][0].json.response).toContain('expected content');
}, TEST_TIMEOUT);
```

## Resource Management

### Automatic Cleanup

The test suite automatically manages:

- **Socket Files**: Cleanup of Unix domain socket files
- **Process Termination**: Graceful shutdown of Python servers
- **Temporary Directories**: Removal of test-specific directories
- **File Operations**: Cleanup of temporarily created files

### Resource Tracking

The `ResourceManager` class provides:

```typescript
// Track resources for cleanup
resourceManager.trackSocketPath('/tmp/test.sock');
resourceManager.trackProcess(pythonProcess);
resourceManager.trackTempDir('/tmp/test-dir');

// Automatic cleanup on test completion
await resourceManager.cleanupAll();
```

## Server Management

### Python Server Lifecycle

```typescript
// Initialize and start server
const serverManager = new PythonServerManager(
  configPath,
  socketPath,
  resourceManager
);

await serverManager.start(); // Starts Python server
await serverManager.stop();  // Graceful shutdown
```

### Health Checks

```typescript
// Wait for server readiness
const isReady = await healthCheck(socketPath, timeout);

// Ping-based health verification
const response = await sendPing(socketPath);
```

## Debugging

### Common Issues

1. **Server Startup Timeout**
   - Check Python 3 availability
   - Verify socket server script path
   - Review server configuration

2. **Socket Permission Errors**
   - Ensure `/tmp` directory access
   - Check socket file permissions
   - Verify cleanup completed from previous runs

3. **Test Timeouts**
   - Increase `TEST_TIMEOUT` for slow systems
   - Check server responsiveness
   - Review test complexity

### Debug Commands

```bash
# Check Python server manually
python3 ../../server/socket-server.py tests/e2e/test-config.json

# Test socket connectivity
python3 ../../server/cli-client.py /tmp/e2e-test-unix-socket-bridge.sock ping

# View detailed test output
npm run test:e2e -- --verbose --no-cache
```

### Log Analysis

The tests provide detailed logging:

- **Server startup/shutdown events**
- **Socket communication attempts**
- **Command execution traces**
- **Error details with context**

## CI/CD Integration

### GitHub Actions

The E2E tests are designed for CI/CD environments with:

- **Isolated execution**: Each test run uses unique socket paths
- **Resource cleanup**: Comprehensive cleanup prevents test interference
- **Error reporting**: Detailed failure information for debugging
- **Timeout handling**: Reasonable timeouts for various environments

### Pre-commit Validation

Include E2E tests in pre-commit hooks:

```bash
# Full validation pipeline
npm run lint && npm run test && npm run build && npm run test:e2e
```

## Extending the Tests

### Adding New Test Scenarios

1. **Add command to test-config.json**
2. **Create test case with appropriate mock context**
3. **Validate response structure and content**
4. **Include error scenarios if applicable**

### Custom Server Configurations

```typescript
// Create custom test server config
const customConfig = {
  name: "Custom Test Server",
  socket_path: "/tmp/custom-test.sock",
  commands: {
    custom_command: {
      description: "Custom test command",
      executable: ["echo", "custom response"],
      timeout: 5
    }
  }
};
```

### Mock Context Customization

```typescript
// Create specialized mock contexts
const mockContext = createMockExecuteFunctions({
  socketPath: customSocketPath,
  command: 'custom_command',
  timeout: 10000,
  responseFormat: 'json',
  parameters: { 
    parameter: [
      { name: 'custom_param', value: 'custom_value' }
    ] 
  }
});
```

## Best Practices

1. **Resource Cleanup**: Always use ResourceManager for test resource tracking
2. **Server Lifecycle**: Start server in `beforeAll`, stop in `afterAll`
3. **Test Isolation**: Use unique socket paths for concurrent test suites
4. **Error Handling**: Test both success and failure scenarios
5. **Timeouts**: Set appropriate timeouts for server operations
6. **Validation**: Verify both response structure and content
7. **Documentation**: Document any custom test scenarios or configurations