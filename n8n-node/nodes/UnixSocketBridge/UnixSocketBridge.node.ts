import {
  IExecuteFunctions,
  ILoadOptionsFunctions,
  INodeExecutionData,
  INodePropertyOptions,
  INodeType,
  INodeTypeDescription,
  NodeConnectionType,
  NodeOperationError,
} from "n8n-workflow";
import * as net from "net";

/**
 * Interfaces for type safety
 */
interface SocketCommand {
  command: string;
  parameters?: Record<string, any>;
}

interface ServerInfo {
  success: boolean;
  server_info?: {
    name: string;
    description?: string;
    version?: string;
    commands: Record<
      string,
      {
        description?: string;
        parameters?: Record<string, any>;
        examples?: any[];
      }
    >;
  };
  error?: string;
}

interface CommandResponse {
  success: boolean;
  command?: string;
  returncode?: number;
  stdout?: string;
  stderr?: string;
  error?: string;
  output?: string;
  parsed_output?: any;
  timestamp?: number;
}

/**
 * Unix Socket Bridge Node for n8n
 *
 * This node provides a generic interface for communicating with Unix domain socket servers.
 * It supports auto-discovery of available commands, parameter validation, and multiple
 * response formats.
 *
 * @example
 * // Basic usage with auto-discovery
 * const node = new UnixSocketBridge();
 * // Configure socket path: /tmp/playerctl.sock
 * // Enable auto-discovery to see available commands
 * // Select command from dropdown and execute
 *
 * @example
 * // Manual command execution
 * const node = new UnixSocketBridge();
 * // Set autoDiscover to false
 * // Manually specify command and parameters
 *
 * @since 1.0.0
 */
export class UnixSocketBridge implements INodeType {
  description: INodeTypeDescription = {
    displayName: "Unix Socket Bridge",
    name: "unixSocketBridge",
    icon: "fa:plug",
    group: ["communication"],
    version: 1,
    subtitle:
      '={{$parameter["autoDiscover"] ? $parameter["discoveredCommand"] : $parameter["command"]}} @ {{$parameter["socketPath"]}}',
    description: "Unix domain socket communication with configurable servers",
    defaults: {
      name: "Unix Socket Bridge",
    },
    inputs: [NodeConnectionType.Main],
    outputs: [NodeConnectionType.Main],
    properties: [
      {
        displayName: "Socket Path",
        name: "socketPath",
        type: "string",
        default: "/tmp/socket.sock",
        placeholder: "/tmp/socket.sock",
        description: "Path to the Unix domain socket file",
        required: true,
      },
      {
        displayName: "Auto-Discover Commands",
        name: "autoDiscover",
        type: "boolean",
        default: true,
        description:
          "Automatically discover available commands from the server (recommended)",
      },
      {
        displayName: "Available Commands",
        name: "discoveredCommand",
        type: "options",
        typeOptions: {
          loadOptionsMethod: "getAvailableCommands",
          loadOptionsDependsOn: ["socketPath"], // Force reload when socket path changes
        },
        displayOptions: {
          show: {
            autoDiscover: [true],
          },
        },
        default: "",
        description: "Choose from available commands on the server",
        placeholder: "Select a command...",
      },
      {
        displayName: "Refresh Commands",
        name: "refreshCommands",
        type: "notice",
        displayOptions: {
          show: {
            autoDiscover: [true],
          },
        },
        default: "",
        description:
          "If commands don't load, try changing the socket path slightly and changing it back, or toggle auto-discovery off/on",
      },
      {
        displayName: "Manual Command",
        name: "command",
        type: "string",
        displayOptions: {
          show: {
            autoDiscover: [false],
          },
        },
        default: '={{ $json.command || "status" }}',
        description: "Command to send to the server (manual mode)",
        placeholder: "status",
      },
      {
        displayName: "Parameters",
        name: "parameters",
        type: "fixedCollection",
        placeholder: "Add Parameter",
        typeOptions: {
          multipleValues: true,
        },
        default: {},
        options: [
          {
            name: "parameter",
            displayName: "Parameter",
            values: [
              {
                displayName: "Name",
                name: "name",
                type: "string",
                default: "",
                description: 'Parameter name (e.g., "player")',
                placeholder: "player",
                required: false,
              },
              {
                displayName: "Value",
                name: "value",
                type: "string",
                default: "",
                description: 'Parameter value (e.g., "spotify")',
                placeholder: "spotify",
              },
              {
                displayName: "Type",
                name: "type",
                type: "options",
                options: [
                  {
                    name: "Auto-Detect",
                    value: "auto",
                    description: "Automatically detect the type",
                  },
                  {
                    name: "String",
                    value: "string",
                    description: "Text value",
                  },
                  {
                    name: "Number",
                    value: "number",
                    description: "Numeric value",
                  },
                  {
                    name: "Boolean",
                    value: "boolean",
                    description: "True/False value",
                  },
                  {
                    name: "JSON",
                    value: "json",
                    description: "Complex JSON value",
                  },
                ],
                default: "auto",
                description: "Parameter value type",
              },
            ],
          },
        ],
        description: "Additional parameters to pass with the command",
      },
      {
        displayName: "Timeout (ms)",
        name: "timeout",
        type: "number",
        default: 5000,
        description: "Connection timeout in milliseconds",
        typeOptions: {
          minValue: 1000,
          maxValue: 30000,
        },
      },
      {
        displayName: "Response Format",
        name: "responseFormat",
        type: "options",
        options: [
          {
            name: "Auto-Detect",
            value: "auto",
            description: "Automatically detect JSON or return as text",
          },
          {
            name: "JSON",
            value: "json",
            description:
              "Parse response as JSON (will error if not valid JSON)",
          },
          {
            name: "Text",
            value: "text",
            description: "Return response as plain text",
          },
        ],
        default: "auto",
        description: "How to interpret the server response",
      },
      {
        displayName: "Options",
        name: "options",
        type: "collection",
        placeholder: "Add Option",
        default: {},
        options: [
          {
            displayName: "Continue On Fail",
            name: "continueOnFail",
            type: "boolean",
            default: false,
            description: "Whether to continue workflow execution on error",
          },
          {
            displayName: "Max Response Size",
            name: "maxResponseSize",
            type: "number",
            default: 1048576,
            description: "Maximum response size in bytes (default: 1MB)",
            typeOptions: {
              minValue: 1024,
              maxValue: 10485760,
            },
          },
          {
            displayName: "Include Metadata",
            name: "includeMetadata",
            type: "boolean",
            default: true,
            description:
              "Include metadata like timestamp and socket path in response",
          },
        ],
      },
    ],
  };

