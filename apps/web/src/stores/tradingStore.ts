'use client';

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { tradingApi } from '@/lib/api-client';

interface TradingState {
  tradingMode: 'PAPER' | 'LIVE';
  connectionStatus: string;
  authenticated: boolean;
  profile: any;
  auditLogs: string[];
  loading: boolean;
  error: string | null;
  fetchStatus: () => Promise<void>;
  setTradingMode: (mode: 'PAPER' | 'LIVE') => Promise<void>;
  triggerKillSwitch: () => Promise<void>;
  fetchAuditLogs: (limit?: number) => Promise<void>;
}

export const useTradingStore = create<TradingState>()(
  devtools(
    (set, get) => ({
      tradingMode: 'PAPER',
      connectionStatus: 'disconnected',
      authenticated: false,
      profile: null,
      auditLogs: [],
      loading: false,
      error: null,

      fetchStatus: async () => {
        set({ loading: true, error: null });
        try {
          const res = await tradingApi.getMode();
          set({
            tradingMode: res.trading_mode.toUpperCase() as 'PAPER' | 'LIVE',
            connectionStatus: res.connection_status,
            authenticated: res.authenticated,
            profile: res.profile,
          });
        } catch (err) {
          set({ error: err instanceof Error ? err.message : 'Failed to fetch trading status.' });
        } finally {
          set({ loading: false });
        }
      },

      setTradingMode: async (mode: 'PAPER' | 'LIVE') => {
        set({ loading: true, error: null });
        try {
          const res = await tradingApi.setMode(mode);
          set({
            tradingMode: res.trading_mode.toUpperCase() as 'PAPER' | 'LIVE',
          });
          // Refresh status to fetch any new profile/connection info
          await get().fetchStatus();
        } catch (err) {
          const errMsg = err instanceof Error ? err.message : 'Failed to update trading mode.';
          set({ error: errMsg });
          throw new Error(errMsg);
        } finally {
          set({ loading: false });
        }
      },

      triggerKillSwitch: async () => {
        set({ loading: true, error: null });
        try {
          await tradingApi.triggerKillSwitch();
          set({ tradingMode: 'PAPER', connectionStatus: 'disconnected' });
          await get().fetchStatus();
        } catch (err) {
          set({ error: err instanceof Error ? err.message : 'Emergency kill switch failed.' });
        } finally {
          set({ loading: false });
        }
      },

      fetchAuditLogs: async (limit = 50) => {
        try {
          const res = await tradingApi.getAuditLog(limit);
          set({ auditLogs: res.logs || [] });
        } catch {
          // Fail silently for logs background refresh
        }
      },
    }),
    { name: 'TradingStore' }
  )
);
