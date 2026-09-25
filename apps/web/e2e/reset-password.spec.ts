import { test, expect } from '@playwright/test';

test('forgot and reset password flow', async ({ page }) => {
  await page.goto('/en/forgot-password');
  await expect(page.getByRole('heading', { name: 'Reset Password' })).toBeVisible();
  
  await page.fill('input[type="email"]', 'test@example.com');
  await page.route('**/auth/v1/recover*', route => route.fulfill({ status: 200 }));
  await page.click('button[type="submit"]');
  
  await expect(page.getByText('Check your email for reset link')).toBeVisible();

  // Test the reset route directly
  await page.goto('/en/reset-password#access_token=mock_token');
  await expect(page.getByRole('heading', { name: 'Update Password' })).toBeVisible();

  await page.fill('input[type="password"]', 'newpassword123');
  await page.route('**/auth/v1/recover*', route => route.fulfill({ status: 200 }));
  await page.click('button[type="submit"]');

  // Supabase mock returns error or redirects
});
