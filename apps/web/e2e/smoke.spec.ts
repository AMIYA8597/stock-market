/**
 * Post-deploy smoke test — runs against production (or SMOKE_TARGET_URL).
 *
 * Uses a dedicated smoke-test account whose credentials live in GitHub
 * Secrets (SMOKE_TEST_EMAIL / SMOKE_TEST_PASSWORD).  The account must exist
 * in the production Supabase project and must NOT be used for anything else.
 *
 * This test makes REAL network calls — no mocks.
 * Run with: playwright test --config playwright.smoke.config.ts
 *
 * Verifies:
 *   1. The login page loads.
 *   2. Two-step sign-in (email → Continue → password → Sign In) succeeds.
 *   3. /dashboard loads and shows no error page.
 */

import { test, expect } from '@playwright/test';

const EMAIL = process.env.SMOKE_TEST_EMAIL ?? '';
const PASSWORD = process.env.SMOKE_TEST_PASSWORD ?? '';

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

test('smoke: two-step sign in with smoke account reaches /dashboard', async ({ page }) => {
  await page.goto('/en/login');
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible({ timeout: 15_000 });

  // Step 1: email
  await page.fill('input[placeholder="Email"]', EMAIL);
  await page.click('button:has-text("Continue")');

  // Step 2: password
  await expect(page.getByPlaceholder('Password')).toBeVisible({ timeout: 10_000 });
  await page.fill('input[placeholder="Password"]', PASSWORD);
  await page.click('button:has-text("Sign In")');

  // After successful login, must land on dashboard
  await expect(page).toHaveURL(/\/(en\/)?dashboard/, { timeout: 30_000 });

  // Dashboard must render without a 500 / error heading
  await expect(page.getByRole('heading', { name: /error|something went wrong/i })).not.toBeVisible();

  // At least the body has content (not a blank page)
  const bodyText = await page.locator('body').innerText();
  expect(bodyText.length).toBeGreaterThan(50);
});
