# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: reset-password.spec.ts >> forgot and reset password flow
- Location: e2e\reset-password.spec.ts:3:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Check your email for reset link')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText('Check your email for reset link') with timeout 5000ms
  - waiting for getByText('Check your email for reset link')

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
  - heading "Reset Password" [level=1]
  - paragraph: "Failed to execute 'json' on 'Response': Unexpected end of JSON input"
  - textbox "Email": test@example.com
  - button "Send Reset Link"
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
  3  | test('forgot and reset password flow', async ({ page }) => {
  4  |   await page.goto('/en/forgot-password');
  5  |   await expect(page.getByRole('heading', { name: 'Reset Password' })).toBeVisible();
  6  |   
  7  |   await page.fill('input[type="email"]', 'test@example.com');
  8  |   await page.route('**/auth/v1/recover*', route => route.fulfill({ status: 200 }));
  9  |   await page.click('button[type="submit"]');
  10 |   
> 11 |   await expect(page.getByText('Check your email for reset link')).toBeVisible();
     |                                                                   ^ Error: expect(locator).toBeVisible() failed
  12 | 
  13 |   // Test the reset route directly
  14 |   await page.goto('/en/reset-password#access_token=mock_token');
  15 |   await expect(page.getByRole('heading', { name: 'Update Password' })).toBeVisible();
  16 | 
  17 |   await page.fill('input[type="password"]', 'newpassword123');
  18 |   await page.route('**/auth/v1/recover*', route => route.fulfill({ status: 200 }));
  19 |   await page.click('button[type="submit"]');
  20 | 
  21 |   // Supabase mock returns error or redirects
  22 | });
  23 | 
```