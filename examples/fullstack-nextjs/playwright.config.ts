import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: {
    baseURL: "http://localhost:3011",
    channel: process.env.AUTHKIT_E2E_BROWSER_CHANNEL,
  },
  webServer: process.env.AUTHKIT_E2E_NO_SERVER
    ? undefined
    : [
        {
          command: "AUTHKIT_ACCESS_TOKEN_TTL=2 uv run uvicorn main:app --app-dir backend --port 8011",
          url: "http://localhost:8011/openapi.json",
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
        {
          command: "NEXT_PUBLIC_AUTHKIT_API_URL=http://localhost:8011/auth pnpm dev:e2e",
          url: "http://localhost:3011",
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
});
