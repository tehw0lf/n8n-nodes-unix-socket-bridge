/**
 * Python Server Process Manager for E2E Tests
 * Manages the lifecycle of the Python socket server process
 */
import { ChildProcess, spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

import { healthCheck } from './utils/health-check';

export class PythonServerManager {
  private serverProcess: ChildProcess | null = null;
  private configPath: string;
  private socketPath: string;
  private isServerReady: boolean = false;
  private serverLogs: string[] = [];

  constructor(configPath: string, socketPath?: string, resourceManager?: any) {
    this.configPath = configPath;

    if (socketPath) {
      this.socketPath = socketPath;
    } else {
      // Extract socket path from config
      const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
      this.socketPath = config.socket_path;
    }

    // Track this instance with resource manager if provided
    if (resourceManager) {
      resourceManager.trackSocketPath(this.socketPath);
    }
  }

  /**
   * Start the Python server process
   */
  async start(): Promise<void> {
    return this.startServer();
  }

  /**
   * Start the Python server process (internal method)
   */
  async startServer(): Promise<void> {
    if (this.serverProcess) {
      throw new Error("Server is already running");
    }

    // Ensure socket file doesn't exist
    if (fs.existsSync(this.socketPath)) {
      fs.unlinkSync(this.socketPath);
    }

    // Get the absolute path to the Python server
    const serverScriptPath = path.resolve(
      __dirname,
      "../../..",
      "server/socket-server.py"
    );

    if (!fs.existsSync(serverScriptPath)) {
      throw new Error(`Python server script not found at: ${serverScriptPath}`);
    }

    console.log(`Starting Python server with config: ${this.configPath}`);
    console.log(`Server script path: ${serverScriptPath}`);
    console.log(`Socket path: ${this.socketPath}`);

    // Spawn the Python server process
    this.serverProcess = spawn("python3", [serverScriptPath, this.configPath], {
      stdio: ["pipe", "pipe", "pipe"],
      env: { 
        ...process.env, 
        PYTHONUNBUFFERED: "1",
        AUTH_ENABLED: "false" // Disable authentication for e2e tests
      },
    });

    // Set up process event handlers
    this.setupProcessHandlers();

    // Wait for server to be ready
    await this.waitForReadiness(10000); // 10 second timeout
  }

  /**
   * Set up event handlers for the server process
   */
  private setupProcessHandlers(): void {
    if (!this.serverProcess) return;

    this.serverProcess.stdout?.on("data", (data: Buffer) => {
      const log = data.toString();
      this.serverLogs.push(log);
      console.log(`[SERVER STDOUT] ${log.trim()}`);
    });

    this.serverProcess.stderr?.on("data", (data: Buffer) => {
      const log = data.toString();
      this.serverLogs.push(log);
      console.log(`[SERVER STDERR] ${log.trim()}`);
    });

    this.serverProcess.on("error", (error: Error) => {
      console.error(`[SERVER ERROR] ${error.message}`);
    });

    this.serverProcess.on(
      "exit",
      (code: number | null, signal: string | null) => {
        console.log(
          `[SERVER EXIT] Process exited with code ${code}, signal ${signal}`
        );
        this.isServerReady = false;
        this.serverProcess = null;
      }
    );
  }

  /**
   * Wait for server to be ready
   */
  async waitForReadiness(timeoutMs: number = 5000): Promise<void> {
    const startTime = Date.now();
    const pollInterval = 100;

    while (Date.now() - startTime < timeoutMs) {
      // Check if socket file exists
      if (fs.existsSync(this.socketPath)) {
        // Try to connect and send ping
        try {
          const isHealthy = await healthCheck(this.socketPath, 1000);
          if (isHealthy) {
            this.isServerReady = true;
            console.log("✅ Server is ready and responding to health checks");
            return;
          }
        } catch (error) {
          // Continue polling
        }
      }

      // Check if process is still running
      if (!this.serverProcess || this.serverProcess.killed) {
        throw new Error("Server process terminated during startup");
      }

      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Server did not become ready within ${timeoutMs}ms`);
  }

  /**
   * Stop the server process
   */
  async stop(): Promise<void> {
    return this.stopServer();
  }

  /**
   * Stop the server process (internal method)
   */
  async stopServer(): Promise<void> {
    if (!this.serverProcess) {
      console.log("Server is not running");
      return;
    }

    console.log("Stopping Python server...");

    // Send SIGTERM first
    this.serverProcess.kill("SIGTERM");

    // Wait for graceful shutdown
    const gracefulShutdownPromise = new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        console.log("Forcing server shutdown with SIGKILL");
        this.serverProcess?.kill("SIGKILL");
        resolve();
      }, 5000);

      this.serverProcess?.on("exit", () => {
        clearTimeout(timeout);
        resolve();
      });
    });

    await gracefulShutdownPromise;

    // Clean up socket file
    if (fs.existsSync(this.socketPath)) {
      fs.unlinkSync(this.socketPath);
      console.log("Socket file cleaned up");
    }

    this.serverProcess = null;
    this.isServerReady = false;
    console.log("✅ Server stopped successfully");
  }

  /**
   * Check if server is running and ready
   */
  isReady(): boolean {
    return (
      this.isServerReady &&
      this.serverProcess !== null &&
      !this.serverProcess.killed
    );
  }

  /**
   * Get server logs
   */
  getLogs(): string[] {
    return [...this.serverLogs];
  }

  /**
   * Get socket path
   */
  getSocketPath(): string {
    return this.socketPath;
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    try {
      await this.stopServer();
    } catch (error) {
      console.error("Error during cleanup:", error);
    }
  }
}
