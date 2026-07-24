/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
'use client';

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { tradingApi } from '@/lib/api-client';

interface TradingState {
  tradingMode: 'PAPER' | 'LIVE';
  setTradingMode: (mode: 'PAPER' | 'LIVE') => void;
}

export const useTradingStore = create<TradingState>()(
  devtools(
    (set) => ({
      tradingMode: 'PAPER',
      setTradingMode: (mode: 'PAPER' | 'LIVE') => set({ tradingMode: mode }),
    }),
    { name: 'TradingStore' }
  )
);
