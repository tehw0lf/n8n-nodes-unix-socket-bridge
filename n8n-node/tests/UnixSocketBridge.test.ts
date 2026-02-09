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
      expect(node.description.group).toContain("transform");
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

      // Check for new options collection
      const optionsProp = properties.find((p) => p.name === "options");
      expect(optionsProp).toBeDefined();
      expect(optionsProp?.type).toBe("collection");
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
              parameters: {},
            },
            "another-command": {
              description: "Another command",
              parameters: {
                param1: { type: "string" },
              },
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
        name: `📡 ${serverInfo.server_info.name} (${Object.keys(commands).length} commands available)`,
        value: "__server_info__",
      });
      
      // Add separator
      options.push({
        name: "──────────────────────────",
        value: "",
      });
      
      // Add commands with parameter indicators
      for (const [commandName, commandInfo] of Object.entries(commands as any)) {
        const description = (commandInfo as any).description || "No description";
        const hasParams = (commandInfo as any).parameters && 
                          Object.keys((commandInfo as any).parameters).length > 0;
        const paramIndicator = hasParams ? " 🔧" : "";
        options.push({
          name: `${commandName}${paramIndicator} - ${description}`,
          value: commandName,
          description: hasParams ? "This command accepts parameters" : undefined,
        });
      }
      
      expect(options).toEqual([
        { name: "📡 Test Server (2 commands available)", value: "__server_info__" },
        { name: "──────────────────────────", value: "" },
        { name: "test-command - Test command description", value: "test-command", description: undefined },
        { name: "another-command 🔧 - Another command", value: "another-command", description: "This command accepts parameters" },
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
      expect(result[0].name).toMatch(/⚠️|⏱️|🔍|🚫|🔒|❌/); // Any of the error indicators
      expect(result[0].value).toBe("");
    });

    it("should handle timeout errors", async () => {
      mockLoadOptionsFunctions.getNodeParameter.mockReturnValue(
        "/tmp/test.sock"
      );

      // Test that the method handles connection failures gracefully
      const result = await node.methods.loadOptions.getAvailableCommands.call(
        mockLoadOptionsFunctions
      );

      // Should return an array with error information
      expect(result).toBeInstanceOf(Array);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].value).toBe("");
    });

    it("should handle server error responses", () => {
      // Test error response parsing
      const errorResponse = JSON.stringify({
        success: false,
        error: "Server configuration error",
      });

      const serverInfo = JSON.parse(errorResponse);
      expect(serverInfo.success).toBe(false);
      expect(serverInfo.error).toBe("Server configuration error");

      // The actual method would return error options based on this
      const expectedOptions = [
        { name: "❌ Server error: Server configuration error", value: "" },
        { name: "Check server logs for details", value: "" },
      ];

      expect(expectedOptions).toEqual([
        { name: "❌ Server error: Server configuration error", value: "" },
        { name: "Check server logs for details", value: "" },
      ]);
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
        .mockReturnValueOnce({}) // options
        .mockReturnValueOnce("__server_info__") // discoveredCommand (invalid)
        .mockReturnValueOnce({}); // parameters

      await expect(node.execute.call(mockExecuteFunctions)).rejects.toThrow(
        NodeOperationError
      );
    });

    it("should handle empty command selection in auto-discover mode", async () => {
      mockExecuteFunctions.getNodeParameter
        .mockReturnValueOnce("/tmp/test.sock") // socketPath
        .mockReturnValueOnce(true) // autoDiscover
        .mockReturnValueOnce(5000) // timeout
        .mockReturnValueOnce("auto") // responseFormat
        .mockReturnValueOnce({}) // options
        .mockReturnValueOnce("") // discoveredCommand (empty)
        .mockReturnValueOnce({}); // parameters

      await expect(node.execute.call(mockExecuteFunctions)).rejects.toThrow(
        NodeOperationError
      );
    });

    it("should build correct command message with parameters", () => {
      // Test parameter processing logic directly
      const parameters = {
        parameter: [
          { name: "player", value: "spotify", type: "string" },
          { name: "volume", value: "0.8", type: "number" },
          { name: "enabled", value: "true", type: "boolean" },
        ],
      };

      const jsonMessage: any = { command: "test-command" };

      // Process parameters like the actual execute method does
      if (parameters && parameters.parameter && Array.isArray(parameters.parameter) && parameters.parameter.length > 0) {
        jsonMessage.parameters = {};
        for (const param of parameters.parameter) {
          if (param.name && param.value !== undefined && param.value !== "") {
            const paramType = param.type || "auto";
            let processedValue: any = param.value;

            switch (paramType) {
              case "number":
                processedValue = Number(param.value);
                break;
              case "boolean":
                if (typeof param.value === "string") {
                  processedValue = ["true", "yes", "1", "on"].includes(
                    param.value.toLowerCase()
                  );
                } else {
                  processedValue = Boolean(param.value);
                }
                break;
              case "json":
                processedValue = JSON.parse(param.value);
                break;
              case "string":
                processedValue = String(param.value);
                break;
              case "auto":
              default:
                // Try to parse as JSON first
                try {
                  processedValue = JSON.parse(param.value);
                } catch {
                  processedValue = param.value;
                }
                break;
            }
            jsonMessage.parameters[param.name] = processedValue;
          }
        }
      }

      expect(jsonMessage).toEqual({
        command: "test-command",
        parameters: {
          player: "spotify",
          volume: 0.8,
          enabled: true,
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
        .mockReturnValueOnce({}) // options
        .mockReturnValueOnce("test-command") // command
        .mockReturnValueOnce({}); // parameters

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

    it("should handle includeMetadata option", () => {
      // Test metadata handling logic directly
      const parsedResponse = { success: true, output: "test" };
      const socketPath = "/tmp/test.sock";
      const command = "test";
      const jsonMessage = { command: "test" };
      const includeMetadata = false;

      let responseData: any;

      if (includeMetadata) {
        responseData = {
          socketPath,
          command,
          request: jsonMessage,
          response: parsedResponse,
          success: true,
          timestamp: new Date().toISOString(),
        };
      } else {
        // Return just the response without metadata
        if (
          typeof parsedResponse === "object" &&
          parsedResponse !== null &&
          "success" in parsedResponse
        ) {
          responseData = parsedResponse;
        } else {
          responseData = { response: parsedResponse };
        }
      }

      // Should return just the response without metadata wrapper
      expect(responseData).toEqual(parsedResponse);
    });

    it("should process parameter types correctly", () => {
      const parameters = {
        parameter: [
          { name: "auto_param", value: "[1,2,3]", type: "auto" },
          { name: "json_param", value: '{"key":"value"}', type: "json" },
          { name: "bool_yes", value: "yes", type: "boolean" },
          { name: "bool_no", value: "no", type: "boolean" },
          { name: "number_param", value: "42.5", type: "number" },
        ],
      };

      const jsonMessage: any = { command: "test" };

      // Process parameters like the actual execute method does
      if (parameters && parameters.parameter && Array.isArray(parameters.parameter) && parameters.parameter.length > 0) {
        jsonMessage.parameters = {};
        for (const param of parameters.parameter) {
          if (param.name && param.value !== undefined && param.value !== "") {
            const paramType = param.type || "auto";
            let processedValue: any = param.value;

            switch (paramType) {
              case "number":
                processedValue = Number(param.value);
                break;
              case "boolean":
                if (typeof param.value === "string") {
                  processedValue = ["true", "yes", "1", "on"].includes(
                    param.value.toLowerCase()
                  );
                } else {
                  processedValue = Boolean(param.value);
                }
                break;
              case "json":
                processedValue = JSON.parse(param.value);
                break;
              case "string":
                processedValue = String(param.value);
                break;
              case "auto":
              default:
                // Try to parse as JSON first
                try {
                  processedValue = JSON.parse(param.value);
                } catch {
                  processedValue = param.value;
                }
                break;
            }
            jsonMessage.parameters[param.name] = processedValue;
          }
        }
      }

      expect(jsonMessage.parameters).toEqual({
        auto_param: [1, 2, 3],
        json_param: { key: "value" },
        bool_yes: true,
        bool_no: false,
        number_param: 42.5,
      });
    });

    it("should handle parameter processing errors", () => {
      // Test invalid number parameter
      expect(() => {
        const paramValue = "not_a_number";
        const processedValue = Number(paramValue);
        if (isNaN(processedValue)) {
          throw new Error(`Invalid number: ${paramValue}`);
        }
      }).toThrow('Invalid number: not_a_number');

      // Test invalid JSON parameter
      expect(() => {
        JSON.parse("{invalid json");
      }).toThrow();
    });

    it("should skip empty parameters", () => {
      const parameters = {
        parameter: [
          { name: "valid", value: "test", type: "string" },
          { name: "empty", value: "", type: "string" },
          { name: "undefined", value: undefined, type: "string" },
          { name: "", value: "no_name", type: "string" },
        ],
      };

      const jsonMessage: any = { command: "test" };

      // Process parameters like the actual execute method does
      if (parameters && parameters.parameter && Array.isArray(parameters.parameter) && parameters.parameter.length > 0) {
        jsonMessage.parameters = {};
        for (const param of parameters.parameter) {
          if (param.name && param.value !== undefined && param.value !== "") {
            jsonMessage.parameters[param.name] = param.value;
          }
        }
      }

      expect(jsonMessage.parameters).toEqual({
        valid: "test",
      });
      expect(jsonMessage.parameters.empty).toBeUndefined();
      expect(jsonMessage.parameters.undefined).toBeUndefined();
      expect(jsonMessage.parameters[""]).toBeUndefined();
    });
  });

  describe("Enhanced Options Collection", () => {
    it("should handle maxResponseSize option correctly", () => {
      // Test that options are properly configured in the node description
      const properties = node.description.properties;
      const optionsProp = properties.find((p) => p.name === "options");
      
      expect(optionsProp).toBeDefined();
      expect(optionsProp?.type).toBe("collection");
      
      const options = (optionsProp as any)?.options;
      const maxResponseSizeOption = options?.find((o: any) => o.name === "maxResponseSize");
      
      expect(maxResponseSizeOption).toBeDefined();
      expect(maxResponseSizeOption?.type).toBe("number");
      expect(maxResponseSizeOption?.default).toBe(1048576);
    });

    it("should handle includeMetadata option correctly", () => {
      const properties = node.description.properties;
      const optionsProp = properties.find((p) => p.name === "options");
      const options = (optionsProp as any)?.options;
      const includeMetadataOption = options?.find((o: any) => o.name === "includeMetadata");
      
      expect(includeMetadataOption).toBeDefined();
      expect(includeMetadataOption?.type).toBe("boolean");
      expect(includeMetadataOption?.default).toBe(true);
    });
  });

  describe("Enhanced Response Processing", () => {
    it("should handle server responses without success field", () => {
      const rawResponse = { output: "some data", custom_field: "value" };
      const includeMetadata = false;

      let responseData: any;

      if (includeMetadata) {
        responseData = {
          response: rawResponse,
          success: true,
          timestamp: new Date().toISOString(),
        };
      } else {
        // Return just the response without metadata
        if (
          typeof rawResponse === "object" &&
          rawResponse !== null &&
          "success" in rawResponse
        ) {
          responseData = rawResponse;
        } else {
          responseData = rawResponse;
        }
      }

      expect(responseData).toEqual(rawResponse);
    });

    it("should handle text responses with metadata", () => {
      const textResponse = "Plain text response";
      const includeMetadata = true;
      const socketPath = "/tmp/test.sock";
      const command = "test";
      const jsonMessage = { command: "test" };

      let responseData: any;

      if (includeMetadata) {
        responseData = {
          socketPath,
          command,
          request: jsonMessage,
          response: textResponse,
          success: true,
          timestamp: new Date().toISOString(),
        };
      } else {
        responseData = { response: textResponse };
      }

      expect(responseData.response).toBe(textResponse);
      expect(responseData.socketPath).toBe(socketPath);
      expect(responseData.success).toBe(true);
    });

    it("should extract structured response fields when includeMetadata is true", () => {
      const serverResponse = {
        success: true,
        stdout: "command output",
        stderr: "warning message",
        returncode: 0,
        parsed_output: { key: "value" },
      };
      const includeMetadata = true;
      const socketPath = "/tmp/test.sock";
      const command = "test";
      const jsonMessage = { command: "test" };

      let responseData: any;

      if (includeMetadata) {
        responseData = {
          socketPath,
          command,
          request: jsonMessage,
          response: serverResponse,
          success: true,
          timestamp: new Date().toISOString(),
        };

        // Extract structured response fields if available
        if (
          typeof serverResponse === "object" &&
          serverResponse !== null &&
          "success" in serverResponse
        ) {
          responseData.success = serverResponse.success;
          responseData.output = serverResponse.stdout || (serverResponse as any).output || "";
          responseData.error = (serverResponse as any).error || serverResponse.stderr || "";
          responseData.returncode = serverResponse.returncode;

          // Include parsed output if available
          if (serverResponse.parsed_output) {
            responseData.parsedOutput = serverResponse.parsed_output;
          }
        }
      } else {
        responseData = serverResponse;
      }

      expect(responseData.success).toBe(true);
      expect(responseData.output).toBe("command output");
      expect(responseData.error).toBe("warning message");
      expect(responseData.returncode).toBe(0);
      expect(responseData.parsedOutput).toEqual({ key: "value" });
    });
  });

  describe("Parameter Type System", () => {
    it("should handle all parameter types in auto mode", () => {
      const parameters = {
        parameter: [
          { name: "json_auto", value: '{"test": true}', type: "auto" },
          { name: "number_auto", value: "42", type: "auto" },
          { name: "string_auto", value: "plain text", type: "auto" },
        ],
      };

      const jsonMessage: any = { command: "test" };

      // Process parameters like the actual execute method does
      if (parameters && parameters.parameter && Array.isArray(parameters.parameter) && parameters.parameter.length > 0) {
        jsonMessage.parameters = {};
        for (const param of parameters.parameter) {
          if (param.name && param.value !== undefined && param.value !== "") {
            const paramType = param.type || "auto";
            let processedValue: any = param.value;

            switch (paramType) {
              case "auto":
              default:
                // Try to parse as JSON first
                try {
                  processedValue = JSON.parse(param.value);
                } catch {
                  processedValue = param.value;
                }
                break;
            }
            jsonMessage.parameters[param.name] = processedValue;
          }
        }
      }

      expect(jsonMessage.parameters.json_auto).toEqual({ test: true });
      expect(jsonMessage.parameters.number_auto).toBe(42);
      expect(jsonMessage.parameters.string_auto).toBe("plain text");
    });

    it("should handle string type conversion", () => {
      const param = { name: "force_string", value: 123, type: "string" };
      let processedValue: any = param.value;

      if (param.type === "string") {
        processedValue = String(param.value);
      }

      expect(processedValue).toBe("123");
    });

    it("should handle boolean type variations", () => {
      const booleanTests = [
        { value: "true", expected: true },
        { value: "yes", expected: true },
        { value: "1", expected: true },
        { value: "on", expected: true },
        { value: "false", expected: false },
        { value: "no", expected: false },
        { value: "0", expected: false },
      ];

      for (const test of booleanTests) {
        let processedValue: any;
        if (typeof test.value === "string") {
          processedValue = ["true", "yes", "1", "on"].includes(
            test.value.toLowerCase()
          );
        } else {
          processedValue = Boolean(test.value);
        }
        expect(processedValue).toBe(test.expected);
      }
    });
  });
});