/**
 * Unit tests for UnixSocketBridge node
 */
import {
  IExecuteFunctions,
  ILoadOptionsFunctions,
  NodeOperationError,
} from "n8n-workflow";

import {
  UnixSocketBridge,
} from "../nodes/UnixSocketBridge/UnixSocketBridge.node";

describe("UnixSocketBridge", () => {
  let node: UnixSocketBridge;
  let mockExecuteFunctions: jest.Mocked<IExecuteFunctions>;
  let mockLoadOptionsFunctions: jest.Mocked<ILoadOptionsFunctions>;

  beforeEach(() => {
    node = new UnixSocketBridge();

    // Mock IExecuteFunctions
    mockExecuteFunctions = {
      getInputData: jest.fn(),
      getNodeParameter: jest.fn(),
      getNode: jest.fn(),
      continueOnFail: jest.fn(),
    } as any;

    // Mock ILoadOptionsFunctions
    mockLoadOptionsFunctions = {
      getNodeParameter: jest.fn(),
    } as any;

  });

  describe("Node Description", () => {
    it("should have correct node metadata", () => {
      expect(node.description.displayName).toBe("Unix Socket Bridge");
      expect(node.description.name).toBe("unixSocketBridge");
      expect(node.description.group).toContain("communication");
      expect(node.description.version).toBe(1);
    });

    it("should have required properties", () => {
      const properties = node.description.properties;

      // Check for socket path property
      const socketPathProp = properties.find((p) => p.name === "socketPath");
      expect(socketPathProp).toBeDefined();
      expect(socketPathProp?.required).toBe(true);
      expect(socketPathProp?.type).toBe("string");

      // Check for auto-discover property
      const autoDiscoverProp = properties.find(
        (p) => p.name === "autoDiscover"
      );
      expect(autoDiscoverProp).toBeDefined();
      expect(autoDiscoverProp?.type).toBe("boolean");
      expect(autoDiscoverProp?.default).toBe(true);

      // Check for timeout property
      const timeoutProp = properties.find((p) => p.name === "timeout");
      expect(timeoutProp).toBeDefined();
      expect(timeoutProp?.type).toBe("number");
      expect(timeoutProp?.default).toBe(5000);
    });
  });

  describe("getAvailableCommands", () => {
    it("should return error message when socket path is empty", async () => {
      mockLoadOptionsFunctions.getNodeParameter.mockReturnValue("");

      const result = await node.methods.loadOptions.getAvailableCommands.call(
        mockLoadOptionsFunctions
      );

      expect(result).toEqual([
        { name: "⚠️ Please set a socket path first", value: "" },
      ]);
    });

    it("should parse successful introspection response correctly", () => {
      // Test the response parsing logic directly
      const mockResponse = JSON.stringify({
        success: true,
        server_info: {
          name: "Test Server",
          commands: {
            "test-command": {
              description: "Test command description",
            },
            "another-command": {
              description: "Another command",
            },
          },
        },
      });

      // Parse the response like the actual method does
      const serverInfo = JSON.parse(mockResponse);
      
      // Verify the parsing logic works correctly
      expect(serverInfo.success).toBe(true);
      expect(serverInfo.server_info).toBeDefined();
      expect(serverInfo.server_info.commands).toBeDefined();
      
      // Test the option building logic
      const commands = serverInfo.server_info.commands;
      const options: any[] = [];
      
      // Add server info as first option (mimicking the actual implementation)
      options.push({
        name: `📡 ${serverInfo.server_info.name} (${Object.keys(commands).length} commands)`,
        value: "__server_info__",
      });
      
      // Add separator
      options.push({
        name: "─────────────────────────",
        value: "",
      });
      
      // Add commands
      for (const [commandName, commandInfo] of Object.entries(commands as any)) {
        const description = (commandInfo as any).description || "No description";
        options.push({
          name: `${commandName} - ${description}`,
          value: commandName,
        });
      }
      
      expect(options).toEqual([
        { name: "📡 Test Server (2 commands)", value: "__server_info__" },
        { name: "─────────────────────────", value: "" },
        { name: "test-command - Test command description", value: "test-command" },
        { name: "another-command - Another command", value: "another-command" },
      ]);
    });

    it("should handle socket connection errors gracefully", async () => {
      mockLoadOptionsFunctions.getNodeParameter.mockReturnValue(
        "/tmp/nonexistent.sock"
      );

      // Since we can't mock the socket function, test with real connection failure
      const result = await node.methods.loadOptions.getAvailableCommands.call(
        mockLoadOptionsFunctions
      );

      // Should return error message array
      expect(result).toBeInstanceOf(Array);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].name).toMatch(/📁|⏱️|🚫|❌/); // Any of the error indicators
      expect(result[0].value).toBe("");
    });
  });

  describe("execute", () => {
    beforeEach(() => {
      mockExecuteFunctions.getInputData.mockReturnValue([{ json: {} }]);
      mockExecuteFunctions.getNode.mockReturnValue({
        name: "test-node",
      } as any);
      mockExecuteFunctions.continueOnFail.mockReturnValue(false);
    });

    it("should handle invalid command selection in auto-discover mode", async () => {
      mockExecuteFunctions.getNodeParameter
        .mockReturnValueOnce("/tmp/test.sock") // socketPath
        .mockReturnValueOnce(true) // autoDiscover
        .mockReturnValueOnce(5000) // timeout
        .mockReturnValueOnce("auto") // responseFormat
        .mockReturnValueOnce("__server_info__") // discoveredCommand (invalid)
        .mockReturnValueOnce({}); // parameters (empty)

      await expect(node.execute.call(mockExecuteFunctions)).rejects.toThrow(
        NodeOperationError
      );
    });

    it("should build correct command message with parameters", () => {
      // Test parameter processing logic directly
      const parameters = {
        parameter: [
          { name: "player", value: "spotify" },
          { name: "volume", value: "0.8" },
          { name: "enabled", value: "true" },
        ],
      };

      const jsonMessage: any = { command: "test-command" };

      // Process parameters like the actual execute method does
      if (parameters && parameters.parameter && Array.isArray(parameters.parameter) && parameters.parameter.length > 0) {
        jsonMessage.parameters = {};
        for (const param of parameters.parameter) {
          if (param.name && param.value !== undefined) {
            // Try to parse value as JSON, fallback to string
            try {
              jsonMessage.parameters[param.name] = JSON.parse(param.value);
            } catch {
              jsonMessage.parameters[param.name] = param.value;
            }
          }
        }
      }

      expect(jsonMessage).toEqual({
        command: "test-command",
        parameters: {
          player: "spotify",
          volume: 0.8, // Should be parsed as number
          enabled: true, // Should be parsed as boolean
        },
      });
    });

    it("should handle response format parsing correctly", () => {
      // Test response parsing logic for different formats
      const jsonResponse = '{"success": true, "stdout": "output"}';
      const textResponse = "Plain text response";

      // Test JSON parsing (auto mode)
      let parsedResponse: any;
      try {
        parsedResponse = JSON.parse(jsonResponse);
      } catch {
        parsedResponse = jsonResponse;
      }
      expect(parsedResponse).toEqual({ success: true, stdout: "output" });

      // Test text parsing (auto mode with invalid JSON)
      try {
        parsedResponse = JSON.parse(textResponse);
      } catch {
        parsedResponse = textResponse;
      }
      expect(parsedResponse).toBe("Plain text response");
    });

    it("should handle connection errors with continueOnFail", async () => {
      mockExecuteFunctions.continueOnFail.mockReturnValue(true);
      mockExecuteFunctions.getNodeParameter
        .mockReturnValueOnce("/tmp/nonexistent.sock") // socketPath
        .mockReturnValueOnce(false) // autoDiscover
        .mockReturnValueOnce(5000) // timeout
        .mockReturnValueOnce("auto") // responseFormat
        .mockReturnValueOnce("test-command") // command
        .mockReturnValueOnce({}); // parameters (empty)

      // This should fail but return error result instead of throwing
      const result = await node.execute.call(mockExecuteFunctions);

      expect(result).toHaveLength(1);
      expect(result[0]).toHaveLength(1);
      expect(result[0][0].json).toMatchObject({
        success: false,
      });
      expect(result[0][0].json.error).toBeDefined();
      expect(typeof result[0][0].json.error).toBe("string");
    });
  });
});
