/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
'use client';

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface TradingState {
  tradingMode: 'PAPER' | 'LIVE';
}

export const useTradingStore = create<TradingState>()(
  devtools(
    (): TradingState => ({
      tradingMode: 'PAPER',
    }),
    { name: 'TradingStore' }
  )
);
