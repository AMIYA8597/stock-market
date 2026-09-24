import { test, expect } from '@playwright/test';

test('auth page should render correctly', async ({ page }) => {
  await page.goto('/login');
  await expect(page.locator('form')).toBeVisible();
});
