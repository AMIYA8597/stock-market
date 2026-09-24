import { test, expect } from '@playwright/test';

test('dashboard page should render correctly', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.locator('body')).toBeVisible();
});
