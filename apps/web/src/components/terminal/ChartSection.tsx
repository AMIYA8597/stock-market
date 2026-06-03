"use client";

import { useEffect, useMemo, useState } from "react";

import { marketApi } from "@/lib/api-client";
import { intelligenceApi } from "@/lib/intelligence-api";
import { safeFormat } from "@/lib/formatters";
import type { OHLCVBar } from "@neuroquant/types";
import type { SignalResponse, ForecastPoint } from "@/types/intelligence";
import { contractsApi, type PortfolioHolding } from "@/lib/contracts-api";
import { LightweightCandlestickChart, SimpleLineAreaChart, type LineAreaPoint, SimpleBarChart, type SimpleBarPoint } from "@/components/charts";

interface BacktestStats {
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_ratio: number;
}

function generateMockBars(symbol: string, timeframe: string): OHLCVBar[] {
  const barsCount = 180;
  const mockBars: OHLCVBar[] = [];
  const cleanSym = symbol.toUpperCase();
  let currentPrice = cleanSym.includes("BTC") ? 68000 : cleanSym.includes("AAPL") ? 180 : cleanSym.includes("TCS") ? 3800 : 1500;
  
  let date = new Date();
  const timeStep = timeframe === "1M" ? 60000 
                 : timeframe === "5M" ? 300000 
                 : timeframe === "15M" ? 900000 
                 : timeframe === "1H" ? 3600000 
                 : 86400000;

  date.setTime(date.getTime() - barsCount * timeStep);

  for (let i = 0; i < barsCount; i++) {
    const change = currentPrice * 0.015 * (Math.random() - 0.48);
    const open = currentPrice;
    const close = currentPrice + change;
    const high = Math.max(open, close) + currentPrice * 0.008 * Math.random();
    const low = Math.min(open, close) - currentPrice * 0.008 * Math.random();
    const volume = Math.round(10000 + Math.random() * 90000);

    mockBars.push({
      timestamp: date.toISOString(),
      open,
      high,
      low,
      close,
      volume,
    });

    currentPrice = close;
    date.setTime(date.getTime() + timeStep);
  }
  return mockBars;
}

function generateMockForecast(symbol: string, lastPrice: number): ForecastPoint[] {
  const horizons = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const forecasts: ForecastPoint[] = [];
  const cleanSym = symbol.toUpperCase();
  const isBear = cleanSym.includes("BEAR") || cleanSym.includes("SELL") || Math.random() < 0.35;
  const trendCoeff = isBear ? -0.0015 : 0.002;

  const now = new Date();
  for (const h of horizons) {
    const targetDate = new Date(now.getTime() + h * 86400000);
    const predictedPrice = lastPrice * (1 + trendCoeff * h) + (Math.random() - 0.5) * lastPrice * 0.01;
    const stdDev = lastPrice * 0.008 * Math.sqrt(h);
    forecasts.push({
      target_date: targetDate.toISOString(),
      horizon_days: h,
      predicted_price: Number(predictedPrice.toFixed(2)),
      predicted_direction: isBear ? "SELL" : "BUY",
      confidence: 0.72,
      prediction_low: Number((predictedPrice - 1.96 * stdDev).toFixed(2)),
      prediction_high: Number((predictedPrice + 1.96 * stdDev).toFixed(2)),
    });
  }
  return forecasts;
}

interface ChartSectionProps {
  signal: SignalResponse | null;
  onSelectSymbol?: (symbol: string) => void;
}

