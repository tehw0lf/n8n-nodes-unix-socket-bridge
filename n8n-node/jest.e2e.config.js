const baseConfig = require("./jest.config.js");

module.exports = {
  ...baseConfig,
  testMatch: ["**/tests/e2e/**/*.test.ts"],
  testTimeout: 60000, // 60 second timeout for E2E tests
  setupFilesAfterEnv: [],
  maxWorkers: 1, // Run E2E tests serially to avoid socket conflicts
  displayName: "E2E Tests",
  verbose: true,
};