  /**
   * Methods available on this node for dynamic option loading
   */
  methods = {
    loadOptions: {
      /**
       * Discovers available commands from a Unix socket server
       *
       * This method connects to the specified socket and sends an introspection
       * request to discover what commands are available. It provides user-friendly
       * error messages and fallback options when the server is unavailable.
       *
       * @param this - The load options function context from n8n
       * @returns Promise resolving to an array of command options for the dropdown
       */
      async getAvailableCommands(
        this: ILoadOptionsFunctions
      ): Promise<INodePropertyOptions[]> {
        const socketPath = this.getNodeParameter("socketPath") as string;
        const timeout = 5000;

        // Provide immediate feedback
        if (!socketPath || socketPath.trim() === "") {
          return [{ name: "⚠️ Please set a socket path first", value: "" }];
        }

        try {
          const introspectionRequest: SocketCommand = {
            command: "__introspect__",
          };

          const response = await sendToUnixSocket(
            socketPath,
            JSON.stringify(introspectionRequest),
            timeout
          );

          const serverInfo: ServerInfo = JSON.parse(response);

          if (
            serverInfo.success &&
            serverInfo.server_info &&
            serverInfo.server_info.commands
          ) {
            const commands = serverInfo.server_info.commands;
            const options: INodePropertyOptions[] = [];

            // Add server info as header
            options.push({
              name: `📡 ${serverInfo.server_info.name} (${
                Object.keys(commands).length
              } commands available)`,
              value: "__server_info__",
            });

            // Add separator
            options.push({
              name: "──────────────────────────",
              value: "",
            });

            // Add commands with better formatting
            for (const [commandName, commandInfo] of Object.entries(commands)) {
              const description = commandInfo.description || "No description";
              const hasParams =
                commandInfo.parameters &&
                Object.keys(commandInfo.parameters).length > 0;

              const paramIndicator = hasParams ? " 🔧" : "";
              options.push({
                name: `${commandName}${paramIndicator} - ${description}`,
                value: commandName,
                description: hasParams
                  ? "This command accepts parameters"
                  : undefined,
              });
            }

            return options;
          } else if (serverInfo.error) {
            return [
              { name: `❌ Server error: ${serverInfo.error}`, value: "" },
              { name: "Check server logs for details", value: "" },
            ];
          } else {
            return [
              { name: "⚠️ Server responded but no commands found", value: "" },
              { name: "Check server configuration", value: "" },
            ];
          }
        } catch (error: any) {
          // More specific error messages
          if (error.message.includes("timeout")) {
            return [
              {
                name: "⏱️ Connection timeout - is the server running?",
                value: "",
              },
              {
                name: "Try: python3 socket-server.py config.json",
                value: "",
              },
            ];
          } else if (
            error.message.includes("ENOENT") ||
            error.message.includes("not found")
          ) {
            return [
              { name: "🔍 Socket file not found", value: "" },
              { name: `Path: ${socketPath}`, value: "" },
              { name: "Check if server is running", value: "" },
            ];
          } else if (error.message.includes("ECONNREFUSED")) {
            return [
              { name: "🚫 Connection refused", value: "" },
              { name: "Server may not be listening on this socket", value: "" },
            ];
          } else if (error.message.includes("EACCES")) {
            return [
              { name: "🔒 Permission denied", value: "" },
              { name: "Check socket file permissions", value: "" },
            ];
          } else {
            const shortError = error.message.substring(0, 50);
            return [
              {
                name: `❌ Error: ${shortError}${
                  error.message.length > 50 ? "..." : ""
                }`,
                value: "",
              },
              { name: "You can still use manual mode", value: "" },
            ];
          }
        }
      },
    },
  };

