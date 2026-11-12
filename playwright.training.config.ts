import { randomUUID } from "node:crypto";
import path from "node:path";
import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

const apiURL = "http://127.0.0.1:8123";
const webURL = "http://127.0.0.1:3123";
const runtime = path.resolve(".runtime", `e2e-training-${randomUUID()}`);

export default defineConfig({
  ...base,
  testMatch: "**/training.spec.ts",
  outputDir: "test-results/training",
  timeout: 360_000,
  use: { ...base.use, baseURL: webURL },
  webServer: [
    {
      command: "uv run --no-sync uvicorn --app-dir apps/api portfolio_api.main:app --host 127.0.0.1 --port 8123",
      url: `${apiURL}/ready`,
      timeout: 60_000,
      reuseExistingServer: false,
      env: {
        PYTHONPATH: path.resolve("packages"),
        PORTFOLIO_DB_PATH: path.join(runtime, "portfolio.sqlite3"),
        TRAINING_ROOT: path.join(runtime, "models"),
        ENABLE_TEST_FIXTURES: "false",
      },
    },
    {
      command: "pnpm --filter @portfolio/web exec next start --hostname 127.0.0.1 --port 3123",
      url: `${webURL}/dashboard`,
      timeout: 60_000,
      reuseExistingServer: false,
      env: { API_BASE_URL: apiURL },
    },
  ],
});
