/**
 * Session helper for Playwright E2E tests.
 *
 * Builds and injects a fake Supabase session cookie that the Next.js
 * middleware reads via @supabase/ssr's createServerClient.
 *
 * How @supabase/ssr stores session cookies (verified from node_modules source):
 *   - Cookie name : "supabase.auth.token"  (auth-js STORAGE_KEY constant)
 *   - Cookie value: "base64-" + base64url(JSON.stringify(session))
 *     where base64url uses the alphabet A-Za-z0-9-_ (no padding)
 *   - The session object: { access_token, refresh_token, expires_at,
 *                           expires_in, token_type, user }
 *
 * The middleware's getSession() reads the cookie, decodes it, checks
 * expires_at, and returns the session directly (no network call) when
 * expires_at is more than 90 s in the future.
 *
 * Additionally, supabase.auth.setSession() (called by the login page after
 * receiving tokens from our backend) ALWAYS calls GET /auth/v1/user when
 * the JWT has not expired. Use mockSupabaseUser() to intercept that call
 * so that setSession() can complete without a real Supabase project.
 */

import type { BrowserContext, Page } from '@playwright/test';
import { createChunks, stringToBase64URL } from '@supabase/ssr';

// ── Cookie name ───────────────────────────────────────────────────────────
// @supabase/supabase-js derives the storage key as:
//   `sb-${baseUrl.hostname.split('.')[0]}-auth-token`
// We derive it the same way. First we try process.env (set by playwright.config.ts
// or CI env); if unavailable we fall back to asking the RUNNING browser via
// page.evaluate(), which always has the real value baked-in by Next.js.

function cookieNameFromUrl(supabaseUrl: string): string {
  try {
    const ref = new URL(supabaseUrl).hostname.split('.')[0];
    return `sb-${ref}-auth-token`;
  } catch {
    return 'sb-placeholder-auth-token';
  }
}

// Synchronous: works when NEXT_PUBLIC_SUPABASE_URL is in the test-runner env.
function getCookieNameSync(): string {
  return cookieNameFromUrl(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co',
  );
}

// Async: derives the cookie name from any cookie already set by the Supabase
// browser client on the current page (most reliable), falling back to the
// test-runner's env var if no Supabase cookie has been set yet.
export async function getCookieName(page: Page): Promise<string> {
  // Read all cookies currently set in the browser context.
  const cookies = await page.context().cookies();
  // The Supabase session cookie always matches sb-*-auth-token.
  const match = cookies.find(({ name }) => /^sb-.+-auth-token$/.test(name));
  if (match) return match.name;
  // No session cookie yet — fall back to the env-derived name.
  return getCookieNameSync();
}

// ── Types ─────────────────────────────────────────────────────────────────

interface FakeUser {
  id: string;
  email: string;
  role: string;
  aud: string;
  created_at: string;
}

interface FakeSession {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  expires_in: number;
  token_type: string;
  user: FakeUser;
}

// ── Fake data ─────────────────────────────────────────────────────────────

const FAKE_USER: FakeUser = {
  id: 'test-user-id-00000000-0000-0000-0000-000000000001',
  email: 'e2etest@example.com',
  role: 'authenticated',
  aud: 'authenticated',
  created_at: '2025-01-01T00:00:00.000Z',
};

/**
 * Builds a fake JWT with a future exp. auth-js decodeJWT does base64url
 * decode without signature verification, so this is sufficient.
 */
function fakeFutureJwt(email = FAKE_USER.email, expiresIn = 3600): string {
  const header = bufferToBase64URL(Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })));
  const now = Math.floor(Date.now() / 1000);
  const payload = bufferToBase64URL(
    Buffer.from(
      JSON.stringify({
        sub: FAKE_USER.id,
        email,
        role: 'authenticated',
        aud: 'authenticated',
        iat: now,
        exp: now + expiresIn,
      }),
    ),
  );
  // Signature is not verified by the client — any non-empty string works.
  return `${header}.${payload}.fakesignature`;
}

// ── Base64URL helper ──────────────────────────────────────────────────────

/** Standard Base64URL encoding (no padding), matching @supabase/ssr's alphabet. */
function bufferToBase64URL(buf: Buffer): string {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// ── Cookie builder ────────────────────────────────────────────────────────

/**
 * Returns `{ name, value }[]` for the Supabase session cookie(s) that
 * @supabase/ssr's createServerClient reads in the Next.js middleware,
 * handling chunking according to MAX_CHUNK_SIZE.
 *
 * @param overrides   Optional partial session overrides (e.g. access_token)
 * @param cookieName  Override the cookie name (default: derived from env)
 */
export function buildSessionCookies(
  overrides: Partial<FakeSession> = {},
  cookieName = getCookieNameSync(),
): Array<{ name: string; value: string }> {
  const now = Math.floor(Date.now() / 1000);
  const expiresIn = 3600;
  const session: FakeSession = {
    access_token: fakeFutureJwt(),
    refresh_token: 'fake-refresh-token',
    expires_at: now + expiresIn,
    expires_in: expiresIn,
    token_type: 'bearer',
    user: FAKE_USER,
    ...overrides,
  };

  const json = JSON.stringify(session);
  const encoded = 'base64-' + stringToBase64URL(json);

  return createChunks(cookieName, encoded);
}

/**
 * Returns `{ name, value }` for the primary Supabase session cookie.
 */
export function buildSessionCookie(
  overrides: Partial<FakeSession> = {},
  cookieName = getCookieNameSync(),
): { name: string; value: string } {
  const cookies = buildSessionCookies(overrides, cookieName);
  return cookies[0] ?? { name: cookieName, value: '' };
}

// ── Public helpers ────────────────────────────────────────────────────────

/**
 * Injects fake Supabase session cookie(s) into the browser context so that
 * the Next.js middleware treats the visitor as authenticated.
 *
 * Pass `page` when available (e.g. inside route handlers) to derive the
 * cookie name from the running Next.js app's baked-in env value, which is
 * always correct. Without `page`, the name is derived from the test-runner's
 * NEXT_PUBLIC_SUPABASE_URL env var (set from .env.local by playwright.config).
 *
 * Call this before page.goto() on any protected route.
 */
export async function injectSession(
  context: BrowserContext,
  overrides: Partial<FakeSession> = {},
  page?: Page,
): Promise<void> {
  const cookieName = page ? await getCookieName(page) : getCookieNameSync();
  const cookies = buildSessionCookies(overrides, cookieName);
  await context.addCookies(
    cookies.map((c) => ({
      name: c.name,
      value: c.value,
      domain: 'localhost',
      path: '/',
      sameSite: 'Lax',
      httpOnly: false,
    })),
  );
}

/**
 * Mocks Supabase's GET /auth/v1/user so that supabase.auth.setSession()
 * can complete without a real Supabase project.
 *
 * setSession() calls this endpoint when the access_token has not expired.
 * Must be called BEFORE the page action that triggers setSession().
 */
export async function mockSupabaseUser(page: Page, user: Partial<FakeUser> = {}): Promise<void> {
  const fakeUser = { ...FAKE_USER, ...user };
  await page.route('**/auth/v1/user', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fakeUser),
    }),
  );
}

/** Returns the access token that the login/register mocks hand back. */
export function fakeAccessToken(email?: string): string {
  return fakeFutureJwt(email);
}
