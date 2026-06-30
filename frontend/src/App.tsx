import React, { useState, useCallback, useEffect } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useMutation,
} from "@tanstack/react-query";
import axios from "axios";
import { CandleChart, StockQuote } from "./components/ForecastChart";
import "./index.css";

/* ───────────────────────── Error Boundary ────────────────────── */
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: {
    children: React.ReactNode;
    fallback?: React.ReactNode;
  }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="error-box" style={{ margin: 16 }}>
            ⚠ Something went wrong rendering this section. Please refresh the
            page.
          </div>
        )
      );
    }
    return this.props.children;
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

const API = "/api/v1";

/* ───────────────────────── Types ─────────────────────────── */
interface IndexData {
  name: string;
  ticker: string;
  value: number;
  change: number;
  change_pct: number;
  regime_state: string;
}

interface MoverData {
  ticker: string;
  name: string;
  exchange: string;
  price?: number;
  latest_close?: number;
  change_pct: number;
  volume?: number;
  latest_volume?: number;
  signal_direction: string;
  confidence: number;
}

interface PaperPosition {
  id: string;
  symbol: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
}

interface PaperOrder {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  order_type: string;
  limit_price: number | null;
  status: string;
  brokerage: number;
  stt: number;
  slippage: number;
  net_amount: number;
  timestamp: string;
  signal_relation?: string | null;
}

interface PaperPnL {
  cash_balance: number;
  total_holdings_value: number;
  total_equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  daily_realized_loss: number;
  daily_loss_limit: number;
  circuit_breaker_triggered: boolean;
}

interface AISignal {
  direction: string;
  confidence: number;
  rationale: string;
  stopLoss?: number;
  takeProfit?: number;
  targetPrice?: number;
}

/* ───────────────────────── Formatters ─────────────────────── */
function fmt(n: number, d = 2) {
  if (n == null || isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
}

/* ───────────────────────── Hooks ──────────────────────────── */
function useIndices() {
  return useQuery<IndexData[]>({
    queryKey: ["indices"],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/global/indices`);
      return data;
    },
    staleTime: 60 * 1000,
    refetchInterval: 90 * 1000,
    retry: 2,
  });
}

function useMovers(exchange: string, type: string) {
  return useQuery<MoverData[]>({
    queryKey: ["movers", exchange, type],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/global/movers`, {
        params: { exchange, type },
      });
      return data;
    },
    staleTime: 60 * 1000,
    retry: 2,
  });
}

/* ───────────────────────── Components ─────────────────────── */
const INTERVALS = [
  { label: "1m", value: "1m", period: "1d" },
  { label: "5m", value: "5m", period: "5d" },
  { label: "15m", value: "15m", period: "1mo" },
  { label: "1H", value: "1h", period: "1mo" },
  { label: "1D", value: "1d", period: "1y" },
  { label: "1W", value: "1w", period: "5y" },
];

const EXCHANGES = ["NSE", "NYSE", "CRYPTO"] as const;
const MOVER_TYPES = ["gainers", "losers", "volume", "momentum"] as const;

