/**
 * Mock n8n execution context utilities for E2E tests
 */
import { expect, jest } from '@jest/globals';

/**
 * Create a mock IExecuteFunctions context for testing
 */
export function createMockExecuteFunctions(
  parameters: Record<string, any> = {}
): any {
  const mockParameters: { [key: string]: any } = {
    socketPath: "/tmp/e2e-test-unix-socket-bridge.sock",
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

/**
 * Create mock context for auto-discover mode
 */
export function createAutoDiscoverMockContext(
  socketPath: string,
  discoveredCommand: string = "__introspect__"
): any {
  return createMockExecuteFunctions({
    socketPath,
    autoDiscover: true,
    timeout: 5000,
    responseFormat: "json",
    discoveredCommand,
    parameters: { parameter: [] },
  });
}

/**
 * Create mock context for manual command execution
 */
export function createCommandExecutionMockContext(
  socketPath: string,
  command: string,
  parameters: Array<{ name: string; value: any }> = []
): any {
  return createMockExecuteFunctions({
    socketPath,
    autoDiscover: false,
    timeout: 5000,
    responseFormat: "auto",
    command,
    parameters: { parameter: parameters },
  });
}

/**
 * Create mock context with custom settings
 */
export function createCustomMockContext(
  socketPath: string,
  options: {
    autoDiscover?: boolean;
    timeout?: number;
    responseFormat?: string;
    command?: string;
    parameters?: Array<{ name: string; value: any }>;
    continueOnFail?: boolean;
  } = {}
): any {
  const mockContext = createMockExecuteFunctions({
    socketPath,
    autoDiscover: options.autoDiscover ?? false,
    timeout: options.timeout ?? 5000,
    responseFormat: options.responseFormat ?? "auto",
    command: options.command ?? "ping",
    parameters: { parameter: options.parameters ?? [] },
  });

  if (options.continueOnFail !== undefined) {
    mockContext.continueOnFail.mockReturnValue(options.continueOnFail);
  }

  return mockContext;
}

/**
 * Parameter builder helper
 */
export class ParameterBuilder {
  private parameters: Array<{ name: string; value: any }> = [];

  add(name: string, value: any): ParameterBuilder {
    this.parameters.push({ name, value });
    return this;
  }

  addString(name: string, value: string): ParameterBuilder {
    return this.add(name, value);
  }

  addNumber(name: string, value: number): ParameterBuilder {
    return this.add(name, value);
  }

  addBoolean(name: string, value: boolean): ParameterBuilder {
    return this.add(name, value);
  }

  build(): Array<{ name: string; value: any }> {
    return [...this.parameters];
  }

  clear(): ParameterBuilder {
    this.parameters = [];
    return this;
  }
}

/**
 * Test scenario builder
 */
export interface TestScenario {
  name: string;
  socketPath: string;
  mockContext: any;
  expectedSuccess: boolean;
  expectedError?: string;
  validations?: Array<(result: any) => void>;
}

export class TestScenarioBuilder {
  private scenarios: TestScenario[] = [];

  addIntrospectionTest(socketPath: string): TestScenarioBuilder {
    const mockContext = createAutoDiscoverMockContext(
      socketPath,
      "__introspect__"
    );

    this.scenarios.push({
      name: "Server Introspection",
      socketPath,
      mockContext,
      expectedSuccess: true,
      validations: [
        (result) => {
          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.success).toBe(true);
          expect(result[0][0].json.response.server_info).toBeDefined();
        },
      ],
    });

    return this;
  }

  addCommandTest(
    socketPath: string,
    command: string,
    parameters: Array<{ name: string; value: any }> = []
  ): TestScenarioBuilder {
    const mockContext = createCommandExecutionMockContext(
      socketPath,
      command,
      parameters
    );

    this.scenarios.push({
      name: `Command: ${command}`,
      socketPath,
      mockContext,
      expectedSuccess: true,
      validations: [
        (result) => {
          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.success).toBe(true);
        },
      ],
    });

    return this;
  }

  addErrorTest(
    socketPath: string,
    command: string,
    expectedError: string
  ): TestScenarioBuilder {
    const mockContext = createCommandExecutionMockContext(socketPath, command);

    this.scenarios.push({
      name: `Error Test: ${command}`,
      socketPath,
      mockContext,
      expectedSuccess: false,
      expectedError,
      validations: [
        (result) => {
          expect(result).toHaveLength(1);
          expect(result[0]).toHaveLength(1);
          expect(result[0][0].json.success).toBe(false);
          if (expectedError) {
            expect(result[0][0].json.error).toContain(expectedError);
          }
        },
      ],
    });

    return this;
  }

  build(): TestScenario[] {
    return [...this.scenarios];
  }

  clear(): TestScenarioBuilder {
    this.scenarios = [];
    return this;
  }
}
