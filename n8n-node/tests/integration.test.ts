/**
 * Integration tests for Unix Socket Bridge
 * These tests simulate real socket server interactions
 */
import * as fs from "fs";
import { IExecuteFunctions } from "n8n-workflow";
import * as net from "net";
import * as path from "path";

import { UnixSocketBridge } from "../nodes/UnixSocketBridge/UnixSocketBridge.node";

describe("UnixSocketBridge Integration Tests", () => {
  let node: UnixSocketBridge;
  let mockExecuteFunctions: jest.Mocked<IExecuteFunctions>;
  let testSocketPath: string;
  let mockServer: net.Server;

  beforeAll(() => {
    testSocketPath = path.join(__dirname, "test.sock");
  });

  beforeEach(() => {
    node = new UnixSocketBridge();

    mockExecuteFunctions = {
      getInputData: jest.fn().mockReturnValue([{ json: {} }]),
      getNodeParameter: jest.fn(),
      getNode: jest.fn().mockReturnValue({
        name: "test-node",
        id: "test-id",
        typeVersion: 1,
        type: "unixSocketBridge",
        position: [0, 0],
        parameters: {},
      } as any),
      continueOnFail: jest.fn().mockReturnValue(false),
    } as any;

    // Clean up any existing socket file
    if (fs.existsSync(testSocketPath)) {
      fs.unlinkSync(testSocketPath);
    }
  });

  afterEach(() => {
    if (mockServer && mockServer.listening) {
      mockServer.close();
    }

    // Clean up socket file
    if (fs.existsSync(testSocketPath)) {
      fs.unlinkSync(testSocketPath);
    }
  });

  describe("Real Socket Communication", () => {
    it("should handle introspection command", (done) => {
      const serverInfo = {
        success: true,
        server_info: {
          name: "Test Socket Server",
          description: "A test server for integration testing",
          version: "1.0.0",
          commands: {
            ping: {
              description: "Simple ping command",
              parameters: {},
            },
            echo: {
              description: "Echo back the input",
              parameters: {
                message: {
                  description: "Message to echo",
                  type: "string",
                  required: true,
                },
              },
            },
          },
        },
      };

      // Create a mock socket server
      mockServer = net.createServer((socket) => {
        socket.on("data", (data) => {
          const request = JSON.parse(data.toString());

          if (request.command === "__introspect__") {
            socket.write(JSON.stringify(serverInfo));
            socket.end();
          }
        });
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(true) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("json") // responseFormat
            .mockReturnValueOnce("__introspect__"); // discoveredCommand

          const result = await node.execute.call(mockExecuteFunctions);

          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.response).toEqual(serverInfo);
          expect(result[0][0].json.success).toBe(true);

          done();
        } catch (error) {
          done(error);
        }
      });
    });

    it("should handle ping command", (done) => {
      const pingResponse = {
        success: true,
        message: "pong",
      };

      mockServer = net.createServer((socket) => {
        socket.on("data", (data) => {
          const request = JSON.parse(data.toString());

          if (request.command === "__ping__") {
            socket.write(JSON.stringify(pingResponse));
            socket.end();
          }
        });
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("json") // responseFormat
            .mockReturnValueOnce("__ping__"); // command

          const result = await node.execute.call(mockExecuteFunctions);

          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.response).toEqual(pingResponse);

          done();
        } catch (error) {
          done(error);
        }
      });
    });

    it("should handle command with parameters", (done) => {
      const echoResponse = {
        success: true,
        output: "Hello World!",
        returncode: 0,
      };

      mockServer = net.createServer((socket) => {
        socket.on("data", (data) => {
          const request = JSON.parse(data.toString());

          if (request.command === "echo" && request.parameters) {
            const response = {
              ...echoResponse,
              output: request.parameters.message,
            };
            socket.write(JSON.stringify(response));
            socket.end();
          }
        });
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("json") // responseFormat
            .mockReturnValueOnce("echo") // command
            .mockReturnValueOnce({
              // parameters
              parameter: [{ name: "message", value: "Hello World!" }],
            });

          const result = await node.execute.call(mockExecuteFunctions);

          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect((result[0][0].json.response as any).output).toBe("Hello World!");
          expect(result[0][0].json.success).toBe(true);

          done();
        } catch (error) {
          done(error);
        }
      });
    });

    it("should handle server connection timeout", async () => {
      // Use a non-existent socket path to trigger timeout
      const nonExistentPath = path.join(__dirname, "nonexistent.sock");

      mockExecuteFunctions.getNodeParameter
        .mockReturnValueOnce(nonExistentPath) // socketPath
        .mockReturnValueOnce(false) // autoDiscover
        .mockReturnValueOnce(100) // timeout (short for quick test)
        .mockReturnValueOnce("json") // responseFormat
        .mockReturnValueOnce("test"); // command

      await expect(node.execute.call(mockExecuteFunctions)).rejects.toThrow();
    });

    it("should handle malformed server responses", (done) => {
      mockServer = net.createServer((socket) => {
        socket.on("data", () => {
          // Send invalid JSON
          socket.write("Invalid JSON response {");
          socket.end();
        });
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("json") // responseFormat (strict JSON)
            .mockReturnValueOnce("test"); // command

          await expect(
            node.execute.call(mockExecuteFunctions)
          ).rejects.toThrow();

          done();
        } catch (error) {
          done(error);
        }
      });
    });

    it("should handle auto-detect response format with invalid JSON", (done) => {
      const textResponse = "This is a plain text response, not JSON";

      mockServer = net.createServer((socket) => {
        socket.on("data", () => {
          socket.write(textResponse);
          socket.end();
        });
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("auto") // responseFormat (auto-detect)
            .mockReturnValueOnce("test"); // command

          const result = await node.execute.call(mockExecuteFunctions);

          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.response).toBe(textResponse);

          done();
        } catch (error) {
          done(error);
        }
      });
    });
  });

  describe("Error Handling Integration", () => {
    it("should handle server that closes connection immediately", (done) => {
      mockServer = net.createServer((socket) => {
        // Close connection immediately without sending data
        socket.end();
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("auto") // responseFormat
            .mockReturnValueOnce("test"); // command

          const result = await node.execute.call(mockExecuteFunctions);

          // The socket implementation handles immediate close gracefully
          // by returning an empty response rather than throwing
          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.response).toBe("");
          expect(result[0][0].json.success).toBe(true);

          done();
        } catch (error) {
          done(error);
        }
      });
    });

    it("should handle multiple requests to same socket", (done) => {
      let requestCount = 0;
      const responses = [
        { success: true, output: "First response" },
        { success: true, output: "Second response" },
      ];

      mockServer = net.createServer((socket) => {
        socket.on("data", () => {
          socket.write(JSON.stringify(responses[requestCount]));
          requestCount++;
          socket.end();
        });
      });

      mockServer.listen(testSocketPath, async () => {
        try {
          // First request
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("json") // responseFormat
            .mockReturnValueOnce("test1"); // command

          const result1 = await node.execute.call(mockExecuteFunctions);
          expect((result1[0][0].json.response as any).output).toBe("First response");

          // Reset mocks for second request
          jest.clearAllMocks();
          mockExecuteFunctions.getInputData.mockReturnValue([{ json: {} }]);
          mockExecuteFunctions.getNode.mockReturnValue({
            name: "test-node",
            id: "test-id",
            typeVersion: 1,
            type: "unixSocketBridge",
            position: [0, 0],
            parameters: {},
          } as any);
          mockExecuteFunctions.continueOnFail.mockReturnValue(false);

          // Second request
          mockExecuteFunctions.getNodeParameter
            .mockReturnValueOnce(testSocketPath) // socketPath
            .mockReturnValueOnce(false) // autoDiscover
            .mockReturnValueOnce(5000) // timeout
            .mockReturnValueOnce("json") // responseFormat
            .mockReturnValueOnce("test2"); // command

          const result2 = await node.execute.call(mockExecuteFunctions);
          expect((result2[0][0].json.response as any).output).toBe("Second response");

          done();
        } catch (error) {
          done(error);
        }
      });
    });
  });
});
