import { create } from "zustand";
import type { Quote, RegimeState } from "@neuroquant/types";

interface MarketStore {
  quotes: Map<string, Quote>;
  globalRegime: RegimeState;
  globalConfidence: number;
  setQuote: (symbol: string, quote: Quote) => void;
  setQuotes: (quotes: Quote[]) => void;
  setRegime: (regime: RegimeState, confidence: number) => void;
}

export const useMarketStore = create<MarketStore>((set) => ({
  quotes: new Map(),
  globalRegime: "sideways",
  globalConfidence: 50,

  setQuote: (symbol, quote) =>
    set((s) => {
      const next = new Map(s.quotes);
      next.set(symbol, quote);
      return { quotes: next };
    }),

  setQuotes: (quotes) =>
    set((s) => {
      const next = new Map(s.quotes);
      quotes.forEach((q) => next.set(q.symbol, q));
      return { quotes: next };
    }),

  setRegime: (regime, confidence) =>
    set({ globalRegime: regime, globalConfidence: confidence }),
}));
