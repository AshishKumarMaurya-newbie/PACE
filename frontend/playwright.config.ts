import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const databasePath = join(tmpdir(), `pace-e2e-${process.pid}.sqlite`);
const backendDirectory = resolve(process.cwd(), "../backend");
const frontendOrigin = "http://127.0.0.1:3010";
const apiOrigin = "http://127.0.0.1:8010";

process.env.PACE_E2E_DB_PATH = databasePath;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: frontendOrigin,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
  globalTeardown: "./tests/e2e/global-teardown.ts",
  webServer: [
    {
      command:
        "python -m alembic upgrade head && python -m uvicorn app.main:app --host 127.0.0.1 --port 8010",
      cwd: backendDirectory,
      url: `${apiOrigin}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: `sqlite:///${databasePath.replace(/\\/g, "/")}`,
        JWT_SECRET: "pace-e2e-only-random-secret-32-characters-minimum",
        ALLOW_REGISTRATION: "true",
        FRONTEND_ORIGIN: frontendOrigin,
        SECURE_COOKIE: "false",
      },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3010",
      cwd: process.cwd(),
      url: `${frontendOrigin}/login`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        PACE_E2E: "1",
        NEXT_PUBLIC_API_URL: `${apiOrigin}/api/v1`,
      },
    },
  ],
});
