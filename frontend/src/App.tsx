import React, { useState, useCallback, useEffect } from 'react';
import { QueryClient, QueryClientProvider, useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { CandleChart, StockQuote } from './components/ForecastChart';
import './index.css';

/* ───────────────────────── Error Boundary ────────────────────── */
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info);
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="error-box" style={{ margin: 16 }}>
          ⚠ Something went wrong rendering this section. Please refresh the page.
        </div>
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

const API = '/api/v1';

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

/* ───────────────────────── Formatters ─────────────────────── */
function fmt(n: number, d = 2) {
  if (n == null || isNaN(n)) return '—';
  return n.toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
}

// function fmtChg(pct: number) {
//   const up = pct >= 0;
//   const cls = up ? 'positive' : 'negative';
//   const arrow = up ? '▲' : '▼';
//   return <span className={`mono ${cls}`}>{arrow} {up ? '+' : ''}{fmt(pct, 2)}%</span>;
// }

/* ───────────────────────── Hooks ──────────────────────────── */
function useIndices() {
  return useQuery<IndexData[]>({
    queryKey: ['indices'],
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
    queryKey: ['movers', exchange, type],
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
  { label: '1m',  value: '1m',  period: '1d' },
  { label: '5m',  value: '5m',  period: '5d' },
  { label: '15m', value: '15m', period: '1mo' },
  { label: '1H',  value: '1h',  period: '1mo' },
  { label: '1D',  value: '1d',  period: '1y' },
  { label: '1W',  value: '1w',  period: '5y' },
];

const EXCHANGES = ['NSE', 'NYSE', 'CRYPTO'] as const;
const MOVER_TYPES = ['gainers', 'losers', 'volume', 'momentum'] as const;

function IndexChips() {
  const { data, isLoading } = useIndices();

  if (isLoading) {
    return (
      <div className="topbar-indices">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="index-chip">
            <div className="idx-name">–––</div>
            <div className="loading-dots">
              <span /><span /><span />
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
            <div className={`idx-chg ${up ? 'positive' : 'negative'}`}>
              {up ? '▲' : '▼'} {Math.abs(idx.change_pct).toFixed(2)}%
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MoversPanel({ onSelectSymbol }: { onSelectSymbol: (symbol: string) => void }) {
  const [exchange, setExchange] = useState<string>('NSE');
  const [moverType, setMoverType] = useState<string>('gainers');
  const { data, isLoading, error } = useMovers(exchange, moverType);

  const maxVol = Math.max(...(data ?? []).map((m) => m.latest_volume ?? m.volume ?? 0)) || 1;

  return (
    <div className="card">
      <div className="card-header" style={{ flexDirection: 'column', gap: 10, alignItems: 'stretch' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">Market Movers</span>
          <div className="tabs" style={{ width: 'auto' }}>
            {EXCHANGES.map((ex) => (
              <button
                key={ex}
                className={`tab-btn ${exchange === ex ? 'active' : ''}`}
                onClick={() => setExchange(ex)}
                id={`exchange-tab-${ex}`}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
        <div className="tabs">
          {MOVER_TYPES.map((t) => (
            <button
              key={t}
              className={`tab-btn ${moverType === t ? 'active' : ''}`}
              onClick={() => setMoverType(t)}
              id={`mover-type-${t}`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="card-body" style={{ padding: 0 }}>
        {isLoading && (
          <div className="loader-wrap" style={{ minHeight: 200 }}>
            <div className="spinner" />
            <span>Fetching movers…</span>
          </div>
        )}
        {error && (
          <div className="error-box" style={{ margin: 16 }}>
            ⚠ Failed to load movers. Backend may be offline.
          </div>
        )}
        {!isLoading && !error && (
          <div className="mover-list">
            {(data ?? []).slice(0, 15).map((m, i) => {
              const price = m.price ?? m.latest_close ?? 0;
              const vol   = m.latest_volume ?? m.volume ?? 0;
              const up = m.change_pct >= 0;
              const volPct = maxVol > 0 ? Math.min(100, (vol / maxVol) * 100) : 0;

              return (
                <div
                  key={`${m.ticker}-${i}`}
                  className="mover-row"
                  id={`mover-${m.ticker}`}
                  onClick={() => onSelectSymbol(m.ticker)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="mover-rank">{i + 1}</div>
                  <div className="mover-info">
                    <div className="mover-ticker">{m.ticker.replace('.NS', '')}</div>
                    <div className="mover-name">{m.name}</div>
                    {moverType === 'volume' && (
                      <div className="vol-bar-track" style={{ marginTop: 4 }}>
                        <div className="vol-bar-fill" style={{ width: `${volPct}%` }} />
                      </div>
                    )}
                  </div>
                  <div>
                    {price > 0 && (
                      <div className="mover-price">
                        {exchange === 'CRYPTO' ? `$${fmt(price, price < 1 ? 4 : 2)}` : `₹${fmt(price)}`}
                      </div>
                    )}
                    <div className={`mover-chg ${up ? 'positive' : 'negative'}`}>
                      {up ? '+' : ''}{fmt(m.change_pct, 2)}%
                    </div>
                  </div>
                  <div>
                    <span className={`signal-badge signal-${m.signal_direction ?? 'NEUTRAL'}`} style={{ fontSize: 9 }}>
                      {(m.signal_direction ?? 'NEUTRAL').replace('_', ' ')}
                    </span>
                  </div>
                </div>
              );
            })}
            {(data ?? []).length === 0 && (
              <div className="no-data">
                <span style={{ fontSize: 24 }}>📊</span>
                <span>No data available</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ChartPanel({ symbol, setSymbol }: { symbol: string; setSymbol: (symbol: string) => void }) {
  const [rawSymbol, setRawSymbol] = useState(symbol);
  const [intervalIdx, setIntervalIdx] = useState(4); // default 1D

  // Keep input aligned if symbol changes externally (e.g. clicking movers)
  useEffect(() => {
    setRawSymbol(symbol);
  }, [symbol]);

  const apply = useCallback(() => {
    const s = rawSymbol.trim().toUpperCase() || 'RELIANCE.NS';
    setSymbol(s);
  }, [rawSymbol, setSymbol]);

  const { value: interval, period } = INTERVALS[intervalIdx];

  return (
    <div className="card" style={{ flex: '1 1 auto', marginBottom: 0 }}>
      <div className="card-header">
        <div className="symbol-row" style={{ margin: 0, gap: 12 }}>
          <input
            id="symbol-input"
            className="symbol-input"
            value={rawSymbol}
            onChange={(e) => setRawSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && apply()}
            placeholder="RELIANCE.NS"
            spellCheck={false}
          />
          <button
            id="go-btn"
            onClick={apply}
            style={{
              background: 'var(--accent)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              padding: '8px 16px',
              color: '#fff',
              fontWeight: 600,
              fontSize: 13,
              cursor: 'pointer',
              transition: 'opacity 0.15s',
              fontFamily: 'var(--font)',
            }}
          >
            Go
          </button>
          <div className="interval-btns">
            {INTERVALS.map((iv, i) => (
              <button
                key={iv.label}
                id={`interval-btn-${iv.value}`}
                className={`interval-btn ${i === intervalIdx ? 'active' : ''}`}
                onClick={() => setIntervalIdx(i)}
              >
                {iv.label}
              </button>
            ))}
          </div>
        </div>
        <span className="card-title" style={{ whiteSpace: 'nowrap' }}>Candlestick Chart</span>
      </div>

      <div style={{ padding: '16px 20px' }}>
        <div className="chart-wrapper" style={{ position: 'relative' }}>
          <CandleChart symbol={symbol} interval={interval} period={period} />
          <StockQuote symbol={symbol} />
        </div>
      </div>
    </div>
  );
}

/* ─────────────────── Paper Trading Panel ────────────────── */
function TradingPanel({ activeSymbol }: { activeSymbol: string }) {
  // const queryClient = useQueryClient();
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [quantity, setQuantity] = useState<number>(1);
  const [limitPrice, setLimitPrice] = useState<string>('');
  
  // Feedback messages
  const [alertMsg, setAlertMsg] = useState<{ text: string; isError: boolean } | null>(null);

  // Queries for Wallet and Open Positions
  const { data: walletStats, refetch: refetchPnL } = useQuery<PaperPnL>({
    queryKey: ['paper-pnl'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/paper-trade/pnl`);
      return data;
    },
    refetchInterval: 5000, // Sync P&L mark-to-market every 5s
  });

  const { data: positions, refetch: refetchPositions } = useQuery<PaperPosition[]>({
    queryKey: ['paper-positions'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/paper-trade/positions`);
      return data;
    },
    refetchInterval: 5000, // Sync unrealized P&L MTM every 5s
  });

  const { data: history, refetch: refetchHistory } = useQuery<PaperOrder[]>({
    queryKey: ['paper-history'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/paper-trade/history`);
      return data;
    },
    refetchInterval: 10000,
  });

  // Mutators
  const orderMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await axios.post(`${API}/paper-trade/order`, payload);
      return data;
    },
    onSuccess: (data) => {
      setAlertMsg({ text: `Order executed successfully: ${data.order.side} ${data.order.quantity} of ${data.order.symbol} @ ₹${fmt(data.order.price)}`, isError: false });
      refetchPnL();
      refetchPositions();
      refetchHistory();
    },
    onError: (err: any) => {
      const errMsg = err.response?.data?.detail?.message || err.message || 'Order submission failed';
      setAlertMsg({ text: errMsg, isError: true });
    }
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      const { data } = await axios.post(`${API}/paper-trade/reset`);
      return data;
    },
    onSuccess: () => {
      setAlertMsg({ text: 'Paper trading account reset successfully.', isError: false });
      refetchPnL();
      refetchPositions();
      refetchHistory();
    },
    onError: (err: any) => {
      setAlertMsg({ text: err.message || 'Reset failed', isError: true });
    }
  });

  const handleOrderSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAlertMsg(null);

    const payload: any = {
      symbol: activeSymbol,
      side: side,
      quantity: Number(quantity),
      order_type: orderType,
    };

    if (orderType === 'LIMIT') {
      if (!limitPrice || isNaN(Number(limitPrice))) {
        setAlertMsg({ text: 'Please specify a valid limit price', isError: true });
        return;
      }
      payload.limit_price = Number(limitPrice);
    }

    orderMutation.mutate(payload);
  };

  const handleQuickClose = (symbol: string, qty: number) => {
    setAlertMsg(null);
    orderMutation.mutate({
      symbol,
      side: 'SELL',
      quantity: qty,
      order_type: 'MARKET'
    });
  };

  // Client-side Win Rate Calculation
  let wins = 0;
  let losses = 0;
  const symbolBuys: Record<string, { qty: number, cost: number }> = {};
  const sortedHistory = history ? [...history].reverse() : [];
  
  sortedHistory.forEach(o => {
    if (o.status !== 'FILLED') return;
    const sym = o.symbol;
    if (o.side === 'BUY') {
      if (!symbolBuys[sym]) symbolBuys[sym] = { qty: 0, cost: 0 };
      symbolBuys[sym].qty += o.quantity;
      symbolBuys[sym].cost += o.net_amount; // cash outflow
    } else if (o.side === 'SELL') {
      const buyState = symbolBuys[sym];
      if (buyState && buyState.qty > 0) {
        const avgBuyPrice = buyState.cost / buyState.qty;
        const costOfSold = avgBuyPrice * o.quantity;
        const profit = o.net_amount - costOfSold; // o.net_amount for SELL is positive cash inflow
        if (profit > 0) {
          wins++;
        } else {
          losses++;
        }
        buyState.qty -= o.quantity;
        buyState.cost -= avgBuyPrice * o.quantity;
      }
    }
  });
  const winRate = (wins + losses) > 0 ? (wins / (wins + losses)) * 100 : 0;

  return (
    <div className="card card-glass" style={{ marginTop: 16 }}>
      <div className="card-header" style={{ justifyContent: 'space-between' }}>
        <span className="card-title">💵 Paper Trading Terminal (Free-Tier Mode)</span>
        <button
          onClick={() => {
            if (window.confirm('Reset wallet to ₹1,00,000 and close all open positions?')) {
              resetMutation.mutate();
            }
          }}
          style={{
            background: 'rgba(255, 71, 87, 0.1)',
            color: 'var(--danger)',
            border: '1px solid rgba(255, 71, 87, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 12px',
            fontSize: 12,
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          Reset Wallet
        </button>
      </div>

      <div className="card-body" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 20 }}>
        {/* Left: Order Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, borderRight: '1px solid rgba(37,40,54,0.4)', paddingRight: 20 }}>
          {/* Wallet stats widget */}
          {walletStats && (
            <div style={{ background: 'rgba(37,40,54,0.3)', borderRadius: 'var(--radius-md)', padding: 12, fontSize: 13 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Wallet Balance:</span>
                <span className="mono font-bold">₹{fmt(walletStats.cash_balance)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Holdings Value:</span>
                <span className="mono">₹{fmt(walletStats.total_holdings_value)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(37,40,54,0.6)', paddingTop: 6, marginBottom: 6 }}>
                <span style={{ color: 'var(--text)' }}>Total Portfolio Equity:</span>
                <span className="mono font-bold" style={{ color: 'var(--accent)' }}>₹{fmt(walletStats.total_equity)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Realized P&L:</span>
                <span className={`mono ${walletStats.realized_pnl >= 0 ? 'positive' : 'negative'}`}>
                  ₹{fmt(walletStats.realized_pnl)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Unrealized P&L:</span>
                <span className={`mono ${walletStats.unrealized_pnl >= 0 ? 'positive' : 'negative'}`}>
                  ₹{fmt(walletStats.unrealized_pnl)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Simulated Win Rate:</span>
                <span className="mono font-bold" style={{ color: winRate >= 50 ? 'var(--success)' : (winRate > 0 ? 'var(--danger)' : 'var(--text)') }}>
                  {(wins + losses) > 0 ? `${winRate.toFixed(1)}% (${wins}W - ${losses}L)` : '—'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, borderTop: '1px solid rgba(37,40,54,0.4)', paddingTop: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Daily Loss / Limit:</span>
                <span className="mono" style={{ color: walletStats.circuit_breaker_triggered ? 'var(--danger)' : 'var(--text)' }}>
                  ₹{fmt(walletStats.daily_realized_loss)} / ₹{fmt(walletStats.daily_loss_limit)}
                </span>
              </div>
              {walletStats.circuit_breaker_triggered && (
                <div style={{ color: 'var(--danger)', fontSize: 11, marginTop: 8, textAlign: 'center', fontWeight: 'bold' }}>
                  🚨 Daily Loss Circuit Breaker Triggered. Buying blocked.
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleOrderSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Active Ticker: <span className="mono" style={{ color: 'var(--text)', fontWeight: 'bold' }}>{activeSymbol}</span></div>
            
            {/* Side Selection Tab */}
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                type="button"
                onClick={() => setSide('BUY')}
                style={{
                  flex: 1,
                  background: side === 'BUY' ? '#00d97e' : 'rgba(37,40,54,0.4)',
                  color: side === 'BUY' ? '#0d0e14' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 0',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                BUY
              </button>
              <button
                type="button"
                onClick={() => setSide('SELL')}
                style={{
                  flex: 1,
                  background: side === 'SELL' ? '#ff4757' : 'rgba(37,40,54,0.4)',
                  color: side === 'SELL' ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 0',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                SELL
              </button>
            </div>

            {/* Order Type Toggle */}
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Order Type</label>
              <div className="tabs">
                <button
                  type="button"
                  className={`tab-btn ${orderType === 'MARKET' ? 'active' : ''}`}
                  onClick={() => setOrderType('MARKET')}
                  style={{ padding: '6px 0', flex: 1 }}
                >
                  Market
                </button>
                <button
                  type="button"
                  className={`tab-btn ${orderType === 'LIMIT' ? 'active' : ''}`}
                  onClick={() => setOrderType('LIMIT')}
                  style={{ padding: '6px 0', flex: 1 }}
                >
                  Limit
                </button>
              </div>
            </div>

            {/* Quantity */}
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Quantity (Shares/Units)</label>
              <input
                type="number"
                min="0.0001"
                step="any"
                className="symbol-input"
                style={{ width: '100%' }}
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                required
              />
            </div>

            {/* Limit Price */}
            {orderType === 'LIMIT' && (
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Limit Price (₹)</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.05"
                  className="symbol-input"
                  style={{ width: '100%' }}
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(e.target.value)}
                  placeholder="Enter trigger price"
                  required
                />
              </div>
            )}

            {/* Feedback Alert */}
            {alertMsg && (
              <div
                className={alertMsg.isError ? 'error-box' : 'success-box'}
                style={{
                  fontSize: 12,
                  padding: 10,
                  borderRadius: 'var(--radius-md)',
                  background: alertMsg.isError ? 'rgba(255,71,87,0.1)' : 'rgba(0,217,126,0.1)',
                  color: alertMsg.isError ? 'var(--danger)' : 'var(--success)',
                  border: alertMsg.isError ? '1px solid rgba(255,71,87,0.2)' : '1px solid rgba(0,217,126,0.2)',
                  marginTop: 6,
                  wordBreak: 'break-word',
                }}
              >
                {alertMsg.text}
              </div>
            )}

            <button
              type="submit"
              disabled={orderMutation.isPending}
              style={{
                width: '100%',
                background: side === 'BUY' ? '#00d97e' : '#ff4757',
                color: side === 'BUY' ? '#0d0e14' : '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                padding: '10px 0',
                fontWeight: 700,
                fontSize: 14,
                cursor: 'pointer',
                marginTop: 8,
                opacity: orderMutation.isPending ? 0.6 : 1,
              }}
            >
              {orderMutation.isPending ? 'Sending...' : `Submit ${side} Order`}
            </button>
          </form>
        </div>

        {/* Right: Open Positions and History tables */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, overflowX: 'auto' }}>
          {/* Open Positions Table */}
          <div>
            <div style={{ fontSize: 13, fontWeight: 'bold', color: 'var(--text)', marginBottom: 8 }}>💼 Open Positions</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid rgba(37,40,54,0.6)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '6px 4px' }}>Symbol</th>
                  <th style={{ padding: '6px 4px' }}>Qty</th>
                  <th style={{ padding: '6px 4px' }}>Avg Buy (₹)</th>
                  <th style={{ padding: '6px 4px' }}>Live Price (₹)</th>
                  <th style={{ padding: '6px 4px' }}>Unrealized P&L (₹)</th>
                  <th style={{ padding: '6px 4px' }}>% P&L</th>
                  <th style={{ padding: '6px 4px', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(positions ?? []).map((pos) => {
                  const isPos = pos.unrealized_pnl >= 0;
                  return (
                    <tr key={pos.id} style={{ borderBottom: '1px solid rgba(37,40,54,0.3)' }}>
                      <td className="mono font-bold" style={{ padding: '8px 4px' }}>{pos.symbol}</td>
                      <td className="mono" style={{ padding: '8px 4px' }}>{fmt(pos.quantity, 4)}</td>
                      <td className="mono" style={{ padding: '8px 4px' }}>{fmt(pos.avg_buy_price)}</td>
                      <td className="mono" style={{ padding: '8px 4px' }}>{fmt(pos.current_price)}</td>
                      <td className={`mono ${isPos ? 'positive' : 'negative'}`} style={{ padding: '8px 4px' }}>
                        {isPos ? '+' : ''}{fmt(pos.unrealized_pnl)}
                      </td>
                      <td className={`mono ${isPos ? 'positive' : 'negative'}`} style={{ padding: '8px 4px' }}>
                        {isPos ? '+' : ''}{fmt(pos.unrealized_pnl_pct)}%
                      </td>
                      <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                        <button
                          onClick={() => handleQuickClose(pos.symbol, pos.quantity)}
                          style={{
                            background: 'rgba(255, 71, 87, 0.15)',
                            color: 'var(--danger)',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            fontSize: 10,
                            fontWeight: 'bold',
                            cursor: 'pointer',
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
                    <td colSpan={7} style={{ padding: '16px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No open positions. Use the order form to BUY shares.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Order History Table */}
          <div>
            <div style={{ fontSize: 13, fontWeight: 'bold', color: 'var(--text)', marginBottom: 8 }}>📜 Order & Execution History</div>
            <div style={{ maxHeight: 150, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid rgba(37,40,54,0.6)', color: 'var(--text-muted)', position: 'sticky', top: 0, background: '#0d0e14' }}>
                    <th style={{ padding: '4px' }}>Time</th>
                    <th style={{ padding: '4px' }}>Symbol</th>
                    <th style={{ padding: '4px' }}>Side</th>
                    <th style={{ padding: '4px' }}>Qty</th>
                    <th style={{ padding: '4px' }}>Price (₹)</th>
                    <th style={{ padding: '4px' }}>Type</th>
                    <th style={{ padding: '4px' }}>Status</th>
                    <th style={{ padding: '4px' }}>Signal Match</th>
                  </tr>
                </thead>
                <tbody>
                  {(history ?? []).slice(0, 30).map((o) => {
                    const isBuy = o.side === 'BUY';
                    const isFilled = o.status === 'FILLED';
                    return (
                      <tr key={o.id} style={{ borderBottom: '1px solid rgba(37,40,54,0.2)', opacity: o.status === 'CANCELLED' ? 0.5 : 1 }}>
                        <td style={{ padding: '6px 4px', color: 'var(--text-muted)' }}>
                          {new Date(o.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="mono font-bold" style={{ padding: '6px 4px' }}>{o.symbol}</td>
                        <td className="mono" style={{ padding: '6px 4px', color: isBuy ? '#00d97e' : '#ff4757', fontWeight: 'bold' }}>{o.side}</td>
                        <td className="mono" style={{ padding: '6px 4px' }}>{fmt(o.quantity, 2)}</td>
                        <td className="mono" style={{ padding: '6px 4px' }}>{fmt(o.price)}</td>
                        <td style={{ padding: '6px 4px' }}>{o.order_type}</td>
                        <td style={{ padding: '6px 4px', color: isFilled ? '#00d97e' : o.status === 'PENDING' ? '#f59e0b' : '#ff4757', fontWeight: 'bold' }}>
                          {o.status}
                        </td>
                        <td style={{ padding: '6px 4px' }}>
                          {o.status === 'FILLED' && o.signal_relation && (
                            <span 
                              style={{
                                fontSize: 9,
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontWeight: 'bold',
                                textTransform: 'uppercase',
                                background: o.signal_relation === 'AGREEMENT' ? 'rgba(0, 217, 126, 0.15)' : (o.signal_relation === 'AGAINST' ? 'rgba(255, 71, 87, 0.15)' : 'rgba(139, 144, 160, 0.15)'),
                                color: o.signal_relation === 'AGREEMENT' ? '#00d97e' : (o.signal_relation === 'AGAINST' ? '#ff4757' : '#8b90a0'),
                                border: o.signal_relation === 'AGREEMENT' ? '1px solid rgba(0, 217, 126, 0.3)' : (o.signal_relation === 'AGAINST' ? '1px solid rgba(255, 71, 87, 0.3)' : '1px solid rgba(139, 144, 160, 0.3)')
                              }}
                            >
                              {o.signal_relation.toLowerCase()}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {(history ?? []).length === 0 && (
                    <tr>
                      <td colSpan={8} style={{ padding: '16px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No transactions recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
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

function Watchlist({ onSelectSymbol, activeSymbol }: { onSelectSymbol: (symbol: string) => void, activeSymbol: string }) {
  const [symbols, setSymbols] = useState<string[]>(() => {
    const saved = localStorage.getItem('neuroquant_watchlist');
    return saved ? JSON.parse(saved) : ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'BTC-USD'];
  });
  const [items, setItems] = useState<Record<string, WatchlistItem>>({});
  const [newSymbol, setNewSymbol] = useState('');
  const [flashStates, setFlashStates] = useState<Record<string, 'up' | 'down' | null>>({});

  // Persist watchlist
  useEffect(() => {
    localStorage.setItem('neuroquant_watchlist', JSON.stringify(symbols));
  }, [symbols]);

  // Connect to websocket to monitor live prices/signals for all watchlisted symbols
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/prices`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({ action: 'subscribe', symbols }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const sym = payload.symbol?.toUpperCase();
        if (sym && symbols.includes(sym)) {
          setItems(prev => {
            const current = prev[sym] || { symbol: sym, price: null, change_pct: null, signal: null, lastUpdated: 0 };
            if (payload.type === 'tick') {
              const oldPrice = current.price;
              const newPrice = payload.price;

              if (oldPrice !== null && newPrice !== oldPrice) {
                setFlashStates(prevFlash => ({
                  ...prevFlash,
                  [sym]: newPrice > oldPrice ? 'up' : 'down'
                }));
                setTimeout(() => {
                  setFlashStates(prevFlash => ({
                    ...prevFlash,
                    [sym]: null
                  }));
                }, 1000);
              }

              return {
                ...prev,
                [sym]: {
                  ...current,
                  price: newPrice,
                  change_pct: payload.change_pct,
                  lastUpdated: Date.now()
                }
              };
            } else if (payload.type === 'signal') {
              return {
                ...prev,
                [sym]: {
                  ...current,
                  signal: payload.direction,
                  lastUpdated: Date.now()
                }
              };
            }
            return prev;
          });
        }
      } catch (e) {
        console.error('Watchlist ws error:', e);
      }
    };

    return () => {
      try {
        socket.send(JSON.stringify({ action: 'unsubscribe', symbols }));
      } catch (e) {}
      socket.close();
    };
  }, [symbols]);

  // Fetch initial quotes for symbols
  useEffect(() => {
    const fetchInitial = async () => {
      for (const sym of symbols) {
        try {
          const { data } = await axios.get(`${API}/global/quote/${encodeURIComponent(sym)}`);
          setItems(prev => ({
            ...prev,
            [sym]: {
              symbol: sym,
              price: data.price,
              change_pct: data.change_pct,
              signal: data.signal?.direction ?? 'NEUTRAL',
              lastUpdated: Date.now()
            }
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
      setSymbols(prev => [...prev, clean]);
      setNewSymbol('');
    }
  };

  const handleRemove = (sym: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSymbols(prev => prev.filter(s => s !== sym));
    setItems(prev => {
      const copy = { ...prev };
      delete copy[sym];
      return copy;
    });
  };

  return (
    <div className="card card-glass" style={{ marginBottom: 0 }}>
      <div className="card-header" style={{ justifyContent: 'space-between', paddingBottom: 10, flexWrap: 'wrap', gap: 6 }}>
        <span className="card-title">⭐ Watchlist</span>
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 6 }}>
          <input
            className="symbol-input"
            style={{ padding: '4px 8px', fontSize: 11, width: 110 }}
            placeholder="ADD TICKER (TCS.NS)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
          />
          <button type="submit" className="tab-btn active" style={{ padding: '4px 8px', fontSize: 11, width: 'auto', flex: 'none' }}>Add</button>
        </form>
      </div>
      <div className="card-body" style={{ padding: 0, maxHeight: 220, overflowY: 'auto' }}>
        <div className="mover-list">
          {symbols.map(sym => {
            const item = items[sym];
            const price = item?.price;
            const pct = item?.change_pct ?? 0;
            const up = pct >= 0;
            const sig = item?.signal ?? 'NEUTRAL';
            const isStale = item && (Date.now() - item.lastUpdated > 45000);
            const flash = flashStates[sym];

            return (
              <div
                key={sym}
                className={`mover-row ${activeSymbol === sym ? 'active-symbol-row' : ''} ${flash === 'up' ? 'flash-up' : (flash === 'down' ? 'flash-down' : '')}`}
                onClick={() => onSelectSymbol(sym)}
                style={{ cursor: 'pointer', padding: '10px 16px', borderBottom: '1px solid rgba(37,40,54,0.2)' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className="mover-ticker" style={{ fontSize: 13 }}>{sym.replace('.NS', '')}</span>
                    {isStale && <span style={{ fontSize: 8, color: 'var(--danger)', background: 'rgba(255,71,87,0.1)', padding: '1px 4px', borderRadius: 3 }}>Offline</span>}
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{sym.includes('.NS') ? 'NSE India' : 'Crypto/US'}</span>
                </div>
                
                <div style={{ textAlign: 'right', marginRight: 16 }}>
                  <div className="mover-price" style={{ fontSize: 13 }}>{price != null ? `₹${fmt(price)}` : '—'}</div>
                  <div className={`mover-chg ${up ? 'positive' : 'negative'}`} style={{ fontSize: 11 }}>
                    {price != null ? `${up ? '+' : ''}${fmt(pct, 2)}%` : ''}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className={`signal-badge signal-${sig}`} style={{ fontSize: 8, padding: '2px 6px' }}>
                    {sig.replace('_', ' ')}
                  </span>
                  <button
                    onClick={(e) => handleRemove(sym, e)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      fontSize: 14,
                      padding: '4px'
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
          {symbols.length === 0 && (
            <div className="no-data" style={{ padding: '20px 0' }}>
              <span>Watchlist is empty</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────── App Shell ──────────────────────── */
function Dashboard() {
  const [searchVal, setSearchVal] = useState('');
  const [activeSymbol, setActiveSymbol] = useState('RELIANCE.NS');

  const onSearchSubmit = () => {
    if (searchVal.trim()) {
      setActiveSymbol(searchVal.trim().toUpperCase());
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

        <IndexChips />

        <div className="topbar-actions">
          <div className="search-wrap">
            <span className="search-icon">🔍</span>
            <input
              id="global-search"
              className="search-input"
              placeholder="Search symbol (e.g. INFY.NS)…"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onSearchSubmit();
              }}
              spellCheck={false}
            />
          </div>
        </div>
      </header>

      {/* ── Info Banner for Paper Trading & Data Delay ── */}
      <div style={{
        background: 'rgba(99, 102, 241, 0.08)',
        borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
        padding: '8px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 12,
        color: '#8b90a0',
        fontFamily: 'var(--font)',
        flexWrap: 'wrap',
        gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: '#00d97e', fontWeight: 'bold', background: 'rgba(0,217,126,0.1)', padding: '2px 8px', borderRadius: 4, fontSize: 10 }}>
            PAPER TRADING MODE
          </span>
          <span>Simulated portfolio with virtual capital. No real-money order execution.</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>⚠️ Free-Tier Feed:</span>
          <span>Quotes and charts are delayed by 15–20 minutes.</span>
        </div>
      </div>

      {/* ── Main Content ── */}
      <main className="main-layout" role="main">
        {/* Left: Chart + metrics + Paper Trading */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ErrorBoundary>
            <ChartPanel symbol={activeSymbol} setSymbol={setActiveSymbol} />
          </ErrorBoundary>
          
          <ErrorBoundary>
            <TradingPanel activeSymbol={activeSymbol} />
          </ErrorBoundary>
        </div>

        {/* Right: Watchlist + Movers sidebar */}
        <div className="right-sidebar">
          <ErrorBoundary>
            <Watchlist activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />
          </ErrorBoundary>
          <ErrorBoundary>
            <MoversPanel onSelectSymbol={setActiveSymbol} />
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
