/**
 * Cleanup utilities for E2E tests
 */
import { ChildProcess } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Clean up socket files
 */
export function cleanupSocketFiles(socketPaths: string[]): void {
  for (const socketPath of socketPaths) {
    try {
      if (fs.existsSync(socketPath)) {
        fs.unlinkSync(socketPath);
        console.log(`Cleaned up socket file: ${socketPath}`);
      }
    } catch (error: any) {
      console.warn(
        `Failed to cleanup socket file ${socketPath}:`,
        error.message
      );
    }
  }
}

/**
 * Kill process forcefully
 */
export async function forceKillProcess(
  process: ChildProcess,
  timeoutMs: number = 5000
): Promise<void> {
  if (!process || process.killed) {
    return;
  }

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      if (!process.killed) {
        process.kill("SIGKILL");
      }
      resolve();
    }, timeoutMs);

    process.on("exit", () => {
      clearTimeout(timeout);
      resolve();
    });

    // Try graceful shutdown first
    process.kill("SIGTERM");
  });
}

/**
 * Clean up test directory
 */
export function cleanupTestDirectory(testDir: string): void {
  try {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
      console.log(`Cleaned up test directory: ${testDir}`);
    }
  } catch (error: any) {
    console.warn(`Failed to cleanup test directory ${testDir}:`, error.message);
  }
}

/**
 * Ensure directory exists
 */
export function ensureDirectoryExists(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * Create temporary directory for test
 */
export function createTempTestDir(prefix: string = "e2e-test"): string {
  const tempDir = path.join(
    "/tmp",
    `${prefix}-${Date.now()}-${Math.random().toString(36).substring(7)}`
  );
  ensureDirectoryExists(tempDir);
  return tempDir;
}

/**
 * Safe file operations with error handling
 */
export class SafeFileOperations {
  private filesToCleanup: string[] = [];

  /**
   * Write file and track for cleanup
   */
  writeFile(filePath: string, content: string): void {
    try {
      ensureDirectoryExists(path.dirname(filePath));
      fs.writeFileSync(filePath, content, "utf-8");
      this.filesToCleanup.push(filePath);
    } catch (error: any) {
      throw new Error(`Failed to write file ${filePath}: ${error.message}`);
    }
  }

  /**
   * Read file safely
   */
  readFile(filePath: string): string {
    try {
      return fs.readFileSync(filePath, "utf-8");
    } catch (error: any) {
      throw new Error(`Failed to read file ${filePath}: ${error.message}`);
    }
  }

  /**
   * Cleanup all tracked files
   */
  cleanup(): void {
    for (const filePath of this.filesToCleanup) {
      try {
        if (fs.existsSync(filePath)) {
          fs.unlinkSync(filePath);
        }
      } catch (error: any) {
        console.warn(`Failed to cleanup file ${filePath}:`, error.message);
      }
    }
    this.filesToCleanup = [];
  }
}

/**
 * Resource manager for comprehensive cleanup
 */
export class ResourceManager {
  private socketPaths: string[] = [];
  private processes: ChildProcess[] = [];
  private tempDirs: string[] = [];
  private fileOperations: SafeFileOperations;

  constructor() {
    this.fileOperations = new SafeFileOperations();
  }

  /**
   * Track socket path for cleanup
   */
  trackSocketPath(socketPath: string): void {
    this.socketPaths.push(socketPath);
  }

  /**
   * Track process for cleanup
   */
  trackProcess(process: ChildProcess): void {
    this.processes.push(process);
  }

  /**
   * Track temporary directory for cleanup
   */
  trackTempDir(tempDir: string): void {
    this.tempDirs.push(tempDir);
  }

  /**
   * Get file operations handler
   */
  getFileOperations(): SafeFileOperations {
    return this.fileOperations;
  }

  /**
   * Cleanup all tracked resources
   */
  async cleanupAll(): Promise<void> {
    console.log("Starting comprehensive resource cleanup...");

    // Cleanup processes
    for (const process of this.processes) {
      try {
        await forceKillProcess(process);
      } catch (error: any) {
        console.warn("Error cleaning up process:", error.message);
      }
    }

    // Cleanup socket files
    cleanupSocketFiles(this.socketPaths);

    // Cleanup files
    this.fileOperations.cleanup();

    // Cleanup temporary directories
    for (const tempDir of this.tempDirs) {
      cleanupTestDirectory(tempDir);
    }

    console.log("✅ Resource cleanup completed");
  }
}
