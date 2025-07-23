/**
 * Health check utilities for E2E tests
 */
import * as fs from 'fs';
import { Socket } from 'net';

/**
 * Perform a health check by sending a ping command to the socket server
 */
export async function healthCheck(
  socketPath: string,
  timeoutMs: number = 2000
): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new Socket();
    let hasResponse = false;

    // Set up timeout
    const timeout = setTimeout(() => {
      if (!hasResponse) {
        socket.destroy();
        resolve(false);
      }
    }, timeoutMs);

    socket.on("connect", () => {
      const pingCommand = JSON.stringify({ command: "__ping__" });
      socket.write(pingCommand);
    });

    socket.on("data", (data: any) => {
      hasResponse = true;
      clearTimeout(timeout);

      try {
        const response = JSON.parse(data.toString());
        const isHealthy =
          response.success === true && response.message === "pong";
        socket.destroy();
        resolve(isHealthy);
      } catch (error) {
        socket.destroy();
        resolve(false);
      }
    });

    socket.on("error", () => {
      clearTimeout(timeout);
      resolve(false);
    });

    socket.on("close", () => {
      clearTimeout(timeout);
      if (!hasResponse) {
        resolve(false);
      }
    });

    // Attempt to connect
    try {
      socket.connect(socketPath);
    } catch (error) {
      clearTimeout(timeout);
      resolve(false);
    }
  });
}

/**
 * Wait for socket file to exist
 */
export async function waitForSocketFile(
  socketPath: string,
  timeoutMs: number = 5000
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    if (fs.existsSync(socketPath)) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  return false;
}

/**
 * Perform multiple health checks with retry logic
 */
export async function robustHealthCheck(
  socketPath: string,
  maxRetries: number = 5,
  retryDelayMs: number = 500,
  timeoutMs: number = 2000
): Promise<boolean> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const isHealthy = await healthCheck(socketPath, timeoutMs);
      if (isHealthy) {
        return true;
      }
    } catch (error: any) {
      console.log(`Health check attempt ${attempt} failed:`, error.message);
    }

    if (attempt < maxRetries) {
      await new Promise((resolve) => setTimeout(resolve, retryDelayMs));
    }
  }

  return false;
}