  /**
   * Executes the Unix Socket Bridge node
   *
   * This method handles the main execution logic, including:
   * - Parameter validation and processing
   * - Socket communication
   * - Response parsing and formatting
   * - Error handling with optional continuation
   *
   * @param this - The execution function context from n8n
   * @returns Promise resolving to node execution data
   */
  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];

    for (let i = 0; i < items.length; i++) {
      try {
        const socketPath = this.getNodeParameter("socketPath", i) as string;
        const autoDiscover = this.getNodeParameter(
          "autoDiscover",
          i
        ) as boolean;
        const timeout = this.getNodeParameter("timeout", i) as number;
        const responseFormat = this.getNodeParameter(
          "responseFormat",
          i
        ) as string;

        // Get options
        const options = this.getNodeParameter("options", i, {}) as any;
        const maxResponseSize = options.maxResponseSize || 1048576;
        const includeMetadata = options.includeMetadata !== false;

        let command: string;
        if (autoDiscover) {
          command = this.getNodeParameter("discoveredCommand", i) as string;
          // Validate command selection
          if (command === "__server_info__" || command === "" || !command) {
            throw new NodeOperationError(
              this.getNode(),
              "Please select a valid command from the dropdown",
              {
                itemIndex: i,
                description: "Use the dropdown to select an available command",
              }
            );
          }
        } else {
          command = this.getNodeParameter("command", i) as string;
          if (!command) {
            throw new NodeOperationError(
              this.getNode(),
              "Command is required",
              { itemIndex: i }
            );
          }
        }

        // Build the request
        const jsonMessage: SocketCommand = { command };

        // Process parameters with type handling
        const parameters = this.getNodeParameter("parameters", i, {}) as any;
        if (
          parameters &&
          parameters.parameter &&
          Array.isArray(parameters.parameter) &&
          parameters.parameter.length > 0
        ) {
          jsonMessage.parameters = {};

          for (const param of parameters.parameter) {
            if (param.name && param.value !== undefined && param.value !== "") {
              const paramType = param.type || "auto";
              let processedValue: any = param.value;

              try {
                switch (paramType) {
                  case "number":
                    processedValue = Number(param.value);
                    if (isNaN(processedValue)) {
                      throw new Error(`Invalid number: ${param.value}`);
                    }
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
                      // If not JSON, keep as string
                      processedValue = param.value;
                    }
                    break;
                }

                jsonMessage.parameters[param.name] = processedValue;
              } catch (error: any) {
                throw new NodeOperationError(
                  this.getNode(),
                  `Failed to process parameter "${param.name}": ${error.message}`,
                  { itemIndex: i }
                );
              }
            }
          }
        }

        const messageToSend = JSON.stringify(jsonMessage);

        // Send message to Unix socket with size limit
        const response = await sendToUnixSocket(
          socketPath,
          messageToSend,
          timeout,
          maxResponseSize
        );

        // Parse response based on format setting
        let parsedResponse: any;
        if (responseFormat === "auto") {
          try {
            parsedResponse = JSON.parse(response);
          } catch {
            parsedResponse = response;
          }
        } else if (responseFormat === "json") {
          try {
            parsedResponse = JSON.parse(response);
          } catch (error: any) {
            throw new NodeOperationError(
              this.getNode(),
              `Failed to parse response as JSON: ${error.message}`,
              {
                itemIndex: i,
                description:
                  "Server response is not valid JSON. Try using 'Text' response format.",
              }
            );
          }
        } else {
          parsedResponse = response;
        }

        // Build response data
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

          // Extract structured response fields if available
          if (
            typeof parsedResponse === "object" &&
            parsedResponse !== null &&
            "success" in parsedResponse
          ) {
            const cmdResponse = parsedResponse as CommandResponse;
            responseData.success = cmdResponse.success;
            responseData.output =
              cmdResponse.stdout || cmdResponse.output || "";
            responseData.error = cmdResponse.error || cmdResponse.stderr || "";
            responseData.returncode = cmdResponse.returncode;

            // Include parsed output if available
            if (cmdResponse.parsed_output) {
              responseData.parsedOutput = cmdResponse.parsed_output;
            }
          }
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

        returnData.push({
          json: responseData,
          pairedItem: i,
        });
      } catch (error: any) {
        if (this.continueOnFail()) {
          returnData.push({
            json: {
              error: error.message,
              success: false,
              timestamp: new Date().toISOString(),
              itemIndex: i,
            },
            pairedItem: i,
          });
          continue;
        }
        throw error;
      }
    }

    return [returnData];
  }
}

