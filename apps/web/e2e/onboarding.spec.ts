import { test, expect } from '@playwright/test';

test('onboarding flow', async ({ page }) => {
  await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 200, json: { email: 'test@test.com' }}));
  await page.route('**/api/v1/onboarding', route => route.fulfill({ status: 200 }));
  // Fake login state for Next.js middleware by setting a cookie or localstorage?
  // Actually, middleware uses Supabase cookies! We can mock middleware by running Next in test mode or just mock the page route?
  // In Playwright we can set the cookie:
  await page.context().addCookies([{ name: 'sb-access-token', value: 'mock', domain: 'localhost', path: '/' }, { name: 'sb-refresh-token', value: 'mock', domain: 'localhost', path: '/' }]);
  await page.goto('/en/onboarding');
  await expect(page.getByText('Set up your account')).toBeVisible();
  
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
