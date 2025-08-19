import {
  afterAll,
  beforeAll,
  describe,
  expect,
  jest,
  test,
} from "@jest/globals";
import { IDataObject } from "n8n-workflow";
import * as path from "path";

import { UnixSocketBridge } from "../../nodes/UnixSocketBridge/UnixSocketBridge.node";
import { PythonServerManager } from "./python-server-manager";
import { ResourceManager } from "./utils/cleanup";

/**
 * End-to-End tests for Unix Socket Bridge
 * Tests the actual integration between n8n node and Python socket server
 */
// Test configuration
const TEST_CONFIG_PATH = path.join(__dirname, "test-config.json");
const TEST_SOCKET_PATH = "/tmp/e2e-test-unix-socket-bridge.sock";
const SERVER_STARTUP_TIMEOUT = 10000;
const TEST_TIMEOUT = 30000;

/**
 * Create a mock IExecuteFunctions context for testing
 */
function createMockExecuteFunctions(parameters: Record<string, any> = {}): any {
  const mockParameters: { [key: string]: any } = {
    socketPath: TEST_SOCKET_PATH,
    autoDiscover: false,
    timeout: 5000,
    responseFormat: "auto",
    command: "ping",
    parameters: { parameter: [] },
    ...parameters,
  };

  let paramIndex = 0;
  const paramValues = Object.values(mockParameters);

  const mockExecuteFunctions: any = {
    getInputData: jest.fn().mockReturnValue([{ json: {} }]),
    getNodeParameter: jest.fn().mockImplementation((...args: any[]) => {
      const paramName = args[0] as string;
      if (mockParameters[paramName] !== undefined) {
        return mockParameters[paramName];
      }
      return paramValues[paramIndex++];
    }),
    getNode: jest.fn().mockReturnValue({
      name: "E2E Test Node",
      id: "e2e-test-id",
      typeVersion: 1,
      type: "unixSocketBridge",
      position: [0, 0],
      parameters: mockParameters,
    } as any),
    continueOnFail: jest.fn().mockReturnValue(false),
  };

  return mockExecuteFunctions;
}

