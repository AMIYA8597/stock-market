'use client';

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface TerminalState {
  selectedSymbol: string;
  timeframe: '1m' | '5m' | '15m' | '1h' | '1d' | '1w' | '1M';
  setSelectedSymbol: (symbol: string) => void;
  setTimeframe: (timeframe: '1m' | '5m' | '15m' | '1h' | '1d' | '1w' | '1M') => void;
}

export const useTerminalStore = create<TerminalState>()(
  devtools(
    (set) => ({
      selectedSymbol: 'RELIANCE.NS',
      timeframe: '1d',
      setSelectedSymbol: (symbol: string) => set({ selectedSymbol: symbol }),
      setTimeframe: (timeframe) => set({ timeframe }),
    }),
    { name: 'TerminalStore' }
  )
);

interface PortfolioState {
  holdings: Array<{
    symbol: string;
    quantity: number;
    avgPrice: number;
    currentPrice: number;
  }>;
  cash: number;
  setHoldings: (holdings: PortfolioState['holdings']) => void;
  setCash: (cash: number) => void;
}

export const usePortfolioStore = create<PortfolioState>()(
  devtools(
    (set) => ({
      holdings: [],
      cash: 0,
      setHoldings: (holdings) => set({ holdings }),
      setCash: (cash) => set({ cash }),
    }),
    { name: 'PortfolioStore' }
  )
);

interface Alert {
  id: string;
  symbol: string;
  type: string;
  triggered: boolean;
  timestamp: number;
}

interface AlertState {
  alerts: Alert[];
  addAlert: (alert: Alert) => void;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertState>()(
  devtools(
    (set) => ({
      alerts: [],
      addAlert: (alert) =>
        set((state) => ({
          alerts: [alert, ...state.alerts].slice(0, 100),
        })),
      removeAlert: (id) =>
        set((state) => ({
          alerts: state.alerts.filter((a) => a.id !== id),
        })),
      clearAlerts: () => set({ alerts: [] }),
    }),
    { name: 'AlertStore' }
  )
);
