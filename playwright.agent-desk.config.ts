import { randomUUID } from "node:crypto";
import path from "node:path";
import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

const apiURL = "http://127.0.0.1:8124";
const webURL = "http://127.0.0.1:3124";
const runtime = path.resolve(".runtime", `e2e-agent-desk-${randomUUID()}`);

export default defineConfig({
  ...base,
  testMatch: "**/agent-desk.spec.ts",
  outputDir: ".runtime/playwright-agent-desk",
  timeout: 90_000,
  use: { ...base.use, baseURL: webURL },
  webServer: [
    {
      command: "uv run --python 3.11 --no-sync python tests/e2e/agent_desk_server.py",
      url: `${apiURL}/ready`,
      timeout: 60_000,
      reuseExistingServer: false,
      env: {
        PORTFOLIO_DB_PATH: path.join(runtime, "portfolio.sqlite3"),
        TRAINING_ROOT: path.join(runtime, "models"),
        ENABLE_TEST_FIXTURES: "false",
      },
    },
    {
      command: "pnpm --filter @portfolio/web exec next start --hostname 127.0.0.1 --port 3124",
      url: `${webURL}/dashboard`,
      timeout: 60_000,
      reuseExistingServer: false,
      env: { API_BASE_URL: apiURL },
    },
  ],
});
