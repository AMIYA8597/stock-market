import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    // Playwright owns e2e/*.spec.ts (run via `pnpm test:e2e`). Vitest's
    // default include glob matches *.spec.ts too, so without this
    // exclude, plain `pnpm test` (= `vitest run`, the project's own
    // canonical unit-test script) tries to execute Playwright's
    // test()/expect() API through Vitest's runner and crashes on every
    // e2e spec file.
    exclude: ['**/node_modules/**', '**/e2e/**', '**/.next/**'],
  },
});
