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
      "Socket error: ENOENT: no such file or directory"
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
});
