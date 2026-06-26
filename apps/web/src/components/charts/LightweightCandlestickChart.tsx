"use client";

import { useEffect, useRef, useState } from "react";
import {
  type IChartApi,
  type HistogramData,
  type UTCTimestamp,
} from "lightweight-charts";
import { detectPatterns } from "@/lib/patternDetector";
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

import { useChartInstance, type LiveChartApi } from "./tradingview/useChartInstance";
import { drawIndicators } from "./tradingview/indicatorsRenderer";
import { drawSMC } from "./tradingview/smcRenderer";
import { drawSubPanes } from "./tradingview/subpaneRenderer";

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
}

function sanitizeSeriesData<T extends { time: unknown }>(data: T[]): T[] {
  if (data.length === 0) return [];

  // Create a sorted copy by timestamp ascending to satisfy lightweight-charts requirements
  const sorted = [...data].sort((a, b) => {
    const timeA = a.time as string | number | { year: number; month: number; day: number };
    const timeB = b.time as string | number | { year: number; month: number; day: number };
    const tA = typeof timeA === "object" && timeA !== null
      ? Math.floor(new Date(`${timeA.year}-${timeA.month}-${timeA.day}`).getTime() / 1000)
      : Number(timeA);
    const tB = typeof timeB === "object" && timeB !== null
      ? Math.floor(new Date(`${timeB.year}-${timeB.month}-${timeB.day}`).getTime() / 1000)
      : Number(timeB);
    return tA - tB;
  });

  const sanitized: T[] = [];
  let lastTimeValue = 0;
  for (let i = 0; i < sorted.length; i++) {
    const item = sorted[i];
    if (!item) continue;
    const itemTime = item.time as string | number | { year: number; month: number; day: number };
    let time = typeof itemTime === "object" && itemTime !== null
      ? Math.floor(new Date(`${itemTime.year}-${itemTime.month}-${itemTime.day}`).getTime() / 1000)
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

export function LightweightCandlestickChart({
  bars,
  height = 340,
  chartStyle = "candlestick",
  indicators = {},
  predictions = [],
  symbol = "",
}: LightweightCandlestickChartProps): JSX.Element {
  const mainContainerRef = useRef<HTMLDivElement | null>(null);
  const [legend, setLegend] = useState<{
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    timestamp: string;
  } | null>(null);

  const cleanSymbol = symbol
    ? symbol
        .replace(".NS", "")
        .replace("^NSEI", "NIFTY 50")
        .replace("^NSEBANK", "BANK NIFTY")
        .replace("^BSESN", "SENSEX")
    : "";
  const rsiContainerRef = useRef<HTMLDivElement | null>(null);
  const macdContainerRef = useRef<HTMLDivElement | null>(null);
  const atrContainerRef = useRef<HTMLDivElement | null>(null);

  const mainChartRef = useRef<IChartApi | null>(null);
  const rsiChartRef = useRef<IChartApi | null>(null);
  const macdChartRef = useRef<IChartApi | null>(null);
  const atrChartRef = useRef<IChartApi | null>(null);
  const lastSymbolRef = useRef<string>("");
  const lastFirstBarTimeRef = useRef<string>("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const latestLogicalRangeRef = useRef<any>(null);

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

  const activeSubPanes = [rsi, macd, atr].filter(Boolean).length;
  const { chart: mainChart } = useChartInstance({
    containerRef: mainContainerRef,
    height,
    activeSubPanes,
  });

  useEffect(() => {
    if (!mainChart || !(mainChart as LiveChartApi).isAlive || bars.length === 0 || !mainContainerRef.current) return;

    const firstBarTime = bars[0]?.timestamp || "";
    const configChanged = symbol !== lastSymbolRef.current || firstBarTime !== lastFirstBarTimeRef.current;
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

    // Prepare calculations for indicators
    const candleData: Candle[] = bars.map(b => ({
      time: toUtcTimestamp(b.timestamp),
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
      volume: b.volume
    }));

    const indResults = computeIndicators(candleData, {
      rsi,
      macd,
      vwap,
      atr,
      superTrend,
      ichimoku,
      smc
    });

    // Detect patterns and build markers
    const baseMarkers = patterns ? detectPatterns(bars) : [];
    const smcMarkers = (smc && indResults.smc)
      ? indResults.smc.marketStructure.map(ms => ({
          time: ms.time as UTCTimestamp,
          position: (ms.direction === "bullish" ? "aboveBar" : "belowBar") as "aboveBar" | "belowBar" | "inBar",
          color: ms.type === "CHoCH" ? "#F50057" : "#FFEB3B",
          shape: (ms.direction === "bullish" ? "arrowUp" : "arrowDown") as "arrowUp" | "arrowDown" | "circle" | "square",
          text: `${ms.type} (${Math.round(ms.level)})`
        }))
      : [];

    const finalMarkers = [...baseMarkers, ...smcMarkers].sort((a, b) => Number(a.time) - Number(b.time));

    // Create Main Series Based on Selected Chart Style
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let mainSeries: any = null;

    if (chartStyle === "line") {
      mainSeries = mainChart.addLineSeries({ color: "#00E676", lineWidth: 2 });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))));
    } else if (chartStyle === "area") {
      mainSeries = mainChart.addAreaSeries({
        topColor: "rgba(0, 230, 118, 0.3)",
        bottomColor: "rgba(0, 230, 118, 0.0)",
        lineColor: "#00E676",
        lineWidth: 2,
      });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))));
    } else if (chartStyle === "ohlc-bar") {
      mainSeries = mainChart.addBarSeries({ upColor: "#00E676", downColor: "#FF3B5C", openVisible: true, thinBars: false });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({
        time: toUtcTimestamp(bar.timestamp),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))));
    } else if (chartStyle === "baseline") {
      const firstClose = bars[0]?.close ?? 0;
      mainSeries = mainChart.addBaselineSeries({
        baseValue: { type: "price", price: firstClose },
        topFillColor1: "rgba(0, 230, 118, 0.3)",
        topFillColor2: "rgba(0, 230, 118, 0.0)",
        topLineColor: "#00E676",
        bottomFillColor1: "rgba(255, 59, 92, 0.0)",
        bottomFillColor2: "rgba(255, 59, 92, 0.3)",
        bottomLineColor: "#FF3B5C",
        lineWidth: 2,
      });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))));
    } else if (chartStyle === "heikin-ashi") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(buildHeikinAshi(bars)));
    } else if (chartStyle === "hollow-candlestick") {
      mainSeries = mainChart.addCandlestickSeries({
        upColor: "rgba(0,0,0,0)",
        borderUpColor: "#00E676",
        wickUpColor: "#00E676",
        downColor: "#FF3B5C",
        borderDownColor: "#FF3B5C",
        wickDownColor: "#FF3B5C",
        borderVisible: true,
        wickVisible: true,
      });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({
        time: toUtcTimestamp(bar.timestamp),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))));
    } else if (chartStyle === "volume") {
      mainSeries = mainChart.addAreaSeries({
        topColor: "rgba(0, 212, 245, 0.4)",
        bottomColor: "rgba(0, 212, 245, 0.0)",
        lineColor: "#00D4F5",
        lineWidth: 2,
      });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.volume }))));
    } else if (chartStyle === "renko") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(buildRenko(bars)));
    } else if (chartStyle === "point-figure") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickVisible: false, borderVisible: true });
      mainSeries.setData(sanitizeSeriesData(buildPointAndFigure(bars)));
    } else if (chartStyle === "kagi") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickVisible: false, borderVisible: true });
      mainSeries.setData(sanitizeSeriesData(buildKagi(bars)));
    } else if (chartStyle === "range-bar") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(buildRangeBars(bars)));
    } else if (chartStyle === "three-line-break") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickVisible: false, borderVisible: true });
      mainSeries.setData(sanitizeSeriesData(buildThreeLineBreak(bars)));
    } else if (chartStyle === "equivolume") {
      mainSeries = mainChart.addCandlestickSeries({ borderVisible: true, wickVisible: true });
      const avgVolume = bars.reduce((sum, bar) => sum + bar.volume, 0) / (bars.length || 1);
      const equivData = bars.map((bar) => {
        const ratio = Math.max(0.2, Math.min(1.0, bar.volume / (avgVolume || 1)));
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
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(buildTickChart(bars)));
    } else if (chartStyle === "volume-profile") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({
        time: toUtcTimestamp(bar.timestamp),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))));
      const levels = calculateVolumeProfile(bars);
      mainSeries.createPriceLine({ price: levels.poc, color: "#FF9800", lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: "POC" });
      mainSeries.createPriceLine({ price: levels.vah, color: "#E040FB", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "VAH" });
      mainSeries.createPriceLine({ price: levels.val, color: "#00E5FF", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "VAL" });
    } else if (chartStyle === "market-profile") {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({
        time: toUtcTimestamp(bar.timestamp),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))));
      const levels = calculateMarketProfile(bars);
      mainSeries.createPriceLine({ price: levels.poc, color: "#FF5722", lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: "TPO POC" });
      mainSeries.createPriceLine({ price: levels.vah, color: "#9C27B0", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "TPO VAH" });
      mainSeries.createPriceLine({ price: levels.val, color: "#00E676", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "TPO VAL" });
    } else if (chartStyle === "spread") {
      mainSeries = mainChart.addAreaSeries({
        topColor: "rgba(236, 72, 153, 0.3)",
        bottomColor: "rgba(236, 72, 153, 0.0)",
        lineColor: "#EC4899",
        lineWidth: 2,
      });
      mainSeries.setData(sanitizeSeriesData(buildSpread(bars)));
    } else if (chartStyle === "relative-strength") {
      mainSeries = mainChart.addLineSeries({ color: "#8B5CF6", lineWidth: 2 });
      mainSeries.setData(sanitizeSeriesData(buildRelativeStrength(bars)));
    } else if (chartStyle === "mountain") {
      mainSeries = mainChart.addAreaSeries({
        topColor: "rgba(0, 212, 245, 0.4)",
        bottomColor: "rgba(0, 212, 245, 0.0)",
        lineColor: "#00D4F5",
        lineWidth: 3,
      });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))));
    } else {
      mainSeries = mainChart.addCandlestickSeries({ upColor: "#00E676", downColor: "#FF3B5C", wickUpColor: "#00E676", wickDownColor: "#FF3B5C", borderVisible: false });
      mainSeries.setData(sanitizeSeriesData(bars.map((bar) => ({
        time: toUtcTimestamp(bar.timestamp),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))));
    }

    if (mainSeries) {
      addedSeries.push(mainSeries);
      if (finalMarkers.length > 0) {
        mainSeries.setMarkers(finalMarkers);
      }
    }

    // Standard volume histogram overlay
    const volumeSeries = mainChart.addHistogramSeries({
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
      color: bar.close >= bar.open ? "rgba(0,230,118,0.3)" : "rgba(255,59,92,0.3)",
    }));
    volumeSeries.setData(sanitizeSeriesData(volumeData));

    // Draw Advanced Indicators & SMC overlays
    drawIndicators(mainChart, {
      ema9, ema21, ema50, ema200, sma20, sma50, sma100, bollingerBands, superTrend, ichimoku, vwap
    }, closes, times, indResults, addedSeries);

    drawSMC(mainChart, indResults, bars, addedSeries);

    // Draw stacked synchronized oscillator panes
    const subPaneHeight = 110;
    drawSubPanes(
      subCharts,
      indResults,
      subPaneHeight,
      rsi,
      rsiContainerRef.current,
      rsiChartRef,
      macd,
      macdContainerRef.current,
      macdChartRef,
      atr,
      atrContainerRef.current,
      atrChartRef
    );

    // Draw AI Forecast Projection lines
    if (predictions && predictions.length > 0 && chartStyle !== "volume") {
      const lastBar = bars[bars.length - 1];
      if (lastBar) {
        const lastTime = toUtcTimestamp(lastBar.timestamp);
        const lastClose = lastBar.close;

        const predLineSeries = mainChart.addLineSeries({
          color: "rgba(0, 212, 245, 0.85)",
          lineWidth: 2,
          lineStyle: 1,
          title: "AI Forecast",
        });
        addedSeries.push(predLineSeries);

        const sortedPredictions = [...predictions].sort(
          (a, b) => new Date(a.target_date).getTime() - new Date(b.target_date).getTime()
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

        const hasBounds = sortedPredictions.every((p) => p.prediction_low !== undefined && p.prediction_high !== undefined);
        if (hasBounds) {
          const upperSeries = mainChart.addLineSeries({
            color: "rgba(0, 212, 245, 0.4)",
            lineWidth: 1,
            lineStyle: 2,
            title: "Forecast Upper",
          });
          const lowerSeries = mainChart.addLineSeries({
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
      mainChart.timeScale().setVisibleLogicalRange(latestLogicalRangeRef.current);
    }

    // Set up watermark (TradingView/Zerodha style)
    mainChart.applyOptions({
      watermark: {
        visible: true,
        fontSize: Math.min(48, Math.floor(mainContainerRef.current?.clientWidth ? mainContainerRef.current.clientWidth / 12 : 48)),
        fontFamily: "var(--font-jetbrains), monospace",
        color: "rgba(255, 255, 255, 0.025)",
        text: cleanSymbol,
        horzAlign: "center",
        vertAlign: "center",
      }
    });

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
      const matchingBar = bars.find(b => toUtcTimestamp(b.timestamp) === time);
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

    // Resize observer handling
    const observer = new ResizeObserver(() => {
      if (!mainContainerRef.current) return;
      const width = mainContainerRef.current.clientWidth;
      mainChart.applyOptions({ width });
      subCharts.forEach((ch) => {
        ch.applyOptions({ width });
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
      rsiChartRef.current = null;
      macdChartRef.current = null;
      atrChartRef.current = null;
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
    symbol
  ]);

  const formatVolume = (val: number): string => {
    if (val >= 1e6) return (val / 1e6).toFixed(2) + "M";
    if (val >= 1e3) return (val / 1e3).toFixed(1) + "K";
    return String(val);
  };

  return (
    <div className="flex flex-col gap-1.5 h-full w-full relative">
      {legend && (
        <div className="absolute top-2 left-2 z-[99] pointer-events-none flex flex-wrap gap-x-2 gap-y-0.5 rounded bg-[rgba(10,14,24,0.72)] backdrop-blur-sm border border-[rgba(255,255,255,0.08)] px-2 py-0.5 text-[10px] font-mono text-[var(--nq-text-secondary)] shadow-md select-none">
          <span className="font-semibold text-[var(--nq-text-primary)] mr-1.5">{cleanSymbol}</span>
          <span>O:<span className={legend.close >= legend.open ? "text-[#00e676] ml-0.5" : "text-[#ff3b5c] ml-0.5"}>{legend.open.toFixed(2)}</span></span>
          <span className="ml-1.5">H:<span className={legend.close >= legend.open ? "text-[#00e676] ml-0.5" : "text-[#ff3b5c] ml-0.5"}>{legend.high.toFixed(2)}</span></span>
          <span className="ml-1.5">L:<span className={legend.close >= legend.open ? "text-[#00e676] ml-0.5" : "text-[#ff3b5c] ml-0.5"}>{legend.low.toFixed(2)}</span></span>
          <span className="ml-1.5">C:<span className={legend.close >= legend.open ? "text-[#00e676] ml-0.5" : "text-[#ff3b5c] ml-0.5"}>{legend.close.toFixed(2)}</span></span>
          <span className="ml-1.5">V:<span className="text-[var(--nq-accent-cyan)] ml-0.5">{formatVolume(legend.volume)}</span></span>
        </div>
      )}
      <div ref={mainContainerRef} className="w-full flex-1 min-h-[240px] relative" />
      {rsi && <div ref={rsiContainerRef} className="w-full h-[110px] relative border-t border-[rgba(255,255,255,0.08)] mt-1" />}
      {macd && <div ref={macdContainerRef} className="w-full h-[110px] relative border-t border-[rgba(255,255,255,0.08)] mt-1" />}
      {atr && <div ref={atrContainerRef} className="w-full h-[110px] relative border-t border-[rgba(255,255,255,0.08)] mt-1" />}
    </div>
  );
}
