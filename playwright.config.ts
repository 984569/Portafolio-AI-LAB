import { defineConfig } from "@playwright/test";
import path from "node:path";

process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(".runtime/browsers");

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/platform.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "uv run python scripts/run_api.py",
      url: "http://127.0.0.1:8000/ready",
      reuseExistingServer: false,
      timeout: 30_000,
      env: { PORTFOLIO_DB_PATH: `.runtime/e2e-${Date.now()}.sqlite3`, ENABLE_TEST_FIXTURES: "true" },
    },
    {
      command: "pnpm --filter @portfolio/web start",
      url: "http://127.0.0.1:3000/dashboard",
      reuseExistingServer: false,
      timeout: 60_000,
      env: { API_BASE_URL: "http://127.0.0.1:8000" },
    },
  ],
});
