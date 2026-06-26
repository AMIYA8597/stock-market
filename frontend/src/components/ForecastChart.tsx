import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  AreaSeries,
  BarSeries,
} from 'lightweight-charts';
import type {
  IChartApi,
  ISeriesApi,
  SeriesType,
} from 'lightweight-charts';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

/* ─── Types ─────────────────────────────────────────── */
interface OhlcvPoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema9?: number;
  ema21?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_hist?: number;
}

interface HistoryResponse {
  symbol: string;
  interval: string;
  data: OhlcvPoint[];
}

interface QuoteResponse {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap: number;
  pe_ratio: number;
  high_52w: number;
  low_52w: number;
  regime: { state: string; probs: Record<string, number> };
  signal: { direction: string; confidence: number; rationale?: string };
  timestamp: string;
}

const API = '/api/v1';

/* ─── API helpers ───────────────────────────────────── */
const fetchHistory = async (symbol: string, interval: string, period: string): Promise<HistoryResponse> => {
  const { data } = await axios.get(`${API}/global/history/${encodeURIComponent(symbol)}`, {
    params: { interval, period },
  });
  return data;
};

const fetchQuote = async (symbol: string): Promise<QuoteResponse> => {
  const { data } = await axios.get(`${API}/global/quote/${encodeURIComponent(symbol)}`);
  return data;
};

