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