describe("Unix Socket Bridge E2E Tests", () => {
  let serverManager: PythonServerManager;
  let resourceManager: ResourceManager;
  let unixSocketBridge: UnixSocketBridge;

  beforeAll(async () => {
    console.log("🚀 Starting Unix Socket Bridge E2E Tests");

    // Initialize resource manager for cleanup
    resourceManager = new ResourceManager();
    resourceManager.trackSocketPath(TEST_SOCKET_PATH);

    // Initialize Python server manager
    serverManager = new PythonServerManager(
      TEST_CONFIG_PATH,
      TEST_SOCKET_PATH,
      resourceManager
    );

    // Start the Python server
    console.log("📡 Starting Python socket server...");
    await serverManager.start();
    console.log("✅ Python socket server started successfully");

    // Initialize the n8n node
    unixSocketBridge = new UnixSocketBridge();
  }, SERVER_STARTUP_TIMEOUT);

  afterAll(async () => {
    console.log("🧹 Cleaning up E2E test resources...");

    if (serverManager) {
      await serverManager.stop();
    }

    if (resourceManager) {
      await resourceManager.cleanupAll();
    }

    console.log("✅ E2E test cleanup completed");
  });

  describe("Server Health and Introspection", () => {
    test(
      "should successfully ping the server",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "ping",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);
        expect((result[0][0].json.response as IDataObject).stdout).toBe("pong");
      },
      TEST_TIMEOUT
    );

    test(
      "should introspect server capabilities",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "__introspect__",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);

        const response = result[0][0].json.response as any;
        expect(response).toBeDefined();
        expect(response.server_info).toBeDefined();
        expect(response.server_info.name).toBe("E2E Test Server");
        expect(response.server_info.commands).toBeDefined();
        expect(Object.keys(response.server_info.commands)).toContain("ping");
        expect(Object.keys(response.server_info.commands)).toContain("echo");
      },
      TEST_TIMEOUT
    );
  });

  describe("Command Execution", () => {
    test(
      "should not execute echo command without parameters",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "echo",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(false);
        expect((result[0][0].json.response as IDataObject).error).toBe(
          "Missing required parameter: message"
        );
      },
      TEST_TIMEOUT
    );

    test(
      "should execute echo command with string parameter",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "echo",
          parameters: {
            parameter: [{ name: "message", value: "Custom Test Message" }],
          },
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);
        expect(result[0][0].json.response).toBeDefined();
        expect((result[0][0].json.response as IDataObject).stdout).toContain(
          "Custom Test Message"
        );
      },
      TEST_TIMEOUT
    );

    test(
      "should execute sleep command with number parameter",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "sleep",
          parameters: {
            parameter: [{ name: "seconds", value: 1 }],
          },
        });

        const startTime = Date.now();
        const result = await unixSocketBridge.execute.call(mockContext);
        const endTime = Date.now();

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);

        // Should have slept for approximately 1 second
        expect(endTime - startTime).toBeGreaterThanOrEqual(900);
        expect(endTime - startTime).toBeLessThan(2000);
      },
      TEST_TIMEOUT
    );

    test(
      "should execute whoami command",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "whoami",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);
        expect((result[0][0].json.response as IDataObject).stdout).toEqual(
          process.env.USER
        );
      },
      TEST_TIMEOUT
    );

    test(
      "should execute parameter test with multiple parameter types",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "test_params",
          parameters: {
            parameter: [
              { name: "string_param", value: "test_message" },
              { name: "number_param", value: 42 },
              { name: "boolean_param", value: true },
            ],
          },
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);

        const response = result[0][0].json.response as IDataObject;
        expect(response.stdout).toContain("--string_param test_message");
        expect(response.stdout).toContain("--number_param 42");
        expect(response.stdout).toContain("--boolean_param=True");
      },
      TEST_TIMEOUT
    );
  });

  describe("Error Handling", () => {
    test(
      "should handle command failures gracefully",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "fail",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(false);
        expect(result[0][0].json.error).toBeDefined();
        expect(result[0][0].json.returncode).toBe(1);
      },
      TEST_TIMEOUT
    );

    test(
      "should handle command timeouts",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "timeout_test",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(false);
        expect(result[0][0].json.error).toContain("timeout");
      },
      TEST_TIMEOUT
    );

    test(
      "should handle invalid commands",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "nonexistent_command",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(false);
        expect(result[0][0].json.error).toContain("Unknown command");
      },
      TEST_TIMEOUT
    );

    test(
      "should handle invalid socket path",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: "/tmp/nonexistent-socket.sock",
          command: "ping",
        });

        await expect(() =>
          unixSocketBridge.execute.call(mockContext)
        ).rejects.toThrowError(
          "Socket error: Socket not found at /tmp/nonexistent-socket.sock"
        );
      },
      TEST_TIMEOUT
    );
  });

  describe("Response Format Handling", () => {
    test(
      "should auto-detect JSON responses",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "__introspect__",
          responseFormat: "auto",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);
        expect(typeof result[0][0].json.response).toBe("object");
      },
      TEST_TIMEOUT
    );

    test(
      "should handle text responses",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          command: "echo",
          responseFormat: "text",
        });

        const result = await unixSocketBridge.execute.call(mockContext);

        expect(result).toHaveLength(1);
        expect(result[0]).toHaveLength(1);
        expect(result[0][0].json.success).toBe(true);
        expect(typeof result[0][0].json.response).toBe("string");
      },
      TEST_TIMEOUT
    );
  });

  describe("Concurrent Operations", () => {
    test(
      "should handle multiple concurrent requests",
      async () => {
        const promises: Promise<any>[] = [];
        const numConcurrentRequests = 5;

        for (let i = 0; i < numConcurrentRequests; i++) {
          const mockContext = createMockExecuteFunctions({
            socketPath: TEST_SOCKET_PATH,
            command: "echo",
            parameters: {
              parameter: [
                { name: "message", value: `Concurrent Request ${i + 1}` },
              ],
            },
          });

          promises.push(unixSocketBridge.execute.call(mockContext));
        }

        const results = await Promise.all(promises);

        expect(results).toHaveLength(numConcurrentRequests);

        for (let i = 0; i < numConcurrentRequests; i++) {
          expect(results[i]).toHaveLength(1);
          expect(results[i][0]).toHaveLength(1);
          expect(results[i][0][0].json.success).toBe(true);
          expect(
            (results[i][0][0].json.response as IDataObject).stdout
          ).toContain(`Concurrent Request ${i + 1}`);
        }
      },
      TEST_TIMEOUT
    );
  });

  describe("Dynamic Command Discovery", () => {
    test(
      "should discover available commands via introspection",
      async () => {
        const mockContext = createMockExecuteFunctions({
          socketPath: TEST_SOCKET_PATH,
          autoDiscover: true,
        });

        // Simulate n8n's dynamic command loading
        const availableCommands =
          await unixSocketBridge.methods?.loadOptions?.getAvailableCommands?.call(
            mockContext
          );

        expect(availableCommands).toBeDefined();
        expect(Array.isArray(availableCommands)).toBe(true);
        expect(availableCommands.length).toBeGreaterThan(0);

        const commandNames = availableCommands.map((cmd: any) => cmd.value);
        expect(commandNames).toContain("ping");
        expect(commandNames).toContain("echo");
        expect(commandNames).toContain("sleep");
        expect(commandNames).toContain("whoami");
      },
      TEST_TIMEOUT
    );
  });
});
