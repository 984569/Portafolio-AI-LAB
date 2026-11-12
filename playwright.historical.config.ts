import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  testMatch: "**/historical.spec.ts",
  timeout: 90_000,
  webServer: Array.isArray(base.webServer) ? base.webServer.map(server => ({
    ...server, env: { ...server.env, ENABLE_TEST_FIXTURES: "false" },
  })) : base.webServer,
});
