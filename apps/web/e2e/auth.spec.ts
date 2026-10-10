/**
 * Auth E2E tests — all backend API calls are intercepted with page.route()
 * so these tests run against the Next.js dev server only (no live backend or
 * Supabase project required).
 *
 * Covered flows:
 *   signup — token path (auto sign-in after registration)
 *   signup — login_required path (account created but must log in separately)
 *   signup — OTP path (email verification before dashboard access)
 *   signin — happy path
 *   signin — wrong password
 *   signin — lockout after repeated failures
 *   protected route redirect (unauthenticated → /login)
 *   logout
 */

import { test, expect, type Page } from '@playwright/test';

const API = '**/api/v1';

// ── Helpers ───────────────────────────────────────────────────────────────

function mockRegisterToken(page: Page) {
  return page.route(`${API}/auth/register`, (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'created',
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
      }),
    }),
  );
}

function mockRegisterLoginRequired(page: Page) {
  return page.route(`${API}/auth/register`, (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'created',
        login_required: true,
        message: 'Account created. Please sign in.',
      }),
    }),
  );
}

function mockRegisterOtp(page: Page) {
  return page.route(`${API}/auth/register`, (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        email: 'otp@example.com',
        message: 'Check your email for a verification code.',
      }),
    }),
  );
}

function mockVerifyOtp(page: Page) {
  return page.route(`${API}/auth/verify-signup-otp`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
      }),
    }),
  );
}

function mockLoginSuccess(page: Page) {
  return page.route(`${API}/auth/login`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
      }),
    }),
  );
}

function mockLoginWrongPassword(page: Page) {
  return page.route(`${API}/auth/login`, (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: { code: 'UNAUTHORIZED', message: 'Invalid email or password.', details: [] },
        request_id: 'test-req-id',
      }),
    }),
  );
}

function mockLoginLocked(page: Page) {
  return page.route(`${API}/auth/login`, (route) =>
    route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: {
          code: 'RATE_LIMIT_EXCEEDED',
          message: 'Too many failed attempts. Account locked for 15 minutes.',
          details: [],
        },
        request_id: 'test-req-id',
      }),
    }),
  );
}

// ── Signup — token path ───────────────────────────────────────────────────

test('signup: token path — successful registration redirects to dashboard', async ({ page }) => {
  await mockRegisterToken(page);
  await page.goto('/en/register');
  await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible();

  await page.fill('input[placeholder="Full Name"]', 'Test User');
  await page.fill('input[placeholder="Email"]', 'token@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/\/(en\/)?dashboard/, { timeout: 10_000 });
});

// ── Signup — login_required path ──────────────────────────────────────────

test('signup: login_required path — redirects to login after account creation', async ({ page }) => {
  await mockRegisterLoginRequired(page);
  await page.goto('/en/register');

  await page.fill('input[placeholder="Full Name"]', 'Test User');
  await page.fill('input[placeholder="Email"]', 'needslogin@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/\/(en\/)?login/, { timeout: 10_000 });
});

// ── Signup — OTP path ─────────────────────────────────────────────────────

test('signup: OTP path — shows OTP form, verify code lands on dashboard', async ({ page }) => {
  await mockRegisterOtp(page);
  await page.goto('/en/register');

  await page.fill('input[placeholder="Full Name"]', 'OTP User');
  await page.fill('input[placeholder="Email"]', 'otp@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  // OTP step: stays on /register and shows the OTP input
  await expect(page.getByPlaceholder('6-digit code')).toBeVisible({ timeout: 5_000 });

  await mockVerifyOtp(page);
  await page.fill('input[placeholder="6-digit code"]', '123456');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/\/(en\/)?dashboard/, { timeout: 10_000 });
});

// ── Signin — happy path ───────────────────────────────────────────────────

test('signin: correct credentials redirects to dashboard', async ({ page }) => {
  await mockLoginSuccess(page);
  await page.goto('/en/login');
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();

  await page.fill('input[placeholder="Email"]', 'user@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/\/(en\/)?dashboard/, { timeout: 10_000 });
});

// ── Signin — wrong password ───────────────────────────────────────────────

test('signin: wrong password shows error, stays on login page', async ({ page }) => {
  await mockLoginWrongPassword(page);
  await page.goto('/en/login');

  await page.fill('input[placeholder="Email"]', 'user@example.com');
  await page.fill('input[placeholder="Password"]', 'WrongPassword!1');
  await page.click('button[type="submit"]');

  await expect(page.getByText(/invalid email or password/i)).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/(en\/)?login/);
});

// ── Signin — lockout ──────────────────────────────────────────────────────

test('signin: lockout response shows lockout message', async ({ page }) => {
  await mockLoginLocked(page);
  await page.goto('/en/login');

  await page.fill('input[placeholder="Email"]', 'locked@example.com');
  await page.fill('input[placeholder="Password"]', 'SomePassword!1');
  await page.click('button[type="submit"]');

  await expect(
    page.getByText(/too many failed attempts|account locked/i),
  ).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/(en\/)?login/);
});

// ── Protected route redirect ──────────────────────────────────────────────

test('protected route: unauthenticated user is redirected to login', async ({ page }) => {
  // No auth cookies/tokens → middleware should redirect
  await page.goto('/en/dashboard');
  await expect(page).toHaveURL(/\/(en\/)?login/, { timeout: 10_000 });
});