/**
 * Helper function for Unix socket communication with improved robustness
 *
 * Establishes a connection to a Unix domain socket, sends a message,
 * and returns the response. Includes timeout handling, chunked reading
 * for large responses, and proper cleanup of socket resources.
 *
 * @param socketPath - Path to the Unix domain socket file
 * @param message - Message to send (typically JSON-formatted command)
 * @param timeoutMs - Connection timeout in milliseconds
 * @param maxResponseSize - Maximum response size in bytes
 * @returns Promise resolving to the server response as a string
 *
 * @throws {Error} When socket connection fails, times out, or response too large
 */
export async function sendToUnixSocket(
  socketPath: string,
  message: string,
  timeoutMs: number,
  maxResponseSize: number = 1048576
): Promise<string> {
  return new Promise((resolve, reject) => {
    const socket = new net.Socket();
    let response = "";
    let responseBuffer = Buffer.alloc(0);

    const timeoutHandle = setTimeout(() => {
      socket.destroy();
      reject(new Error(`Socket connection timeout after ${timeoutMs}ms`));
    }, timeoutMs);

    socket.on("connect", () => {
      socket.write(message);
    });

    socket.on("data", (data: Buffer) => {
      // Use buffer concatenation for binary safety
      responseBuffer = Buffer.concat([responseBuffer, data]);

      // Check size limit
      if (responseBuffer.length > maxResponseSize) {
        socket.destroy();
        clearTimeout(timeoutHandle);
        reject(new Error(`Response too large (max ${maxResponseSize} bytes)`));
      }
    });

    socket.on("end", () => {
      clearTimeout(timeoutHandle);
      try {
        response = responseBuffer.toString("utf-8");
        resolve(response);
      } catch (error: any) {
        reject(new Error(`Failed to decode response: ${error.message}`));
      }
    });

    socket.on("close", (hadError: boolean) => {
      clearTimeout(timeoutHandle);
      if (!hadError && responseBuffer.length > 0) {
        try {
          response = responseBuffer.toString("utf-8");
          resolve(response);
        } catch (error: any) {
          reject(new Error(`Failed to decode response: ${error.message}`));
        }
      } else if (!hadError && response) {
        resolve(response);
      } else if (!hadError) {
        reject(new Error("Socket closed without response"));
      }
    });

    socket.on("error", (error: Error) => {
      clearTimeout(timeoutHandle);

      // Provide more helpful error messages
      let errorMessage = error.message;
      if (error.message.includes("ENOENT")) {
        errorMessage = `Socket not found at ${socketPath}`;
      } else if (error.message.includes("ECONNREFUSED")) {
        errorMessage = `Connection refused at ${socketPath} - is the server running?`;
      } else if (error.message.includes("EACCES")) {
        errorMessage = `Permission denied accessing ${socketPath}`;
      } else if (error.message.includes("ETIMEDOUT")) {
        errorMessage = `Connection timed out to ${socketPath}`;
      }

      reject(new Error(`Socket error: ${errorMessage}`));
    });

    // Connect to socket
    try {
      socket.connect(socketPath);
    } catch (error: any) {
      clearTimeout(timeoutHandle);
      reject(new Error(`Failed to connect: ${error.message}`));
    }
  });
}
