# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onboarding.spec.ts >> onboarding flow
- Location: e2e\onboarding.spec.ts:3:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Set up your account')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText('Set up your account') with timeout 5000ms
  - waiting for getByText('Set up your account')

```

```yaml
- banner:
  - link "NeuroQuant Market intelligence platform":
    - /url: /
    - img
    - paragraph: NeuroQuant
    - paragraph: Market intelligence platform
  - navigation:
    - link "Blog":
      - /url: /blog
    - link "Pricing":
      - /url: /pricing
    - link "Dashboard":
      - /url: /dashboard
  - text: Live market state
  - link "Sign in":
    - /url: /login
    - button "Sign in"
  - link "Start free":
    - /url: /register
    - button "Start free":
      - text: Start free
      - img
- main:
  - text: Secure workflow
  - heading "AI-native market operating system for modern teams." [level=1]
  - paragraph: Unify research, predictions, execution, and risk controls in one premium workspace built for scale and trust.
  - img
  - paragraph: Workflow depth
  - paragraph: Research to execution
  - img
  - paragraph: Security first
  - paragraph: RBAC and MFA ready
  - img
  - paragraph: Premium UI
  - paragraph: Responsive and polished
  - heading "Login" [level=1]
  - textbox "Email"
  - textbox "Password"
  - button "Sign In"
  - link "NeuroQuant":
    - /url: /
  - text: "- Secure enterprise access"
- contentinfo:
  - img
  - paragraph: NeuroQuant
  - paragraph: Premium AI stock intelligence
  - paragraph: "Built for institutional workflows: research, market monitoring, execution, and portfolio oversight in one scalable interface."
  - text: React Next.js Framer Motion Tailwind
  - paragraph: Explore
  - link "Dashboard":
    - /url: /dashboard
  - link "Blog":
    - /url: /blog
  - link "Pricing":
    - /url: /pricing
  - paragraph: Status
  - paragraph:
    - img
    - text: 99.98% platform uptime
  - paragraph:
    - img
    - text: Live model feed active
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test('onboarding flow', async ({ page }) => {
  4  |   await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 200, json: { email: 'test@test.com' }}));
  5  |   await page.route('**/api/v1/onboarding', route => route.fulfill({ status: 200 }));
  6  |   // Fake login state for Next.js middleware by setting a cookie or localstorage?
  7  |   // Actually, middleware uses Supabase cookies! We can mock middleware by running Next in test mode or just mock the page route?
  8  |   // In Playwright we can set the cookie:
  9  |   await page.context().addCookies([{ name: 'sb-access-token', value: 'mock', domain: 'localhost', path: '/' }, { name: 'sb-refresh-token', value: 'mock', domain: 'localhost', path: '/' }]);
  10 |   await page.goto('/en/onboarding');
> 11 |   await expect(page.getByText('Set up your account')).toBeVisible();
     |                                                       ^ Error: expect(locator).toBeVisible() failed
  12 |   
  13 |   // Step 1
  14 |   await page.fill('input[type="text"]', 'John Doe');
  15 |   await page.click('button:has-text("Next")');
  16 |   
  17 |   // Step 2
  18 |   await expect(page.getByText('Organization')).toBeVisible();
  19 |   await page.click('button:has-text("Next")');
  20 | 
  21 |   // Step 3
  22 |   await expect(page.getByText('Market Preferences')).toBeVisible();
  23 |   await page.click('button:has-text("Next")');
  24 | 
  25 |   // Step 4
  26 |   await expect(page.getByText('Workspace Setup')).toBeVisible();
  27 |   await page.fill('textarea', 'AAPL, MSFT');
  28 |   
  29 |   // Finish
  30 |   await page.click('button:has-text("Finish")');
  31 | });
  32 | 
```