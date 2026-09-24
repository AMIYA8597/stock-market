/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useRef, useState } from "react";
import {
  type IChartApi,
  type HistogramData,
  type UTCTimestamp,
  CandlestickSeries, LineSeries, AreaSeries, HistogramSeries, BaselineSeries, BarSeries,
  createSeriesMarkers,
} from 'lightweight-charts';
import { MousePointer, MoveRight, Minus, Layers, Trash2 } from "lucide-react";
// Patterns now fetched from backend via /api/v1/market/patterns/{symbol}
import { computeIndicators, type Candle } from "@/utils/indicators";
import {
  type PriceBar,
  toUtcTimestamp,
  buildHeikinAshi,
  buildRenko,
  buildPointAndFigure,
  buildKagi,
  buildRangeBars,
  buildThreeLineBreak,
  buildTickChart,
  buildSpread,
  buildRelativeStrength,
  calculateVolumeProfile,
  calculateMarketProfile,
} from "@/utils/chartFormatters";
import { marketApi } from "@/lib/api-client";

import {
  useChartInstance,
  type LiveChartApi,
} from "./tradingview/useChartInstance";
import { drawIndicators } from "./tradingview/indicatorsRenderer";
import { drawSMC } from "./tradingview/smcRenderer";
import { drawSubPanes } from "./tradingview/subpaneRenderer";

import { type Quote } from "@neuroquant/types";

// Stable references for default prop values. An inline `= []` / `= {}` default
// parameter is re-evaluated (new identity) on every render — when that value is a
// dependency of an effect which also sets state unconditionally, it causes an
// infinite render loop ("Maximum update depth exceeded").
const EMPTY_PREDICTIONS: LightweightCandlestickChartProps["predictions"] = [];
const EMPTY_INDICATORS: NonNullable<LightweightCandlestickChartProps["indicators"]> = {};

interface LightweightCandlestickChartProps {
  bars: PriceBar[];
  height?: number;
  chartStyle?:
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
    | "mountain";
  indicators?: {
    ema9?: boolean;
    ema21?: boolean;
    ema50?: boolean;
    ema200?: boolean;
    sma20?: boolean;
    sma50?: boolean;
    sma100?: boolean;
    bollingerBands?: boolean;
    patterns?: boolean;
    superTrend?: boolean;
    ichimoku?: boolean;
    vwap?: boolean;
    rsi?: boolean;
    macd?: boolean;
    atr?: boolean;
    smc?: boolean;
  };
  predictions?: {
    target_date: string;
    predicted_price: number;
    prediction_low?: number;
    prediction_high?: number;
  }[];
  symbol?: string;
  liveTick?: any;
}

function sanitizeSeriesData<T extends { time: unknown }>(data: T[]): T[] {
  if (data.length === 0) return [];

  // Create a sorted copy by timestamp ascending to satisfy lightweight-charts requirements
  const sorted = [...data].sort((a, b) => {
    const timeA = a.time as
      | string
      | number
      | { year: number; month: number; day: number };
    const timeB = b.time as
      | string
      | number
      | { year: number; month: number; day: number };
    const tA =
      typeof timeA === "object" && timeA !== null
        ? Math.floor(
            new Date(`${timeA.year}-${timeA.month}-${timeA.day}`).getTime() /
              1000,
          )
        : Number(timeA);
    const tB =
      typeof timeB === "object" && timeB !== null
        ? Math.floor(
            new Date(`${timeB.year}-${timeB.month}-${timeB.day}`).getTime() /
              1000,
          )
        : Number(timeB);
    return tA - tB;
  });

  const sanitized: T[] = [];
  let lastTimeValue = 0;
  for (let i = 0; i < sorted.length; i++) {
    const item = sorted[i];
    if (!item) continue;
    const itemTime = item.time as
      | string
      | number
      | { year: number; month: number; day: number };
    let time =
      typeof itemTime === "object" && itemTime !== null
        ? Math.floor(
            new Date(
              `${itemTime.year}-${itemTime.month}-${itemTime.day}`,
            ).getTime() / 1000,
          )
        : Number(itemTime);

    if (time <= lastTimeValue) {
      time = lastTimeValue + 1;
    }
    lastTimeValue = time;
    sanitized.push({
      ...item,
      time: time as unknown as T["time"],
    });
  }
  return sanitized;
}

interface Drawing {
  id: string;
  type: "trendline" | "horizontal" | "fibonacci";
  points: { time: number; price: number }[];
}

