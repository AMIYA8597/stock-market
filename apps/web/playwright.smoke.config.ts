import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke test config — runs only apps/web/e2e/smoke.spec.ts against a
 * deployed environment (SMOKE_TARGET_URL).
 *
 * Unlike the main playwright.config.ts, this config does NOT start any
 * local dev servers, and smoke.spec.ts is NOT excluded here.
 *
 * Usage:
 *   SMOKE_TARGET_URL=https://neuroquant-sm.vercel.app \
 *   SMOKE_TEST_EMAIL=... SMOKE_TEST_PASSWORD=... \
 *   pnpm exec playwright test --config playwright.smoke.config.ts
 */

export default defineConfig({
  testMatch: ['**/e2e/smoke.spec.ts'],
  fullyParallel: false,
  retries: 1,
  reporter: 'html',
  use: {
    baseURL: process.env.SMOKE_TARGET_URL ?? 'https://neuroquant-sm.vercel.app',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // No webServer — we test the already-deployed site.
});
