// @vitest-environment node
//
// This test exercises a pure function with zero DOM dependency. The
// project-wide default (vitest.config.ts) sets environment: 'jsdom' for
// tests that actually need it, but constructing jsdom here pulls in
// undici's CacheStorage polyfill, which currently throws
// "webidl.util.markAsUncloneable is not a function" on Node 20 - a
// jsdom/undici/Node API-surface incompatibility unrelated to this test.
// Running this file under the plain 'node' environment avoids that
// incompatible code path entirely instead of masking it.
import { describe, it, expect } from 'vitest';
import { normalizeSymbol } from './symbols';
import symbolCases from '../../../../packages/contracts/symbol_cases.json';

describe('normalizeSymbol', () => {
  it('passes all shared test cases', () => {
    for (const testCase of symbolCases) {
      const [canonical, exchange] = normalizeSymbol(testCase.raw, testCase.exchange_hint);
      expect(canonical).toBe(testCase.expected_canonical);
      expect(exchange).toBe(testCase.expected_exchange);
    }
  });
});
