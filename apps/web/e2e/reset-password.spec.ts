import { test, expect } from '@playwright/test';

test('forgot and reset password flow', async ({ page }) => {
  await page.goto('/en/forgot-password');
  await expect(page.getByRole('heading', { name: 'Forgot Password' })).toBeVisible();

  await page.route('**/api/v1/auth/forgot-password', (route) =>
    route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({ message: "If that email is registered, we've sent a password reset code." }),
    }),
  );

  await page.fill('input[type="email"]', 'test@example.com');
  await page.click('button[type="submit"]');

  // Successful submission navigates to /reset-password with the email prefilled.
  await expect(page).toHaveURL(/\/reset-password\?email=/);
  await expect(page.getByRole('heading', { name: 'Reset Password' })).toBeVisible();

  await page.route('**/api/v1/auth/reset-password', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Password updated. You can now sign in with your new password.' }),
    }),
  );

  await page.fill('input[placeholder="6-digit reset code"]', '123456');
  await page.fill('input[placeholder="New Password"]', 'Str0ng!NewPassw0rd#9');
  await page.fill('input[placeholder="Confirm New Password"]', 'Str0ng!NewPassw0rd#9');
  await page.click('button[type="submit"]');

  // Successful reset redirects to /login.
  await expect(page).toHaveURL(/\/login/);
});

test('reset-password shows an error for an invalid code', async ({ page }) => {
  await page.goto('/en/reset-password?email=test%40example.com');
  await expect(page.getByRole('heading', { name: 'Reset Password' })).toBeVisible();

  await page.route('**/api/v1/auth/reset-password', (route) =>
    route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Incorrect reset code.', details: [] },
        request_id: 'test-request-id',
      }),
    }),
  );

  await page.fill('input[placeholder="6-digit reset code"]', '000000');
  await page.fill('input[placeholder="New Password"]', 'Str0ng!NewPassw0rd#9');
  await page.fill('input[placeholder="Confirm New Password"]', 'Str0ng!NewPassw0rd#9');
  await page.click('button[type="submit"]');

  await expect(page.getByText('Incorrect reset code.')).toBeVisible();
});
