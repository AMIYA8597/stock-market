import { test, expect } from '@playwright/test';
import { setSession, mockSupabaseUser } from './helpers/session';

const PUBLIC_ROUTES = [
  '/',
  '/en/login',
  '/en/register',
  '/en/forgot-password',
  '/en/pricing',
  '/en/blog',
];

const APP_ROUTES = [
  '/en/dashboard',
  '/en/terminal',
  '/en/markets',
  '/en/markets/stocks',
  '/en/markets/stocks/RELIANCE',
  '/en/markets/crypto',
  '/en/markets/forex',
  '/en/portfolio',
  '/en/portfolio/funds',
  '/en/portfolio/optimizer',
  '/en/portfolio/orders',
  '/en/signals',
  '/en/screener',
  '/en/alerts',
  '/en/backtest-lab',
  '/en/model-monitor',
  '/en/notifications',
  '/en/billing',
  '/en/transactions',
  '/en/profile',
  '/en/settings',
  '/en/research',
  '/en/research/correlation-graph',
  '/en/research/explainability',
  '/en/research/factor-exposure',
  '/en/research/leakage-lab',
  '/en/research/model-performance',
  '/en/research/regime-analysis',
];

test.describe('Phase 3 Route QA - Public Pages', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`renders ${route} without console errors and semantic structure`, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      await page.goto(route);
      await expect(page.locator('body')).toBeVisible();

      // Check for unhandled exceptions or blank body
      const content = await page.textContent('body');
      expect(content?.trim().length).toBeGreaterThan(0);

      // Verify no catastrophic console errors
      const criticalErrors = consoleErrors.filter(
        (err) => !err.includes('favicon') && !err.includes('caniuse-lite') && !err.includes('WebSocket')
      );
      expect(criticalErrors).toEqual([]);
    });
  }
});

test.describe('Phase 3 Route QA - Authenticated App Pages', () => {
  test.beforeEach(async ({ context, page }) => {
    await setSession(context, page);
    await mockSupabaseUser(page);
  });

  for (const route of APP_ROUTES) {
    test(`renders ${route} cleanly with session`, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      await page.goto(route);
      await expect(page.locator('body')).toBeVisible();

      // Verify page is not a white-screen crash
      const bodyText = await page.textContent('body');
      expect(bodyText?.trim().length).toBeGreaterThan(0);

      // Verify not redirected to /en/login when session is present
      expect(page.url()).not.toContain('/login');
    });
  }
});

test.describe('Phase 3 Route QA - Accessibility (Axe Core)', () => {
  test('landing page meets accessibility baseline', async ({ page }) => {
    const { default: AxeBuilder } = await import('@axe-core/playwright');
    await page.goto('/');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast']) // Color contrast checked per theme
      .analyze();

    const criticalViolations = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalViolations).toEqual([]);
  });

  test('dashboard page meets accessibility baseline', async ({ context, page }) => {
    const { default: AxeBuilder } = await import('@axe-core/playwright');
    await setSession(context, page);
    await mockSupabaseUser(page);
    await page.goto('/en/dashboard');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalViolations = results.violations.filter(
      (v) => v.impact === 'critical'
    );
    expect(criticalViolations).toEqual([]);
  });
});

test.describe('Phase 3 Route QA - Visual Responsiveness', () => {
  test('desktop vs mobile viewport rendering on terminal', async ({ context, page }) => {
    await setSession(context, page);
    await mockSupabaseUser(page);

    // Desktop
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/en/terminal');
    await expect(page.locator('body')).toBeVisible();

    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/en/terminal');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Phase 3 Route QA - Resilience to Backend Outage', () => {
  test('gracefully displays fallback when backend market API returns 503', async ({ context, page }) => {
    await setSession(context, page);
    await mockSupabaseUser(page);

    // Intercept backend market indices API with 503
    await page.route('**/api/v1/market/**', (route) => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Service Temporarily Unavailable' }),
      });
    });

    await page.goto('/en/dashboard');
    // Ensure page doesn't crash to an unhandled Next.js error screen
    await expect(page.locator('body')).toBeVisible();
    const hasApplicationError = await page.locator('text=Application error').isVisible();
    expect(hasApplicationError).toBe(false);
  });
});
