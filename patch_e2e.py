import re

with open('apps/web/e2e/onboarding.spec.ts', 'r') as f:
    text = f.read()

text = text.replace("await page.goto('/en/onboarding');", """await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 200, json: { email: 'test@test.com' }}));
  await page.route('**/api/v1/onboarding', route => route.fulfill({ status: 200 }));
  // Fake login state for Next.js middleware by setting a cookie or localstorage?
  // Actually, middleware uses Supabase cookies! We can mock middleware by running Next in test mode or just mock the page route?
  // In Playwright we can set the cookie:
  await page.context().addCookies([{ name: 'sb-access-token', value: 'mock', domain: 'localhost', path: '/' }, { name: 'sb-refresh-token', value: 'mock', domain: 'localhost', path: '/' }]);
  await page.goto('/en/onboarding');""")

with open('apps/web/e2e/onboarding.spec.ts', 'w') as f:
    f.write(text)

with open('apps/web/e2e/reset-password.spec.ts', 'r') as f:
    text = f.read()

text = text.replace("await page.click('button[type=\"submit\"]');", """await page.route('**/auth/v1/recover*', route => route.fulfill({ status: 200 }));
  await page.click('button[type="submit"]');""")
text = text.replace("await page.goto('/en/reset-password');", "await page.goto('/en/reset-password#access_token=mock_token');")

with open('apps/web/e2e/reset-password.spec.ts', 'w') as f:
    f.write(text)
