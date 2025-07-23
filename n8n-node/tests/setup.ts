/**
 * Jest setup file for Unix Socket Bridge tests
 */

// Mock n8n-workflow for testing
jest.mock("n8n-workflow", () => ({
  NodeConnectionType: {
    Main: "main",
  },
  NodeOperationError: class extends Error {
    constructor(node: any, message: string) {
      super(message);
      this.name = "NodeOperationError";
    }
  },
}));

// Global test timeout
jest.setTimeout(10000);

// Console warnings for debugging
process.env.NODE_ENV = "test";
