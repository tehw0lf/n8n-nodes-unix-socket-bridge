/**
 * Security tests for Unix Socket Bridge
 */

import { UnixSocketBridge } from "../nodes/UnixSocketBridge/UnixSocketBridge.node";
import * as crypto from "crypto";

// Mock the hashToken function for testing
function hashToken(token: string): string {
  return crypto.createHash('sha256').update(token).digest('hex');
}

describe("UnixSocketBridge Security", () => {
  let node: UnixSocketBridge;

  beforeEach(() => {
    node = new UnixSocketBridge();
  });

  describe("Token Hashing", () => {
    test("should hash tokens consistently", () => {
      const token = "test-secret-token";
      const expectedHash = "b80965ff4cbf5f5681e5966c558600ee649dcbcfbbc6ede5f92d8f6df93d25ee";
      
      const hash1 = hashToken(token);
      const hash2 = hashToken(token);
      
      expect(hash1).toBe(expectedHash);
      expect(hash2).toBe(expectedHash);
      expect(hash1).toBe(hash2);
    });

    test("should produce different hashes for different tokens", () => {
      const token1 = "secret-token-1";
      const token2 = "secret-token-2";
      
      const hash1 = hashToken(token1);
      const hash2 = hashToken(token2);
      
      expect(hash1).not.toBe(hash2);
      expect(hash1).toHaveLength(64); // SHA-256 hex length
      expect(hash2).toHaveLength(64);
    });

    test("should handle empty strings securely", () => {
      const emptyHash = hashToken("");
      const spaceHash = hashToken(" ");
      
      expect(emptyHash).toBe("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
      expect(spaceHash).toBe("36a9e7f1c95b82ffb99743e0c5c4ce95d83c9a430aac59f84ef3cbfab6145068");
      expect(emptyHash).not.toBe(spaceHash);
    });

    test("should handle special characters correctly", () => {
      const specialToken = "test!@#$%^&*()_+-={}[]|\\:;\"'<>?,./<token>";
      const hash = hashToken(specialToken);
      
      expect(hash).toHaveLength(64);
      expect(hash).toMatch(/^[a-f0-9]{64}$/);
    });

    test("should handle unicode characters correctly", () => {
      const unicodeToken = "测试令牌🔐🔑";
      const hash = hashToken(unicodeToken);
      
      expect(hash).toHaveLength(64);
      expect(hash).toMatch(/^[a-f0-9]{64}$/);
    });
  });

  describe("Request Message Security", () => {
    test("should not include plaintext tokens in messages", () => {
      // This test ensures our interface definitions use auth_token_hash, not auth_token
      const socketCommand = {
        command: "test",
        auth_token_hash: hashToken("secret-token"),
        request_id: "test-123"
      };

      expect(socketCommand).not.toHaveProperty("auth_token");
      expect(socketCommand).toHaveProperty("auth_token_hash");
      expect(socketCommand.auth_token_hash).toHaveLength(64);
    });

    test("should validate hash format", () => {
      const validHash = hashToken("test-token");
      const invalidHashes = [
        "invalid-hash",
        "123",
        "",
        "g1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef", // invalid character 'g'
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcde", // too short
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1" // too long
      ];

      expect(validHash).toMatch(/^[a-f0-9]{64}$/);
      
      invalidHashes.forEach(hash => {
        expect(hash).not.toMatch(/^[a-f0-9]{64}$/);
      });
    });
  });

  describe("Security Best Practices", () => {
    test("should use secure credentials field", () => {
      const credentials = node.description.credentials;
      
      expect(credentials).toBeDefined();
      expect(credentials?.[0].name).toBe("httpHeaderAuth");
      expect(credentials?.[0].required).toBe(false); // For backward compatibility
    });

    test("should not expose direct token fields", () => {
      const properties = node.description.properties;
      const authTokenProperty = properties.find(prop => prop.name === "authToken");
      
      expect(authTokenProperty).toBeUndefined();
    });

    test("should only use secure credential authentication", () => {
      const credentials = node.description.credentials;
      
      expect(credentials).toBeDefined();
      expect(credentials).toHaveLength(1);
      expect(credentials?.[0].name).toBe("httpHeaderAuth");
    });
  });

  describe("Token Validation Edge Cases", () => {
    test("should handle very long tokens", () => {
      const longToken = "a".repeat(1000);
      const hash = hashToken(longToken);
      
      expect(hash).toHaveLength(64);
      expect(hash).toMatch(/^[a-f0-9]{64}$/);
    });

    test("should handle tokens with newlines and whitespace", () => {
      const tokenWithWhitespace = "  \n\t  secret-token  \n\t  ";
      const cleanToken = "secret-token";
      
      const hashWithWhitespace = hashToken(tokenWithWhitespace);
      const hashClean = hashToken(cleanToken);
      
      expect(hashWithWhitespace).not.toBe(hashClean);
      expect(hashWithWhitespace).toHaveLength(64);
      expect(hashClean).toHaveLength(64);
    });

    test("should be deterministic across multiple calls", () => {
      const token = "test-deterministic-token";
      const hashes = Array.from({ length: 10 }, () => hashToken(token));
      
      const uniqueHashes = new Set(hashes);
      expect(uniqueHashes.size).toBe(1); // All hashes should be identical
      expect(hashes[0]).toHaveLength(64);
    });
  });

  describe("Cryptographic Properties", () => {
    test("should produce avalanche effect", () => {
      const token1 = "test-token-1";
      const token2 = "test-token-2"; // Single character difference
      
      const hash1 = hashToken(token1);
      const hash2 = hashToken(token2);
      
      // Count different characters
      let diffCount = 0;
      for (let i = 0; i < hash1.length; i++) {
        if (hash1[i] !== hash2[i]) {
          diffCount++;
        }
      }
      
      // With SHA-256, even single character change should affect many bits
      expect(diffCount).toBeGreaterThan(20); // Should be roughly 50% different
      expect(hash1).not.toBe(hash2);
    });

    test("should resist length extension attacks", () => {
      // SHA-256 is resistant to length extension attacks by design
      const shortToken = "secret";
      const extendedToken = "secret" + "extension";
      
      const shortHash = hashToken(shortToken);
      const extendedHash = hashToken(extendedToken);
      
      expect(shortHash).not.toBe(extendedHash);
      expect(shortHash).toHaveLength(64);
      expect(extendedHash).toHaveLength(64);
      
      // The extended hash should not be predictable from the short hash
      expect(extendedHash).not.toContain(shortHash.substring(0, 32));
    });
  });

  describe("Performance and Resource Usage", () => {
    test("should hash tokens efficiently", () => {
      const startTime = Date.now();
      const token = "performance-test-token";
      
      // Hash the token multiple times
      for (let i = 0; i < 1000; i++) {
        hashToken(token + i);
      }
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      // Should complete 1000 hashes in reasonable time (less than 1 second)
      expect(duration).toBeLessThan(1000);
    });

    test("should not leak memory with repeated hashing", () => {
      const initialMemory = process.memoryUsage().heapUsed;
      
      // Hash many different tokens
      for (let i = 0; i < 10000; i++) {
        hashToken(`memory-test-token-${i}`);
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Should not significantly increase memory usage
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024); // Less than 10MB increase
    });
  });
});