import { test, expect } from '@playwright/test';
import { injectSession } from './helpers/session';

test('onboarding flow', async ({ page, context }) => {
  await page.route(/\/api\/v1\/auth\/me/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ email: 'test@test.com' }) }),
  );
  await page.route(/\/api\/v1\/onboarding/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) }),
  );

  // Inject a real Supabase session cookie so the Next.js middleware lets the
  // request through to /en/onboarding instead of redirecting to /login.
  await injectSession(context);

  await page.goto('/en/onboarding');
  await expect(page.getByText('Set up your account')).toBeVisible({ timeout: 10_000 });

  // Step 1
  await page.fill('input[type="text"]', 'John Doe');
  await page.click('button:has-text("Next")');

  // Step 2
  await expect(page.getByText('Organization')).toBeVisible();
  await page.click('button:has-text("Next")');

  // Step 3
  await expect(page.getByText('Market Preferences')).toBeVisible();
  await page.click('button:has-text("Next")');

  // Step 4
  await expect(page.getByText('Workspace Setup')).toBeVisible();
  await page.fill('textarea', 'AAPL, MSFT');

  // Finish
  await page.click('button:has-text("Finish")');
});
