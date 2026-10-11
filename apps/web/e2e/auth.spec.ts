/**
 * Auth E2E tests.
 *
 * Backend API calls are intercepted with page.route(). The Supabase
 * /auth/v1/user endpoint is also mocked because supabase.auth.setSession()
 * always calls it when the access token is not expired.
 *
 * Covered flows:
 *   signup — token path (auto sign-in after registration → /en/dashboard)
 *   signup — login_required path (→ /en/login?registered=1)
 *   signup — OTP path (verify code → /en/dashboard)
 *   signup — password mismatch / weak password validation errors
 *   login — two-step: email → "Continue" → password → "Sign In" → /en/dashboard
 *   login — unknown email (Account not found)
 *   login — wrong password (Incorrect password.)
 *   login — 403 → Verify Your Email step
 *   login — 429 → lockout message
 *   protected route redirect while logged out → /en/login
 */

import { test, expect } from '@playwright/test';
import type { BrowserContext } from '@playwright/test';
import { mockSupabaseUser, injectSession, fakeAccessToken } from './helpers/session';

// ── Shared mock helpers ───────────────────────────────────────────────────

async function mockCheckEmailExists(page: import('@playwright/test').Page) {
  await page.route(/\/api\/v1\/auth\/check-email/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ exists: true }) }),
  );
}

async function mockCheckEmailNotFound(page: import('@playwright/test').Page) {
  await page.route(/\/api\/v1\/auth\/check-email/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ exists: false }) }),
  );
}

// Injects a valid session cookie inside the route handler so it is in place
// before `window.location.href` fires. supabase.auth.setSession() may still
// try to call /auth/v1/user; if that mock intercepts it the cookie is
// refreshed (still valid); if it doesn't, the pre-injected cookie survives.
async function mockLoginSuccess(page: import('@playwright/test').Page, context: BrowserContext) {
  const token = fakeAccessToken('user@example.com');
  await page.route(/\/api\/v1\/auth\/login/, async (route) => {
    await injectSession(context, { access_token: token }, page);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: token, refresh_token: 'fake-refresh', token_type: 'bearer' }),
    });
  });
  await mockSupabaseUser(page, { email: 'user@example.com' });
}

// ── Signup ────────────────────────────────────────────────────────────────

test('signup: token path — registration with tokens redirects to /en/dashboard', async ({ page, context }) => {
  const token = fakeAccessToken('token@example.com');
  await page.route(/\/api\/v1\/auth\/register/, async (route) => {
    await injectSession(context, { access_token: token }, page);
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: token, refresh_token: 'fake-refresh', token_type: 'bearer' }),
    });
  });
  await mockSupabaseUser(page, { email: 'token@example.com' });

  await page.goto('/en/register');
  await expect(page.getByRole('heading', { name: 'Register' })).toBeVisible();

  await page.fill('input[placeholder="Full Name"]', 'Token User');
  await page.fill('input[placeholder="Email"]', 'token@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/\/en\/dashboard/, { timeout: 15_000 });
});

test('signup: login_required path — redirects to /en/login?registered=1', async ({ page }) => {
  await page.route(/\/api\/v1\/auth\/register/, (route) =>
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

  await page.goto('/en/register');
  await page.fill('input[placeholder="Full Name"]', 'Login Required User');
  await page.fill('input[placeholder="Email"]', 'needslogin@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  // Must land on login with registered=1 so the page shows "Account created. Please sign in."
  await expect(page).toHaveURL(/\/en\/login\?.*registered=1/, { timeout: 15_000 });
});

test('signup: OTP path — shows OTP form, verify lands on /en/dashboard', async ({ page, context }) => {
  await page.route(/\/api\/v1\/auth\/register/, (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ email: 'otp@example.com', message: 'Check your email for a verification code.' }),
    }),
  );

  await page.goto('/en/register');
  await page.fill('input[placeholder="Full Name"]', 'OTP User');
  await page.fill('input[placeholder="Email"]', 'otp@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'Str0ng!Passw0rd#9');
  await page.click('button[type="submit"]');

  // OTP step appears on the same page
  await expect(page.getByRole('heading', { name: 'Verify Your Email' })).toBeVisible({ timeout: 5_000 });

  const verifyToken = fakeAccessToken('otp@example.com');
  await page.route(/\/api\/v1\/auth\/verify-signup-otp/, async (route) => {
    await injectSession(context, { access_token: verifyToken }, page);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: verifyToken, refresh_token: 'fake-refresh', token_type: 'bearer' }),
    });
  });
  await mockSupabaseUser(page, { email: 'otp@example.com' });

  await page.fill('input[placeholder="6-digit code"]', '123456');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL(/\/en\/dashboard/, { timeout: 15_000 });
});

test('signup: password mismatch shows error on form', async ({ page }) => {
  await page.goto('/en/register');
  await page.fill('input[placeholder="Full Name"]', 'Test');
  await page.fill('input[placeholder="Email"]', 'mismatch@example.com');
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.fill('input[placeholder="Confirm Password"]', 'DifferentPassword#1');
  await page.click('button[type="submit"]');

  await expect(page.getByText('Passwords do not match.')).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/en\/register/);
});

