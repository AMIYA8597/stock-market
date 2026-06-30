"use client";

import { useEffect, useMemo, useState } from "react";
import { useTradingStore } from "@/stores/tradingStore";
import { paperTradingApi } from "@/lib/api-client";
import { contractsApi } from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { useOrderHistory } from "@/hooks/use-order-history";
import { safeFormat } from "@/lib/formatters";

interface PortfolioTabProps {
  symbol: string | undefined;
}

export default function PortfolioTab({ symbol }: PortfolioTabProps): JSX.Element {
  const { tradingMode } = useTradingStore();
  const { orders: sessionOrders } = useOrderHistory();
  
  const [activeTab, setActiveTab] = useState<"positions" | "orders" | "history">("positions");

  // Paper state variables
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [paperPnl, setPaperPnl] = useState<any>({
    cash_balance: 100000.0,
    total_holdings_value: 0.0,
    total_equity: 100000.0,
    realized_pnl: 0.0,
    unrealized_pnl: 0.0,
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [paperPositions, setPaperPositions] = useState<any[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [paperHistory, setPaperHistory] = useState<any[]>([]);

  // Live state variables
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [liveHoldings, setLiveHoldings] = useState<any[]>([]);
  const [liveCash, setLiveCash] = useState<number>(1000000);

  const [loading, setLoading] = useState<boolean>(true);

  // Fetch portfolio data depending on active mode
  const loadPortfolioData = async () => {
    try {
      if (tradingMode === "PAPER") {
        const [pnlRes, posRes, histRes] = await Promise.all([
          paperTradingApi.getPnl(),
          paperTradingApi.getPositions(),
          paperTradingApi.getHistory(),
        ]);
        setPaperPnl(pnlRes);
        setPaperPositions(posRes || []);
        setPaperHistory(histRes || []);
      } else {
        const holdingsRes = await contractsApi.getPortfolioHoldings();
        setLiveHoldings(holdingsRes.holdings || []);
        const wallet = await contractsApi.getWalletBalance();
        setLiveCash(Number(wallet.wallet_balance ?? 1000000));
      }
    } catch (e) {
      console.error("Failed to load portfolio data", e);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    setLoading(true);
    void loadPortfolioData();
    const interval = setInterval(loadPortfolioData, 3000);
    return () => clearInterval(interval);
  }, [tradingMode, symbol]);

  // WebSocket Price Feed subscription for live MTM calculation
  const paperSymbols = useMemo(() => paperPositions.map((pos) => pos.symbol), [paperPositions]);
  const { ticks: paperTicks } = usePriceFeed(paperSymbols);

  const liveSymbols = useMemo(() => liveHoldings.map((h) => h.symbol), [liveHoldings]);
  const { ticks: liveTicks } = usePriceFeed(liveSymbols);

  // Compute live prices and unrealized MTM P&L
  const computedPaperPositions = useMemo(() => {
    return paperPositions.map((pos) => {
      const tick = paperTicks.get(pos.symbol.toUpperCase());
      const current_price = tick ? tick.price : pos.current_price;
      const unrealized_pnl = pos.quantity * (current_price - pos.avg_buy_price);
      const unrealized_pnl_pct = pos.avg_buy_price > 0 ? ((current_price - pos.avg_buy_price) / pos.avg_buy_price) * 100 : 0;
      return {
        ...pos,
        current_price,
        unrealized_pnl,
        unrealized_pnl_pct,
      };
    });
  }, [paperPositions, paperTicks]);

  const computedLiveHoldings = useMemo(() => {
    return liveHoldings.map((h) => {
      const tick = liveTicks.get(h.symbol.toUpperCase());
      const ltp = tick ? tick.price : h.ltp;
      const unrealized_pnl = h.quantity * (ltp - h.avg_buy_price);
      return {
        ...h,
        ltp,
        unrealized_pnl,
      };
    });
  }, [liveHoldings, liveTicks]);

  const totalPaperUnrealizedPnl = useMemo(() => {
    return computedPaperPositions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0);
  }, [computedPaperPositions]);

  const totalLiveUnrealizedPnl = useMemo(() => {
    return computedLiveHoldings.reduce((sum, h) => sum + h.unrealized_pnl, 0);
  }, [computedLiveHoldings]);

  // Order filtration (Pending vs Finished)
  const pendingPaperOrders = useMemo(() => {
    return paperHistory.filter((o) => o.status === "PENDING");
  }, [paperHistory]);

  const finishedPaperTrades = useMemo(() => {
    return paperHistory.filter((o) => o.status !== "PENDING");
  }, [paperHistory]);

  // Actions
  const handleCancelOrder = async (orderId: string, symbol: string) => {
    if (!confirm("Are you sure you want to cancel this pending limit order?")) return;
    try {
      await paperTradingApi.cancelOrder(orderId, symbol);
      void loadPortfolioData();
    } catch (e) {
      alert("Failed to cancel order: " + (e instanceof Error ? e.message : e));
    }
  };

  const handleResetWallet = async () => {
    if (!confirm("Are you sure you want to reset your paper trading account? All open positions will be closed and balance reset to ₹1,00,000.")) return;
    try {
      setLoading(true);
      await paperTradingApi.resetWallet();
      await loadPortfolioData();
    } catch (e) {
      alert("Failed to reset wallet: " + (e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  };

  // UI calculations
  const cash = tradingMode === "PAPER" ? paperPnl.cash_balance : liveCash;
  const unrealizedPnl = tradingMode === "PAPER" ? totalPaperUnrealizedPnl : totalLiveUnrealizedPnl;
  const realizedPnl = tradingMode === "PAPER" ? paperPnl.realized_pnl : 0;
  const totalAssets = cash + unrealizedPnl + (tradingMode === "PAPER" ? paperPnl.total_holdings_value : 0);

  return (
    <div className="flex flex-col gap-3 min-w-[650px] text-xs">
      {/* Capital Status Cards */}
      <div className="grid grid-cols-4 gap-2">
        <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
          <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Available Cash</p>
          <p className="text-xs font-bold font-mono text-[var(--nq-text-primary)]">₹{safeFormat(cash, 2)}</p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
          <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Unrealized MTM P&L</p>
          <p className={`text-xs font-bold font-mono ${unrealizedPnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
            {unrealizedPnl >= 0 ? "+" : ""}₹{safeFormat(unrealizedPnl, 2)}
          </p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
          <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Realized P&L</p>
          <p className={`text-xs font-bold font-mono ${realizedPnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
            {realizedPnl >= 0 ? "+" : ""}₹{safeFormat(realizedPnl, 2)}
          </p>
        </div>
        <div className="relative rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2 flex justify-between items-center pr-3">
          <div>
            <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Total Account Value</p>
            <p className="text-xs font-bold font-mono text-[var(--nq-text-primary)]">₹{safeFormat(totalAssets, 2)}</p>
          </div>
          {tradingMode === "PAPER" && (
            <button
              onClick={handleResetWallet}
              className="rounded border border-[#FF3B5C]/40 bg-[rgba(255,59,92,0.08)] px-2 py-1 text-[8px] font-bold uppercase text-[#FF3B5C] hover:bg-[rgba(255,59,92,0.18)] transition"
              title="Reset capital back to ₹1,00,000 and close open positions"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Pane Sub-Tabs selection (TradingView Style) */}
      <div className="flex border-b border-[var(--nq-border)] gap-2 pb-1 mb-1 font-mono text-[10px]">
        <button
          onClick={() => setActiveTab("positions")}
          className={`px-3 py-1 font-semibold uppercase transition-colors border-b-2 ${
            activeTab === "positions"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Open Positions ({tradingMode === "PAPER" ? computedPaperPositions.length : computedLiveHoldings.length})
        </button>
        <button
          onClick={() => setActiveTab("orders")}
          className={`px-3 py-1 font-semibold uppercase transition-colors border-b-2 ${
            activeTab === "orders"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Order Book ({tradingMode === "PAPER" ? pendingPaperOrders.length : sessionOrders.length})
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`px-3 py-1 font-semibold uppercase transition-colors border-b-2 ${
            activeTab === "history"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Trade History ({tradingMode === "PAPER" ? finishedPaperTrades.length : 0})
        </button>
      </div>

      {/* Tab Panels */}
      <div className="min-h-[140px] max-h-[220px] overflow-y-auto ds-scrollable pr-1">
        {loading ? (
          <div className="py-8 text-center text-[var(--nq-text-secondary)] animate-pulse">Syncing trading account data...</div>
        ) : (
          <>
            {/* Open Positions Panel */}
            {activeTab === "positions" && (
              <table className="w-full text-left font-mono">
                <thead>
                  <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                    <th className="pb-1.5">Symbol</th>
                    <th className="pb-1.5 text-right">Qty</th>
                    <th className="pb-1.5 text-right">Avg Price</th>
                    <th className="pb-1.5 text-right">LTP (Live)</th>
                    <th className="pb-1.5 text-right">Current Value</th>
                    <th className="pb-1.5 text-right">Realized P&L</th>
                    <th className="pb-1.5 text-right">Unrealized MTM P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {tradingMode === "PAPER" ? (
                    computedPaperPositions.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                          No open simulated positions. Submit an order from the right panel to execute.
                        </td>
                      </tr>
                    ) : (
                      computedPaperPositions.map((pos) => {
                        const currentVal = pos.quantity * pos.current_price;
                        return (
                          <tr key={pos.id} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                            <td className="py-2 font-bold text-[var(--nq-text-primary)]">{pos.symbol}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">{pos.quantity.toLocaleString()}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(pos.avg_buy_price, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-primary)] font-bold">₹{safeFormat(pos.current_price, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(currentVal, 2)}</td>
                            <td className={`py-2 text-right font-semibold ${pos.realized_pnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                              ₹{safeFormat(pos.realized_pnl, 2)}
                            </td>
                            <td className={`py-2 text-right font-bold ${pos.unrealized_pnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                              {pos.unrealized_pnl >= 0 ? "+" : ""}₹{safeFormat(pos.unrealized_pnl, 2)} ({pos.unrealized_pnl_pct.toFixed(2)}%)
                            </td>
                          </tr>
                        );
                      })
                    )
                  ) : (
                    computedLiveHoldings.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                          No open live positions in the MongoDB model database.
                        </td>
                      </tr>
                    ) : (
                      computedLiveHoldings.map((h, i) => {
                        const currentVal = h.quantity * h.ltp;
                        return (
                          <tr key={i} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                            <td className="py-2 font-bold text-[var(--nq-text-primary)]">{h.symbol}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">{h.quantity}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(h.avg_buy_price, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-primary)] font-bold">₹{safeFormat(h.ltp, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(currentVal, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">--</td>
                            <td className={`py-2 text-right font-bold ${h.unrealized_pnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                              {h.unrealized_pnl >= 0 ? "+" : ""}₹{safeFormat(h.unrealized_pnl, 2)}
                            </td>
                          </tr>
                        );
                      })
                    )
                  )}
                </tbody>
              </table>
            )}

            {/* Order Book Panel */}
            {activeTab === "orders" && (
              <table className="w-full text-left font-mono">
                <thead>
                  <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                    <th className="pb-1.5">Submitted</th>
                    <th className="pb-1.5">Symbol</th>
                    <th className="pb-1.5">Side</th>
                    <th className="pb-1.5">Type</th>
                    <th className="pb-1.5 text-right">Qty</th>
                    <th className="pb-1.5 text-right">Limit Price</th>
                    <th className="pb-1.5 text-right">Est. Value</th>
                    <th className="pb-1.5">Status</th>
                    <th className="pb-1.5 text-center">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {tradingMode === "PAPER" ? (
                    pendingPaperOrders.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                          No pending limit orders in paper book.
                        </td>
                      </tr>
                    ) : (
                      pendingPaperOrders.map((ord) => {
                        const notional = ord.quantity * (ord.limit_price || ord.price);
                        return (
                          <tr key={ord.id} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                            <td className="py-2 text-[var(--nq-text-secondary)]">{new Date(ord.timestamp).toLocaleTimeString()}</td>
                            <td className="py-2 font-bold text-[var(--nq-text-primary)]">{ord.symbol}</td>
                            <td className={`py-2 font-bold ${ord.side === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>{ord.side}</td>
                            <td className="py-2 text-[var(--nq-text-secondary)]">{ord.order_type}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">{ord.quantity.toLocaleString()}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(ord.limit_price || ord.price, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(notional, 2)}</td>
                            <td className="py-2">
                              <span className="rounded bg-[rgba(255,184,0,0.1)] text-[#FFB800] border border-[#FFB800]/25 px-1.5 py-0.5 text-[8px] font-bold uppercase">
                                {ord.status}
                              </span>
                            </td>
                            <td className="py-2 text-center">
                              <button
                                onClick={() => handleCancelOrder(ord.id, ord.symbol)}
                                className="rounded bg-[rgba(255,59,92,0.15)] text-[#FF3B5C] border border-[#FF3B5C]/35 px-2 py-0.5 text-[9px] font-bold uppercase hover:bg-[rgba(255,59,92,0.25)] transition"
                              >
                                Cancel
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )
                  ) : (
                    sessionOrders.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                          No pending orders placed in this live session.
                        </td>
                      </tr>
                    ) : (
                      sessionOrders.map((ord, idx) => {
                        const notional = ord.quantity * ord.price;
                        return (
                          <tr key={idx} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                            <td className="py-2 text-[var(--nq-text-secondary)]">{new Date(ord.timestamp).toLocaleTimeString()}</td>
                            <td className="py-2 font-bold text-[var(--nq-text-primary)]">{ord.symbol}</td>
                            <td className={`py-2 font-bold ${ord.type === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>{ord.type}</td>
                            <td className="py-2 text-[var(--nq-text-secondary)]">LIMIT</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">{ord.quantity.toLocaleString()}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(ord.price, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(notional, 2)}</td>
                            <td className="py-2">
                              <span className="rounded bg-[rgba(0,230,118,0.1)] text-[#00E676] border border-[#00E676]/25 px-1.5 py-0.5 text-[8px] font-bold uppercase">
                                FILLED
                              </span>
                            </td>
                            <td className="py-2 text-center text-[var(--nq-text-muted)]">--</td>
                          </tr>
                        );
                      })
                    )
                  )}
                </tbody>
              </table>
            )}

            {/* Trade History Panel */}
            {activeTab === "history" && (
              <table className="w-full text-left font-mono">
                <thead>
                  <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                    <th className="pb-1.5">Executed At</th>
                    <th className="pb-1.5">Symbol</th>
                    <th className="pb-1.5">Side</th>
                    <th className="pb-1.5 text-right">Qty</th>
                    <th className="pb-1.5 text-right">Price</th>
                    <th className="pb-1.5 text-right">Brokerage</th>
                    <th className="pb-1.5 text-right">STT</th>
                    <th className="pb-1.5 text-right">Net Value</th>
                    <th className="pb-1.5">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {tradingMode === "PAPER" ? (
                    finishedPaperTrades.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                          No filled or cancelled history.
                        </td>
                      </tr>
                    ) : (
                      finishedPaperTrades.map((ord) => {
                        const statusColors: Record<string, string> = {
                          FILLED: "bg-[rgba(0,230,118,0.1)] text-[#00E676] border-[#00E676]/20",
                          CANCELLED: "bg-[rgba(158,158,158,0.1)] text-[#9E9E9E] border-[#9E9E9E]/20",
                          REJECTED: "bg-[rgba(255,59,92,0.1)] text-[#FF3B5C] border-[#FF3B5C]/20",
                        };
                        return (
                          <tr key={ord.id} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                            <td className="py-2 text-[var(--nq-text-secondary)]">{new Date(ord.timestamp).toLocaleString()}</td>
                            <td className="py-2 font-bold text-[var(--nq-text-primary)]">{ord.symbol}</td>
                            <td className={`py-2 font-bold ${ord.side === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>{ord.side}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">{ord.quantity.toLocaleString()}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(ord.price, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(ord.brokerage, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(ord.stt, 2)}</td>
                            <td className="py-2 text-right text-[var(--nq-text-primary)] font-bold">₹{safeFormat(ord.net_amount, 2)}</td>
                            <td className="py-2">
                              <span className={`rounded px-1.5 py-0.5 text-[8px] font-bold uppercase border ${statusColors[ord.status] || "border-transparent"}`}>
                                {ord.status}
                              </span>
                            </td>
                          </tr>
                        );
                      })
                    )
                  ) : (
                    <tr>
                      <td colSpan={9} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                        Live execution logs are rendered in the right-side Audit Log console.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  );
}