function IndexChips() {
  const { data, isLoading } = useIndices();

  if (isLoading) {
    return (
      <div className="topbar-indices">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="index-chip">
            <div className="idx-name">–––</div>
            <div className="loading-dots">
              <span />
              <span />
              <span />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="topbar-indices">
      {(data ?? []).map((idx) => {
        const up = idx.change_pct >= 0;
        return (
          <div key={idx.ticker} className="index-chip">
            <div className="idx-name">{idx.name}</div>
            <div className="idx-val mono">{fmt(idx.value, 2)}</div>
            <div className={`idx-chg ${up ? "positive" : "negative"}`}>
              {up ? "▲" : "▼"} {Math.abs(idx.change_pct).toFixed(2)}%
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MoversPanel({
  onSelectSymbol,
}: {
  onSelectSymbol: (symbol: string) => void;
}) {
  const [exchange, setExchange] = useState<string>("NSE");
  const [moverType, setMoverType] = useState<string>("gainers");
  const { data, isLoading, error } = useMovers(exchange, moverType);

  const maxVol =
    Math.max(...(data ?? []).map((m) => m.latest_volume ?? m.volume ?? 0)) || 1;

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div
        className="card-header"
        style={{
          flexDirection: "column",
          gap: 8,
          alignItems: "stretch",
          padding: "12px 16px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span className="card-title">Market Movers</span>
          <div className="tabs" style={{ width: "auto", margin: 0 }}>
            {EXCHANGES.map((ex) => (
              <button
                key={ex}
                className={`tab-btn ${exchange === ex ? "active" : ""}`}
                onClick={() => setExchange(ex)}
                id={`exchange-tab-${ex}`}
                style={{ padding: "3px 8px", fontSize: 10 }}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
        <div className="tabs" style={{ margin: 0 }}>
          {MOVER_TYPES.map((t) => (
            <button
              key={t}
              className={`tab-btn ${moverType === t ? "active" : ""}`}
              onClick={() => setMoverType(t)}
              id={`mover-type-${t}`}
              style={{ padding: "3px 6px", fontSize: 10, flex: 1 }}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div
        className="card-body"
        style={{ padding: 0, maxHeight: 220, overflowY: "auto" }}
      >
        {isLoading && (
          <div className="loader-wrap" style={{ minHeight: 120 }}>
            <div className="spinner" />
            <span>Fetching movers…</span>
          </div>
        )}
        {error && (
          <div className="error-box" style={{ margin: 12 }}>
            ⚠ Failed to load movers.
          </div>
        )}
        {!isLoading && !error && (
          <div className="mover-list">
            {(data ?? []).slice(0, 8).map((m, i) => {
              const price = m.price ?? m.latest_close ?? 0;
              const vol = m.latest_volume ?? m.volume ?? 0;
              const up = m.change_pct >= 0;
              const volPct =
                maxVol > 0 ? Math.min(100, (vol / maxVol) * 100) : 0;

              return (
                <div
                  key={`${m.ticker}-${i}`}
                  className="mover-row"
                  id={`mover-${m.ticker}`}
                  onClick={() => onSelectSymbol(m.ticker)}
                  style={{ cursor: "pointer", padding: "8px 12px" }}
                >
                  <div className="mover-info">
                    <div className="mover-ticker" style={{ fontSize: 12 }}>
                      {m.ticker.replace(".NS", "")}
                    </div>
                    <div className="mover-name" style={{ fontSize: 10 }}>
                      {m.name}
                    </div>
                    {moverType === "volume" && (
                      <div
                        className="vol-bar-track"
                        style={{ marginTop: 2, height: 2 }}
                      >
                        <div
                          className="vol-bar-fill"
                          style={{ width: `${volPct}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: "right" }}>
                    {price > 0 && (
                      <div className="mover-price" style={{ fontSize: 12 }}>
                        {exchange === "CRYPTO"
                          ? `$${fmt(price, price < 1 ? 4 : 2)}`
                          : `₹${fmt(price)}`}
                      </div>
                    )}
                    <div
                      className={`mover-chg ${up ? "positive" : "negative"}`}
                      style={{ fontSize: 10 }}
                    >
                      {up ? "+" : ""}
                      {fmt(m.change_pct, 2)}%
                    </div>
                  </div>
                  <div>
                    <span
                      className={`signal-badge signal-${m.signal_direction ?? "NEUTRAL"}`}
                      style={{ fontSize: 8, padding: "1px 4px" }}
                    >
                      {(m.signal_direction ?? "NEUTRAL").replace("_", " ")}
                    </span>
                  </div>
                </div>
              );
            })}
            {(data ?? []).length === 0 && (
              <div className="no-data" style={{ padding: "16px" }}>
                <span>No data available</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ChartPanel({
  symbol,
  setSymbol,
  intervalIdx,
  setIntervalIdx,
  onPriceChange,
  onSignalChange,
}: {
  symbol: string;
  setSymbol: (symbol: string) => void;
  intervalIdx: number;
  setIntervalIdx: (idx: number) => void;
  onPriceChange?: (
    price: number,
    change: number,
    changePct: number,
    volume: number,
  ) => void;
  onSignalChange?: (signal: AISignal) => void;
}) {
  const [rawSymbol, setRawSymbol] = useState(symbol);

  useEffect(() => {
    setRawSymbol(symbol);
  }, [symbol]);

  const apply = useCallback(() => {
    const s = rawSymbol.trim().toUpperCase() || "RELIANCE.NS";
    setSymbol(s);
  }, [rawSymbol, setSymbol]);

  const { value: interval, period } = INTERVALS[intervalIdx];

  return (
    <div className="card" style={{ flex: "1 1 auto", marginBottom: 0 }}>
      <div
        className="card-header"
        style={{
          padding: "10px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div className="symbol-row" style={{ margin: 0, gap: 10 }}>
          <input
            id="symbol-input"
            className="symbol-input"
            value={rawSymbol}
            onChange={(e) => setRawSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            placeholder="RELIANCE.NS"
            spellCheck={false}
            style={{ width: 130, padding: "5px 10px", fontSize: 12 }}
          />
          <button
            id="go-btn"
            onClick={apply}
            style={{
              background: "var(--accent)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "6px 12px",
              color: "#fff",
              fontWeight: 600,
              fontSize: 12,
              cursor: "pointer",
              fontFamily: "var(--font)",
            }}
          >
            Go
          </button>
          <div className="interval-btns" style={{ display: "flex", gap: 4 }}>
            {INTERVALS.map((iv, i) => (
              <button
                key={iv.label}
                id={`interval-btn-${iv.value}`}
                className={`interval-btn ${i === intervalIdx ? "active" : ""}`}
                onClick={() => setIntervalIdx(i)}
                style={{ padding: "4px 8px", fontSize: 11 }}
              >
                {iv.label}
              </button>
            ))}
          </div>
        </div>
        <span
          className="card-title"
          style={{ whiteSpace: "nowrap", fontSize: 12 }}
        >
          Live Charting
        </span>
      </div>

      <div style={{ padding: "10px", background: "#0a0b0f" }}>
        <div className="chart-wrapper" style={{ position: "relative" }}>
          <CandleChart symbol={symbol} interval={interval} period={period} />
          <StockQuote
            symbol={symbol}
            onPriceChange={onPriceChange}
            onSignalChange={onSignalChange}
          />
        </div>
      </div>
    </div>
  );
}

/* ─────────────────── Watchlist Panel ────────────────────── */
interface WatchlistItem {
  symbol: string;
  price: number | null;
  change_pct: number | null;
  signal: string | null;
  lastUpdated: number;
}

const Sparkline: React.FC<{ prices: number[] }> = ({ prices }) => {
  if (!prices || prices.length < 2) {
    return (
      <div
        style={{
          width: 55,
          height: 16,
          background: "rgba(37,40,54,0.1)",
          borderRadius: 2,
        }}
      />
    );
  }
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 55;
  const height = 16;

  const points = prices
    .map((p, idx) => {
      const x = (idx / (prices.length - 1)) * width;
      const y = height - ((p - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  const isUp = prices[prices.length - 1] >= prices[0];
  const color = isUp ? "var(--green)" : "var(--red)";

  return (
    <svg
      width={width}
      height={height}
      style={{ overflow: "visible", opacity: 0.85 }}
    >
      <polyline fill="none" stroke={color} strokeWidth="1.2" points={points} />
    </svg>
  );
};

function Watchlist({
  onSelectSymbol,
  activeSymbol,
  onStatusChange,
}: {
  onSelectSymbol: (symbol: string) => void;
  activeSymbol: string;
  onStatusChange?: (
    status: "CONNECTED" | "RECONNECTING" | "DISCONNECTED",
  ) => void;
}) {
  const [symbols, setSymbols] = useState<string[]>(() => {
    const saved = localStorage.getItem("neuroquant_watchlist");
    return saved
      ? JSON.parse(saved)
      : ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "BTC-USD"];
  });
  const [items, setItems] = useState<Record<string, WatchlistItem>>({});
  const [newSymbol, setNewSymbol] = useState("");
  const [flashStates, setFlashStates] = useState<
    Record<string, "up" | "down" | null>
  >({});
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});
  const [connectionStatus, setConnectionStatus] = useState<
    "CONNECTED" | "RECONNECTING" | "DISCONNECTED"
  >("DISCONNECTED");

  useEffect(() => {
    localStorage.setItem("neuroquant_watchlist", JSON.stringify(symbols));
  }, [symbols]);

  // Propagate WebSocket connection status to parent
  useEffect(() => {
    if (onStatusChange) {
      onStatusChange(connectionStatus);
    }
  }, [connectionStatus, onStatusChange]);

  // Fetch sequential sparkline history data to avoid rate limit spikes
  useEffect(() => {
    const fetchSparklines = async () => {
      const updatedSparklines = { ...sparklines };
      let updated = false;

      for (const sym of symbols) {
        if (!updatedSparklines[sym]) {
          try {
            const { data } = await axios.get(
              `${API}/global/history/${encodeURIComponent(sym)}`,
              {
                params: { interval: "1h", period: "5d" },
              },
            );
            if (data && data.data) {
              const prices = data.data
                .slice(-24)
                .map((d: any) => Number(d.close));
              updatedSparklines[sym] = prices;
              updated = true;
            }
          } catch (e) {
            console.warn(`Failed to fetch sparkline for ${sym}`, e);
          }
        }
      }
      if (updated) {
        setSparklines(updatedSparklines);
      }
    };
    fetchSparklines();
  }, [symbols]);

  // Connect to websocket with auto-reconnect logic
  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let attempt = 0;

    const connect = () => {
      setConnectionStatus("RECONNECTING");
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/prices`;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setConnectionStatus("CONNECTED");
        attempt = 0;
        socket?.send(JSON.stringify({ action: "subscribe", symbols }));
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const sym = payload.symbol?.toUpperCase();
          if (sym && symbols.includes(sym)) {
            setItems((prev) => {
              const current = prev[sym] || {
                symbol: sym,
                price: null,
                change_pct: null,
                signal: null,
                lastUpdated: 0,
              };
              if (payload.type === "tick") {
                const oldPrice = current.price;
                const newPrice = payload.price;

                if (oldPrice !== null && newPrice !== oldPrice) {
                  setFlashStates((prevFlash) => ({
                    ...prevFlash,
                    [sym]: newPrice > oldPrice ? "up" : "down",
                  }));
                  setTimeout(() => {
                    setFlashStates((prevFlash) => ({
                      ...prevFlash,
                      [sym]: null,
                    }));
                  }, 800);
                }

                // Update sparkline prices in real time (append latest tick price)
                setSparklines((prevSpk) => {
                  const spk = prevSpk[sym];
                  if (spk && spk.length > 0) {
                    const newSpk = [...spk.slice(1), newPrice];
                    return { ...prevSpk, [sym]: newSpk };
                  }
                  return prevSpk;
                });

                return {
                  ...prev,
                  [sym]: {
                    ...current,
                    price: newPrice,
                    change_pct: payload.change_pct,
                    lastUpdated: Date.now(),
                  },
                };
              } else if (payload.type === "signal") {
                return {
                  ...prev,
                  [sym]: {
                    ...current,
                    signal: payload.direction,
                    lastUpdated: Date.now(),
                  },
                };
              }
              return prev;
            });
          }
        } catch (e) {
          console.error("Watchlist ws error:", e);
        }
      };

      socket.onclose = () => {
        setConnectionStatus("DISCONNECTED");
        const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
        attempt++;
        reconnectTimeout = setTimeout(() => {
          connect();
        }, delay);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      if (socket) {
        try {
          socket.send(JSON.stringify({ action: "unsubscribe", symbols }));
        } catch (e) {}
        socket.close();
      }
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [symbols]);

  // Fetch initial quotes for symbols
  useEffect(() => {
    const fetchInitial = async () => {
      for (const sym of symbols) {
        try {
          const { data } = await axios.get(
            `${API}/global/quote/${encodeURIComponent(sym)}`,
          );
          setItems((prev) => ({
            ...prev,
            [sym]: {
              symbol: sym,
              price: data.price,
              change_pct: data.change_pct,
              signal: data.signal?.direction ?? "NEUTRAL",
              lastUpdated: Date.now(),
            },
          }));
        } catch (e) {
          console.warn(`Failed to fetch initial quote for ${sym}:`, e);
        }
      }
    };
    fetchInitial();
  }, [symbols]);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = newSymbol.trim().toUpperCase();
    if (clean && !symbols.includes(clean)) {
      setSymbols((prev) => [...prev, clean]);
      setNewSymbol("");
    }
  };

  const handleRemove = (sym: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSymbols((prev) => prev.filter((s) => s !== sym));
    setItems((prev) => {
      const copy = { ...prev };
      delete copy[sym];
      return copy;
    });
    setSparklines((prev) => {
      const copy = { ...prev };
      delete copy[sym];
      return copy;
    });
  };

  return (
    <div className="card card-glass" style={{ marginBottom: 0 }}>
      <div
        className="card-header"
        style={{
          justifyContent: "space-between",
          padding: "10px 16px",
          flexWrap: "wrap",
          gap: 6,
        }}
      >
        <span className="card-title" style={{ fontSize: 12 }}>
          Watchlist
        </span>
        <form onSubmit={handleAdd} style={{ display: "flex", gap: 6 }}>
          <input
            className="symbol-input"
            style={{ padding: "3px 6px", fontSize: 10, width: 95 }}
            placeholder="ADD SYMBOL"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
          />
          <button
            type="submit"
            className="tab-btn active"
            style={{
              padding: "3px 6px",
              fontSize: 10,
              width: "auto",
              flex: "none",
            }}
          >
            Add
          </button>
        </form>
      </div>
      <div
        className="card-body"
        style={{ padding: 0, maxHeight: 380, overflowY: "auto" }}
      >
        <div className="mover-list">
          {symbols.map((sym) => {
            const item = items[sym];
            const price = item?.price;
            const pct = item?.change_pct ?? 0;
            const up = pct >= 0;
            const sig = item?.signal ?? "NEUTRAL";
            const isStale = item && Date.now() - item.lastUpdated > 45000;
            const flash = flashStates[sym];
            const spkPrices = sparklines[sym] || [];

            return (
              <div
                key={sym}
                className={`mover-row ${activeSymbol === sym ? "active-symbol-row" : ""} ${flash === "up" ? "flash-up" : flash === "down" ? "flash-down" : ""}`}
                onClick={() => onSelectSymbol(sym)}
                style={{
                  cursor: "pointer",
                  padding: "8px 12px",
                  borderBottom: "1px solid rgba(37,40,54,0.2)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    width: "80px",
                    flexShrink: 0,
                  }}
                >
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <span className="mover-ticker" style={{ fontSize: 12 }}>
                      {sym.replace(".NS", "")}
                    </span>
                    {isStale && (
                      <span
                        style={{
                          fontSize: 8,
                          color: "var(--danger)",
                          background: "rgba(255,71,87,0.1)",
                          padding: "1px 3px",
                          borderRadius: 2,
                        }}
                      >
                        Offline
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: 8, color: "var(--text-muted)" }}>
                    {sym.includes(".NS") ? "NSE" : "Crypto/US"}
                  </span>
                </div>

                {/* Mini Sparkline rendering */}
                <div
                  style={{
                    flex: "1 1 auto",
                    display: "flex",
                    justifyContent: "center",
                    padding: "0 8px",
                  }}
                >
                  <Sparkline prices={spkPrices} />
                </div>

                <div
                  style={{ textAlign: "right", width: "70px", flexShrink: 0 }}
                >
                  <div className="mover-price" style={{ fontSize: 12 }}>
                    {price != null ? `₹${fmt(price)}` : "—"}
                  </div>
                  <div
                    className={`mover-chg ${up ? "positive" : "negative"}`}
                    style={{ fontSize: 10 }}
                  >
                    {price != null ? `${up ? "+" : ""}${fmt(pct, 2)}%` : ""}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    width: "75px",
                    justifyContent: "flex-end",
                    flexShrink: 0,
                  }}
                >
                  <span
                    className={`signal-badge signal-${sig}`}
                    style={{ fontSize: 8, padding: "1px 4px" }}
                  >
                    {sig.replace("_", " ")}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => handleRemove(sym, e)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      fontSize: 13,
                      padding: "2px",
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
          {symbols.length === 0 && (
            <div className="no-data" style={{ padding: "16px 0" }}>
              <span>Watchlist is empty</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────── Market Depth Panel ────────────────── */
interface DepthLevel {
  price: number;
  quantity: number;
  orders: number;
}

function MarketDepth({
  price,
  symbol,
}: {
  price: number | null;
  symbol: string;
}) {
  const [depth, setDepth] = useState<{
    bids: DepthLevel[];
    asks: DepthLevel[];
  }>({ bids: [], asks: [] });

  // Generate deterministic ticking L2 market depth based on last traded price
  useEffect(() => {
    if (!price || price <= 0) return;

    // Seed PRNG with symbol and current 10s timeframe to allow L2 depth ticks to sync
    const timeSeed = Math.floor(Date.now() / 10000) * 10;
    let hash = 0;
    const seedStr = symbol + timeSeed;
    for (let i = 0; i < seedStr.length; i++) {
      hash = (hash << 5) - hash + seedStr.charCodeAt(i);
      hash |= 0;
    }
    const seed = Math.abs(hash);

    let current = seed;
    const nextRand = () => {
      current = (current * 1664525 + 1013904223) % 4294967296;
      return current / 4294967296;
    };

    const isNSE = symbol.endsWith(".NS");
    const tickSize = isNSE ? 0.05 : 0.01;
    const spread = Math.max(
      tickSize,
      Math.round((price * 0.0006) / tickSize) * tickSize,
    );

    const bids: DepthLevel[] = [];
    const asks: DepthLevel[] = [];

    const baseQty = Math.round(100 + nextRand() * 2000);

    for (let i = 0; i < 5; i++) {
      const bidPrice = price - spread / 2 - i * tickSize;
      const askPrice = price + spread / 2 + i * tickSize;

      const bidQty = Math.round(
        baseQty * (1.2 - i * 0.15) * (0.85 + nextRand() * 0.3),
      );
      const askQty = Math.round(
        baseQty * (1.2 - i * 0.15) * (0.85 + nextRand() * 0.3),
      );

      bids.push({
        price: Math.round(bidPrice * 100) / 100,
        quantity: Math.max(1, bidQty),
        orders: Math.round(1 + nextRand() * 12),
      });

      asks.push({
        price: Math.round(askPrice * 100) / 100,
        quantity: Math.max(1, askQty),
        orders: Math.round(1 + nextRand() * 12),
      });
    }

    setDepth({ bids, asks });
  }, [price, symbol]);

  if (!price || depth.bids.length === 0) {
    return (
      <div
        className="card card-glass"
        style={{
          padding: "16px",
          textAlign: "center",
          color: "var(--text-muted)",
        }}
      >
        <span>No L2 Depth data available — wait for quote</span>
      </div>
    );
  }

  const maxQty =
    Math.max(
      ...depth.bids.map((b) => b.quantity),
      ...depth.asks.map((a) => a.quantity),
    ) || 1;
  const totalBidQty = depth.bids.reduce((a, b) => a + b.quantity, 0);
  const totalAskQty = depth.asks.reduce((a, b) => a + b.quantity, 0);
  const bidRatio =
    totalBidQty + totalAskQty > 0
      ? (totalBidQty / (totalBidQty + totalAskQty)) * 100
      : 50;

  return (
    <div className="card card-glass" style={{ padding: "12px 14px" }}>
      <div
        className="card-title"
        style={{
          fontSize: 11,
          marginBottom: 8,
          color: "var(--text-secondary)",
        }}
      >
        Market Depth (L2 simulated order book)
      </div>

      {/* Bid/Ask grid table */}
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 11,
          tableLayout: "fixed",
        }}
      >
        <thead>
          <tr
            style={{
              borderBottom: "1px solid rgba(37,40,54,0.5)",
              color: "var(--text-muted)",
              textAlign: "left",
            }}
          >
            <th style={{ padding: "4px 0", width: "14%" }}>Orders</th>
            <th style={{ padding: "4px 0", width: "18%", textAlign: "right" }}>
              Qty
            </th>
            <th
              style={{
                padding: "4px 4px",
                width: "18%",
                textAlign: "right",
                color: "var(--green)",
              }}
            >
              Bid
            </th>

            <th
              style={{ padding: "4px 4px", width: "18%", color: "var(--red)" }}
            >
              Ask
            </th>
            <th style={{ padding: "4px 0", width: "18%", textAlign: "right" }}>
              Qty
            </th>
            <th style={{ padding: "4px 0", width: "14%", textAlign: "right" }}>
              Orders
            </th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 5 }).map((_, i) => {
            const bid = depth.bids[i];
            const ask = depth.asks[i];

            const bidPct = bid ? (bid.quantity / maxQty) * 100 : 0;
            const askPct = ask ? (ask.quantity / maxQty) * 100 : 0;

            return (
              <tr
                key={i}
                style={{ borderBottom: "1px solid rgba(37,40,54,0.15)" }}
              >
                {/* Bid details */}
                <td style={{ padding: "4px 0", color: "var(--text-muted)" }}>
                  {bid?.orders}
                </td>
                <td
                  className="mono"
                  style={{ padding: "4px 0", textAlign: "right" }}
                >
                  {bid?.quantity}
                </td>
                <td
                  className="mono font-bold"
                  style={{
                    padding: "4px 4px",
                    textAlign: "right",
                    color: "var(--green)",
                    background: `linear-gradient(to left, rgba(0, 217, 126, 0.06) ${bidPct}%, transparent ${bidPct}%)`,
                  }}
                >
                  {fmt(bid?.price)}
                </td>

                {/* Ask details */}
                <td
                  className="mono font-bold"
                  style={{
                    padding: "4px 4px",
                    color: "var(--red)",
                    background: `linear-gradient(to right, rgba(255, 71, 87, 0.06) ${askPct}%, transparent ${askPct}%)`,
                  }}
                >
                  {fmt(ask?.price)}
                </td>
                <td
                  className="mono"
                  style={{ padding: "4px 0", textAlign: "right" }}
                >
                  {ask?.quantity}
                </td>
                <td
                  style={{
                    padding: "4px 0",
                    textAlign: "right",
                    color: "var(--text-muted)",
                  }}
                >
                  {ask?.orders}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Depth ratio bar */}
      <div style={{ marginTop: 8, fontSize: 10 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 2,
            color: "var(--text-muted)",
          }}
        >
          <span>
            Total Bid:{" "}
            <span className="mono font-bold" style={{ color: "var(--green)" }}>
              {totalBidQty}
            </span>
          </span>
          <span>
            Total Ask:{" "}
            <span className="mono font-bold" style={{ color: "var(--red)" }}>
              {totalAskQty}
            </span>
          </span>
        </div>
        <div
          style={{
            height: 4,
            background: "var(--red)",
            borderRadius: 2,
            overflow: "hidden",
            display: "flex",
          }}
        >
          <div
            style={{
              width: `${bidRatio}%`,
              background: "var(--green)",
              height: "100%",
              transition: "width 0.3s",
            }}
          />
        </div>
      </div>
    </div>
  );
}

/* ─────────────────── AI Signal explanation Panel ─────────── */
function AISignalPanel({ signal }: { signal: AISignal | null }) {
  if (!signal) {
    return (
      <div
        className="card card-glass"
        style={{
          padding: "16px",
          textAlign: "center",
          color: "var(--text-muted)",
        }}
      >
        <span>No AI Signal generated for symbol</span>
      </div>
    );
  }

  return (
    <div className="card card-glass" style={{ padding: "12px 14px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <span className="card-title" style={{ fontSize: 11, margin: 0 }}>
          AI Ensemble Decision
        </span>
        <span
          className={`signal-badge signal-${signal.direction}`}
          style={{ padding: "2px 8px", fontSize: 10 }}
        >
          {signal.direction.replace("_", " ")}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 8,
        }}
      >
        <span
          style={{
            fontSize: 11,
            color: "var(--text-muted)",
            whiteSpace: "nowrap",
          }}
        >
          Confidence:
        </span>
        <div
          style={{
            height: 6,
            background: "rgba(37,40,54,0.6)",
            borderRadius: 3,
            flex: 1,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              background: signal.direction.includes("BUY")
                ? "var(--green)"
                : signal.direction.includes("SELL")
                  ? "var(--red)"
                  : "var(--text-muted)",
              width: `${Math.round(signal.confidence * 100)}%`,
              transition: "width 0.3s ease",
            }}
          />
        </div>
        <span
          className="mono font-bold"
          style={{ fontSize: 11, minWidth: 28, textAlign: "right" }}
        >
          {Math.round(signal.confidence * 100)}%
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 8,
          margin: "8px 0",
          padding: "6px 8px",
          background: "rgba(37,40,54,0.2)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 9, color: "var(--text-muted)" }}>
            Stop Loss
          </div>
          <div
            className="mono font-bold"
            style={{ fontSize: 10, color: "var(--red)" }}
          >
            ₹{fmt(signal.stopLoss ?? 0)}
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 9, color: "var(--text-muted)" }}>
            Target Price
          </div>
          <div
            className="mono font-bold"
            style={{ fontSize: 10, color: "var(--green)" }}
          >
            ₹{fmt(signal.targetPrice ?? 0)}
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 9, color: "var(--text-muted)" }}>
            Take Profit
          </div>
          <div
            className="mono font-bold"
            style={{ fontSize: 10, color: "var(--accent-light)" }}
          >
            ₹{fmt(signal.takeProfit ?? 0)}
          </div>
        </div>
      </div>

      {signal.rationale && (
        <div
          style={{
            fontSize: 10,
            color: "var(--text-secondary)",
            lineHeight: "1.4",
            fontStyle: "italic",
            borderTop: "1px solid rgba(37,40,54,0.3)",
            paddingTop: 6,
            marginTop: 6,
          }}
        >
          💡 {signal.rationale}
        </div>
      )}
    </div>
  );
}

/* ─────────────────── Tabbed Bottom Console ──────────────── */
interface BottomConsoleProps {
  walletStats: PaperPnL | undefined;
  positions: PaperPosition[] | undefined;
  history: PaperOrder[] | undefined;
  winRate: number;
  wins: number;
  losses: number;
  onSelectSymbol: (symbol: string) => void;
  onQuickClose: (symbol: string, qty: number) => void;
  onCancelOrder: (orderId: string, symbol: string) => void;
  onResetWallet: () => void;
}

function BottomConsole({
  walletStats,
  positions,
  history,
  winRate,
  wins,
  losses,
  onSelectSymbol,
  onQuickClose,
  onCancelOrder,
  onResetWallet,
}: BottomConsoleProps) {
  const [activeTab, setActiveTab] = useState<
    "positions" | "orders" | "history" | "portfolio"
  >("positions");

  const pendingOrders = (history ?? []).filter((o) => o.status === "PENDING");
  const otherOrders = (history ?? []).filter((o) => o.status !== "PENDING");

  return (
    <div className="card card-glass" style={{ minHeight: 260 }}>
      {/* Console Tab header */}
      <div
        className="card-header"
        style={{ padding: "6px 12px", borderBottom: "1px solid var(--border)" }}
      >
        <div className="tabs" style={{ width: "auto", margin: 0 }}>
          <button
            type="button"
            className={`tab-btn ${activeTab === "positions" ? "active" : ""}`}
            onClick={() => setActiveTab("positions")}
          >
            Positions ({positions?.length ?? 0})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "orders" ? "active" : ""}`}
            onClick={() => setActiveTab("orders")}
          >
            Order Book (
            {pendingOrders.length ? `${pendingOrders.length} Pending` : "0"})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "history" ? "active" : ""}`}
            onClick={() => setActiveTab("history")}
          >
            Trade Log ({otherOrders.length})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "portfolio" ? "active" : ""}`}
            onClick={() => setActiveTab("portfolio")}
          >
            Portfolio Dashboard
          </button>
        </div>

        {activeTab === "portfolio" && (
          <button
            type="button"
            onClick={onResetWallet}
            style={{
              background: "rgba(255, 71, 87, 0.1)",
              color: "var(--red)",
              border: "1px solid rgba(255, 71, 87, 0.3)",
              borderRadius: "4px",
              padding: "4px 10px",
              fontSize: 10,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Reset Paper Wallet
          </button>
        )}
      </div>

      {/* Console content body */}
      <div
        className="card-body"
        style={{ padding: "10px 14px", maxHeight: 200, overflowY: "auto" }}
      >
        {/* TAB 1: Positions */}
        {activeTab === "positions" && (
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}
          >
            <thead>
              <tr
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid rgba(37,40,54,0.6)",
                  color: "var(--text-muted)",
                }}
              >
                <th style={{ padding: "4px" }}>Symbol</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>
                  Avg Buy (₹)
                </th>
                <th style={{ padding: "4px", textAlign: "right" }}>
                  Live Price (₹)
                </th>
                <th style={{ padding: "4px", textAlign: "right" }}>
                  Unrealized P&L (₹)
                </th>
                <th style={{ padding: "4px", textAlign: "right" }}>% P&L</th>
                <th style={{ padding: "4px", textAlign: "center" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(positions ?? []).map((pos) => {
                const isPos = pos.unrealized_pnl >= 0;
                return (
                  <tr
                    key={pos.id}
                    style={{ borderBottom: "1px solid rgba(37,40,54,0.25)" }}
                  >
                    <td
                      className="mono font-bold"
                      style={{
                        padding: "6px 4px",
                        cursor: "pointer",
                        color: "var(--accent-light)",
                      }}
                      onClick={() => onSelectSymbol(pos.symbol)}
                    >
                      {pos.symbol}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(pos.quantity, 4)}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(pos.avg_buy_price)}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(pos.current_price)}
                    </td>
                    <td
                      className={`mono ${isPos ? "positive" : "negative"}`}
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {isPos ? "+" : ""}
                      {fmt(pos.unrealized_pnl)}
                    </td>
                    <td
                      className={`mono ${isPos ? "positive" : "negative"}`}
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {isPos ? "+" : ""}
                      {fmt(pos.unrealized_pnl_pct)}%
                    </td>
                    <td style={{ padding: "6px 4px", textAlign: "center" }}>
                      <button
                        type="button"
                        onClick={() => onQuickClose(pos.symbol, pos.quantity)}
                        style={{
                          background: "rgba(255, 71, 87, 0.12)",
                          color: "var(--red)",
                          border: "none",
                          borderRadius: "4px",
                          padding: "3px 8px",
                          fontSize: 10,
                          fontWeight: "bold",
                          cursor: "pointer",
                        }}
                      >
                        Quick Close
                      </button>
                    </td>
                  </tr>
                );
              })}
              {(positions ?? []).length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    style={{
                      padding: "24px 0",
                      textAlign: "center",
                      color: "var(--text-muted)",
                    }}
                  >
                    No open positions. Select a watchlist asset to submit a BUY
                    order on the right.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {/* TAB 2: Orders (Pending & open orderbook) */}
        {activeTab === "orders" && (
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}
          >
            <thead>
              <tr
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid rgba(37,40,54,0.6)",
                  color: "var(--text-muted)",
                }}
              >
                <th style={{ padding: "4px" }}>Time</th>
                <th style={{ padding: "4px" }}>Symbol</th>
                <th style={{ padding: "4px" }}>Side</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>
                  Limit Price (₹)
                </th>
                <th style={{ padding: "4px" }}>Type</th>
                <th style={{ padding: "4px", textAlign: "center" }}>Status</th>
                <th style={{ padding: "4px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {pendingOrders.map((o) => {
                const isBuy = o.side === "BUY";
                return (
                  <tr
                    key={o.id}
                    style={{ borderBottom: "1px solid rgba(37,40,54,0.25)" }}
                  >
                    <td
                      style={{ padding: "6px 4px", color: "var(--text-muted)" }}
                    >
                      {new Date(o.timestamp).toLocaleTimeString()}
                    </td>
                    <td
                      className="mono font-bold"
                      style={{ padding: "6px 4px" }}
                    >
                      {o.symbol}
                    </td>
                    <td
                      className="mono"
                      style={{
                        padding: "6px 4px",
                        color: isBuy ? "var(--green)" : "var(--red)",
                        fontWeight: "bold",
                      }}
                    >
                      {o.side}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(o.quantity, 2)}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(o.price)}
                    </td>
                    <td style={{ padding: "6px 4px" }}>{o.order_type}</td>
                    <td
                      style={{
                        padding: "6px 4px",
                        textAlign: "center",
                        color: "#f59e0b",
                        fontWeight: "bold",
                      }}
                    >
                      {o.status}
                    </td>
                    <td style={{ padding: "6px 4px", textAlign: "center" }}>
                      <button
                        type="button"
                        onClick={() => onCancelOrder(o.id, o.symbol)}
                        style={{
                          background: "rgba(245, 158, 11, 0.12)",
                          color: "#f59e0b",
                          border: "none",
                          borderRadius: "4px",
                          padding: "3px 8px",
                          fontSize: 10,
                          fontWeight: "bold",
                          cursor: "pointer",
                        }}
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                );
              })}
              {pendingOrders.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    style={{
                      padding: "24px 0",
                      textAlign: "center",
                      color: "var(--text-muted)",
                    }}
                  >
                    No pending limit orders. Submit a LIMIT order to place it in
                    the book.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {/* TAB 3: History (Logs) */}
        {activeTab === "history" && (
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}
          >
            <thead>
              <tr
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid rgba(37,40,54,0.6)",
                  color: "var(--text-muted)",
                }}
              >
                <th style={{ padding: "4px" }}>Time</th>
                <th style={{ padding: "4px" }}>Symbol</th>
                <th style={{ padding: "4px" }}>Side</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>
                  Fill Price (₹)
                </th>
                <th style={{ padding: "4px", textAlign: "right" }}>
                  Net Amt (₹)
                </th>
                <th style={{ padding: "4px", textAlign: "center" }}>Status</th>
                <th style={{ padding: "4px", textAlign: "center" }}>
                  Signal Match
                </th>
              </tr>
            </thead>
            <tbody>
              {otherOrders.map((o) => {
                const isBuy = o.side === "BUY";
                const isFilled = o.status === "FILLED";
                return (
                  <tr
                    key={o.id}
                    style={{
                      borderBottom: "1px solid rgba(37,40,54,0.2)",
                      opacity: o.status === "CANCELLED" ? 0.5 : 1,
                    }}
                  >
                    <td
                      style={{ padding: "6px 4px", color: "var(--text-muted)" }}
                    >
                      {new Date(o.timestamp).toLocaleTimeString()}
                    </td>
                    <td
                      className="mono font-bold"
                      style={{ padding: "6px 4px" }}
                    >
                      {o.symbol}
                    </td>
                    <td
                      className="mono"
                      style={{
                        padding: "6px 4px",
                        color: isBuy ? "var(--green)" : "var(--red)",
                        fontWeight: "bold",
                      }}
                    >
                      {o.side}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(o.quantity, 2)}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(o.price)}
                    </td>
                    <td
                      className="mono"
                      style={{ padding: "6px 4px", textAlign: "right" }}
                    >
                      {fmt(Math.abs(o.net_amount))}
                    </td>
                    <td
                      style={{
                        padding: "6px 4px",
                        textAlign: "center",
                        color: isFilled ? "var(--green)" : "var(--red)",
                        fontWeight: "bold",
                      }}
                    >
                      {o.status}
                    </td>
                    <td style={{ padding: "6px 4px", textAlign: "center" }}>
                      {o.status === "FILLED" && o.signal_relation && (
                        <span
                          style={{
                            fontSize: 9,
                            padding: "1px 5px",
                            borderRadius: "3px",
                            fontWeight: "bold",
                            textTransform: "uppercase",
                            background:
                              o.signal_relation === "AGREEMENT"
                                ? "rgba(0, 217, 126, 0.12)"
                                : o.signal_relation === "AGAINST"
                                  ? "rgba(255, 71, 87, 0.12)"
                                  : "rgba(139, 144, 160, 0.12)",
                            color:
                              o.signal_relation === "AGREEMENT"
                                ? "var(--green)"
                                : o.signal_relation === "AGAINST"
                                  ? "var(--red)"
                                  : "var(--text-muted)",
                            border:
                              o.signal_relation === "AGREEMENT"
                                ? "1px solid rgba(0, 217, 126, 0.25)"
                                : o.signal_relation === "AGAINST"
                                  ? "1px solid rgba(255, 71, 87, 0.25)"
                                  : "1px solid rgba(139, 144, 160, 0.25)",
                          }}
                        >
                          {o.signal_relation.toLowerCase()}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {otherOrders.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    style={{
                      padding: "24px 0",
                      textAlign: "center",
                      color: "var(--text-muted)",
                    }}
                  >
                    No execution log history recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {/* TAB 4: Portfolio Summary & Dashboard */}
        {activeTab === "portfolio" && walletStats && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 16,
            }}
          >
            {/* Cash & Equity */}
            <div
              style={{
                background: "rgba(37,40,54,0.2)",
                padding: 12,
                borderRadius: "var(--radius-md)",
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  marginBottom: 2,
                }}
              >
                CASH BALANCE
              </div>
              <div className="mono font-bold" style={{ fontSize: 16 }}>
                ₹{fmt(walletStats.cash_balance)}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-secondary)",
                  marginTop: 4,
                }}
              >
                Holdings: ₹{fmt(walletStats.total_holdings_value)}
              </div>
            </div>

            <div
              style={{
                background: "rgba(37,40,54,0.2)",
                padding: 12,
                borderRadius: "var(--radius-md)",
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  marginBottom: 2,
                }}
              >
                PORTFOLIO EQUITY
              </div>
              <div
                className="mono font-bold"
                style={{ fontSize: 16, color: "var(--accent-light)" }}
              >
                ₹{fmt(walletStats.total_equity)}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color:
                    walletStats.unrealized_pnl >= 0
                      ? "var(--green)"
                      : "var(--red)",
                  marginTop: 4,
                }}
              >
                MTM: {walletStats.unrealized_pnl >= 0 ? "+" : ""}₹
                {fmt(walletStats.unrealized_pnl)}
              </div>
            </div>

            {/* Performance Stats */}
            <div
              style={{
                background: "rgba(37,40,54,0.2)",
                padding: 12,
                borderRadius: "var(--radius-md)",
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  marginBottom: 2,
                }}
              >
                SIMULATED WIN RATE
              </div>
              <div
                className="mono font-bold"
                style={{
                  fontSize: 16,
                  color:
                    winRate >= 50
                      ? "var(--green)"
                      : winRate > 0
                        ? "var(--red)"
                        : "var(--text)",
                }}
              >
                {winRate.toFixed(1)}%
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  marginTop: 4,
                }}
              >
                Trades: {wins}W - {losses}L
              </div>
            </div>

            {/* Daily risk limit and circuit breaker */}
            <div
              style={{
                background: "rgba(37,40,54,0.2)",
                padding: 12,
                borderRadius: "var(--radius-md)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 2,
                }}
              >
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  DAILY RISK GATE
                </span>
                {walletStats.circuit_breaker_triggered && (
                  <span
                    style={{
                      fontSize: 8,
                      background: "var(--red)",
                      color: "#fff",
                      padding: "1px 4px",
                      borderRadius: 2,
                      fontWeight: 700,
                    }}
                  >
                    BLOCKED
                  </span>
                )}
              </div>
              <div
                className="mono font-bold"
                style={{
                  fontSize: 15,
                  color: walletStats.circuit_breaker_triggered
                    ? "var(--red)"
                    : "var(--text)",
                }}
              >
                ₹{fmt(walletStats.daily_realized_loss)} / ₹
                {fmt(walletStats.daily_loss_limit)}
              </div>
              <div
                style={{
                  height: 3,
                  background: "rgba(37,40,54,0.6)",
                  borderRadius: 1.5,
                  marginTop: 6,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    background: "var(--red)",
                    width: `${Math.min(100, (walletStats.daily_realized_loss / walletStats.daily_loss_limit) * 100)}%`,
                    transition: "width 0.3s",
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─────────────────── Order Form Component ───────────────── */
function OrderEntryForm({
  activeSymbol,
  livePrice,
  walletStats,
  onSubmitOrder,
  orderPending,
}: {
  activeSymbol: string;
  livePrice: number | null;
  walletStats: PaperPnL | undefined;
  onSubmitOrder: (payload: any) => void;
  orderPending: boolean;
}) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [quantity, setQuantity] = useState<number>(1);
  const [limitPrice, setLimitPrice] = useState<string>("");

  // Sync limit price to live price if user switches to LIMIT
  useEffect(() => {
    if (livePrice && !limitPrice) {
      setLimitPrice(livePrice.toFixed(2));
    }
  }, [livePrice, orderType]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const payload: any = {
      symbol: activeSymbol,
      side: side,
      quantity: Number(quantity),
      order_type: orderType,
    };

    if (orderType === "LIMIT") {
      payload.limit_price = Number(limitPrice);
    }

    onSubmitOrder(payload);
  };

  const tradePrice =
    orderType === "LIMIT"
      ? Number(limitPrice) || livePrice || 0
      : livePrice || 0;
  const grossVal = quantity * tradePrice;

  // Calculate simulated friction/charges (0.05% brokerage, 0.1% STT, 0.05% slippage for buy)
  const estCharges =
    side === "BUY"
      ? min(20, grossVal * 0.0005) + grossVal * 0.001 + grossVal * 0.0005
      : min(20, grossVal * 0.0005) + grossVal * 0.001 + grossVal * 0.0005;
  const estTotal =
    side === "BUY" ? grossVal + estCharges : grossVal - estCharges;

  function min(a: number, b: number) {
    return a < b ? a : b;
  }

  // Guards
  const exceedsRiskLimit =
    walletStats && grossVal > 0.5 * walletStats.total_equity;
  const blockBuy = side === "BUY" && walletStats?.circuit_breaker_triggered;
  const insufficientFunds =
    side === "BUY" && walletStats && estTotal > walletStats.cash_balance;

  return (
    <div className="card card-glass" style={{ padding: "12px 14px" }}>
      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", flexDirection: "column", gap: 10 }}
      >
        {/* Buy/Sell tab buttons */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => setSide("BUY")}
            style={{
              flex: 1,
              background:
                side === "BUY" ? "var(--green)" : "rgba(37,40,54,0.3)",
              color: side === "BUY" ? "#0a0b0f" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "6px 0",
              fontWeight: 700,
              fontSize: 12,
              cursor: "pointer",
              transition: "background 0.2s",
            }}
          >
            BUY
          </button>
          <button
            type="button"
            onClick={() => setSide("SELL")}
            style={{
              flex: 1,
              background: side === "SELL" ? "var(--red)" : "rgba(37,40,54,0.3)",
              color: side === "SELL" ? "#fff" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "6px 0",
              fontWeight: 700,
              fontSize: 12,
              cursor: "pointer",
              transition: "background 0.2s",
            }}
          >
            SELL
          </button>
        </div>

        {/* Order execution type selector */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Order Type:
          </span>
          <div className="tabs" style={{ width: "auto", margin: 0 }}>
            <button
              type="button"
              className={`tab-btn ${orderType === "MARKET" ? "active" : ""}`}
              onClick={() => setOrderType("MARKET")}
              style={{ padding: "3px 8px", fontSize: 10 }}
            >
              Market
            </button>
            <button
              type="button"
              className={`tab-btn ${orderType === "LIMIT" ? "active" : ""}`}
              onClick={() => setOrderType("LIMIT")}
              style={{ padding: "3px 8px", fontSize: 10 }}
            >
              Limit
            </button>
          </div>
        </div>

        {/* Inputs */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: orderType === "LIMIT" ? "1fr 1fr" : "1fr",
            gap: 8,
          }}
        >
          <div>
            <label
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                display: "block",
                marginBottom: 2,
              }}
            >
              Quantity
            </label>
            <input
              id="quantity-input"
              type="number"
              min="0.0001"
              step="any"
              className="symbol-input"
              style={{ width: "100%", padding: "5px 8px", fontSize: 12 }}
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              required
            />
          </div>
          {orderType === "LIMIT" && (
            <div>
              <label
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  display: "block",
                  marginBottom: 2,
                }}
              >
                Limit Price (₹)
              </label>
              <input
                type="number"
                min="0.01"
                step="0.05"
                className="symbol-input"
                style={{ width: "100%", padding: "5px 8px", fontSize: 12 }}
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
                required
              />
            </div>
          )}
        </div>

        {/* Dynamic transaction estimator */}
        {tradePrice > 0 && (
          <div
            style={{
              background: "rgba(37,40,54,0.15)",
              borderRadius: "var(--radius-sm)",
              padding: "6px 8px",
              fontSize: 10,
              color: "var(--text-secondary)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 3,
              }}
            >
              <span>Est. Value:</span>
              <span className="mono">₹{fmt(grossVal)}</span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 3,
              }}
            >
              <span>Brokerage + STT + Slip:</span>
              <span className="mono">₹{fmt(estCharges)}</span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                borderTop: "1px solid rgba(37,40,54,0.3)",
                paddingTop: 4,
                fontWeight: "bold",
              }}
            >
              <span>
                {side === "BUY" ? "Estimated Outflow:" : "Estimated Inflow:"}
              </span>
              <span
                className="mono"
                style={{
                  color: side === "BUY" ? "var(--green)" : "var(--red)",
                }}
              >
                ₹{fmt(estTotal)}
              </span>
            </div>
          </div>
        )}

        {/* Warnings and alerts */}
        {exceedsRiskLimit && (
          <div
            className="error-box"
            style={{ fontSize: 9, padding: "4px 8px", borderRadius: 4 }}
          >
            ⚠ Risk Gate Warning: Order value exceeds 50% of portfolio equity
            limit.
          </div>
        )}
        {insufficientFunds && (
          <div
            className="error-box"
            style={{ fontSize: 9, padding: "4px 8px", borderRadius: 4 }}
          >
            ⚠ Insufficient Funds: Outflow exceeds current cash balance.
          </div>
        )}
        {blockBuy && (
          <div
            className="error-box"
            style={{ fontSize: 9, padding: "4px 8px", borderRadius: 4 }}
          >
            🚨 Blocked: Daily Loss Circuit Breaker Triggered.
          </div>
        )}

        <button
          type="submit"
          disabled={
            orderPending ||
            blockBuy ||
            insufficientFunds ||
            exceedsRiskLimit ||
            !livePrice
          }
          style={{
            width: "100%",
            background: side === "BUY" ? "var(--green)" : "var(--red)",
            color: side === "BUY" ? "#0a0b0f" : "#fff",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "8px 0",
            fontWeight: 700,
            fontSize: 13,
            cursor: "pointer",
            marginTop: 4,
            opacity:
              orderPending ||
              blockBuy ||
              insufficientFunds ||
              exceedsRiskLimit ||
              !livePrice
                ? 0.4
                : 1,
            transition: "opacity 0.2s",
          }}
        >
          {orderPending ? "Executing..." : `Place ${side} ${orderType} Order`}
        </button>
      </form>
    </div>
  );
}

/* ───────────────────────── App Shell ──────────────────────── */
function Dashboard() {
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE.NS");
  const [searchVal, setSearchVal] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<
    "CONNECTED" | "RECONNECTING" | "DISCONNECTED"
  >("DISCONNECTED");
  const [intervalIdx, setIntervalIdx] = useState(4); // default 1D (Daily)

  // Real-time ticking values from active symbol
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [liveSignal, setLiveSignal] = useState<AISignal | null>(null);

  // Alert feedback
  const [feedback, setFeedback] = useState<{
    text: string;
    isError: boolean;
  } | null>(null);

  // Queries
  const { data: walletStats, refetch: refetchPnL } = useQuery<PaperPnL>({
    queryKey: ["paper-pnl"],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/paper-trade/pnl`);
      return data;
    },
    refetchInterval: 5000, // Refresh MTM mark-to-market calculations
  });

  const { data: positions, refetch: refetchPositions } = useQuery<
    PaperPosition[]
  >({
    queryKey: ["paper-positions"],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/paper-trade/positions`);
      return data;
    },
    refetchInterval: 5000,
  });

  const { data: history, refetch: refetchHistory } = useQuery<PaperOrder[]>({
    queryKey: ["paper-history"],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/paper-trade/history`);
      return data;
    },
    refetchInterval: 7500,
  });

  // Mutators
  const orderMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await axios.post(`${API}/paper-trade/order`, payload);
      return data;
    },
    onSuccess: (data) => {
      setFeedback({
        text: `Order executed: ${data.order.side} ${data.order.quantity} ${data.order.symbol} @ ₹${fmt(data.order.price)}`,
        isError: false,
      });
      refetchPnL();
      refetchPositions();
      refetchHistory();
    },
    onError: (err: any) => {
      const errMsg =
        err.response?.data?.detail?.message || err.message || "Order failed";
      setFeedback({ text: errMsg, isError: true });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async ({
      orderId,
      symbol,
    }: {
      orderId: string;
      symbol: string;
    }) => {
      const { data } = await axios.post(
        `${API}/paper-trade/cancel/${orderId}?symbol=${symbol}`,
      );
      return data;
    },
    onSuccess: () => {
      setFeedback({ text: "Order cancelled successfully.", isError: false });
      refetchPnL();
      refetchPositions();
      refetchHistory();
    },
    onError: (err: any) => {
      const errMsg =
        err.response?.data?.detail?.message || err.message || "Cancel failed";
      setFeedback({ text: errMsg, isError: true });
    },
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      const { data } = await axios.post(`${API}/paper-trade/reset`);
      return data;
    },
    onSuccess: () => {
      setFeedback({
        text: "Paper trading account reset successfully.",
        isError: false,
      });
      refetchPnL();
      refetchPositions();
      refetchHistory();
    },
    onError: (err: any) => {
      setFeedback({ text: err.message || "Reset failed", isError: true });
    },
  });

  // Hotkey keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "SELECT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }

      // Alt + Timeframe switcher
      if (e.altKey) {
        if (e.key === "1") {
          setIntervalIdx(0); // 1m
        } else if (e.key === "5") {
          setIntervalIdx(1); // 5m
        } else if (e.key === "3") {
          setIntervalIdx(2); // 15m
        } else if (e.key === "d" || e.key === "D") {
          setIntervalIdx(4); // 1D
        }
      } else {
        // B / S to focus order panel
        if (e.key.toLowerCase() === "b") {
          e.preventDefault();
          document.getElementById("quantity-input")?.focus();
        } else if (e.key.toLowerCase() === "s") {
          e.preventDefault();
          document.getElementById("quantity-input")?.focus();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Compute stats for portfolio dashboard tab
  let wins = 0;
  let losses = 0;
  const symbolBuys: Record<string, { qty: number; cost: number }> = {};
  const sortedHistory = history ? [...history].reverse() : [];

  sortedHistory.forEach((o) => {
    if (o.status !== "FILLED") return;
    const sym = o.symbol;
    if (o.side === "BUY") {
      if (!symbolBuys[sym]) symbolBuys[sym] = { qty: 0, cost: 0 };
      symbolBuys[sym].qty += o.quantity;
      symbolBuys[sym].cost += o.net_amount;
    } else if (o.side === "SELL") {
      const buyState = symbolBuys[sym];
      if (buyState && buyState.qty > 0) {
        const avgBuyPrice = buyState.cost / buyState.qty;
        const costOfSold = avgBuyPrice * o.quantity;
        const profit = o.net_amount - costOfSold;
        if (profit > 0) wins++;
        else losses++;
        buyState.qty -= o.quantity;
        buyState.cost -= avgBuyPrice * o.quantity;
      }
    }
  });
  const winRate = wins + losses > 0 ? (wins / (wins + losses)) * 100 : 0;

  // Determine market status (NSE/BSE India Standard Time UTC+5:30)
  const getMarketStatus = (): {
    status: "OPEN" | "CLOSED" | "PRE-OPEN";
    label: string;
  } => {
    // Current IST time
    const d = new Date();
    const utc = d.getTime() + d.getTimezoneOffset() * 60000;
    const istOffset = 5.5;
    const istTime = new Date(utc + 3600000 * istOffset);

    const day = istTime.getDay(); // 0 Sunday, 6 Saturday
    const hours = istTime.getHours();
    const mins = istTime.getMinutes();
    const timeVal = hours * 100 + mins;

    if (day === 0 || day === 6) {
      return { status: "CLOSED", label: "Market Closed (Weekend)" };
    }

    if (timeVal >= 900 && timeVal < 915) {
      return { status: "PRE-OPEN", label: "Pre-Open Session" };
    }

    if (timeVal >= 915 && timeVal <= 1530) {
      return { status: "OPEN", label: "Market Open" };
    }

    return { status: "CLOSED", label: "Market Closed" };
  };
  const marketStatus = getMarketStatus();

  const handlePriceChange = useCallback((price: number) => {
    setLivePrice(price);
  }, []);

  const handleSignalChange = useCallback((signal: AISignal) => {
    setLiveSignal(signal);
  }, []);

  const handleSearchSubmit = () => {
    if (searchVal.trim()) {
      setActiveSymbol(searchVal.trim().toUpperCase());
      setSearchVal("");
    }
  };

  return (
    <div className="app">
      {/* ── Topbar ── */}
      <header className="topbar" role="banner">
        <a className="topbar-brand" href="/" id="brand-logo">
          <div className="brand-icon">📈</div>
          <span>QuantEdge</span>
        </a>

        {/* Index prices strip */}
        <IndexChips />

        {/* Topbar Actions / Status indicators */}
        <div
          className="topbar-actions"
          style={{ display: "flex", alignItems: "center", gap: 14 }}
        >
          {/* Connection Status Pill */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background:
                  connectionStatus === "CONNECTED"
                    ? "var(--green)"
                    : connectionStatus === "RECONNECTING"
                      ? "#f59e0b"
                      : "var(--red)",
                boxShadow:
                  connectionStatus === "CONNECTED"
                    ? "0 0 8px var(--green)"
                    : "0 0 8px var(--red)",
              }}
            />
            <span
              style={{
                fontSize: 10,
                fontWeight: 600,
                color: "var(--text-secondary)",
              }}
            >
              {connectionStatus === "CONNECTED"
                ? "Live"
                : connectionStatus === "RECONNECTING"
                  ? "Reconnecting"
                  : "Offline"}
            </span>
          </div>

          {/* Market open indicator */}
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              background:
                marketStatus.status === "OPEN"
                  ? "rgba(0,217,126,0.1)"
                  : "rgba(255,71,87,0.1)",
              color:
                marketStatus.status === "OPEN" ? "var(--green)" : "var(--red)",
              padding: "2px 8px",
              borderRadius: 4,
              whiteSpace: "nowrap",
            }}
          >
            {marketStatus.label}
          </div>

          {/* Portfolio quick stats snippet */}
          {walletStats && (
            <div
              style={{
                fontSize: 11,
                color: "var(--text-secondary)",
                borderLeft: "1px solid var(--border)",
                paddingLeft: 12,
                display: "flex",
                gap: 10,
              }}
            >
              <div>
                Equity:{" "}
                <span
                  className="mono font-bold"
                  style={{ color: "var(--accent-light)" }}
                >
                  ₹{fmt(walletStats.total_equity)}
                </span>
              </div>
              <div>
                Today P&L:{" "}
                <span
                  className={`mono ${walletStats.unrealized_pnl >= 0 ? "positive" : "negative"}`}
                >
                  {walletStats.unrealized_pnl >= 0 ? "+" : ""}₹
                  {fmt(walletStats.unrealized_pnl)}
                </span>
              </div>
            </div>
          )}

          <div className="search-wrap">
            <span className="search-icon">🔍</span>
            <input
              id="global-search"
              className="search-input"
              placeholder="Search symbol (TCS.NS)…"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearchSubmit();
              }}
              spellCheck={false}
              style={{ width: 180 }}
            />
          </div>
        </div>
      </header>

      {/* ── Info Banner for Paper Trading & Data Delay ── */}
      <div
        style={{
          background: "rgba(99, 102, 241, 0.06)",
          borderBottom: "1px solid rgba(99, 102, 241, 0.15)",
          padding: "6px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: 11,
          color: "#8b90a0",
          fontFamily: "var(--font)",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              color: "var(--green)",
              fontWeight: "bold",
              background: "rgba(0,217,126,0.1)",
              padding: "1px 6px",
              borderRadius: 3,
              fontSize: 9,
            }}
          >
            PAPER TRADING
          </span>
          <span>
            Simulated order matching on live market prices. No real capital
            risk.
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color: "#f59e0b", fontWeight: "bold" }}>
            ⚠️ Free-Tier Data Delay:
          </span>
          <span>
            Feed is delayed by 15–20 minutes. Simulated fills are adjusted
            accordingly.
          </span>
        </div>
      </div>

      {/* ── 3-Column main layout ── */}
      <main className="main-layout">
        {/* COLUMN 1: Watchlist Sidebar */}
        <div className="left-sidebar">
          <ErrorBoundary>
            <Watchlist
              activeSymbol={activeSymbol}
              onSelectSymbol={setActiveSymbol}
              onStatusChange={setConnectionStatus}
            />
          </ErrorBoundary>
          <ErrorBoundary>
            <MoversPanel onSelectSymbol={setActiveSymbol} />
          </ErrorBoundary>
        </div>

        {/* COLUMN 2: Center Main Panel (Chart + Console) */}
        <div className="center-column">
          <ErrorBoundary>
            <ChartPanel
              symbol={activeSymbol}
              setSymbol={setActiveSymbol}
              intervalIdx={intervalIdx}
              setIntervalIdx={setIntervalIdx}
              onPriceChange={handlePriceChange}
              onSignalChange={handleSignalChange}
            />
          </ErrorBoundary>

          {/* Feedback overlay box */}
          {feedback && (
            <div
              style={{
                fontSize: 12,
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                background: feedback.isError
                  ? "rgba(255,71,87,0.12)"
                  : "rgba(0,217,126,0.12)",
                color: feedback.isError ? "var(--red)" : "var(--green)",
                border: feedback.isError
                  ? "1px solid rgba(255,71,87,0.25)"
                  : "1px solid rgba(0,217,126,0.25)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>{feedback.text}</span>
              <button
                type="button"
                onClick={() => setFeedback(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  fontWeight: "bold",
                }}
              >
                Close
              </button>
            </div>
          )}

          <ErrorBoundary>
            <BottomConsole
              walletStats={walletStats}
              positions={positions}
              history={history}
              winRate={winRate}
              wins={wins}
              losses={losses}
              onSelectSymbol={setActiveSymbol}
              onQuickClose={(symbol, qty) =>
                orderMutation.mutate({
                  symbol,
                  side: "SELL",
                  quantity: qty,
                  order_type: "MARKET",
                })
              }
              onCancelOrder={(orderId, symbol) =>
                cancelMutation.mutate({ orderId, symbol })
              }
              onResetWallet={() => resetMutation.mutate()}
            />
          </ErrorBoundary>
        </div>

        {/* COLUMN 3: Right Sidebar Panel (Depth + Signal + Trade Form) */}
        <div className="right-sidebar">
          <ErrorBoundary>
            <MarketDepth price={livePrice} symbol={activeSymbol} />
          </ErrorBoundary>

          <ErrorBoundary>
            <AISignalPanel signal={liveSignal} />
          </ErrorBoundary>

          <ErrorBoundary>
            <OrderEntryForm
              activeSymbol={activeSymbol}
              livePrice={livePrice}
              walletStats={walletStats}
              onSubmitOrder={(payload) => orderMutation.mutate(payload)}
              orderPending={orderMutation.isPending}
            />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