test('signup: weak password shows validation error', async ({ page }) => {
  await page.goto('/en/register');
  await page.fill('input[placeholder="Full Name"]', 'Test');
  await page.fill('input[placeholder="Email"]', 'weak@example.com');
  await page.fill('input[placeholder="Password"]', 'short');
  await page.fill('input[placeholder="Confirm Password"]', 'short');
  await page.click('button[type="submit"]');

  // registerSchema validates: min 12 chars, uppercase, number, special char
  // "short" violates all four — the form should show at least one validation error
  await expect(page.locator('ul.list-disc li').first()).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/en\/register/);
});

// ── Login (two-step: email → Continue → password → Sign In) ──────────────

test('login: two-step happy path → /en/dashboard', async ({ page, context }) => {
  await mockCheckEmailExists(page);
  await mockLoginSuccess(page, context);

  await page.goto('/en/login');
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();

  // Step 1: email
  await page.fill('input[placeholder="Email"]', 'user@example.com');
  await page.click('button:has-text("Continue")');

  // Step 2: password step appears
  await expect(page.getByPlaceholder('Password')).toBeVisible({ timeout: 5_000 });
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.locator('button[type="submit"]').click();

  await expect(page).toHaveURL(/\/en\/dashboard/, { timeout: 15_000 });
});

test('login: unknown email shows "Account not found"', async ({ page }) => {
  await mockCheckEmailNotFound(page);

  await page.goto('/en/login');
  await page.fill('input[placeholder="Email"]', 'nobody@example.com');
  await page.click('button:has-text("Continue")');

  await expect(page.getByText(/account not found/i)).toBeVisible({ timeout: 5_000 });
  // Still on email step
  await expect(page.getByPlaceholder('Email')).toBeVisible();
});

test('login: wrong password shows "Incorrect password."', async ({ page }) => {
  await mockCheckEmailExists(page);
  await page.route(/\/api\/v1\/auth\/login/, (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: { code: 'UNAUTHORIZED', message: 'Incorrect password.', details: [] },
        request_id: 'test-req-id',
      }),
    }),
  );

  await page.goto('/en/login');
  await page.fill('input[placeholder="Email"]', 'user@example.com');
  await page.click('button:has-text("Continue")');
  await expect(page.getByPlaceholder('Password')).toBeVisible({ timeout: 5_000 });
  await page.fill('input[placeholder="Password"]', 'WrongPassword!1');
  await page.locator('button[type="submit"]').click();

  await expect(page.getByText('Incorrect password.')).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/en\/login/);
});

test('login: 403 response shows Verify Your Email step', async ({ page }) => {
  await mockCheckEmailExists(page);
  await page.route(/\/api\/v1\/auth\/login/, (route) =>
    route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: { code: 'FORBIDDEN', message: 'Please verify your email before signing in.', details: [] },
        request_id: 'test-req-id',
      }),
    }),
  );

  await page.goto('/en/login');
  await page.fill('input[placeholder="Email"]', 'unverified@example.com');
  await page.click('button:has-text("Continue")');
  await expect(page.getByPlaceholder('Password')).toBeVisible({ timeout: 5_000 });
  await page.fill('input[placeholder="Password"]', 'Str0ng!Passw0rd#9');
  await page.locator('button[type="submit"]').click();

  await expect(page.getByRole('heading', { name: 'Verify Your Email' })).toBeVisible({ timeout: 5_000 });
});

test('login: 429 shows lockout message', async ({ page }) => {
  await mockCheckEmailExists(page);
  await page.route(/\/api\/v1\/auth\/login/, (route) =>
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

  await page.goto('/en/login');
  await page.fill('input[placeholder="Email"]', 'locked@example.com');
  await page.click('button:has-text("Continue")');
  await expect(page.getByPlaceholder('Password')).toBeVisible({ timeout: 5_000 });
  await page.fill('input[placeholder="Password"]', 'AnyPassword!9');
  await page.locator('button[type="submit"]').click();

  await expect(
    page.getByText(/too many failed attempts|account locked/i),
  ).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/en\/login/);
});

// ── Protected route redirect ──────────────────────────────────────────────

test('protected route: unauthenticated → redirected to /en/login', async ({ page }) => {
  // No session cookie — middleware redirects to /login
  await page.goto('/en/dashboard');
  await expect(page).toHaveURL(/\/en\/login/, { timeout: 10_000 });
});

// ── login_required landing: "Account created. Please sign in." message ────

test('login: arriving from register with ?registered=1 shows "Account created." info', async ({ page }) => {
  await page.goto('/en/login?registered=1&email=new%40example.com');
  // The useEffect reads ?registered=1 and sets info message, advances to password step
  await expect(page.getByText('Account created. Please sign in.')).toBeVisible({ timeout: 5_000 });
  // Should show the password input immediately (useEffect sets step='password')
  await expect(page.getByPlaceholder('Password')).toBeVisible({ timeout: 5_000 });
});