export function LightweightCandlestickChart({
  bars,
  height = 400,
  chartStyle = "candlestick",
  indicators = EMPTY_INDICATORS,
  predictions = EMPTY_PREDICTIONS,
  symbol = "SPY",
  liveTick,
}: LightweightCandlestickChartProps): JSX.Element {
  const mainContainerRef = useRef<HTMLDivElement | null>(null);
  const drawingIdCounter = useRef(0);
  const [legend, setLegend] = useState<{
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    timestamp: string;
  } | null>(null);

  const [activeTool, setActiveTool] = useState<
    "cursor" | "trendline" | "horizontal" | "fibonacci"
  >("cursor");
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [tempStartPoint, setTempStartPoint] = useState<{
    time: number;
    price: number;
  } | null>(null);
  const [tempEndPoint, setTempEndPoint] = useState<{
    time: number;
    price: number;
  } | null>(null);
  const [renderTrigger, setRenderTrigger] = useState(0);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mainSeriesRef = useRef<any>(null);

  const cleanSymbol = symbol
    ? symbol
        .replace(".NS", "")
        .replace("^NSEI", "NIFTY 50")
        .replace("^NSEBANK", "BANK NIFTY")
        .replace("^BSESN", "SENSEX")
    : "";
  const mainChartRef = useRef<IChartApi | null>(null);
  const lastSymbolRef = useRef<string>("");
  const lastFirstBarTimeRef = useRef<string>("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const latestLogicalRangeRef = useRef<any>(null);

  // Support & Resistance Zones State and Fetcher
  const [zones, setZones] = useState<
    { type: string; min: number; max: number; avg: number; mode: string; touches: number }[]
  >([]);

  // Patterns State and Fetcher
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [patternMarkers, setPatternMarkers] = useState<any[]>([]);

  const {
    ema9 = false,
    ema21 = false,
    ema50 = false,
    ema200 = false,
    sma20 = false,
    sma50 = false,
    sma100 = false,
    bollingerBands = false,
    patterns = false,
    superTrend = false,
    ichimoku = false,
    vwap = false,
    rsi = false,
    macd = false,
    atr = false,
    smc = false,
  } = indicators;

  useEffect(() => {
    if (!symbol) return;
    let active = true;
    async function fetchZones() {
      try {
        const data = await marketApi.getZones(symbol!);
        if (active) {
          const allZones = [
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ...(data.classical_zones || []).map((z: any) => ({
              ...z,
              mode: "Classical",
            })),
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ...(data.deep_learning_zones || []).map((z: any) => ({
              ...z,
              mode: "DL",
            })),
          ];
          setZones(allZones);
        }
      } catch (e) {
        console.error("Failed to fetch S/R zones for chart", e);
      }
    }
    void fetchZones();

    // Fetch Patterns
    async function fetchPatterns() {
      if (!patterns) return;
      try {
        const data = await marketApi.getPatterns(symbol!);
        if (active) {
          setPatternMarkers(data.markers || []);
        }
      } catch (e) {
        console.error("Failed to fetch patterns for chart", e);
      }
    }
    void fetchPatterns();

    return () => {
      active = false;
    };
  }, [symbol, patterns]);

  const { chart: mainChart } = useChartInstance({
    containerRef: mainContainerRef,
    height,
  });

  const getCoordinates = (point: { time: number; price: number }) => {
    if (!mainChartRef.current || !mainSeriesRef.current) return null;
    try {
      const timeScale = mainChartRef.current.timeScale();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const x = timeScale.timeToCoordinate(point.time as any);
      const y = mainSeriesRef.current.priceToCoordinate(point.price);
      if (x === null || y === null) return null;
      return { x, y };
    } catch (e) {
      return null;
    }
  };

  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (activeTool === "cursor") return;
    if (!mainChartRef.current || !mainSeriesRef.current) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    try {
      const timeScale = mainChartRef.current.timeScale();
      const time = timeScale.coordinateToTime(mouseX);
      const price = mainSeriesRef.current.coordinateToPrice(mouseY);

      if (time === null || price === null) return;

      if (activeTool === "horizontal") {
        drawingIdCounter.current += 1;
        const newDrawing: Drawing = {
          id: `drawing-${drawingIdCounter.current}`,
          type: "horizontal",
          points: [{ time: Number(time), price }],
        };
        setDrawings((prev) => [...prev, newDrawing]);
        setActiveTool("cursor");
      } else if (activeTool === "trendline" || activeTool === "fibonacci") {
        if (!tempStartPoint) {
          setTempStartPoint({ time: Number(time), price });
        } else {
          drawingIdCounter.current += 1;
          const newDrawing: Drawing = {
            id: `drawing-${drawingIdCounter.current}`,
            type: activeTool,
            points: [tempStartPoint, { time: Number(time), price }],
          };
          setDrawings((prev) => [...prev, newDrawing]);
          setTempStartPoint(null);
          setTempEndPoint(null);
          setActiveTool("cursor");
        }
      }
    } catch (err) {
      console.error("Error drawing point:", err);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (activeTool === "cursor" || !tempStartPoint) return;
    if (!mainChartRef.current || !mainSeriesRef.current) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    try {
      const timeScale = mainChartRef.current.timeScale();
      const time = timeScale.coordinateToTime(mouseX);
      const price = mainSeriesRef.current.coordinateToPrice(mouseY);

      if (time === null || price === null) return;
      setTempEndPoint({ time: Number(time), price });
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    if (!mainChart) return;
    const handleRangeChange = () => {
      setRenderTrigger((prev) => prev + 1);
    };
    mainChart.timeScale().subscribeVisibleLogicalRangeChange(handleRangeChange);
    return () => {
      mainChart
        .timeScale()
        .unsubscribeVisibleLogicalRangeChange(handleRangeChange);
    };
  }, [mainChart]);

  const levelColor = (level: number) => {
    if (level === 1.0 || level === 0.0) return "#EF5350";
    if (level === 0.5) return "#FFB800";
    if (level === 0.618) return "#26A69A";
    return "rgba(255, 255, 255, 0.4)";
  };

  useEffect(() => {
    if (
      !mainChart ||
      !(mainChart as LiveChartApi).isAlive ||
      !mainContainerRef.current
    )
      return;

    if (bars.length === 0) {
      return () => {
        // No-op cleanup for empty bars state
      };
    }

    const firstBarTime = bars[0]?.timestamp || "";
    const configChanged =
      symbol !== lastSymbolRef.current ||
      firstBarTime !== lastFirstBarTimeRef.current;
    lastSymbolRef.current = symbol;
    lastFirstBarTimeRef.current = firstBarTime;

    if (configChanged) {
      latestLogicalRangeRef.current = null;
    }

    mainChartRef.current = mainChart;
    const subCharts: IChartApi[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const addedSeries: any[] = [];

    // Closes and times arrays
    const closes = bars.map((bar) => bar.close);
    const times = bars.map((bar) => toUtcTimestamp(bar.timestamp));

    console.log(
      `[HOP 8 setData] chartStyle=${chartStyle}, bars in=${bars.length}, first=${bars[0]?.timestamp}, last=${bars[bars.length - 1]?.timestamp}`,
    );

    // Prepare calculations for indicators
    const candleData: Candle[] = bars.map((b) => ({
      time: toUtcTimestamp(b.timestamp),
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
      volume: b.volume,
    }));

    const indResults = computeIndicators(candleData, {
      rsi,
      macd,
      vwap,
      atr,
      superTrend,
      ichimoku,
      smc,
    });

    // Detect patterns and build markers
    const baseMarkers = patterns ? patternMarkers : [];
    const smcMarkers =
      smc && indResults.smc
        ? indResults.smc.marketStructure.map((ms) => ({
            time: ms.time as UTCTimestamp,
            position: (ms.direction === "bullish" ? "aboveBar" : "belowBar") as
              | "aboveBar"
              | "belowBar"
              | "inBar",
            color: ms.type === "CHoCH" ? "#F50057" : "#FFEB3B",
            shape: (ms.direction === "bullish" ? "arrowUp" : "arrowDown") as
              | "arrowUp"
              | "arrowDown"
              | "circle"
              | "square",
            text: `${ms.type} (${Math.round(ms.level)})`,
          }))
        : [];

    const finalMarkers = [...baseMarkers, ...smcMarkers].sort(
      (a, b) => Number(a.time) - Number(b.time),
    );

    // Create Main Series Based on Selected Chart Style
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let mainSeries: any = null;

    if (chartStyle === "line") {
      mainSeries = mainChart.addSeries(LineSeries, { color: "#00E676", lineWidth: 2 });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            value: bar.close,
          })),
        ),
      );
    } else if (chartStyle === "area") {
      mainSeries = mainChart.addSeries(AreaSeries, {
        topColor: "rgba(0, 230, 118, 0.3)",
        bottomColor: "rgba(0, 230, 118, 0.0)",
        lineColor: "#00E676",
        lineWidth: 2,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            value: bar.close,
          })),
        ),
      );
    } else if (chartStyle === "ohlc-bar") {
      mainSeries = mainChart.addSeries(BarSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        openVisible: true,
        thinBars: false,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          })),
        ),
      );
    } else if (chartStyle === "baseline") {
      const firstClose = bars[0]?.close ?? 0;
      mainSeries = mainChart.addSeries(BaselineSeries, {
        baseValue: { type: "price", price: firstClose },
        topFillColor1: "rgba(0, 230, 118, 0.3)",
        topFillColor2: "rgba(0, 230, 118, 0.0)",
        topLineColor: "#00E676",
        bottomFillColor1: "rgba(255, 59, 92, 0.0)",
        bottomFillColor2: "rgba(255, 59, 92, 0.3)",
        bottomLineColor: "#FF3B5C",
        lineWidth: 2,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            value: bar.close,
          })),
        ),
      );
    } else if (chartStyle === "heikin-ashi") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(sanitizeSeriesData(buildHeikinAshi(bars)));
    } else if (chartStyle === "hollow-candlestick") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "rgba(0,0,0,0)",
        borderUpColor: "#00E676",
        wickUpColor: "#00E676",
        downColor: "#FF3B5C",
        borderDownColor: "#FF3B5C",
        wickDownColor: "#FF3B5C",
        borderVisible: true,
        wickVisible: true,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          })),
        ),
      );
    } else if (chartStyle === "volume") {
      mainSeries = mainChart.addSeries(AreaSeries, {
        topColor: "rgba(0, 212, 245, 0.4)",
        bottomColor: "rgba(0, 212, 245, 0.0)",
        lineColor: "#00D4F5",
        lineWidth: 2,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            value: bar.volume,
          })),
        ),
      );
    } else if (chartStyle === "renko") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(sanitizeSeriesData(buildRenko(bars)));
    } else if (chartStyle === "point-figure") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickVisible: false,
        borderVisible: true,
      });
      mainSeries.setData(sanitizeSeriesData(buildPointAndFigure(bars)));
    } else if (chartStyle === "kagi") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickVisible: false,
        borderVisible: true,
      });
      mainSeries.setData(sanitizeSeriesData(buildKagi(bars)));
    } else if (chartStyle === "range-bar") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(sanitizeSeriesData(buildRangeBars(bars)));
    } else if (chartStyle === "three-line-break") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickVisible: false,
        borderVisible: true,
      });
      mainSeries.setData(sanitizeSeriesData(buildThreeLineBreak(bars)));
    } else if (chartStyle === "equivolume") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        borderVisible: true,
        wickVisible: true,
      });
      const avgVolume =
        bars.reduce((sum, bar) => sum + bar.volume, 0) / (bars.length || 1);
      const equivData = bars.map((bar) => {
        const ratio = Math.max(
          0.2,
          Math.min(1.0, bar.volume / (avgVolume || 1)),
        );
        const upColor = `rgba(0, 230, 118, ${ratio})`;
        const downColor = `rgba(255, 59, 92, ${ratio})`;
        const color = bar.close >= bar.open ? upColor : downColor;
        return {
          time: toUtcTimestamp(bar.timestamp),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
          color,
          borderColor: color,
          wickColor: color,
        };
      });
      mainSeries.setData(sanitizeSeriesData(equivData));
    } else if (chartStyle === "tick") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(sanitizeSeriesData(buildTickChart(bars)));
    } else if (chartStyle === "volume-profile") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          })),
        ),
      );
      const levels = calculateVolumeProfile(bars);
      mainSeries.createPriceLine({
        price: levels.poc,
        color: "#FF9800",
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: "POC",
      });
      mainSeries.createPriceLine({
        price: levels.vah,
        color: "#E040FB",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: "VAH",
      });
      mainSeries.createPriceLine({
        price: levels.val,
        color: "#00E5FF",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: "VAL",
      });
    } else if (chartStyle === "market-profile") {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          })),
        ),
      );
      const levels = calculateMarketProfile(bars);
      mainSeries.createPriceLine({
        price: levels.poc,
        color: "#FF5722",
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: "TPO POC",
      });
      mainSeries.createPriceLine({
        price: levels.vah,
        color: "#9C27B0",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: "TPO VAH",
      });
      mainSeries.createPriceLine({
        price: levels.val,
        color: "#00E676",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: "TPO VAL",
      });
    } else if (chartStyle === "spread") {
      mainSeries = mainChart.addSeries(AreaSeries, {
        topColor: "rgba(236, 72, 153, 0.3)",
        bottomColor: "rgba(236, 72, 153, 0.0)",
        lineColor: "#EC4899",
        lineWidth: 2,
      });
      mainSeries.setData(sanitizeSeriesData(buildSpread(bars)));
    } else if (chartStyle === "relative-strength") {
      mainSeries = mainChart.addSeries(LineSeries, { color: "#8B5CF6", lineWidth: 2 });
      mainSeries.setData(sanitizeSeriesData(buildRelativeStrength(bars)));
    } else if (chartStyle === "mountain") {
      mainSeries = mainChart.addSeries(AreaSeries, {
        topColor: "rgba(0, 212, 245, 0.4)",
        bottomColor: "rgba(0, 212, 245, 0.0)",
        lineColor: "#00D4F5",
        lineWidth: 3,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            value: bar.close,
          })),
        ),
      );
    } else {
      mainSeries = mainChart.addSeries(CandlestickSeries, {
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(
        sanitizeSeriesData(
          bars.map((bar) => ({
            time: toUtcTimestamp(bar.timestamp),
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          })),
        ),
      );
    }

    if (mainSeries) {
      addedSeries.push(mainSeries);
      mainSeriesRef.current = mainSeries;
      if (finalMarkers.length > 0) {
        // lightweight-charts v5 removed ISeriesApi.setMarkers() — markers are now
        // applied via the separate series-markers plugin.
        createSeriesMarkers(mainSeries, finalMarkers);
      }

      // Draw Support & Resistance zones — cap to the strongest few nearest the
      // current price per side, one labeled line each, or the axis fills with
      // dozens of overlapping labels (every zone x 3 lines) and becomes unreadable.
      if (zones.length > 0) {
        const lastClose = bars.length > 0 ? bars[bars.length - 1]!.close : null;
        const MAX_PER_SIDE = 3;

        const pickTopZones = (side: "support" | "resistance") =>
          zones
            .filter((z) => z.type === side)
            .sort((a, b) => {
              if (lastClose === null) return b.touches - a.touches;
              return Math.abs(a.avg - lastClose) - Math.abs(b.avg - lastClose);
            })
            .slice(0, MAX_PER_SIDE);

        const visibleZones = [
          ...pickTopZones("support"),
          ...pickTopZones("resistance"),
        ];

        visibleZones.forEach((zone) => {
          const isSupport = zone.type === "support";
          const color = isSupport
            ? "rgba(0, 230, 118, 0.65)"
            : "rgba(255, 59, 92, 0.65)";

          mainSeries.createPriceLine({
            price: zone.avg,
            color: color,
            lineWidth: 2,
            lineStyle: 0,
            axisLabelVisible: true,
            title: `${zone.mode} ${isSupport ? "Support" : "Resistance"}`,
          });
        });
      }
    }

    // Standard volume histogram overlay
    const volumeSeries = mainChart.addSeries(HistogramSeries, {
      priceScaleId: "",
      priceFormat: { type: "volume" },
      color: "rgba(0,212,245,0.45)",
    });
    addedSeries.push(volumeSeries);

    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    const volumeData: HistogramData[] = bars.map((bar) => ({
      time: toUtcTimestamp(bar.timestamp),
      value: bar.volume,
      color:
        bar.close >= bar.open ? "rgba(0,230,118,0.3)" : "rgba(255,59,92,0.3)",
    }));
    volumeSeries.setData(sanitizeSeriesData(volumeData));

    // Draw Advanced Indicators & SMC overlays
    drawIndicators(
      mainChart,
      {
        ema9,
        ema21,
        ema50,
        ema200,
        sma20,
        sma50,
        sma100,
        bollingerBands,
        superTrend,
        ichimoku,
        vwap,
      },
      closes,
      times,
      indResults,
      addedSeries,
    );

    drawSMC(mainChart, indResults, bars, addedSeries);

    // Draw stacked synchronized oscillator panes
    drawSubPanes(
      mainChart,
      indResults,
      rsi,
      macd,
      atr,
      addedSeries,
    );

    // Add TradingView attribution
    mainChart.applyOptions({
      localization: {
        priceFormatter: (price: number) => price.toFixed(2),
      },
    });

    // Draw AI Forecast Projection lines
    if (predictions && predictions.length > 0 && chartStyle !== "volume") {
      const lastBar = bars[bars.length - 1];
      if (lastBar) {
        const lastTime = toUtcTimestamp(lastBar.timestamp);
        const lastClose = lastBar.close;

        const predLineSeries = mainChart.addSeries(LineSeries, {
          color: "rgba(0, 212, 245, 0.85)",
          lineWidth: 2,
          lineStyle: 1,
          title: "AI Forecast",
        });
        addedSeries.push(predLineSeries);

        const sortedPredictions = [...predictions].sort(
          (a, b) =>
            new Date(a.target_date).getTime() -
            new Date(b.target_date).getTime(),
        );

        const lineData = [
          { time: lastTime, value: lastClose },
          ...sortedPredictions.map((p) => ({
            time: toUtcTimestamp(p.target_date),
            value: p.predicted_price,
          })),
        ];

        const uniqueLineData = [];
        let lastTimestamp = 0;
        for (const pt of lineData) {
          if (pt.time > lastTimestamp) {
            uniqueLineData.push(pt);
            lastTimestamp = pt.time;
          }
        }
        predLineSeries.setData(uniqueLineData);

        const hasBounds = sortedPredictions.every(
          (p) =>
            p.prediction_low !== undefined && p.prediction_high !== undefined,
        );
        if (hasBounds) {
          const upperSeries = mainChart.addSeries(LineSeries, {
            color: "rgba(0, 212, 245, 0.4)",
            lineWidth: 1,
            lineStyle: 2,
            title: "Forecast Upper",
          });
          const lowerSeries = mainChart.addSeries(LineSeries, {
            color: "rgba(0, 212, 245, 0.4)",
            lineWidth: 1,
            lineStyle: 2,
            title: "Forecast Lower",
          });
          addedSeries.push(upperSeries);
          addedSeries.push(lowerSeries);

          const upperData = [
            { time: lastTime, value: lastClose },
            ...sortedPredictions.map((p) => ({
              time: toUtcTimestamp(p.target_date),
              value: p.prediction_high!,
            })),
          ];
          const lowerData = [
            { time: lastTime, value: lastClose },
            ...sortedPredictions.map((p) => ({
              time: toUtcTimestamp(p.target_date),
              value: p.prediction_low!,
            })),
          ];

          const uniqueUpperData = [];
          const uniqueLowerData = [];
          let uTS = 0;
          let lTS = 0;
          for (const pt of upperData) {
            if (pt.time > uTS) {
              uniqueUpperData.push(pt);
              uTS = pt.time;
            }
          }
          for (const pt of lowerData) {
            if (pt.time > lTS) {
              uniqueLowerData.push(pt);
              lTS = pt.time;
            }
          }

          upperSeries.setData(uniqueUpperData);
          lowerSeries.setData(uniqueLowerData);
        }
      }
    }

    // Setup timescale layout bottom visibility
    const allCharts: IChartApi[] = [mainChart, ...subCharts];
    const bottomActiveIdx = allCharts.length - 1;
    allCharts.forEach((ch, idx) => {
      ch.timeScale().applyOptions({
        visible: idx === bottomActiveIdx,
      });
    });

    // Logical Range Zoom/Pan Synchronization
    let isSyncing = false;
    allCharts.forEach((ch) => {
      ch.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) {
          latestLogicalRangeRef.current = range;
        }
        if (isSyncing || !range) return;
        isSyncing = true;
        allCharts.forEach((targetCh) => {
          if (targetCh !== ch) {
            targetCh.timeScale().setVisibleLogicalRange(range);
          }
        });
        isSyncing = false;
      });
    });

    if (configChanged || !latestLogicalRangeRef.current) {
      mainChart.timeScale().fitContent();
    } else {
      mainChart
        .timeScale()
        .setVisibleLogicalRange(latestLogicalRangeRef.current);
    }

    // Initialize legend with latest bar
    if (bars.length > 0) {
      const lastBar = bars[bars.length - 1];
      if (lastBar) {
        setLegend({
          open: lastBar.open,
          high: lastBar.high,
          low: lastBar.low,
          close: lastBar.close,
          volume: lastBar.volume,
          timestamp: lastBar.timestamp,
        });
      }
    }

    // Legend crosshair sync
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleCrosshairMove = (param: any) => {
      if (!param || !param.time || !param.point) {
        if (bars.length > 0) {
          const lastBar = bars[bars.length - 1];
          if (lastBar) {
            setLegend({
              open: lastBar.open,
              high: lastBar.high,
              low: lastBar.low,
              close: lastBar.close,
              volume: lastBar.volume,
              timestamp: lastBar.timestamp,
            });
          }
        }
        return;
      }

      const time = param.time;
      const matchingBar = bars.find(
        (b) => toUtcTimestamp(b.timestamp) === time,
      );
      if (matchingBar) {
        setLegend({
          open: matchingBar.open,
          high: matchingBar.high,
          low: matchingBar.low,
          close: matchingBar.close,
          volume: matchingBar.volume,
          timestamp: matchingBar.timestamp,
        });
      }
    };

    mainChart.subscribeCrosshairMove(handleCrosshairMove);

    // Resize observer: sub-pane charts need manual width sync since they don't use autoSize
    // The main chart uses autoSize=true so it handles its own resizing
    const observer = new ResizeObserver(() => {
      if (!mainContainerRef.current) return;
      const width = mainContainerRef.current.clientWidth;
      subCharts.forEach((ch) => {
        try {
          ch.applyOptions({ width });
        } catch {
          /* ignore */
        }
      });
    });
    observer.observe(mainContainerRef.current);

    return () => {
      mainChart.unsubscribeCrosshairMove(handleCrosshairMove);
      observer.disconnect();
      subCharts.forEach((ch) => ch.remove());
      addedSeries.forEach((ser) => {
        try {
          mainChart.removeSeries(ser);
        } catch (e) {
          // ignore
        }
      });
      mainChartRef.current = null;
    };
  }, [
    mainChart,
    bars,
    chartStyle,
    ema9,
    ema21,
    ema50,
    ema200,
    sma20,
    sma50,
    sma100,
    bollingerBands,
    patterns,
    predictions,
    superTrend,
    ichimoku,
    vwap,
    rsi,
    macd,
    atr,
    smc,
    cleanSymbol,
    symbol,
  ]);

  useEffect(() => {
    if (liveTick && mainSeriesRef.current && mainChartRef.current) {
      try {
        const time = toUtcTimestamp(liveTick.timestamp);
        // Only update if the tick is newer than or equal to the last candle
        // and doesn't break the ascending time order
        mainSeriesRef.current.update({
          time,
          open: liveTick.open ?? liveTick.price,
          high: liveTick.high ?? liveTick.price,
          low: liveTick.low ?? liveTick.price,
          close: liveTick.price,
          volume: liveTick.volume ?? 0,
        });
      } catch (err) {
        console.warn("[Chart] live tick update failed (likely time out of order):", err);
      }
    }
  }, [liveTick]);

  const formatVolume = (val: number): string => {
    if (val >= 1e6) return (val / 1e6).toFixed(2) + "M";
    if (val >= 1e3) return (val / 1e3).toFixed(1) + "K";
    return String(val);
  };

  return (
    <div className="flex flex-col gap-1.5 h-full w-full relative overflow-y-auto ds-scrollable">
      {legend && (
        <div className="absolute top-2 left-12 z-[99] pointer-events-none flex flex-wrap gap-x-2 gap-y-0.5 rounded bg-[rgba(10,14,24,0.72)] backdrop-blur-sm border border-[rgba(255,255,255,0.08)] px-2 py-0.5 text-[10px] font-mono text-[var(--nq-text-secondary)] shadow-md select-none">
          <span className="font-semibold text-[var(--nq-text-primary)] mr-1.5 flex items-center gap-1.5">
            {cleanSymbol}
            {liveTick?.source && (
              <span className={`rounded border px-1 py-px text-[8px] font-medium uppercase tracking-wider ${
                liveTick.source === "realtime" ? "text-[#00E676] border-[#00E676] bg-[rgba(0,230,118,0.1)]" :
                liveTick.source === "computed" ? "text-[#B388FF] border-[#B388FF] bg-[rgba(179,136,255,0.1)]" :
                "text-[#FFB800] border-[#FFB800] bg-[rgba(255,184,0,0.1)]"
              }`}>
                {liveTick.source === "realtime" ? "Real-time" : liveTick.source === "computed" ? "Computed" : "Delayed"}
              </span>
            )}
          </span>
          <span>
            O:
            <span
              className={
                legend.close >= legend.open
                  ? "text-[#00e676] ml-0.5"
                  : "text-[#ff3b5c] ml-0.5"
              }
            >
              {legend.open.toFixed(2)}
            </span>
          </span>
          <span className="ml-1.5">
            H:
            <span
              className={
                legend.close >= legend.open
                  ? "text-[#00e676] ml-0.5"
                  : "text-[#ff3b5c] ml-0.5"
              }
            >
              {legend.high.toFixed(2)}
            </span>
          </span>
          <span className="ml-1.5">
            L:
            <span
              className={
                legend.close >= legend.open
                  ? "text-[#00e676] ml-0.5"
                  : "text-[#ff3b5c] ml-0.5"
              }
            >
              {legend.low.toFixed(2)}
            </span>
          </span>
          <span className="ml-1.5">
            C:
            <span
              className={
                legend.close >= legend.open
                  ? "text-[#00e676] ml-0.5"
                  : "text-[#ff3b5c] ml-0.5"
              }
            >
              {legend.close.toFixed(2)}
            </span>
          </span>
          <span className="ml-1.5">
            V:
            <span className="text-[var(--nq-accent-cyan)] ml-0.5">
              {formatVolume(legend.volume)}
            </span>
          </span>
        </div>
      )}

      {/* Main Container Wrapper */}
      <div className="relative w-full flex-1 min-h-[240px] overflow-hidden">
        <div ref={mainContainerRef} className="absolute inset-0" />

        {/* Floating Drawing Toolbar */}
        <div className="absolute left-2 top-10 z-[30] flex flex-col gap-1 rounded border border-[var(--nq-border)] bg-[rgba(14,17,23,0.85)] p-1 shadow-2xl backdrop-blur-md">
          {(
            [
              {
                tool: "cursor",
                icon: MousePointer,
                tooltip: "Crosshair / Zoom",
              },
              { tool: "trendline", icon: MoveRight, tooltip: "Trend Line" },
              { tool: "horizontal", icon: Minus, tooltip: "Horizontal Line" },
              {
                tool: "fibonacci",
                icon: Layers,
                tooltip: "Fibonacci Retracement",
              },
            ] as const
          ).map(({ tool, icon: Icon, tooltip }) => (
            <button
              key={tool}
              type="button"
              onClick={() => {
                setActiveTool(tool);
                setTempStartPoint(null);
                setTempEndPoint(null);
              }}
              className={`rounded p-1.5 transition-all duration-150 ${
                activeTool === tool
                  ? "bg-[var(--nq-accent-cyan)]/25 text-[var(--nq-accent-cyan)] shadow-[0_0_8px_rgba(0,212,245,0.15)]"
                  : "text-[var(--nq-text-secondary)] hover:bg-white/5 hover:text-[var(--nq-text-primary)]"
              }`}
              title={tooltip}
            >
              <Icon className="h-3.5 w-3.5" />
            </button>
          ))}
          {drawings.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setDrawings([]);
                setTempStartPoint(null);
                setTempEndPoint(null);
                setActiveTool("cursor");
              }}
              className="rounded p-1.5 text-[var(--nq-accent-red)] hover:bg-[var(--nq-accent-red)]/10 hover:text-[var(--nq-accent-red)] transition-all duration-150 border-t border-[var(--nq-border)] mt-1 pt-1.5"
              title="Clear all drawings"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Drawing SVG Overlay */}
        <svg
          key={renderTrigger}
          className={`absolute inset-0 z-20 ${activeTool !== "cursor" ? "pointer-events-auto cursor-crosshair" : "pointer-events-none"}`}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          style={{ width: "100%", height: "100%", background: "transparent" }}
        >
          {/* 1. Permanent Drawings */}
          {drawings.map((drawing) => {
            if (drawing.type === "trendline" && drawing.points.length === 2) {
              const c1 = getCoordinates(drawing.points[0]!);
              const c2 = getCoordinates(drawing.points[1]!);
              if (!c1 || !c2) return null;
              return (
                <line
                  key={drawing.id}
                  x1={c1.x}
                  y1={c1.y}
                  x2={c2.x}
                  y2={c2.y}
                  stroke="var(--nq-accent-cyan)"
                  strokeWidth="1.5"
                />
              );
            }
            if (drawing.type === "horizontal" && drawing.points.length === 1) {
              const c = getCoordinates(drawing.points[0]!);
              if (!c) return null;
              return (
                <line
                  key={drawing.id}
                  x1="0"
                  y1={c.y}
                  x2="100%"
                  y2={c.y}
                  stroke="var(--nq-accent-cyan)"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
              );
            }
            if (drawing.type === "fibonacci" && drawing.points.length === 2) {
              const p1 = drawing.points[0]!;
              const p2 = drawing.points[1]!;
              const c1 = getCoordinates(p1);
              const c2 = getCoordinates(p2);
              if (!c1 || !c2) return null;

              const levels = [1.0, 0.786, 0.618, 0.5, 0.382, 0.236, 0.0];
              const diff = p1.price - p2.price;

              return (
                <g key={drawing.id}>
                  {/* Diagonal connector line */}
                  <line
                    x1={c1.x}
                    y1={c1.y}
                    x2={c2.x}
                    y2={c2.y}
                    stroke="rgba(255,255,255,0.15)"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                  {levels.map((lvl) => {
                    const price = p2.price + diff * lvl;
                    const y = mainSeriesRef.current?.priceToCoordinate(price);
                    if (y === undefined || y === null) return null;
                    const color = levelColor(lvl);
                    return (
                      <g key={lvl}>
                        <line
                          x1="0"
                          y1={y}
                          x2="100%"
                          y2={y}
                          stroke={color}
                          strokeWidth="1"
                          opacity="0.6"
                        />
                        <text
                          x="50"
                          y={y - 3}
                          fill={color}
                          fontSize="8"
                          fontFamily="monospace"
                          opacity="0.8"
                        >
                          {lvl.toFixed(3)} - ₹{price.toFixed(2)}
                        </text>
                      </g>
                    );
                  })}
                </g>
              );
            }
            return null;
          })}

          {/* 2. Active Preview Drawing */}
          {activeTool !== "cursor" && tempStartPoint && tempEndPoint && (
            <g>
              {activeTool === "trendline" &&
                (() => {
                  const c1 = getCoordinates(tempStartPoint);
                  const c2 = getCoordinates(tempEndPoint);
                  if (!c1 || !c2) return null;
                  return (
                    <line
                      x1={c1.x}
                      y1={c1.y}
                      x2={c2.x}
                      y2={c2.y}
                      stroke="var(--nq-accent-cyan)"
                      strokeWidth="1.5"
                      strokeDasharray="3 3"
                      opacity="0.8"
                    />
                  );
                })()}
              {activeTool === "fibonacci" &&
                (() => {
                  const c1 = getCoordinates(tempStartPoint);
                  const c2 = getCoordinates(tempEndPoint);
                  if (!c1 || !c2) return null;

                  const levels = [1.0, 0.786, 0.618, 0.5, 0.382, 0.236, 0.0];
                  const diff = tempStartPoint.price - tempEndPoint.price;

                  return (
                    <g>
                      <line
                        x1={c1.x}
                        y1={c1.y}
                        x2={c2.x}
                        y2={c2.y}
                        stroke="rgba(255,255,255,0.2)"
                        strokeWidth="1"
                        strokeDasharray="3 3"
                      />
                      {levels.map((lvl) => {
                        const price = tempEndPoint.price + diff * lvl;
                        const y =
                          mainSeriesRef.current?.priceToCoordinate(price);
                        if (y === undefined || y === null) return null;
                        const color = levelColor(lvl);
                        return (
                          <g key={lvl}>
                            <line
                              x1="0"
                              y1={y}
                              x2="100%"
                              y2={y}
                              stroke={color}
                              strokeWidth="1"
                              opacity="0.8"
                            />
                            <text
                              x="50"
                              y={y - 3}
                              fill={color}
                              fontSize="8"
                              fontFamily="monospace"
                            >
                              {lvl.toFixed(3)} - ₹{price.toFixed(2)}
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })()}
            </g>
          )}
        </svg>
      </div>

    </div>
  );
}
