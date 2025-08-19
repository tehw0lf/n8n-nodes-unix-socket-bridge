/**
 * Unit tests for Unix socket communication helper
 */
import * as net from "net";

import { sendToUnixSocket } from "../nodes/UnixSocketBridge/UnixSocketBridge.node";

// Mock the net module for these specific tests
jest.mock("net");
const mockNet = net as jest.Mocked<typeof net>;

describe("sendToUnixSocket", () => {
  let mockSocket: any;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    mockSocket = {
      connect: jest.fn(),
      write: jest.fn(),
      destroy: jest.fn(),
      on: jest.fn(),
      end: jest.fn(),
    };

    // Mock the Socket constructor
    mockNet.Socket.mockImplementation(() => mockSocket);
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("should successfully send message and receive response", async () => {
    const testMessage = JSON.stringify({ command: "test" });
    const testResponse = JSON.stringify({
      success: true,
      output: "test result",
    });

    // Mock successful connection flow
    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      switch (event) {
        case "connect":
          setImmediate(() => callback());
          break;
        case "data":
          setImmediate(() => callback(Buffer.from(testResponse)));
          break;
        case "end":
          setImmediate(() => callback());
          break;
      }
    });

    const promise = sendToUnixSocket("/tmp/test.sock", testMessage, 5000);

    // Fast-forward timers
    jest.runAllTimers();

    const result = await promise;

    expect(result).toBe(testResponse);
    expect(mockSocket.connect).toHaveBeenCalledWith("/tmp/test.sock");
    expect(mockSocket.write).toHaveBeenCalledWith(testMessage);
  });

  it("should handle connection timeout", async () => {
    // Mock timeout scenario - no connect event fired
    mockSocket.on.mockImplementation(() => {
      // Don't trigger connect event to simulate timeout
    });

    const promise = sendToUnixSocket("/tmp/test.sock", "test message", 1000);

    // Fast-forward past timeout
    jest.advanceTimersByTime(1001);

    await expect(promise).rejects.toThrow(
      "Socket connection timeout after 1000ms"
    );
    expect(mockSocket.destroy).toHaveBeenCalled();
  });

  it("should handle socket connection errors", async () => {
    const testError = new Error("ENOENT: no such file or directory");

    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      if (event === "error") {
        setImmediate(() => callback(testError));
      }
    });

    const promise = sendToUnixSocket("/tmp/nonexistent.sock", "test", 5000);

    jest.runAllTimers();

    await expect(promise).rejects.toThrow(
      "Socket error: Socket not found at /tmp/nonexistent.sock"
    );
  });

  it("should handle socket close without response", async () => {
    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      if (event === "close") {
        setImmediate(() => callback());
      }
    });

    const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

    jest.runAllTimers();

    await expect(promise).rejects.toThrow("Socket closed without response");
  });

  it("should handle socket close with response", async () => {
    const testResponse = "response data";

    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      switch (event) {
        case "connect":
          setImmediate(() => callback());
          break;
        case "data":
          // Simulate receiving data
          setImmediate(() => callback(Buffer.from(testResponse)));
          break;
        case "close":
          setImmediate(() => callback());
          break;
      }
    });

    const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

    jest.runAllTimers();

    const result = await promise;
    expect(result).toBe(testResponse);
  });

  it("should handle multiple data chunks", async () => {
    const chunk1 = "first chunk ";
    const chunk2 = "second chunk";
    const expectedResponse = chunk1 + chunk2;

    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      switch (event) {
        case "connect":
          setImmediate(() => callback());
          break;
        case "data":
          setImmediate(() => callback(Buffer.from(chunk1)));
          setImmediate(() => callback(Buffer.from(chunk2)));
          break;
        case "end":
          setImmediate(() => callback());
          break;
      }
    });

    const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

    jest.runAllTimers();

    const result = await promise;
    expect(result).toBe(expectedResponse);
  });

  it("should clear timeout on successful completion", async () => {
    const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");

    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      switch (event) {
        case "connect":
          setImmediate(() => callback());
          break;
        case "data":
          setImmediate(() => callback(Buffer.from("response")));
          break;
        case "end":
          setImmediate(() => callback());
          break;
      }
    });

    const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

    jest.runAllTimers();

    await promise;

    expect(clearTimeoutSpy).toHaveBeenCalled();
  });

  it("should clear timeout on error", async () => {
    const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");
    const testError = new Error("Connection refused");

    mockSocket.on.mockImplementation((event: string, callback: Function) => {
      if (event === "error") {
        setImmediate(() => callback(testError));
      }
    });

    const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

    jest.runAllTimers();

    await expect(promise).rejects.toThrow();
    expect(clearTimeoutSpy).toHaveBeenCalled();
  });

  describe("Enhanced Buffer-based Communication", () => {
    it("should handle large responses with buffer concatenation", async () => {
      const largeData = "x".repeat(10000); // 10KB of data
      const testResponse = JSON.stringify({ data: largeData });

      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "data": {
            // Simulate chunked response
            const chunkSize = 1000;
            for (let i = 0; i < testResponse.length; i += chunkSize) {
              const chunk = testResponse.slice(i, i + chunkSize);
              setImmediate(() => callback(Buffer.from(chunk)));
            }
            break;
          }
          case "end":
            setImmediate(() => callback());
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test message", 5000);

      jest.runAllTimers();

      const result = await promise;
      expect(result).toBe(testResponse);
    });

    it("should enforce custom maxResponseSize limits", async () => {
      const maxSize = 500;
      const largeResponse = "x".repeat(1000); // Exceeds limit

      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "data":
            setImmediate(() => callback(Buffer.from(largeResponse)));
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000, maxSize);

      jest.runAllTimers();

      await expect(promise).rejects.toThrow("Response too large");
      expect(mockSocket.destroy).toHaveBeenCalled();
    });

    it("should handle binary data safely", async () => {
      const binaryData = Buffer.from([
        0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x00, 0x57, 0x6f, 0x72, 0x6c, 0x64,
      ]);

      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "data":
            setImmediate(() => callback(binaryData));
            break;
          case "end":
            setImmediate(() => callback());
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

      jest.runAllTimers();

      const result = await promise;
      expect(result).toBe("Hello\x00World");
    });

    it("should handle Unicode characters properly", async () => {
      const unicodeText = "Hello 世界 🌍 Testing";
      const unicodeBuffer = Buffer.from(unicodeText, "utf-8");

      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "data":
            setImmediate(() => callback(unicodeBuffer));
            break;
          case "end":
            setImmediate(() => callback());
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

      jest.runAllTimers();

      const result = await promise;
      expect(result).toBe(unicodeText);
    });

    it("should handle socket close with partial data", async () => {
      const partialData = "Partial response";

      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "data":
            setImmediate(() => callback(Buffer.from(partialData)));
            break;
          case "close":
            setImmediate(() => callback(false)); // hadError = false
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

      jest.runAllTimers();

      const result = await promise;
      expect(result).toBe(partialData);
    });

    it("should handle decode errors gracefully", async () => {
      const invalidUtf8 = Buffer.from([0xff, 0xfe, 0xfd]);

      // Mock Buffer.toString to throw an error to simulate decode failure
      const originalToString = Buffer.prototype.toString;
      Buffer.prototype.toString = jest
        .fn()
        .mockImplementation((encoding?: string) => {
          if (encoding === "utf-8") {
            throw new Error("Invalid UTF-8 sequence");
          }
          return originalToString.call(this, encoding);
        });

      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "data":
            setImmediate(() => callback(invalidUtf8));
            break;
          case "end":
            // Trigger end to try decoding - will now fail due to mocked toString
            setImmediate(() => callback());
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

      jest.runAllTimers();

      await expect(promise).rejects.toThrow("Failed to decode response");

      // Restore original toString method
      Buffer.prototype.toString = originalToString;
    });

    it("should handle connection errors with specific messages", async () => {
      const errorTypes = [
        {
          error: new Error("ENOENT: no such file"),
          expectedMessage: "Socket not found",
        },
        {
          error: new Error("ECONNREFUSED"),
          expectedMessage: "Connection refused",
        },
        {
          error: new Error("EACCES: permission denied"),
          expectedMessage: "Permission denied",
        },
        {
          error: new Error("ETIMEDOUT"),
          expectedMessage: "Connection timed out",
        },
      ];

      for (const { error, expectedMessage } of errorTypes) {
        mockSocket.on.mockImplementation(
          (event: string, callback: Function) => {
            if (event === "error") {
              setImmediate(() => callback(error));
            }
          }
        );

        const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

        jest.runAllTimers();

        await expect(promise).rejects.toThrow(expectedMessage);
      }
    });
  });

  describe("Performance and Reliability", () => {
    it("should handle rapid consecutive connections", async () => {
      const promises = [];
      const responses = ["response1", "response2", "response3"];

      for (let i = 0; i < 3; i++) {
        const mockSocketInstance = {
          connect: jest.fn(),
          write: jest.fn(),
          destroy: jest.fn(),
          on: jest.fn(),
          end: jest.fn(),
        } as any;

        mockNet.Socket.mockImplementationOnce(() => mockSocketInstance);

        mockSocketInstance.on.mockImplementation(
          (event: string, callback: Function) => {
            switch (event) {
              case "connect":
                setImmediate(() => callback());
                break;
              case "data":
                setImmediate(() => callback(Buffer.from(responses[i])));
                break;
              case "end":
                setImmediate(() => callback());
                break;
            }
          }
        );

        promises.push(sendToUnixSocket("/tmp/test.sock", `test${i}`, 5000));
      }

      jest.runAllTimers();

      const results = await Promise.all(promises);
      expect(results).toEqual(responses);
    });

    it("should cleanup resources on timeout", async () => {
      mockSocket.on.mockImplementation(() => {
        // Don't trigger any events to simulate timeout
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 1000);

      jest.advanceTimersByTime(1001);

      await expect(promise).rejects.toThrow("Socket connection timeout");
      expect(mockSocket.destroy).toHaveBeenCalled();
    });

    it("should handle empty responses", async () => {
      mockSocket.on.mockImplementation((event: string, callback: Function) => {
        switch (event) {
          case "connect":
            setImmediate(() => callback());
            break;
          case "close":
            // Simulate close with no data and no error
            setImmediate(() => callback(false));
            break;
        }
      });

      const promise = sendToUnixSocket("/tmp/test.sock", "test", 5000);

      jest.runAllTimers();

      await expect(promise).rejects.toThrow("Socket closed without response");
    });
  });
});
