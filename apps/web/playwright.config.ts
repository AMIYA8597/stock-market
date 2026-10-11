import { defineConfig, devices } from '@playwright/test';
import { readFileSync } from 'fs';
import { resolve } from 'path';

// Load .env.local so NEXT_PUBLIC_* vars are available in the test-runner process.
// In CI these are already in the environment; the try/catch silently ignores the
// missing file so nothing breaks.
try {
  const raw = readFileSync(resolve(__dirname, '.env.local'), 'utf-8');
  for (const rawLine of raw.split('\n')) {
    // trim() strips CRLF (\r) on Windows and leading/trailing whitespace
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq < 1) continue;
    const key = line.slice(0, eq);
    const val = line.slice(eq + 1).replace(/^["']|["']$/g, '');
    if (/^[A-Z_][A-Z_0-9]*$/.test(key) && !process.env[key]) {
      process.env[key] = val;
    }
  }
} catch { /* .env.local absent in CI — env vars come from GitHub Secrets */ }

export default defineConfig({
  testDir: './e2e',
  // smoke.spec.ts hits production; exclude it from the regular local/CI run.
  // Run it explicitly: playwright test e2e/smoke.spec.ts
  testIgnore: ['**/smoke.spec.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Backend: uvicorn via uv run (skipped if SKIP_BACKEND_SERVER=1)
      command: 'uv run uvicorn app.main:app --port 8000',
      cwd: '../../backend',
      url: 'http://localhost:8000/liveness',
      reuseExistingServer: !process.env.CI,
      timeout: 60 * 1000,
      env: {
        // Use a test SQLite DB so E2E never touches the production Supabase
        DATABASE_URL: 'sqlite+aiosqlite:///./e2e_test.db',
        ENVIRONMENT: 'test',
        DEBUG: 'false',
      },
    },
    {
      command: 'pnpm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
  ],
});
