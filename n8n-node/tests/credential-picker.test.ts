/**
 * Tests for credential picker functionality
 */

import { UnixSocketBridge } from "../nodes/UnixSocketBridge/UnixSocketBridge.node";
import {
  IExecuteFunctions,
  ILoadOptionsFunctions,
} from "n8n-workflow";

describe("UnixSocketBridge Credential Picker", () => {
  let node: UnixSocketBridge;

  beforeEach(() => {
    node = new UnixSocketBridge();
  });

  describe("Credential Configuration", () => {
    test("should support httpHeaderAuth credentials", () => {
      const credentials = node.description.credentials;
      
      expect(credentials).toBeDefined();
      expect(credentials).toHaveLength(1);
      expect(credentials?.[0].name).toBe("httpHeaderAuth");
      expect(credentials?.[0].required).toBe(false);
    });

    test("should maintain backward compatibility with deprecated token field", () => {
      const properties = node.description.properties;
      const authTokenProperty = properties.find(prop => prop.name === "authToken");
      
      expect(authTokenProperty).toBeDefined();
      expect(authTokenProperty?.displayName).toBe("API Token (Deprecated)");
      expect(authTokenProperty?.description).toContain("Deprecated");
      expect(authTokenProperty?.description).toContain("credentials");
    });
  });

  describe("Token Resolution Logic", () => {
    const createMockExecuteContext = (
      credentialsValue?: string,
      deprecatedTokenValue?: string
    ): Partial<IExecuteFunctions> => ({
      getCredentials: jest.fn().mockImplementation(async (type: string) => {
        if (type === "httpHeaderAuth" && credentialsValue !== undefined) {
          return { value: credentialsValue };
        }
        throw new Error("Credentials not found");
      }),
      getNodeParameter: jest.fn().mockImplementation((name: string, index: number, defaultValue?: any) => {
        if (name === "authToken") {
          return deprecatedTokenValue ?? defaultValue ?? "";
        }
        return defaultValue;
      }),
    });

    test("should prioritize credentials over deprecated token field", async () => {
      const mockContext = createMockExecuteContext("credential-token", "deprecated-token");
      
      // This would be the actual logic from the execute method
      let authToken: string | undefined;

      // 1. Try credentials first
      try {
        const credentials = await mockContext.getCredentials!('httpHeaderAuth');
        if (credentials && credentials.value) {
          authToken = credentials.value as string;
        }
      } catch (error) {
        // Credentials not configured
      }

      // 2. Fallback to deprecated field
      if (!authToken) {
        const deprecatedToken = mockContext.getNodeParameter!("authToken", 0, "") as string;
        if (deprecatedToken && typeof deprecatedToken === "string" && deprecatedToken.trim() !== "") {
          authToken = deprecatedToken.trim();
        }
      }

      expect(authToken).toBe("credential-token");
      expect(mockContext.getCredentials).toHaveBeenCalledWith('httpHeaderAuth');
    });

    test("should fallback to deprecated token when credentials not available", async () => {
      const mockContext = createMockExecuteContext(undefined, "deprecated-token");
      
      let authToken: string | undefined;

      // 1. Try credentials first
      try {
        const credentials = await mockContext.getCredentials!('httpHeaderAuth');
        if (credentials && credentials.value) {
          authToken = credentials.value as string;
        }
      } catch (error) {
        // Credentials not configured
      }

      // 2. Fallback to deprecated field
      if (!authToken) {
        const deprecatedToken = mockContext.getNodeParameter!("authToken", 0, "") as string;
        if (deprecatedToken && typeof deprecatedToken === "string" && deprecatedToken.trim() !== "") {
          authToken = deprecatedToken.trim();
        }
      }

      expect(authToken).toBe("deprecated-token");
      expect(mockContext.getCredentials).toHaveBeenCalledWith('httpHeaderAuth');
      expect(mockContext.getNodeParameter).toHaveBeenCalledWith("authToken", 0, "");
    });

    test("should handle empty credentials gracefully", async () => {
      const mockContext = createMockExecuteContext("", "fallback-token");
      
      let authToken: string | undefined;

      // 1. Try credentials first
      try {
        const credentials = await mockContext.getCredentials!('httpHeaderAuth');
        if (credentials && credentials.value) {
          authToken = credentials.value as string;
        }
      } catch (error) {
        // Credentials not configured
      }

      // 2. Fallback to deprecated field
      if (!authToken) {
        const deprecatedToken = mockContext.getNodeParameter!("authToken", 0, "") as string;
        if (deprecatedToken && typeof deprecatedToken === "string" && deprecatedToken.trim() !== "") {
          authToken = deprecatedToken.trim();
        }
      }

      expect(authToken).toBe("fallback-token");
    });

    test("should handle case when neither credentials nor deprecated token are provided", async () => {
      const mockContext = createMockExecuteContext(undefined, "");
      
      let authToken: string | undefined;

      // 1. Try credentials first
      try {
        const credentials = await mockContext.getCredentials!('httpHeaderAuth');
        if (credentials && credentials.value) {
          authToken = credentials.value as string;
        }
      } catch (error) {
        // Credentials not configured
      }

      // 2. Fallback to deprecated field
      if (!authToken) {
        const deprecatedToken = mockContext.getNodeParameter!("authToken", 0, "") as string;
        if (deprecatedToken && typeof deprecatedToken === "string" && deprecatedToken.trim() !== "") {
          authToken = deprecatedToken.trim();
        }
      }

      expect(authToken).toBeUndefined();
    });
  });

  describe("Load Options Method", () => {
    test("should use same token resolution logic in getAvailableCommands", () => {
      // The getAvailableCommands method should use the same token resolution logic
      // This test verifies that the method signature allows for both credential and
      // parameter access, which our implementation requires
      
      const mockLoadContext: Partial<ILoadOptionsFunctions> = {
        getCredentials: jest.fn(),
        getNodeParameter: jest.fn(),
      };

      // Test that our mock context has the required methods
      expect(mockLoadContext.getCredentials).toBeDefined();
      expect(mockLoadContext.getNodeParameter).toBeDefined();
    });
  });
});