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
        description: "Path to the Unix domain socket",
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
          "If commands don't load, try changing the socket path or toggling auto-discovery off/on",
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
              },
              {
                displayName: "Value",
                name: "value",
                type: "string",
                default: "",
                description: 'Parameter value (e.g., "spotify")',
                placeholder: "spotify",
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
       *
       * @example
       * // Socket server response format expected:
       * {
       *   "success": true,
       *   "server_info": {
       *     "name": "PlayerCtl Media Control",
       *     "commands": {
       *       "play": { "description": "Start playback" },
       *       "pause": { "description": "Pause playback" }
       *     }
       *   }
       * }
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
          const introspectionRequest = JSON.stringify({
            command: "__introspect__",
          });
          const response = await sendToUnixSocket(
            socketPath,
            introspectionRequest,
            timeout
          );

          const serverInfo = JSON.parse(response);

          if (
            serverInfo.success &&
            serverInfo.server_info &&
            serverInfo.server_info.commands
          ) {
            const commands = serverInfo.server_info.commands;
            const options: INodePropertyOptions[] = [];

            // Add server info as first option
            options.push({
              name: `📡 ${serverInfo.server_info.name} (${
                Object.keys(commands).length
              } commands)`,
              value: "__server_info__",
            });

            // Add separator
            options.push({
              name: "─────────────────────────",
              value: "",
            });

            // Add commands
            for (const [commandName, commandInfo] of Object.entries(
              commands as any
            )) {
              const description =
                (commandInfo as any).description || "No description";
              options.push({
                name: `${commandName} - ${description}`,
                value: commandName,
              });
            }

            return options;
          } else {
            return [
              { name: "⚠️ Server responded but no commands found", value: "" },
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
                name: "Try: python3 server/socket-server.py config.json",
                value: "",
              },
            ];
          } else if (
            error.message.includes("ENOENT") ||
            error.message.includes("not found")
          ) {
            return [
              { name: "📁 Socket file not found", value: "" },
              { name: "Check socket path and server status", value: "" },
            ];
          } else if (error.message.includes("ECONNREFUSED")) {
            return [
              { name: "🚫 Connection refused", value: "" },
              { name: "Server may not be listening on this socket", value: "" },
            ];
          } else {
            return [
              {
                name: `❌ Error: ${error.message.substring(0, 50)}...`,
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
   *
   * @throws {NodeOperationError} When invalid command is selected or socket communication fails
   *
   * @example
   * // Execution flow:
   * // 1. Validate and extract parameters
   * // 2. Build command request with parameters
   * // 3. Send to Unix socket
   * // 4. Parse and format response
   * // 5. Return structured data
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

        let command: string;
        if (autoDiscover) {
          command = this.getNodeParameter("discoveredCommand", i) as string;
          // Skip if it's the server info option
          if (command === "__server_info__" || command === "") {
            throw new NodeOperationError(
              this.getNode(),
              "Please select a valid command from the dropdown",
              { itemIndex: i }
            );
          }
        } else {
          command = this.getNodeParameter("command", i) as string;
        }

        // Build the request
        const jsonMessage: any = { command };

        // Add parameters if provided
        const parameters = this.getNodeParameter("parameters", i, {}) as any;
        if (
          parameters &&
          parameters.parameter &&
          Array.isArray(parameters.parameter) &&
          parameters.parameter.length > 0
        ) {
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

        const messageToSend = JSON.stringify(jsonMessage);

        // Send message to Unix socket
        const response = await sendToUnixSocket(
          socketPath,
          messageToSend,
          timeout
        );

        let parsedResponse: any;
        if (responseFormat === "auto") {
          // Try to parse as JSON, fallback to text
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
              { itemIndex: i }
            );
          }
        } else {
          parsedResponse = response;
        }

        // Enhance response with metadata
        const responseData: any = {
          socketPath,
          command,
          message: messageToSend,
          response: parsedResponse,
          success: true,
          timestamp: new Date().toISOString(),
        };

        // If response is a structured object with success field, use that
        if (
          typeof parsedResponse === "object" &&
          parsedResponse !== null &&
          "success" in parsedResponse
        ) {
          responseData.success = parsedResponse.success;
          responseData.output = parsedResponse.stdout || parsedResponse.output;
          responseData.error = parsedResponse.error || parsedResponse.stderr;
          responseData.returncode = parsedResponse.returncode;
        }

        returnData.push({
          json: responseData,
        });
      } catch (error: any) {
        if (this.continueOnFail()) {
          returnData.push({
            json: {
              error: error.message,
              success: false,
              timestamp: new Date().toISOString(),
            },
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
 * Helper function for Unix socket communication
 *
 * Establishes a connection to a Unix domain socket, sends a message,
 * and returns the response. Includes timeout handling and proper
 * cleanup of socket resources.
 *
 * @param socketPath - Path to the Unix domain socket file
 * @param message - Message to send (typically JSON-formatted command)
 * @param timeoutMs - Connection timeout in milliseconds
 * @returns Promise resolving to the server response as a string
 *
 * @throws {Error} When socket connection fails, times out, or server errors occur
 *
 * @example
 * ```typescript
 * const response = await sendToUnixSocket(
 *   '/tmp/playerctl.sock',
 *   JSON.stringify({ command: 'play' }),
 *   5000
 * );
 * console.log('Server response:', response);
 * ```
 *
 * @example
 * ```typescript
 * // Error handling
 * try {
 *   const response = await sendToUnixSocket('/tmp/socket.sock', message, 5000);
 *   const result = JSON.parse(response);
 * } catch (error) {
 *   if (error.message.includes('timeout')) {
 *     console.log('Server not responding');
 *   } else if (error.message.includes('ENOENT')) {
 *     console.log('Socket file not found');
 *   }
 * }
 * ```
 */
export async function sendToUnixSocket(
  socketPath: string,
  message: string,
  timeoutMs: number
): Promise<string> {
  return new Promise((resolve, reject) => {
    const socket = new net.Socket();
    let response = "";

    const timeoutHandle = global.setTimeout(() => {
      socket.destroy();
      reject(new Error(`Socket connection timeout after ${timeoutMs}ms`));
    }, timeoutMs);

    socket.on("connect", () => {
      socket.write(message);
    });

    socket.on("data", (data: Buffer) => {
      response += data.toString();
    });

    socket.on("end", () => {
      global.clearTimeout(timeoutHandle);
      resolve(response);
    });

    socket.on("close", () => {
      global.clearTimeout(timeoutHandle);
      if (response) {
        resolve(response);
      } else {
        reject(new Error("Socket closed without response"));
      }
    });

    socket.on("error", (error: Error) => {
      global.clearTimeout(timeoutHandle);
      reject(new Error(`Socket error: ${error.message}`));
    });

    socket.connect(socketPath);
  });
}
