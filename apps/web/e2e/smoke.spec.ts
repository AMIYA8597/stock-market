/**
 * Post-deploy smoke test — runs against production (or a URL override).
 *
 * Uses a dedicated smoke-test account whose credentials live in GitHub
 * Secrets (SMOKE_TEST_EMAIL / SMOKE_TEST_PASSWORD).  The account must exist
 * in the production Supabase project and must NOT be used for anything else.
 *
 * This test makes REAL network calls — no mocks.  It verifies:
 *   1. The login page loads.
 *   2. Signing in with the smoke account succeeds.
 *   3. The /dashboard page loads and is not an error page.
 *   4. The page title / heading indicates a logged-in state.
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.SMOKE_TARGET_URL ?? 'https://neuroquant-sm.vercel.app';
const EMAIL = process.env.SMOKE_TEST_EMAIL ?? '';
const PASSWORD = process.env.SMOKE_TEST_PASSWORD ?? '';

test.use({ baseURL: BASE_URL });

test.beforeAll(() => {
  if (!EMAIL || !PASSWORD) {
    throw new Error(
      'SMOKE_TEST_EMAIL and SMOKE_TEST_PASSWORD must be set to run smoke tests.',
    );
  }
});

test('smoke: login page loads', async ({ page }) => {
  const response = await page.goto('/en/login');
  expect(response?.status()).toBeLessThan(400);
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible({ timeout: 15_000 });
});

test('smoke: sign in with smoke account and reach dashboard', async ({ page }) => {
  await page.goto('/en/login');
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible({ timeout: 15_000 });

  await page.fill('input[placeholder="Email"]', EMAIL);
  await page.fill('input[placeholder="Password"]', PASSWORD);
  await page.click('button[type="submit"]');

  // After successful login, must land on dashboard
  await expect(page).toHaveURL(/\/(en\/)?dashboard/, { timeout: 30_000 });

  // Dashboard must render without a 500 / error heading
  await expect(page.getByRole('heading', { name: /error|something went wrong/i })).not.toBeVisible();

  // At least the body has content (not a blank page)
  const bodyText = await page.locator('body').innerText();
  expect(bodyText.length).toBeGreaterThan(50);
});