/* ─── Formatters ────────────────────────────────────── */
function fmt(n: number, decimals = 2) {
  if (n == null || isNaN(n)) return '—';
  return n.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtBig(n: number): string {
  if (n == null || isNaN(n) || n === 0) return '—';
  if (n >= 1e12) return `₹${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `₹${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `₹${(n / 1e6).toFixed(2)}M`;
  return fmt(n);
}

/* ─── Safe number helper ────────────────────────────── */
function safeNum(val: unknown, fallback = 0): number {
  if (val == null) return fallback;
  const n = Number(val);
  if (isNaN(n) || !isFinite(n)) return fallback;
  return n;
}

/* ─── Helper to parse and round tick bar times ────────── */
const getBarTime = (timestamp: string, interval: string): number => {
  const dateSecs = Math.floor(new Date(timestamp).getTime() / 1000);
  if (isNaN(dateSecs)) return Math.floor(Date.now() / 1000);
  
  if (interval === '1m') return Math.floor(dateSecs / 60) * 60;
  if (interval === '5m') return Math.floor(dateSecs / 300) * 300;
  if (interval === '15m') return Math.floor(dateSecs / 900) * 900;
  if (interval === '1h') return Math.floor(dateSecs / 3600) * 3600;
  if (interval === '1d' || interval === '1D') {
    return Math.floor(dateSecs / 86400) * 86400;
  }
  return dateSecs;
};

/* ─── Indicator Math Helpers ─────────────────────────── */
const computeBollingerBands = (unique: any[], period = 20, multiplier = 2) => {
  const upper: any[] = [];
  const middle: any[] = [];
  const lower: any[] = [];

  for (let i = 0; i < unique.length; i++) {
    if (i < period - 1) continue;
    const slice = unique.slice(i - period + 1, i + 1);
    const closes = slice.map(item => safeNum(item.p.close));
    const sum = closes.reduce((a, b) => a + b, 0);
    const mean = sum / period;

    const sqDiffSum = closes.reduce((a, b) => a + Math.pow(b - mean, 2), 0);
    const stdDev = Math.sqrt(sqDiffSum / period);
    const time = unique[i].ts;

    middle.push({ time, value: mean });
    upper.push({ time, value: mean + multiplier * stdDev });
    lower.push({ time, value: mean - multiplier * stdDev });
  }

  return { upper, middle, lower };
};

const computeVWAP = (unique: any[]) => {
  let cumulativePV = 0;
  let cumulativeV = 0;
  const vwapData: any[] = [];

  for (let i = 0; i < unique.length; i++) {
    const p = unique[i].p;
    const ts = unique[i].ts;
    const h = safeNum(p.high), l = safeNum(p.low), c = safeNum(p.close), v = safeNum(p.volume);

    const typicalPrice = (h + l + c) / 3;
    cumulativePV += typicalPrice * v;
    cumulativeV += v;

    if (cumulativeV > 0) {
      vwapData.push({ time: ts, value: cumulativePV / cumulativeV });
    }
  }
  return vwapData;
};

const computeSupportResistance = (unique: any[], currentPrice: number) => {
  const prices = unique.map(item => safeNum(item.p.close));
  const windowSize = 5;
  const levels: number[] = [];

  for (let i = windowSize; i < prices.length - windowSize; i++) {
    const val = prices[i];
    let isMax = true;
    let isMin = true;

    for (let w = -windowSize; w <= windowSize; w++) {
      if (w === 0) continue;
      if (prices[i + w] >= val) isMax = false;
      if (prices[i + w] <= val) isMin = false;
    }

    if (isMax || isMin) {
      levels.push(val);
    }
  }

  const mergedLevels: number[] = [];
  const sorted = [...levels].sort((a, b) => a - b);
  for (const lvl of sorted) {
    if (mergedLevels.length === 0) {
      mergedLevels.push(lvl);
    } else {
      const last = mergedLevels[mergedLevels.length - 1];
      if ((lvl - last) / last > 0.015) {
        mergedLevels.push(lvl);
      }
    }
  }

  const supports = mergedLevels.filter(lvl => lvl < currentPrice).reverse().slice(0, 3);
  const resistances = mergedLevels.filter(lvl => lvl > currentPrice).slice(0, 3);

  return { supports, resistances };
};

/* ─── CandleChart ───────────────────────────────────── */
export interface CandleChartProps {
  symbol: string;
  interval: string;
  period: string;
}

export const CandleChart: React.FC<CandleChartProps> = ({ symbol, interval, period }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const volumeRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const roRef = useRef<ResizeObserver | null>(null);

  // Indicator series refs
  const ema9Ref = useRef<ISeriesApi<SeriesType> | null>(null);
  const ema21Ref = useRef<ISeriesApi<SeriesType> | null>(null);
  const rsiRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const macdRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const macdSignalRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const macdHistRef = useRef<ISeriesApi<SeriesType> | null>(null);

  // New Indicator series refs
  const bbUpperRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const bbMiddleRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const bbLowerRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const vwapRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const srLinesRef = useRef<any[]>([]);

  // States
  const [chartType, setChartType] = useState<'candlestick' | 'line' | 'area' | 'bar' | 'heikin-ashi'>('candlestick');
  const [showEMA, setShowEMA] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [showBB, setShowBB] = useState(false);
  const [showVWAP, setShowVWAP] = useState(false);
  const [showSR, setShowSR] = useState(false);
  const liveMarkersRef = useRef<any[]>([]);

  // Track the last bar to update correctly on live ticks
  const lastBarRef = useRef<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  } | null>(null);

  const { data, isLoading, error } = useQuery<HistoryResponse>({
    queryKey: ['history', symbol, interval, period],
    queryFn: () => fetchHistory(symbol, interval, period),
    staleTime: 2 * 60 * 1000,
    retry: 2,
  });

  /* Destroy chart helper */
  const destroyChart = useCallback(() => {
    if (roRef.current) {
      roRef.current.disconnect();
      roRef.current = null;
    }
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    candleRef.current = null;
    volumeRef.current = null;
    ema9Ref.current = null;
    ema21Ref.current = null;
    rsiRef.current = null;
    macdRef.current = null;
    macdSignalRef.current = null;
    macdHistRef.current = null;

    bbUpperRef.current = null;
    bbMiddleRef.current = null;
    bbLowerRef.current = null;
    vwapRef.current = null;
    srLinesRef.current = [];
  }, []);

  /* Create chart whenever symbol/interval/period/chartType changes */
  useEffect(() => {
    if (!containerRef.current) return;

    destroyChart();

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0d0e14' },
        textColor: '#8b90a0',
        fontSize: 11,
        fontFamily: "'JetBrains Mono', 'Consolas', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(37,40,54,0.3)', style: LineStyle.Dotted },
        horzLines: { color: 'rgba(37,40,54,0.3)', style: LineStyle.Dotted },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#6366f1', labelBackgroundColor: '#6366f1' },
        horzLine: { color: '#6366f1', labelBackgroundColor: '#6366f1' },
      },
      rightPriceScale: {
        borderColor: '#252836',
        textColor: '#8b90a0',
      },
      leftPriceScale: {
        borderColor: '#252836',
        textColor: '#8b90a0',
        visible: true,
      },
      timeScale: {
        borderColor: '#252836',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: true,
      handleScale: true,
      width: containerRef.current.clientWidth,
      height: 440,
    });

    // Create Main Series based on chartType
    let mainSeries: ISeriesApi<SeriesType>;
    if (chartType === 'line') {
      mainSeries = chart.addSeries(LineSeries, {
        color: '#00d97e',
        lineWidth: 2,
      });
    } else if (chartType === 'area') {
      mainSeries = chart.addSeries(AreaSeries, {
        topColor: 'rgba(0, 217, 126, 0.35)',
        bottomColor: 'rgba(0, 217, 126, 0.0)',
        lineColor: '#00d97e',
        lineWidth: 2,
      });
    } else if (chartType === 'bar') {
      mainSeries = chart.addSeries(BarSeries, {
        upColor: '#00d97e',
        downColor: '#ff4757',
      });
    } else {
      // candlestick or heikin-ashi
      mainSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#00d97e',
        downColor: '#ff4757',
        borderUpColor: '#00d97e',
        borderDownColor: '#ff4757',
        wickUpColor: '#00d97e',
        wickDownColor: '#ff4757',
      });
    }

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: 'rgba(99,102,241,0.25)',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });

    // EMA overlays
    const ema9Series = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 2,
      title: 'EMA 9',
    });
    const ema21Series = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 2,
      title: 'EMA 21',
    });

    // RSI
    const rsiSeries = chart.addSeries(LineSeries, {
      color: '#ec4899',
      lineWidth: 2,
      title: 'RSI',
      priceScaleId: 'left',
    });

    // MACD
    const macdSeries = chart.addSeries(LineSeries, {
      color: '#a855f7',
      lineWidth: 2,
      title: 'MACD',
      priceScaleId: 'left',
    });
    const macdSignalSeries = chart.addSeries(LineSeries, {
      color: '#14b8a6',
      lineWidth: 1,
      title: 'MACD Sig',
      priceScaleId: 'left',
    });
    const macdHistSeries = chart.addSeries(HistogramSeries, {
      color: 'rgba(168,85,247,0.3)',
      priceScaleId: 'left',
    });

    // Bollinger Bands
    const bbUpperSeries = chart.addSeries(LineSeries, {
      color: 'rgba(99, 102, 241, 0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Upper',
    });
    const bbMiddleSeries = chart.addSeries(LineSeries, {
      color: 'rgba(99, 102, 241, 0.3)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Middle',
    });
    const bbLowerSeries = chart.addSeries(LineSeries, {
      color: 'rgba(99, 102, 241, 0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Lower',
    });

    // VWAP
    const vwapSeries = chart.addSeries(LineSeries, {
      color: '#f43f5e',
      lineWidth: 2,
      title: 'VWAP',
    });

    // Set visibility options
    ema9Series.applyOptions({ visible: showEMA });
    ema21Series.applyOptions({ visible: showEMA });
    rsiSeries.applyOptions({ visible: showRSI });
    macdSeries.applyOptions({ visible: showMACD });
    macdSignalSeries.applyOptions({ visible: showMACD });
    macdHistSeries.applyOptions({ visible: showMACD });
    bbUpperSeries.applyOptions({ visible: showBB });
    bbMiddleSeries.applyOptions({ visible: showBB });
    bbLowerSeries.applyOptions({ visible: showBB });
    vwapSeries.applyOptions({ visible: showVWAP });

    chartRef.current = chart;
    candleRef.current = mainSeries;
    volumeRef.current = volumeSeries;
    ema9Ref.current = ema9Series;
    ema21Ref.current = ema21Series;
    rsiRef.current = rsiSeries;
    macdRef.current = macdSeries;
    macdSignalRef.current = macdSignalSeries;
    macdHistRef.current = macdHistSeries;
    bbUpperRef.current = bbUpperSeries;
    bbMiddleRef.current = bbMiddleSeries;
    bbLowerRef.current = bbLowerSeries;
    vwapRef.current = vwapSeries;

    /* Resize observer */
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);
    roRef.current = ro;

    return () => {
      destroyChart();
    };
  }, [symbol, interval, period, chartType, destroyChart]);

  /* Toggle Indicators Visibility */
  useEffect(() => {
    ema9Ref.current?.applyOptions({ visible: showEMA });
    ema21Ref.current?.applyOptions({ visible: showEMA });
  }, [showEMA]);

  useEffect(() => {
    rsiRef.current?.applyOptions({ visible: showRSI });
  }, [showRSI]);

  useEffect(() => {
    macdRef.current?.applyOptions({ visible: showMACD });
    macdSignalRef.current?.applyOptions({ visible: showMACD });
    macdHistRef.current?.applyOptions({ visible: showMACD });
  }, [showMACD]);

  useEffect(() => {
    bbUpperRef.current?.applyOptions({ visible: showBB });
    bbMiddleRef.current?.applyOptions({ visible: showBB });
    bbLowerRef.current?.applyOptions({ visible: showBB });
  }, [showBB]);

  useEffect(() => {
    vwapRef.current?.applyOptions({ visible: showVWAP });
  }, [showVWAP]);

  /* Update data when query result arrives */
  useEffect(() => {
    if (!data || !candleRef.current || !volumeRef.current) return;
    if (!data.data || data.data.length === 0) return;

    const parseTime = (t: unknown): number => {
      if (t == null) return NaN;
      if (typeof t === 'number') {
        return t > 1e12 ? Math.floor(t / 1000) : Math.floor(t);
      }
      const str = String(t).trim();
      const ms = new Date(str).getTime();
      if (isNaN(ms)) return NaN;
      return Math.floor(ms / 1000);
    };

    const parsed = data.data
      .map((p) => {
        const ts = parseTime(p.time);
        return { ts, p };
      })
      .filter(({ ts, p }) => {
        if (isNaN(ts) || ts <= 0) return false;
        const o = safeNum(p.open), h = safeNum(p.high), l = safeNum(p.low), c = safeNum(p.close);
        if (o === 0 && h === 0 && l === 0 && c === 0) return false;
        return true;
      })
      .sort((a, b) => a.ts - b.ts);

    const seen = new Set<number>();
    const unique = parsed.filter(({ ts }) => {
      if (seen.has(ts)) return false;
      seen.add(ts);
      return true;
    });

    if (unique.length === 0) return;

    const lastItem = unique[unique.length - 1];
    lastBarRef.current = {
      time: lastItem.ts,
      open: safeNum(lastItem.p.open),
      high: safeNum(lastItem.p.high),
      low: safeNum(lastItem.p.low),
      close: safeNum(lastItem.p.close),
      volume: safeNum(lastItem.p.volume),
    };

    // Prepare Main Series Data based on chartType
    let mainData: any[] = [];
    if (chartType === 'heikin-ashi') {
      let prevOpen = safeNum(unique[0].p.open);
      let prevClose = safeNum(unique[0].p.close);
      mainData = unique.map(({ ts, p }, idx) => {
        const o = safeNum(p.open), h = safeNum(p.high), l = safeNum(p.low), c = safeNum(p.close);
        const haClose = (o + h + l + c) / 4;
        const haOpen = idx === 0 ? (o + c) / 2 : (prevOpen + prevClose) / 2;
        const haHigh = Math.max(h, haOpen, haClose);
        const haLow = Math.min(l, haOpen, haClose);
        prevOpen = haOpen;
        prevClose = haClose;
        return { time: ts as any, open: haOpen, high: haHigh, low: haLow, close: haClose };
      });
    } else if (chartType === 'line' || chartType === 'area') {
      mainData = unique.map(({ ts, p }) => ({
        time: ts as any,
        value: safeNum(p.close),
      }));
    } else {
      mainData = unique.map(({ ts, p }) => ({
        time: ts as any,
        open: safeNum(p.open),
        high: safeNum(p.high),
        low: safeNum(p.low),
        close: safeNum(p.close),
      }));
    }

    const volumes = unique.map(({ ts, p }) => ({
      time: ts as any,
      value: safeNum(p.volume),
      color: safeNum(p.close) >= safeNum(p.open) ? 'rgba(0,217,126,0.2)' : 'rgba(255,71,87,0.2)',
    }));

    const ema9s = unique
      .filter(({ p }) => p.ema9 != null)
      .map(({ ts, p }) => ({ time: ts as any, value: p.ema9! }));

    const ema21s = unique
      .filter(({ p }) => p.ema21 != null)
      .map(({ ts, p }) => ({ time: ts as any, value: p.ema21! }));

    const rsis = unique
      .filter(({ p }) => p.rsi != null)
      .map(({ ts, p }) => ({ time: ts as any, value: p.rsi! }));

    const macds = unique
      .filter(({ p }) => p.macd != null)
      .map(({ ts, p }) => ({ time: ts as any, value: p.macd! }));

    const macdSignals = unique
      .filter(({ p }) => p.macd_signal != null)
      .map(({ ts, p }) => ({ time: ts as any, value: p.macd_signal! }));

    const macdHists = unique
      .filter(({ p }) => p.macd_hist != null)
      .map(({ ts, p }) => ({
        time: ts as any,
        value: p.macd_hist!,
        color: p.macd_hist! >= 0 ? 'rgba(0,217,126,0.25)' : 'rgba(255,71,87,0.25)',
      }));

    try {
      candleRef.current.setData(mainData);
      volumeRef.current.setData(volumes);
      ema9Ref.current?.setData(ema9s);
      ema21Ref.current?.setData(ema21s);
      rsiRef.current?.setData(rsis);
      macdRef.current?.setData(macds);
      macdSignalRef.current?.setData(macdSignals);
      macdHistRef.current?.setData(macdHists);

      // Bollinger Bands calculation
      if (unique.length >= 20) {
        const { upper, middle, lower } = computeBollingerBands(unique, 20, 2);
        bbUpperRef.current?.setData(upper);
        bbMiddleRef.current?.setData(middle);
        bbLowerRef.current?.setData(lower);
      }

      // VWAP calculation
      const vwapData = computeVWAP(unique);
      vwapRef.current?.setData(vwapData);

      chartRef.current?.timeScale().fitContent();

      // Fetch latest signal to place historical marker on load
      const loadInitialMarker = async () => {
        try {
          const { data: sig } = await axios.get(`${API}/signals/${symbol}`);
          if (sig && sig.ensemble && sig.ensemble.direction !== 'NEUTRAL') {
            const isBuy = sig.ensemble.direction.includes('BUY');
            const lastTs = unique[unique.length - 1].ts;
            const marker = {
              time: lastTs as any,
              position: isBuy ? 'belowBar' : 'aboveBar',
              color: isBuy ? '#00d97e' : '#ff4757',
              shape: isBuy ? 'arrowUp' : 'arrowDown',
              text: `${sig.ensemble.direction.replace('_', ' ')} (${Math.round(Number(sig.ensemble.confidence) * 100)}%)`,
              id: `sig-init-${lastTs}`,
            };
            liveMarkersRef.current = [marker];
            (candleRef.current as any)?.setMarkers([marker]);
          }
        } catch (e) {
          console.warn('Failed to load initial signal marker:', e);
        }
      };
      loadInitialMarker();

    } catch (err) {
      console.error('[CandleChart] Error setting chart data:', err);
    }
  }, [data, chartType]);

  /* Support & Resistance lines redraw useEffect */
  useEffect(() => {
    if (!candleRef.current || !data || !data.data || data.data.length === 0) return;
    
    srLinesRef.current.forEach(line => {
      try {
        candleRef.current?.removePriceLine(line);
      } catch (e) {}
    });
    srLinesRef.current = [];

    if (showSR) {
      const parseTime = (t: unknown): number => {
        if (t == null) return NaN;
        if (typeof t === 'number') return t > 1e12 ? Math.floor(t / 1000) : Math.floor(t);
        const ms = new Date(String(t).trim()).getTime();
        return isNaN(ms) ? NaN : Math.floor(ms / 1000);
      };
      
      const parsed = data.data
        .map((p) => ({ ts: parseTime(p.time), p }))
        .filter(({ ts, p }) => !isNaN(ts) && ts > 0 && (p.open !== 0 || p.close !== 0))
        .sort((a, b) => a.ts - b.ts);
      
      const seen = new Set<number>();
      const unique = parsed.filter(({ ts }) => {
        if (seen.has(ts)) return false;
        seen.add(ts);
        return true;
      });
      
      if (unique.length > 0) {
        const lastPrice = safeNum(unique[unique.length - 1].p.close);
        const { supports, resistances } = computeSupportResistance(unique, lastPrice);
        supports.forEach(sup => {
          const line = candleRef.current!.createPriceLine({
            price: sup,
            color: '#00d97e',
            lineWidth: 1,
            lineStyle: LineStyle.Dotted,
            axisLabelVisible: true,
            title: `Sup ₹${sup.toFixed(1)}`,
          });
          srLinesRef.current.push(line);
        });
        resistances.forEach(res => {
          const line = candleRef.current!.createPriceLine({
            price: res,
            color: '#ff4757',
            lineWidth: 1,
            lineStyle: LineStyle.Dotted,
            axisLabelVisible: true,
            title: `Res ₹${res.toFixed(1)}`,
          });
          srLinesRef.current.push(line);
        });
      }
    }
  }, [showSR, data]);

  /* WebSocket live ticks handler */
  useEffect(() => {
    if (!candleRef.current || !volumeRef.current) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/prices`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log(`ws_chart: connected to ${wsUrl}, subscribing to ${symbol}`);
      socket.send(JSON.stringify({ action: 'subscribe', symbols: [symbol] }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.symbol?.toUpperCase() === symbol.toUpperCase()) {
          if (payload.type === 'tick') {
            const barTime = getBarTime(payload.timestamp, interval);
            const price = payload.price;
            
            let open = price, high = price, low = price, close = price;

            if (lastBarRef.current && lastBarRef.current.time === barTime) {
              open = lastBarRef.current.open;
              high = Math.max(lastBarRef.current.high, price);
              low = Math.min(lastBarRef.current.low, price);
              lastBarRef.current.high = high;
              lastBarRef.current.low = low;
              lastBarRef.current.close = price;
            } else {
              if (lastBarRef.current) {
                open = price;
              }
              lastBarRef.current = {
                time: barTime,
                open,
                high,
                low,
                close,
                volume: payload.volume || 0,
              };
            }

            if (chartType === 'line' || chartType === 'area') {
              candleRef.current?.update({ time: barTime as any, value: close });
            } else if (chartType === 'heikin-ashi') {
              const prevHaOpen = lastBarRef.current ? lastBarRef.current.open : open;
              const prevHaClose = lastBarRef.current ? lastBarRef.current.close : close;
              const haClose = (open + high + low + close) / 4;
              const haOpen = (prevHaOpen + prevHaClose) / 2;
              const haHigh = Math.max(high, haOpen, haClose);
              const haLow = Math.min(low, haOpen, haClose);
              candleRef.current?.update({ time: barTime as any, open: haOpen, high: haHigh, low: haLow, close: haClose });
            } else {
              candleRef.current?.update({ time: barTime as any, open, high, low, close });
            }

            volumeRef.current?.update({
              time: barTime as any,
              value: payload.volume || 0,
              color: close >= open ? 'rgba(0,217,126,0.2)' : 'rgba(255,71,87,0.2)',
            });

            if (payload.ema9 != null) ema9Ref.current?.update({ time: barTime as any, value: payload.ema9 });
            if (payload.ema21 != null) ema21Ref.current?.update({ time: barTime as any, value: payload.ema21 });
            if (payload.rsi != null) rsiRef.current?.update({ time: barTime as any, value: payload.rsi });
            if (payload.macd != null) macdRef.current?.update({ time: barTime as any, value: payload.macd });
            if (payload.macd_signal != null) macdSignalRef.current?.update({ time: barTime as any, value: payload.macd_signal });
            if (payload.macd_hist != null) macdHistRef.current?.update({
              time: barTime as any,
              value: payload.macd_hist,
              color: payload.macd_hist >= 0 ? 'rgba(0,217,126,0.25)' : 'rgba(255,71,87,0.25)',
            });
          } else if (payload.type === 'signal') {
            const barTime = getBarTime(payload.timestamp, interval);
            const direction = payload.direction;
            const confidence = payload.confidence;
            
            if (direction !== 'NEUTRAL') {
              const isBuy = direction.includes('BUY');
              const marker = {
                time: barTime as any,
                position: isBuy ? 'belowBar' : 'aboveBar',
                color: isBuy ? '#00d97e' : '#ff4757',
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: `${direction.replace('_', ' ')} (${Math.round(confidence * 100)}%)`,
                id: `sig-${barTime}-${direction}`,
              };
              
              const filtered = liveMarkersRef.current.filter(m => m.time !== barTime);
              const updated = [...filtered, marker].sort((a, b) => a.time - b.time);
              liveMarkersRef.current = updated;
              (candleRef.current as any)?.setMarkers(updated);
            }
          }
        }
      } catch (err) {
        console.error('ws_chart: error processing websocket message:', err);
      }
    };

    socket.onerror = (err) => {
      console.error('ws_chart: socket error', err);
    };

    return () => {
      console.log(`ws_chart: closing socket and unsubscribing from ${symbol}`);
      try {
        socket.send(JSON.stringify({ action: 'unsubscribe', symbols: [symbol] }));
      } catch (e) {}
      socket.close();
    };
  }, [symbol, interval, chartType]);

  return (
    <div style={{ position: 'relative', width: '100%', minHeight: 510 }}>
      {/* Chart Controls Panel */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 12, alignItems: 'center', fontFamily: 'var(--font)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Chart Type:</span>
          <select 
            value={chartType} 
            onChange={(e: any) => setChartType(e.target.value)}
            style={{
              background: '#1f2029',
              color: 'var(--text)',
              border: '1px solid #252836',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: 12,
              fontFamily: 'var(--font)',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="candlestick">Candlestick</option>
            <option value="line">Line</option>
            <option value="area">Area</option>
            <option value="bar">Bar (OHLC)</option>
            <option value="heikin-ashi">Heikin-Ashi</option>
          </select>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Overlays:</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: '#f59e0b' }}>
            <input type="checkbox" checked={showEMA} onChange={(e) => setShowEMA(e.target.checked)} style={{ accentColor: '#f59e0b' }} />
            EMA (9/21)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: '#ec4899' }}>
            <input type="checkbox" checked={showRSI} onChange={(e) => setShowRSI(e.target.checked)} style={{ accentColor: '#ec4899' }} />
            RSI (14)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: '#a855f7' }}>
            <input type="checkbox" checked={showMACD} onChange={(e) => setShowMACD(e.target.checked)} style={{ accentColor: '#a855f7' }} />
            MACD
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: '#3b82f6' }}>
            <input type="checkbox" checked={showBB} onChange={(e) => setShowBB(e.target.checked)} style={{ accentColor: '#3b82f6' }} />
            Bollinger Bands
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: '#f43f5e' }}>
            <input type="checkbox" checked={showVWAP} onChange={(e) => setShowVWAP(e.target.checked)} style={{ accentColor: '#f43f5e' }} />
            VWAP
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: '#10b981' }}>
            <input type="checkbox" checked={showSR} onChange={(e) => setShowSR(e.target.checked)} style={{ accentColor: '#10b981' }} />
            S&R Levels
          </label>
        </div>
      </div>

      <div
        ref={containerRef}
        className="chart-container"
        id="candlestick-chart"
        style={{ width: '100%', height: 440 }}
      />

      {/* TradingView Attribution */}
      <div style={{
        position: 'absolute',
        bottom: 12,
        right: 12,
        fontSize: 10,
        color: '#8b90a0',
        zIndex: 5,
        pointerEvents: 'auto',
        background: 'rgba(13,14,20,0.85)',
        padding: '2px 6px',
        borderRadius: '3px',
        border: '1px solid rgba(37,40,54,0.4)',
        fontFamily: 'var(--font)',
      }}>
        Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1', textDecoration: 'none', fontWeight: 600 }}>TradingView</a>
      </div>

      {isLoading && (
        <div
          className="loader-wrap"
          style={{
            position: 'absolute',
            top: 40,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(13,14,20,0.85)',
            zIndex: 10,
            minHeight: 400,
          }}
        >
          <div className="spinner" />
          <span>Loading chart data…</span>
        </div>
      )}

      {error && !isLoading && (
        <div
          style={{
            position: 'absolute',
            top: 40,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(13,14,20,0.85)',
            zIndex: 10,
          }}
        >
          <div className="error-box" style={{ margin: '16px' }}>
            ⚠ Chart data unavailable — backend may be offline or symbol not found.
          </div>
        </div>
      )}

      {!isLoading && !error && data && (!data.data || data.data.length === 0) && (
        <div
          style={{
            position: 'absolute',
            top: 40,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 8,
            background: 'rgba(13,14,20,0.85)',
            zIndex: 10,
            color: 'var(--text-muted)',
          }}
        >
          <span style={{ fontSize: 32 }}>📊</span>
          <span style={{ fontSize: 14 }}>No chart data available for this symbol/interval</span>
        </div>
      )}
    </div>
  );
};

/* ─── StockQuote ────────────────────────────────────── */
export const StockQuote: React.FC<{ symbol: string }> = ({ symbol }) => {
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [liveChange, setLiveChange] = useState<number | null>(null);
  const [liveChangePct, setLiveChangePct] = useState<number | null>(null);
  
  // AI Live Signal states
  const [liveSignalDir, setLiveSignalDir] = useState<string | null>(null);
  const [liveSignalConf, setLiveSignalConf] = useState<number | null>(null);
  const [liveSignalRationale, setLiveSignalRationale] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<QuoteResponse>({
    queryKey: ['quote', symbol],
    queryFn: () => fetchQuote(symbol),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
    retry: 2,
  });

  // Sync query data into live states when query loads
  useEffect(() => {
    if (data) {
      setLivePrice(data.price);
      setLiveChange(data.change);
      setLiveChangePct(data.change_pct);
      setLiveSignalDir(data.signal?.direction ?? 'NEUTRAL');
      setLiveSignalConf(data.signal?.confidence ?? 0.5);
      setLiveSignalRationale(data.signal?.rationale ?? '');
    }
  }, [data]);

  /* WebSocket quote/signal listener */
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/prices`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({ action: 'subscribe', symbols: [symbol] }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.symbol?.toUpperCase() === symbol.toUpperCase()) {
          if (payload.type === 'tick') {
            setLivePrice(payload.price);
            setLiveChange(payload.change);
            setLiveChangePct(payload.change_pct);
          } else if (payload.type === 'signal') {
            setLiveSignalDir(payload.direction);
            setLiveSignalConf(payload.confidence);
            setLiveSignalRationale(payload.rationale);
          }
        }
      } catch (err) {
        console.error('ws_quote: error processing websocket message:', err);
      }
    };

    return () => {
      try {
        socket.send(JSON.stringify({ action: 'unsubscribe', symbols: [symbol] }));
      } catch (e) {}
      socket.close();
    };
  }, [symbol]);

  if (isLoading) {
    return (
      <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontSize: 13 }}>
        <div className="loading-dots"><span/><span/><span/></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="error-box" style={{ marginTop: 12 }}>
        ⚠ Quote unavailable.
      </div>
    );
  }

  const priceVal = livePrice ?? data.price;
  const changeVal = liveChange ?? data.change;
  const pctVal = liveChangePct ?? data.change_pct;
  const directionVal = liveSignalDir ?? (data.signal?.direction as string) ?? 'NEUTRAL';
  const confidenceVal = liveSignalConf ?? (data.signal?.confidence as number) ?? 0.5;
  const rationaleVal = liveSignalRationale ?? data.signal?.rationale ?? '';

  const isUp = pctVal >= 0;
  const currency = symbol.includes('-USD') || symbol.includes('USD') ? '$' : '₹';

  return (
    <>
      {/* Price overlay shown above chart */}
      <div className="chart-overlay" id="chart-overlay">
        <div className="chart-symbol">{data.ticker}</div>
        <div className="chart-price mono">
          {currency}{fmt(priceVal)}
        </div>
        <div className={`chart-change mono ${isUp ? 'positive' : 'negative'}`}>
          {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{fmt(changeVal)} ({isUp ? '+' : ''}{fmt(pctVal, 3)}%)
        </div>
      </div>

      {/* Metrics strip below chart */}
      <div className="quote-metrics" id="quote-metrics" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 16 }}>
        <div className="metric-box">
          <div className="metric-label">Volume</div>
          <div className="metric-value mono">
            {safeNum(data.volume) >= 1_000_000
              ? `${(safeNum(data.volume) / 1_000_000).toFixed(1)}M`
              : safeNum(data.volume) >= 1_000
              ? `${(safeNum(data.volume) / 1_000).toFixed(0)}K`
              : safeNum(data.volume)}
          </div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Market Cap</div>
          <div className="metric-value mono">{fmtBig(safeNum(data.market_cap))}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">52W High</div>
          <div className="metric-value mono positive">{currency}{fmt(safeNum(data.high_52w))}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">52W Low</div>
          <div className="metric-value mono negative">{currency}{fmt(safeNum(data.low_52w))}</div>
        </div>
        
        {/* Full width row for AI Signal and Rationale */}
        <div className="metric-box" style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: 8, padding: '12px 16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="metric-label" style={{ margin: 0 }}>AI Live Prediction Signal</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className={`signal-badge signal-${directionVal}`}>
                {directionVal.replace('_', ' ')}
              </span>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Confidence: {Math.round(confidenceVal * 100)}%
              </span>
            </div>
          </div>
          
          <div className="confidence-bar" style={{ height: 6, borderRadius: 3, background: 'rgba(37,40,54,0.6)', overflow: 'hidden' }}>
            <div
              className="confidence-fill"
              style={{
                height: '100%',
                background: directionVal.includes('BUY') ? '#00d97e' : directionVal.includes('SELL') ? '#ff4757' : '#8b90a0',
                width: `${Math.round(confidenceVal * 100)}%`,
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          {rationaleVal && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: '1.4', fontStyle: 'italic', borderTop: '1px solid rgba(37,40,54,0.4)', paddingTop: 6, marginTop: 4 }}>
              💡 {rationaleVal}
            </div>
          )}
        </div>
      </div>
    </>
  );
};