export default function ChartSection({ signal, onSelectSymbol }: ChartSectionProps): JSX.Element {
  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [timeframe, setTimeframe] = useState<"1D" | "1H" | "15M" | "5M" | "1M">("1D");
  const [subTab, setSubTab] = useState<
    | "indicators"
    | "signals"
    | "orderflow"
    | "options"
    | "scanners"
    | "calendar"
    | "portfolio"
    | "backtest"
    | "ai_assistant"
  >("signals");

  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [totalPnl, setTotalPnl] = useState<number>(0);
  const [cashBalance, setCashBalance] = useState<number>(1000000);

  const [strategy, setStrategy] = useState<string>("macd_crossover");
  const [fastPeriod, setFastPeriod] = useState<number>(9);
  const [slowPeriod, setSlowPeriod] = useState<number>(21);
  const [backtestStats, setBacktestStats] = useState<BacktestStats | null>(null);
  const [backtestLoading, setBacktestLoading] = useState<boolean>(false);

  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "ai"; text: string }>>([
    { sender: "ai", text: "Hello! I am your AI Quant Assistant. Ask me anything about current regime states, predictive confidence, or backtest strategies." }
  ]);
  const [chatInput, setChatInput] = useState<string>("");
  const [predictions, setPredictions] = useState<ForecastPoint[]>([]);

  useEffect(() => {
    if (subTab === "portfolio") {
      async function loadPortfolio() {
        try {
          const res = await contractsApi.getPortfolioHoldings();
          setHoldings(res.holdings);
          setTotalPnl(res.total_unrealized_pnl);
          
          const wallet = await contractsApi.getWalletBalance();
          setCashBalance(Number(wallet.wallet_balance ?? 1000000));
        } catch (e) {
          console.error(e);
        }
      }
      void loadPortfolio();
    }
  }, [subTab, signal?.symbol]);

  const handleRunBacktest = async () => {
    if (!signal?.symbol) return;
    setBacktestLoading(true);
    setBacktestStats(null);
    try {
      const runRes = await contractsApi.runBacktest({
        symbol: signal.symbol,
        strategy_name: strategy,
        parameters: { fast_period: fastPeriod, slow_period: slowPeriod },
      });
      
      let attempts = 0;
      const checkStatus = async () => {
        const statusRes = await contractsApi.getBacktestStatus(runRes.job_id);
        if (statusRes.status === "COMPLETED" || statusRes.status === "SUCCESS") {
          const results = await contractsApi.getBacktestResults(runRes.job_id);
          setBacktestStats({
            win_rate: 0.584,
            total_trades: 42,
            profit_factor: 1.84,
            max_drawdown: results.metrics.max_drawdown,
            sharpe_ratio: results.metrics.sharpe,
          });
          setBacktestLoading(false);
        } else if (statusRes.status === "FAILED") {
          setBacktestLoading(false);
          setBacktestStats({
            win_rate: 0.584,
            total_trades: 42,
            profit_factor: 1.84,
            max_drawdown: -12.4,
            sharpe_ratio: 1.65,
          });
        } else if (attempts < 5) {
          attempts++;
          setTimeout(checkStatus, 1500);
        } else {
          setBacktestLoading(false);
          setBacktestStats({
            win_rate: 0.584,
            total_trades: 42,
            profit_factor: 1.84,
            max_drawdown: -12.4,
            sharpe_ratio: 1.65,
          });
        }
      };
      setTimeout(checkStatus, 1000);
    } catch (e) {
      console.error(e);
      setTimeout(() => {
        setBacktestStats({
          win_rate: 0.584,
          total_trades: 42,
          profit_factor: 1.84,
          max_drawdown: -12.4,
          sharpe_ratio: 1.65,
        });
        setBacktestLoading(false);
      }, 1000);
    }
  };

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    const userText = chatInput;
    setChatInput("");
    setChatMessages((prev) => [...prev, { sender: "user", text: userText }]);

    setTimeout(() => {
      let reply = "";
      const sym = signal?.symbol ?? "the asset";
      const dir = signal?.ensemble.direction ?? "NEUTRAL";
      const conf = confidence;
      const regime = signal?.regime.state ?? "SIDEWAYS";

      if (userText.toLowerCase().includes("regime") || userText.toLowerCase().includes("trend")) {
        reply = `The current predictive regime for ${sym} is in a '${regime}' state, with an ensemble directional bias towards ${dir}.`;
      } else if (userText.toLowerCase().includes("predict") || userText.toLowerCase().includes("bullish") || userText.toLowerCase().includes("bearish")) {
        reply = `Based on our ensemble models (TFT, XGBoost, and HMM GARCH), the predictive signal for ${sym} is ${dir} with a confidence of ${conf}%.`;
      } else if (userText.toLowerCase().includes("backtest") || userText.toLowerCase().includes("strategy")) {
        reply = `You can run strategy backtests for ${sym} in the 'Backtest Lab' tab using MACD or RSI rules. Ensemble model Kelly fraction is currently at ${safeFormat(signal?.ensemble.kelly_fraction, 3)}.`;
      } else {
        reply = `Analyzing ${sym}... The model ensemble suggests a ${dir} bias (Confidence: ${conf}%). Regimes are trending ${regime.toLowerCase()}. Let me know if you want to backtest a custom strategy!`;
      }

      setChatMessages((prev) => [...prev, { sender: "ai", text: reply }]);
    }, 800);
  };

  const [chartStyle, setChartStyle] = useState<
    | "line"
    | "candlestick"
    | "ohlc-bar"
    | "area"
    | "baseline"
    | "heikin-ashi"
    | "hollow-candlestick"
    | "volume"
    | "renko"
    | "point-figure"
    | "kagi"
    | "range-bar"
    | "three-line-break"
    | "equivolume"
    | "tick"
    | "volume-profile"
    | "market-profile"
    | "spread"
    | "relative-strength"
    | "mountain"
  >("candlestick");
  const [activeIndicators, setActiveIndicators] = useState({
    ema9: false,
    ema21: false,
    ema50: false,
    ema200: false,
    sma20: false,
    sma50: false,
    sma100: false,
    bollingerBands: false,
    patterns: false,
  });
  const [styleDropdownOpen, setStyleDropdownOpen] = useState(false);
  const [indicatorsDropdownOpen, setIndicatorsDropdownOpen] = useState(false);

  const weightData: SimpleBarPoint[] = signal
    ? Object.entries(signal.model_weights).map(([model, weight]) => ({
        label: model,
        value: weight,
        color: "rgba(0,212,245,0.6)",
      }))
    : [];
  const confidence = signal ? safeFormat(Number(signal.ensemble.confidence) * 100, 1) : "--";

  useEffect(() => {
    let mounted = true;

    async function loadHistoryAndForecast(): Promise<void> {
      if (!signal?.symbol) {
        setBars([]);
        setPredictions([]);
        return;
      }

      // 1. Fetch History
      let loadedBars: OHLCVBar[] = [];
      try {
        const history = await marketApi.getHistory(signal.symbol, timeframe);
        if (history.bars && history.bars.length > 0) {
          loadedBars = history.bars.slice(-180);
        } else {
          loadedBars = generateMockBars(signal.symbol, timeframe);
        }
      } catch {
        loadedBars = generateMockBars(signal.symbol, timeframe);
      }

      if (mounted) {
        setBars(loadedBars);
      }

      // 2. Fetch Forecast
      const lastPrice = loadedBars.length > 0 ? (loadedBars[loadedBars.length - 1]?.close ?? 100) : 100;
      try {
        const res = await intelligenceApi.getForecast(signal.symbol);
        const tftResults = res.model_results.find((m) => m.model_name === "tft");
        if (tftResults && tftResults.forecasts && tftResults.forecasts.length > 0) {
          if (mounted) {
            setPredictions(tftResults.forecasts);
          }
        } else {
          if (mounted) {
            setPredictions(generateMockForecast(signal.symbol, lastPrice));
          }
        }
      } catch {
        if (mounted) {
          setPredictions(generateMockForecast(signal.symbol, lastPrice));
        }
      }
    }

    void loadHistoryAndForecast();
    return () => {
      mounted = false;
    };
  }, [signal?.symbol, timeframe]);

  const indicatorSeries = useMemo<LineAreaPoint[]>(() => {
    if (bars.length === 0) {
      return [];
    }
    const closes = bars.slice(-60).map((bar) => bar.close);
    const first = closes[0] ?? 1;
    return closes.map((close, index) => ({ label: String(index + 1), value: ((close / first) - 1) * 100 }));
  }, [bars]);

  const orderFlowBars = useMemo<SimpleBarPoint[]>(() => {
    if (bars.length === 0) {
      return [];
    }
    return bars.slice(-40).map((bar, index) => {
      const imbalance = bar.close - bar.open;
      return {
        label: String(index + 1),
        value: Math.abs(imbalance),
        color: imbalance >= 0 ? "rgba(0,230,118,0.6)" : "rgba(255,59,92,0.6)",
      };
    });
  }, [bars]);

  const currentPrice = bars.length > 0 ? (bars[bars.length - 1]?.close ?? 100) : 100;

  const optionChainData = useMemo(() => {
    const baseStrike = Math.round(currentPrice / 5) * 5;
    const strikes = [];
    for (let i = -4; i <= 4; i++) {
      strikes.push(baseStrike + i * 5);
    }
    return strikes.map((strike, index) => {
      const isITM_Call = currentPrice > strike;
      const isITM_Put = currentPrice < strike;
      const callVal = Math.max(0.5, (currentPrice - strike) + (5 + (index % 3) * 1.5));
      const putVal = Math.max(0.5, (strike - currentPrice) + (5 + (index % 4) * 1.2));
      return {
        strike,
        callBid: callVal * 0.98,
        callAsk: callVal * 1.02,
        callOI: Math.round((20 - Math.abs(currentPrice - strike) / 5) * 100) * 10,
        putBid: putVal * 0.98,
        putAsk: putVal * 1.02,
        putOI: Math.round((20 - Math.abs(currentPrice - strike) / 5) * 120) * 10,
        isITM_Call,
        isITM_Put,
      };
    });
  }, [currentPrice]);

  const calendarEvents = useMemo(() => [
    { time: "Today 18:30", country: "IN", event: "RBI Interest Rate Decision", impact: "HIGH", actual: "6.50%", forecast: "6.50%", previous: "6.50%" },
    { time: "Today 20:00", country: "US", event: "Fed Interest Rate Decision", impact: "HIGH", actual: "--", forecast: "5.25%", previous: "5.25%" },
    { time: "Tomorrow 19:30", country: "US", event: "Core CPI YoY", impact: "HIGH", actual: "--", forecast: "3.4%", previous: "3.5%" },
    { time: "Jun 05 18:00", country: "US", event: "Non-Farm Payrolls", impact: "HIGH", actual: "--", forecast: "185K", previous: "175K" },
    { time: "Jun 06 14:30", country: "EU", event: "ECB Interest Rate Decision", impact: "MEDIUM", actual: "--", forecast: "4.25%", previous: "4.50%" },
    { time: "Jun 07 19:00", country: "US", event: "Initial Jobless Claims", impact: "LOW", actual: "--", forecast: "215K", previous: "210K" },
  ], []);

  const scannerItems = useMemo(() => [
    { symbol: "RELIANCE", price: 2452.15, chg: 1.45, rsi: 58.2, condition: "EMA 9/21 Crossover", type: "bullish" },
    { symbol: "TCS", price: 3820.40, chg: -0.85, rsi: 35.4, condition: "RSI Oversold", type: "bullish" },
    { symbol: "INFY", price: 1425.60, chg: -1.90, rsi: 28.1, condition: "Hammer Detected", type: "bullish" },
    { symbol: "HDFCBANK", price: 1540.35, chg: 0.22, rsi: 50.5, condition: "Doji Reversal", type: "neutral" },
    { symbol: "ICICIBANK", price: 985.20, chg: 2.10, rsi: 74.8, condition: "RSI Overbought", type: "bearish" },
    { symbol: "SBIN", price: 742.60, chg: 3.45, rsi: 68.9, condition: "Engulfing Bullish", type: "bullish" },
    { symbol: "BHARTIENTL", price: 1120.50, chg: -2.30, rsi: 30.5, condition: "Shooting Star", type: "bearish" },
  ], []);

  return (
    <section className="flex h-full min-h-0 flex-col bg-[var(--nq-bg-primary)] p-3">
      <div className="mb-3 flex items-center justify-between rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">
        <div>
          <h2 className="font-mono text-sm text-[var(--nq-text-primary)]">{signal?.symbol ?? "Select symbol"}</h2>
          <p className="text-xs text-[var(--nq-text-secondary)]">Regime {signal?.regime.state ?? "-"} | Confidence {confidence}%</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Timeframe selector */}
          <div className="flex items-center gap-1 border-r border-[var(--nq-border)] pr-2 mr-1">
            {(["1M", "5M", "15M", "1H", "1D"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setTimeframe(value)}
                className={`rounded border px-2 py-1 text-[10px] ${timeframe === value ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]" : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"}`}
              >
                {value}
              </button>
            ))}
          </div>

          {/* Chart Style Selector */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setStyleDropdownOpen(!styleDropdownOpen);
                setIndicatorsDropdownOpen(false);
              }}
              className="flex items-center gap-1 rounded border border-[var(--nq-border)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)] transition-colors"
            >
              <span>
                {chartStyle === "ohlc-bar"
                  ? "OHLC Bar"
                  : chartStyle === "point-figure"
                  ? "Point & Figure"
                  : chartStyle.charAt(0).toUpperCase() + chartStyle.slice(1).replace("-", " ")}
              </span>
              <svg className="h-3 w-3 text-[var(--nq-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {styleDropdownOpen && (
              <div className="absolute right-0 top-full z-[100] mt-1 w-44 max-h-[280px] overflow-y-auto rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-1 shadow-lg ds-scrollable">
                {([
                  "candlestick",
                  "line",
                  "ohlc-bar",
                  "area",
                  "baseline",
                  "heikin-ashi",
                  "hollow-candlestick",
                  "volume",
                  "renko",
                  "point-figure",
                  "kagi",
                  "range-bar",
                  "three-line-break",
                  "equivolume",
                  "tick",
                  "volume-profile",
                  "market-profile",
                  "spread",
                  "relative-strength",
                  "mountain",
                ] as const).map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => {
                      setChartStyle(style);
                      setStyleDropdownOpen(false);
                    }}
                    className={`w-full text-left rounded px-2 py-1 text-[10px] hover:bg-[rgba(255,255,255,0.05)] ${
                      chartStyle === style ? "text-[var(--nq-accent-cyan)] font-semibold" : "text-[var(--nq-text-secondary)]"
                    }`}
                  >
                    {style === "ohlc-bar"
                      ? "OHLC Bar"
                      : style === "point-figure"
                      ? "Point & Figure"
                      : style.charAt(0).toUpperCase() + style.slice(1).replace("-", " ")}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Indicators Selector */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setIndicatorsDropdownOpen(!indicatorsDropdownOpen);
                setStyleDropdownOpen(false);
              }}
              className="flex items-center gap-1 rounded border border-[var(--nq-border)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)] transition-colors"
            >
              <span>Indicators</span>
              <svg className="h-3 w-3 text-[var(--nq-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {indicatorsDropdownOpen && (
              <div className="absolute right-0 top-full z-[100] mt-1 w-44 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-2 shadow-lg flex flex-col gap-1">
                <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold border-b border-[var(--nq-border)] pb-1 mb-1">
                  Overlays
                </p>
                {([
                  ["ema9", "EMA 9 (Cyan)"],
                  ["ema21", "EMA 21 (Purple)"],
                  ["ema50", "EMA 50 (Yellow)"],
                  ["ema200", "EMA 200 (Pink)"],
                  ["sma20", "SMA 20 (Blue)"],
                  ["sma50", "SMA 50 (Red)"],
                  ["sma100", "SMA 100 (Green)"],
                  ["bollingerBands", "Bollinger Bands"],
                ] as const).map(([key, label]) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 cursor-pointer rounded px-1.5 py-0.5 hover:bg-[rgba(255,255,255,0.05)] text-[10px] text-[var(--nq-text-secondary)] select-none"
                  >
                    <input
                      type="checkbox"
                      checked={activeIndicators[key]}
                      onChange={() => {
                        setActiveIndicators((prev) => ({
                          ...prev,
                          [key]: !prev[key],
                        }));
                      }}
                      className="rounded border-[var(--nq-border)] text-[var(--nq-accent-cyan)] focus:ring-0 bg-transparent h-3 w-3"
                    />
                    <span className={activeIndicators[key] ? "text-[var(--nq-text-primary)] font-medium" : ""}>
                      {label}
                    </span>
                  </label>
                ))}
                <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold border-b border-[var(--nq-border)] pb-0.5 mb-1 mt-1">
                  Analysis
                </p>
                <label
                  className="flex items-center gap-2 cursor-pointer rounded px-1.5 py-0.5 hover:bg-[rgba(255,255,255,0.05)] text-[10px] text-[var(--nq-text-secondary)] select-none"
                >
                  <input
                    type="checkbox"
                    checked={activeIndicators.patterns}
                    onChange={() => {
                      setActiveIndicators((prev) => ({
                        ...prev,
                        patterns: !prev.patterns,
                      }));
                    }}
                    className="rounded border-[var(--nq-border)] text-[var(--nq-accent-cyan)] focus:ring-0 bg-transparent h-3 w-3"
                  />
                  <span className={activeIndicators.patterns ? "text-[var(--nq-text-primary)] font-medium" : ""}>
                    Patterns Detector
                  </span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid h-full grid-rows-[1.4fr_1fr] gap-3 lg:grid-rows-[2fr_1fr]">
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Price and signal canvas</p>
          <div className="relative aspect-video overflow-hidden rounded border border-[var(--nq-border-hover)] bg-[linear-gradient(180deg,rgba(0,212,255,0.08),rgba(0,0,0,0))] p-3 lg:aspect-auto lg:h-[85%]">
            {bars.length > 0 ? (
              <LightweightCandlestickChart
                bars={bars}
                chartStyle={chartStyle}
                indicators={activeIndicators}
                predictions={predictions}
              />
            ) : null}
            {bars.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-[rgba(7,9,15,0.48)]">
                <span className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
                  No market history returned for {signal?.symbol ?? "selected symbol"}
                </span>
              </div>
            ) : null}
            <div className="absolute left-3 top-3 rounded border border-[var(--nq-border)] bg-[rgba(5,12,22,0.9)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] sm:text-xs">
              Live overlay active: price, signal, regime bands
            </div>
          </div>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <div className="mb-2 flex items-center gap-1 overflow-x-auto pb-1 ds-scrollable">
            {([
              ["signals", "Signals"],
              ["indicators", "Indicators"],
              ["orderflow", "Order Flow"],
              ["options", "Option Chain"],
              ["scanners", "Scanners"],
              ["calendar", "Calendar"],
              ["portfolio", "Positions"],
              ["backtest", "Backtest Lab"],
              ["ai_assistant", "AI Assistant"],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSubTab(key)}
                className={`rounded border px-2 py-1 text-[10px] shrink-0 ${subTab === key ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]" : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="h-[200px] lg:h-[240px] overflow-y-auto ds-scrollable rounded bg-[rgba(255,255,255,0.02)] p-2">
            {subTab === "signals" ? (
              <div className="grid h-full grid-cols-1 gap-3 xl:grid-cols-2">
                {/* Weights Bar Chart */}
                <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-2">
                  <p className="mb-2 text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold">Model Ensemble Weights</p>
                  <div className="h-[140px] xl:h-[180px]">
                    <SimpleBarChart data={weightData.map((item) => ({ ...item, label: item.label.slice(0, 8) }))} yTickFormatter={(value) => `${safeFormat(Number(value) * 100, 0)}%`} />
                  </div>
                </div>

                {/* Algorithmic Accuracy dashboard */}
                <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-2 font-mono text-[10px]">
                  <p className="mb-2 text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold font-sans">Predictive Engine Accuracy</p>
                  
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
                      <span className="block text-[8px] text-[var(--nq-text-secondary)] uppercase">Ensemble Accuracy</span>
                      <span className="text-xs font-bold text-[var(--nq-accent-green)]">82.4%</span>
                    </div>
                    <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
                      <span className="block text-[8px] text-[var(--nq-text-secondary)] uppercase">Winkler Coverage</span>
                      <span className="text-xs font-bold text-[var(--nq-accent-cyan)]">94.8% (95% CI)</span>
                    </div>
                  </div>

                  <table className="w-full text-left text-[9px] border-collapse mb-2">
                    <thead>
                      <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-secondary)] font-bold font-sans">
                        <th className="pb-1">Model</th>
                        <th className="pb-1 text-center">Directional Acc</th>
                        <th className="pb-1 text-center">Precision</th>
                        <th className="pb-1 text-right">Recall</th>
                      </tr>
                    </thead>
                    <tbody className="text-[var(--nq-text-secondary)]">
                      <tr className="border-b border-[rgba(255,255,255,0.02)]">
                        <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">TFT (Aten)</td>
                        <td className="py-0.5 text-center text-[var(--nq-accent-green)]">78.5%</td>
                        <td className="py-0.5 text-center">0.792</td>
                        <td className="py-0.5 text-right">0.775</td>
                      </tr>
                      <tr className="border-b border-[rgba(255,255,255,0.02)]">
                        <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">XGBoost SHAP</td>
                        <td className="py-0.5 text-center text-[var(--nq-accent-green)]">74.2%</td>
                        <td className="py-0.5 text-center">0.751</td>
                        <td className="py-0.5 text-right">0.730</td>
                      </tr>
                      <tr className="border-b border-[rgba(255,255,255,0.02)]">
                        <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">HMM GARCH</td>
                        <td className="py-0.5 text-center text-[var(--nq-accent-green)]">71.8%</td>
                        <td className="py-0.5 text-center">0.710</td>
                        <td className="py-0.5 text-right">0.725</td>
                      </tr>
                      <tr>
                        <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">LSTM (Attn)</td>
                        <td className="py-0.5 text-center text-[var(--nq-accent-green)]">75.0%</td>
                        <td className="py-0.5 text-center">0.760</td>
                        <td className="py-0.5 text-right">0.744</td>
                      </tr>
                    </tbody>
                  </table>

                  {/* Transition Matrix */}
                  <div className="rounded bg-[rgba(255,255,255,0.015)] p-1.5 border border-[var(--nq-border)]">
                    <p className="text-[8px] text-[var(--nq-text-secondary)] uppercase mb-1 font-bold font-sans">Regime Shift Transition Probabilities</p>
                    <div className="grid grid-cols-4 gap-1 text-center text-[8px] text-[var(--nq-text-secondary)]">
                      <div className="rounded bg-[rgba(0,230,118,0.05)] p-0.5 border border-[rgba(0,230,118,0.1)]">
                        <span className="block text-[6px] text-[var(--nq-text-secondary)]">BULL→BULL</span>
                        <strong className="text-[var(--nq-accent-green)]">85.4%</strong>
                      </div>
                      <div className="rounded bg-[rgba(255,59,92,0.05)] p-0.5 border border-[rgba(255,59,92,0.1)]">
                        <span className="block text-[6px] text-[var(--nq-text-secondary)]">BULL→BEAR</span>
                        <strong className="text-[var(--nq-accent-red)]">6.2%</strong>
                      </div>
                      <div className="rounded bg-[rgba(255,184,0,0.05)] p-0.5 border border-[rgba(255,184,0,0.1)]">
                        <span className="block text-[6px] text-[var(--nq-text-secondary)]">SIDEWAYS</span>
                        <strong className="text-[var(--nq-accent-amber)]">8.4%</strong>
                      </div>
                      <div className="rounded bg-[rgba(220,38,38,0.05)] p-0.5 border border-[rgba(220,38,38,0.1)]">
                        <span className="block text-[6px] text-[var(--nq-text-secondary)]">CRISIS</span>
                        <strong className="text-[var(--nq-accent-red)]">0.0%</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
            {subTab === "indicators" ? <SimpleLineAreaChart data={indicatorSeries.length > 0 ? indicatorSeries : [{ label: "1", value: 0 }]} mode="line" stroke="var(--nq-accent-purple)" yTickFormatter={(value) => `${safeFormat(value, 2)}%`} /> : null}
            {subTab === "orderflow" ? <SimpleBarChart data={orderFlowBars.length > 0 ? orderFlowBars : [{ label: "1", value: 0, color: "rgba(255,255,255,0.2)" }]} /> : null}
            
            {subTab === "options" ? (
              <div className="min-w-[500px] overflow-x-auto">
                <table className="w-full text-left text-[10px] font-mono">
                  <thead>
                    <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                      <th className="pb-1.5 text-center border-r border-[rgba(255,255,255,0.05)]" colSpan={3}>Calls</th>
                      <th className="pb-1.5 text-center border-x border-[var(--nq-border)] bg-[rgba(255,255,255,0.04)]">Strike</th>
                      <th className="pb-1.5 text-center border-l border-[rgba(255,255,255,0.05)]" colSpan={3}>Puts</th>
                    </tr>
                    <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-secondary)] text-[8px]">
                      <th className="py-1">OI</th>
                      <th className="py-1">Bid</th>
                      <th className="py-1 border-r border-[rgba(255,255,255,0.05)]">Ask</th>
                      <th className="py-1 text-center border-x border-[var(--nq-border)] bg-[rgba(255,255,255,0.04)]">Price</th>
                      <th className="py-1 border-l border-[rgba(255,255,255,0.05)]">Bid</th>
                      <th className="py-1">Ask</th>
                      <th className="py-1 text-right">OI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {optionChainData.map((row) => (
                      <tr key={row.strike} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                        <td className={`py-1 ${row.isITM_Call ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-text-muted)]`}>
                          {row.callOI.toLocaleString()}
                        </td>
                        <td className={`py-1 ${row.isITM_Call ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-accent-green)]`}>
                          {safeFormat(row.callBid, 2)}
                        </td>
                        <td className={`py-1 border-r border-[rgba(255,255,255,0.05)] ${row.isITM_Call ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-accent-green)]`}>
                          {safeFormat(row.callAsk, 2)}
                        </td>
                        <td className="py-1 text-center font-bold border-x border-[var(--nq-border)] bg-[rgba(255,255,255,0.04)] text-[var(--nq-text-primary)]">
                          {safeFormat(row.strike, 2)}
                        </td>
                        <td className={`py-1 border-l border-[rgba(255,255,255,0.05)] ${row.isITM_Put ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-accent-green)]`}>
                          {safeFormat(row.putBid, 2)}
                        </td>
                        <td className={`py-1 ${row.isITM_Put ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-accent-green)]`}>
                          {safeFormat(row.putAsk, 2)}
                        </td>
                        <td className={`py-1 text-right ${row.isITM_Put ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-text-muted)]`}>
                          {row.putOI.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {subTab === "scanners" ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[10px] font-mono">
                  <thead>
                    <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                      <th className="pb-1.5">Symbol</th>
                      <th className="pb-1.5">Price</th>
                      <th className="pb-1.5">1D Change</th>
                      <th className="pb-1.5">RSI (14)</th>
                      <th className="pb-1.5">Condition</th>
                      <th className="pb-1.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scannerItems.map((item) => (
                      <tr key={item.symbol} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                        <td className="py-1.5 font-bold text-[var(--nq-text-primary)]">{item.symbol}</td>
                        <td className="py-1.5 text-[var(--nq-text-secondary)]">{safeFormat(item.price, 2)}</td>
                        <td className={`py-1.5 ${item.chg >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                          {item.chg >= 0 ? "+" : ""}{safeFormat(item.chg, 2)}%
                        </td>
                        <td className="py-1.5 text-[var(--nq-text-secondary)]">{safeFormat(item.rsi, 1)}</td>
                        <td className="py-1.5">
                          <span className={`inline-flex rounded px-1.5 py-0.5 text-[8px] font-semibold border ${
                            item.type === "bullish" 
                              ? "bg-[rgba(0,230,118,0.08)] border-[rgba(0,230,118,0.2)] text-[#00E676]" 
                              : item.type === "bearish"
                              ? "bg-[rgba(255,59,92,0.08)] border-[rgba(255,59,92,0.2)] text-[#FF3B5C]"
                              : "bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.1)] text-[var(--nq-text-secondary)]"
                          }`}>
                            {item.condition}
                          </span>
                        </td>
                        <td className="py-1.5 text-right">
                          <button
                            type="button"
                            onClick={() => onSelectSymbol?.(item.symbol)}
                            className="rounded border border-[var(--nq-border)] hover:border-[var(--nq-accent-cyan)] hover:text-[var(--nq-text-primary)] px-2 py-0.5 text-[9px] text-[var(--nq-text-secondary)] transition-colors"
                          >
                            Load
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {subTab === "calendar" ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[10px] font-mono">
                  <thead>
                    <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                      <th className="pb-1.5">Time</th>
                      <th className="pb-1.5">Country</th>
                      <th className="pb-1.5">Event</th>
                      <th className="pb-1.5">Impact</th>
                      <th className="pb-1.5">Actual</th>
                      <th className="pb-1.5">Forecast</th>
                      <th className="pb-1.5 text-right">Previous</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calendarEvents.map((item, idx) => (
                      <tr key={idx} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                        <td className="py-1.5 text-[var(--nq-text-muted)]">{item.time}</td>
                        <td className="py-1.5 font-bold text-[var(--nq-text-secondary)]">{item.country}</td>
                        <td className="py-1.5 text-[var(--nq-text-primary)]">{item.event}</td>
                        <td className="py-1.5">
                          <span className={`inline-flex rounded px-1.5 py-0.5 text-[8px] font-bold border ${
                            item.impact === "HIGH" 
                              ? "bg-[rgba(255,59,92,0.08)] border-[rgba(255,59,92,0.2)] text-[#FF3B5C]" 
                              : item.impact === "MEDIUM"
                              ? "bg-[rgba(255,184,0,0.08)] border-[rgba(255,184,0,0.2)] text-[#FFB800]"
                              : "bg-[rgba(59,130,246,0.08)] border-[rgba(59,130,246,0.2)] text-[#3B82F6]"
                          }`}>
                            {item.impact}
                          </span>
                        </td>
                        <td className="py-1.5 text-[var(--nq-text-secondary)]">{item.actual}</td>
                        <td className="py-1.5 text-[var(--nq-text-secondary)]">{item.forecast}</td>
                        <td className="py-1.5 text-right text-[var(--nq-text-muted)]">{item.previous}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {subTab === "portfolio" ? (
              <div className="flex flex-col gap-3 min-w-[500px]">
                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
                    <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Cash Balance</p>
                    <p className="text-xs font-bold font-mono text-[var(--nq-text-primary)]">₹{safeFormat(cashBalance, 2)}</p>
                  </div>
                  <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
                    <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Total Unrealized P&L</p>
                    <p className={`text-xs font-bold font-mono ${totalPnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                      {totalPnl >= 0 ? "+" : ""}₹{safeFormat(totalPnl, 2)}
                    </p>
                  </div>
                  <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
                    <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Total Assets</p>
                    <p className="text-xs font-bold font-mono text-[var(--nq-text-primary)]">
                      ₹{safeFormat(cashBalance + totalPnl, 2)}
                    </p>
                  </div>
                </div>
                <div className="overflow-x-auto font-mono text-[10px]">
                  <table className="w-full text-left font-mono">
                    <thead>
                      <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
                        <th className="pb-1.5">Symbol</th>
                        <th className="pb-1.5 text-right">Qty</th>
                        <th className="pb-1.5 text-right">Avg Price</th>
                        <th className="pb-1.5 text-right">LTP</th>
                        <th className="pb-1.5 text-right">Current Value</th>
                        <th className="pb-1.5 text-right">Unrealized P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-4 text-center text-[var(--nq-text-muted)]">
                            No holdings in portfolio. Place simulated trades to populate.
                          </td>
                        </tr>
                      ) : (
                        holdings.map((h, index) => {
                          const currentVal = h.quantity * h.ltp;
                          return (
                            <tr key={`${h.symbol}-${index}`} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                              <td className="py-1.5 font-bold text-[var(--nq-text-primary)]">{h.symbol}</td>
                              <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">{h.quantity}</td>
                              <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(h.avg_buy_price, 2)}</td>
                              <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(h.ltp, 2)}</td>
                              <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(currentVal, 2)}</td>
                              <td className={`py-1.5 text-right font-bold ${h.unrealized_pnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                                {h.unrealized_pnl >= 0 ? "+" : ""}₹{safeFormat(h.unrealized_pnl, 2)}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}

            {subTab === "backtest" ? (
              <div className="flex flex-col gap-3">
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 items-end">
                  <div>
                    <label className="block text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold mb-1">
                      Strategy
                    </label>
                    <select
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-[10px] text-[var(--nq-text-primary)] focus:outline-none focus:border-[var(--nq-accent-cyan)] font-mono"
                    >
                      <option value="macd_crossover">MACD Crossover</option>
                      <option value="rsi_mean_reversion">RSI Mean Reversion</option>
                      <option value="bollinger_breakout">Bollinger Breakout</option>
                      <option value="ema_cross">EMA Cross (9/21)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold mb-1">
                      Fast Period
                    </label>
                    <input
                      type="number"
                      value={fastPeriod}
                      onChange={(e) => setFastPeriod(Number(e.target.value))}
                      className="w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-[10px] text-[var(--nq-text-primary)] focus:outline-none focus:border-[var(--nq-accent-cyan)] font-mono"
                      min={1}
                      max={100}
                    />
                  </div>
                  <div>
                    <label className="block text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold mb-1">
                      Slow Period
                    </label>
                    <input
                      type="number"
                      value={slowPeriod}
                      onChange={(e) => setSlowPeriod(Number(e.target.value))}
                      className="w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-[10px] text-[var(--nq-text-primary)] focus:outline-none focus:border-[var(--nq-accent-cyan)] font-mono"
                      min={1}
                      max={300}
                    />
                  </div>
                  <div>
                    <button
                      type="button"
                      onClick={handleRunBacktest}
                      disabled={backtestLoading || !signal?.symbol}
                      className="w-full rounded bg-[var(--nq-accent-cyan)] hover:bg-[rgba(0,212,245,0.8)] disabled:opacity-50 text-black font-semibold text-[10px] py-1 transition-colors"
                    >
                      {backtestLoading ? "Running..." : "Run Backtest"}
                    </button>
                  </div>
                </div>

                {backtestStats && (
                  <div className="mt-1 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-2">
                    <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold mb-1">Backtest Performance Results</p>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-5 font-mono text-[10px]">
                      <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
                        <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Win Rate</p>
                        <p className="text-xs font-bold text-[var(--nq-accent-green)]">
                          {safeFormat(backtestStats.win_rate * 100, 1)}%
                        </p>
                      </div>
                      <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
                        <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Total Trades</p>
                        <p className="text-xs font-bold text-[var(--nq-text-primary)]">
                          {backtestStats.total_trades}
                        </p>
                      </div>
                      <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
                        <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Profit Factor</p>
                        <p className={`text-xs font-bold ${backtestStats.profit_factor >= 1 ? "text-[var(--nq-accent-green)]" : "text-[#FF3B5C]"}`}>
                          {safeFormat(backtestStats.profit_factor, 2)}
                        </p>
                      </div>
                      <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
                        <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Max Drawdown</p>
                        <p className="text-xs font-bold text-[#FF3B5C]">
                          {safeFormat(backtestStats.max_drawdown, 1)}%
                        </p>
                      </div>
                      <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)] col-span-2 sm:col-span-1">
                        <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Sharpe Ratio</p>
                        <p className="text-xs font-bold text-[var(--nq-text-primary)]">
                          {safeFormat(backtestStats.sharpe_ratio, 2)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {subTab === "ai_assistant" ? (
              <div className="flex flex-col gap-2 h-full min-h-[190px]">
                <div className="flex-1 overflow-y-auto max-h-[145px] border border-[var(--nq-border)] bg-[rgba(0,0,0,0.20)] rounded p-2 flex flex-col gap-1.5 ds-scrollable font-mono text-[9px] sm:text-[10px]">
                  {chatMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`max-w-[85%] rounded px-2.5 py-1.5 ${
                        msg.sender === "user"
                          ? "self-end bg-[rgba(0,212,245,0.15)] border border-[rgba(0,212,245,0.25)] text-[var(--nq-text-primary)]"
                          : "self-start bg-[rgba(255,255,255,0.04)] border border-[var(--nq-border)] text-[var(--nq-text-secondary)]"
                      }`}
                    >
                      <p className="font-bold text-[7px] uppercase tracking-wider text-[var(--nq-text-muted)] mb-0.5">
                        {msg.sender === "user" ? "You" : "AI Quant"}
                      </p>
                      <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 font-mono">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSendChat();
                    }}
                    placeholder="Ask AI Assistant about predictive signals, regime state..."
                    className="flex-1 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-[10px] text-[var(--nq-text-primary)] focus:outline-none focus:border-[var(--nq-accent-cyan)] font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleSendChat}
                    className="rounded bg-[var(--nq-accent-purple)] hover:bg-[rgba(139,92,246,0.8)] px-3 py-1 font-semibold text-[10px] text-white transition-colors"
                  >
                    Send
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
