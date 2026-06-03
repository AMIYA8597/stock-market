"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type CandlestickData,
  type HistogramData,
  type UTCTimestamp,
  type LineData,
} from "lightweight-charts";
import { detectPatterns } from "@/lib/patternDetector";

interface PriceBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

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
  };
  predictions?: {
    target_date: string;
    predicted_price: number;
    prediction_low?: number;
    prediction_high?: number;
  }[];
}

function toUtcTimestamp(value: string): UTCTimestamp {
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
}

function buildSma(values: number[], period: number): number[] {
  const sma: number[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i] ?? 0;
    if (i >= period) {
      sum -= values[i - period] ?? 0;
    }
    const count = Math.min(i + 1, period);
    sma.push(sum / count);
  }
  return sma;
}

function buildEma(values: number[], period: number): number[] {
  if (values.length === 0) {
    return [];
  }
  const k = 2 / (period + 1);
  const ema: number[] = [values[0] ?? 0];
  for (let i = 1; i < values.length; i += 1) {
    ema.push((values[i] ?? 0) * k + (ema[i - 1] ?? 0) * (1 - k));
  }
  return ema;
}

interface BollingerBandsPoints {
  upper: number[];
  middle: number[];
  lower: number[];
}

function buildBollingerBands(values: number[], period: number = 20, multiplier: number = 2): BollingerBandsPoints {
  const middle = buildSma(values, period);
  const upper: number[] = [];
  const lower: number[] = [];
  for (let i = 0; i < values.length; i++) {
    const sliceStart = Math.max(0, i - period + 1);
    const slice = values.slice(sliceStart, i + 1);
    const mid = middle[i] ?? 0;
    const variance = slice.reduce((sum, val) => sum + Math.pow(val - mid, 2), 0) / slice.length;
    const stdDev = Math.sqrt(variance);
    upper.push(mid + multiplier * stdDev);
    lower.push(mid - multiplier * stdDev);
  }
  return { upper, middle, lower };
}

function buildHeikinAshi(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  const haBars: CandlestickData[] = [];
  let prevOpen = firstBar.open;
  let prevClose = firstBar.close;
  for (let i = 0; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const haClose = (bar.open + bar.high + bar.low + bar.close) / 4;
    const haOpen = i === 0 ? (bar.open + bar.close) / 2 : (prevOpen + prevClose) / 2;
    const haHigh = Math.max(bar.high, haOpen, haClose);
    const haLow = Math.min(bar.low, haOpen, haClose);
    haBars.push({
      time: toUtcTimestamp(bar.timestamp),
      open: haOpen,
      high: haHigh,
      low: haLow,
      close: haClose,
    });
    prevOpen = haOpen;
    prevClose = haClose;
  }
  return haBars;
}

function buildRenko(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  const boxSize = Math.max(firstBar.close * 0.008, 0.1);
  const renkoBars: CandlestickData[] = [];
  let brickOpen = Math.round(firstBar.close / boxSize) * boxSize;
  let lastTimeValue = 0;

  for (let i = 0; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const price = bar.close;
    const priceDiff = price - brickOpen;
    const baseTime = toUtcTimestamp(bar.timestamp);

    if (priceDiff >= boxSize) {
      const numBricks = Math.floor(priceDiff / boxSize);
      for (let j = 0; j < numBricks; j++) {
        const nextOpen = brickOpen;
        const nextClose = brickOpen + boxSize;
        let time = baseTime;
        if (time <= lastTimeValue) {
          time = (lastTimeValue + 1) as UTCTimestamp;
        }
        lastTimeValue = time;

        renkoBars.push({
          time,
          open: nextOpen,
          high: nextClose,
          low: nextOpen,
          close: nextClose,
        });
        brickOpen = nextClose;
      }
    } else if (-priceDiff >= boxSize) {
      const numBricks = Math.floor(-priceDiff / boxSize);
      for (let j = 0; j < numBricks; j++) {
        const nextOpen = brickOpen;
        const nextClose = brickOpen - boxSize;
        let time = baseTime;
        if (time <= lastTimeValue) {
          time = (lastTimeValue + 1) as UTCTimestamp;
        }
        lastTimeValue = time;

        renkoBars.push({
          time,
          open: nextOpen,
          high: nextOpen,
          low: nextClose,
          close: nextClose,
        });
        brickOpen = nextClose;
      }
    }
  }
  if (renkoBars.length === 0) {
    const lastBar = bars[bars.length - 1];
    if (lastBar) {
      let time = toUtcTimestamp(lastBar.timestamp);
      if (time <= lastTimeValue) {
        time = (lastTimeValue + 1) as UTCTimestamp;
      }
      renkoBars.push({
        time,
        open: brickOpen,
        high: Math.max(brickOpen, lastBar.close),
        low: Math.min(brickOpen, lastBar.close),
        close: lastBar.close,
      });
    }
  }
  return renkoBars;
}

function buildPointAndFigure(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  const boxSize = Math.max(firstBar.close * 0.012, 0.1);
  const columns: { isUp: boolean; boxes: number[]; timestamp: string }[] = [];
  let currentColumn: number[] = [];
  let isUp = true;
  let lastBoxVal = Math.round(firstBar.close / boxSize) * boxSize;
  currentColumn.push(lastBoxVal);
  let currentTimestamp = firstBar.timestamp;

  for (let i = 1; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const price = bar.close;
    const diff = price - lastBoxVal;
    const boxesMoved = Math.floor(diff / boxSize);

    if (isUp) {
      if (boxesMoved >= 1) {
        for (let j = 1; j <= boxesMoved; j++) {
          lastBoxVal += boxSize;
          currentColumn.push(lastBoxVal);
        }
        currentTimestamp = bar.timestamp;
      } else if (boxesMoved <= -3) {
        columns.push({ isUp, boxes: currentColumn, timestamp: currentTimestamp });
        isUp = false;
        currentColumn = [];
        const numReversals = Math.abs(boxesMoved);
        for (let j = 1; j <= numReversals; j++) {
          lastBoxVal -= boxSize;
          currentColumn.push(lastBoxVal);
        }
        currentTimestamp = bar.timestamp;
      }
    } else {
      if (boxesMoved <= -1) {
        const numDown = Math.abs(boxesMoved);
        for (let j = 1; j <= numDown; j++) {
          lastBoxVal -= boxSize;
          currentColumn.push(lastBoxVal);
        }
        currentTimestamp = bar.timestamp;
      } else if (boxesMoved >= 3) {
        columns.push({ isUp, boxes: currentColumn, timestamp: currentTimestamp });
        isUp = true;
        currentColumn = [];
        for (let j = 1; j <= boxesMoved; j++) {
          lastBoxVal += boxSize;
          currentColumn.push(lastBoxVal);
        }
        currentTimestamp = bar.timestamp;
      }
    }
  }
  if (currentColumn.length > 0) {
    columns.push({ isUp, boxes: currentColumn, timestamp: currentTimestamp });
  }

  const pfBars: CandlestickData[] = [];
  let lastTimeValue = 0;
  for (let colIdx = 0; colIdx < columns.length; colIdx++) {
    const col = columns[colIdx];
    if (!col || col.boxes.length === 0) continue;
    const minBox = Math.min(...col.boxes);
    const maxBox = Math.max(...col.boxes);
    let time = toUtcTimestamp(col.timestamp);
    if (time <= lastTimeValue) {
      time = (lastTimeValue + 1) as UTCTimestamp;
    }
    lastTimeValue = time;

    pfBars.push({
      time,
      open: col.isUp ? minBox : maxBox,
      high: maxBox,
      low: minBox,
      close: col.isUp ? maxBox : minBox,
    });
  }
  return pfBars;
}

function buildKagi(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  const reversalPct = 0.015;
  const kagiBars: CandlestickData[] = [];
  let direction = 0; // 1 = Up, -1 = Down
  let kagiPrice = firstBar.close;
  let peak = kagiPrice;
  let trough = kagiPrice;

  for (let i = 1; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const price = bar.close;
    const time = toUtcTimestamp(bar.timestamp);

    if (direction === 0) {
      if (price > kagiPrice) {
        direction = 1;
        peak = price;
      } else if (price < kagiPrice) {
        direction = -1;
        trough = price;
      }
      kagiPrice = price;
    } else if (direction === 1) {
      if (price >= peak) {
        peak = price;
        kagiPrice = price;
      } else if (price <= peak * (1 - reversalPct)) {
        kagiBars.push({ time, open: peak, high: peak, low: kagiPrice, close: kagiPrice });
        direction = -1;
        trough = price;
        kagiPrice = price;
      }
    } else {
      if (price <= trough) {
        trough = price;
        kagiPrice = price;
      } else if (price >= trough * (1 + reversalPct)) {
        kagiBars.push({ time, open: trough, high: kagiPrice, low: trough, close: kagiPrice });
        direction = 1;
        peak = price;
        kagiPrice = price;
      }
    }
  }
  if (kagiBars.length === 0) {
    return bars.map((b) => ({
      time: toUtcTimestamp(b.timestamp),
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
  }
  return kagiBars;
}

function buildRangeBars(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  const rangeSize = Math.max(firstBar.close * 0.015, 0.1);
  const rangeBars: CandlestickData[] = [];
  let open = firstBar.open;
  let high = firstBar.high;
  let low = firstBar.low;
  let close = firstBar.close;

  for (let i = 1; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const time = toUtcTimestamp(bar.timestamp);
    high = Math.max(high, bar.high);
    low = Math.min(low, bar.low);
    close = bar.close;

    if (high - low >= rangeSize) {
      rangeBars.push({ time, open, high, low, close });
      open = bar.close;
      high = bar.close;
      low = bar.close;
      close = bar.close;
    }
  }
  const lastBar = bars[bars.length - 1];
  if (lastBar) {
    rangeBars.push({ time: toUtcTimestamp(lastBar.timestamp), open, high, low, close });
  }
  return rangeBars;
}

function buildThreeLineBreak(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  if (bars.length < 4) {
    return bars.map((b) => ({
      time: toUtcTimestamp(b.timestamp),
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
  }
  const blocks: { open: number; close: number; time: UTCTimestamp }[] = [];
  blocks.push({
    open: firstBar.open,
    close: firstBar.close,
    time: toUtcTimestamp(firstBar.timestamp),
  });

  for (let i = 1; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const price = bar.close;
    const time = toUtcTimestamp(bar.timestamp);
    const lastBlock = blocks[blocks.length - 1];
    if (!lastBlock) continue;
    const lastClose = lastBlock.close;
    const lastOpen = lastBlock.open;
    const isLastUp = lastClose > lastOpen;

    if (isLastUp) {
      if (price > lastClose) {
        blocks.push({ open: lastClose, close: price, time });
      } else if (price < lastOpen) {
        const limit = Math.min(...blocks.slice(-3).map((b) => Math.min(b.open, b.close)));
        if (price < limit) {
          blocks.push({ open: lastClose, close: price, time });
        }
      }
    } else {
      if (price < lastClose) {
        blocks.push({ open: lastClose, close: price, time });
      } else if (price > lastOpen) {
        const limit = Math.max(...blocks.slice(-3).map((b) => Math.max(b.open, b.close)));
        if (price > limit) {
          blocks.push({ open: lastClose, close: price, time });
        }
      }
    }
  }
  return blocks.map((b) => ({
    time: b.time,
    open: b.open,
    high: Math.max(b.open, b.close),
    low: Math.min(b.open, b.close),
    close: b.close,
  }));
}

function buildTickChart(bars: PriceBar[], ticksPerBar = 5): CandlestickData[] {
  const tickBars: CandlestickData[] = [];
  for (let i = 0; i < bars.length; i += ticksPerBar) {
    const chunk = bars.slice(i, i + ticksPerBar);
    if (chunk.length === 0) continue;
    const firstVal = chunk[0];
    const lastVal = chunk[chunk.length - 1];
    if (!firstVal || !lastVal) continue;
    const open = firstVal.open;
    const close = lastVal.close;
    const high = Math.max(...chunk.map((c) => c.high));
    const low = Math.min(...chunk.map((c) => c.low));
    const time = toUtcTimestamp(lastVal.timestamp);
    tickBars.push({ time, open, high, low, close });
  }
  return tickBars;
}

interface ProfileLevels {
  poc: number;
  vah: number;
  val: number;
}

function calculateVolumeProfile(bars: PriceBar[]): ProfileLevels {
  if (bars.length === 0) return { poc: 0, vah: 0, val: 0 };
  const closes = bars.map((b) => b.close);
  const minPrice = Math.min(...closes);
  const maxPrice = Math.max(...closes);
  const step = Math.max((maxPrice - minPrice) / 30, 0.05);

  const bins = Array.from({ length: 30 }, (_, i) => ({
    price: minPrice + i * step,
    volume: 0,
  }));

  for (const bar of bars) {
    const binIdx = Math.min(Math.floor((bar.close - minPrice) / step), 29);
    const bin = bins[binIdx];
    if (bin) {
      bin.volume += bar.volume;
    }
  }

  let maxVol = 0;
  let pocPrice = minPrice;
  let totalVolume = 0;
  for (const bin of bins) {
    totalVolume += bin.volume;
    if (bin.volume > maxVol) {
      maxVol = bin.volume;
      pocPrice = bin.price;
    }
  }

  const targetVol = totalVolume * 0.7;
  let currentVol = maxVol;
  let pocIdx = bins.findIndex((b) => b.price === pocPrice);
  if (pocIdx === -1) pocIdx = 15;
  let lowIdx = pocIdx;
  let highIdx = pocIdx;

  while (currentVol < targetVol && (lowIdx > 0 || highIdx < 29)) {
    const belowVol = lowIdx > 0 ? (bins[lowIdx - 1]?.volume ?? 0) : 0;
    const aboveVol = highIdx < 29 ? (bins[highIdx + 1]?.volume ?? 0) : 0;

    if (belowVol >= aboveVol && lowIdx > 0) {
      lowIdx--;
      currentVol += belowVol;
    } else if (highIdx < 29) {
      highIdx++;
      currentVol += aboveVol;
    } else if (lowIdx > 0) {
      lowIdx--;
      currentVol += belowVol;
    } else {
      break;
    }
  }

  const val = bins[lowIdx]?.price ?? minPrice;
  const vah = bins[highIdx]?.price ?? maxPrice;
  return { poc: pocPrice, vah, val };
}

function calculateMarketProfile(bars: PriceBar[]): ProfileLevels {
  if (bars.length === 0) return { poc: 0, vah: 0, val: 0 };
  const closes = bars.map((b) => b.close);
  const minPrice = Math.min(...closes);
  const maxPrice = Math.max(...closes);
  const step = Math.max((maxPrice - minPrice) / 30, 0.05);

  const bins = Array.from({ length: 30 }, (_, i) => ({
    price: minPrice + i * step,
    tpoCount: 0,
  }));

  for (const bar of bars) {
    const lowBin = Math.max(0, Math.floor((bar.low - minPrice) / step));
    const highBin = Math.min(29, Math.floor((bar.high - minPrice) / step));
    for (let b = lowBin; b <= highBin; b++) {
      const bin = bins[b];
      if (bin) {
        bin.tpoCount++;
      }
    }
  }

  let maxTPO = 0;
  let pocPrice = minPrice;
  let totalTPO = 0;
  for (const bin of bins) {
    totalTPO += bin.tpoCount;
    if (bin.tpoCount > maxTPO) {
      maxTPO = bin.tpoCount;
      pocPrice = bin.price;
    }
  }

  const targetTPO = totalTPO * 0.7;
  let currentTPO = maxTPO;
  let pocIdx = bins.findIndex((b) => b.price === pocPrice);
  if (pocIdx === -1) pocIdx = 15;
  let lowIdx = pocIdx;
  let highIdx = pocIdx;

  while (currentTPO < targetTPO && (lowIdx > 0 || highIdx < 29)) {
    const belowTPO = lowIdx > 0 ? (bins[lowIdx - 1]?.tpoCount ?? 0) : 0;
    const aboveTPO = highIdx < 29 ? (bins[highIdx + 1]?.tpoCount ?? 0) : 0;

    if (belowTPO >= aboveTPO && lowIdx > 0) {
      lowIdx--;
      currentTPO += belowTPO;
    } else if (highIdx < 29) {
      highIdx++;
      currentTPO += aboveTPO;
    } else if (lowIdx > 0) {
      lowIdx--;
      currentTPO += belowTPO;
    } else {
      break;
    }
  }

  const val = bins[lowIdx]?.price ?? minPrice;
  const vah = bins[highIdx]?.price ?? maxPrice;
  return { poc: pocPrice, vah, val };
}

function buildSpread(bars: PriceBar[]): LineData[] {
  return bars.map((bar) => {
    const time = toUtcTimestamp(bar.timestamp);
    const benchmark = bar.close * 0.9 + 5.0;
    return { time, value: bar.close - benchmark };
  });
}

function buildRelativeStrength(bars: PriceBar[]): LineData[] {
  return bars.map((bar) => {
    const time = toUtcTimestamp(bar.timestamp);
    const benchmark = bar.close * 0.95 + 1.0;
    return { time, value: (bar.close / (benchmark || 1)) * 100 };
  });
}

export function LightweightCandlestickChart({
  bars,
  height = 340,
  chartStyle = "candlestick",
  indicators = {},
  predictions = [],
}: LightweightCandlestickChartProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

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
  } = indicators;

  useEffect(() => {
    if (!rootRef.current || bars.length === 0) {
      return;
    }

    const chart = createChart(rootRef.current, {
      autoSize: false,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8B97A8",
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.12)",
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.12)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        vertLine: { color: "rgba(0,212,245,0.45)", width: 1 },
        horzLine: { color: "rgba(0,212,245,0.45)", width: 1 },
      },
    });

    chartRef.current = chart;

    const markers = patterns ? detectPatterns(bars) : [];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let mainSeries: any = null;

    if (chartStyle === "line") {
      mainSeries = chart.addLineSeries({
        color: "#00E676",
        lineWidth: 2,
      });
      mainSeries.setData(
        bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))
      );
    } else if (chartStyle === "area") {
      mainSeries = chart.addAreaSeries({
        topColor: "rgba(0, 230, 118, 0.3)",
        bottomColor: "rgba(0, 230, 118, 0.0)",
        lineColor: "#00E676",
        lineWidth: 2,
      });
      mainSeries.setData(
        bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))
      );
    } else if (chartStyle === "ohlc-bar") {
      mainSeries = chart.addBarSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        openVisible: true,
        thinBars: false,
      });
      mainSeries.setData(
        bars.map((bar) => ({
          time: toUtcTimestamp(bar.timestamp),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))
      );
    } else if (chartStyle === "baseline") {
      const firstClose = bars[0]?.close ?? 0;
      mainSeries = chart.addBaselineSeries({
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
        bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))
      );
    } else if (chartStyle === "heikin-ashi") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(buildHeikinAshi(bars));
    } else if (chartStyle === "hollow-candlestick") {
      mainSeries = chart.addCandlestickSeries({
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
        bars.map((bar) => ({
          time: toUtcTimestamp(bar.timestamp),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))
      );
    } else if (chartStyle === "volume") {
      mainSeries = chart.addAreaSeries({
        topColor: "rgba(0, 212, 245, 0.4)",
        bottomColor: "rgba(0, 212, 245, 0.0)",
        lineColor: "#00D4F5",
        lineWidth: 2,
      });
      mainSeries.setData(
        bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.volume }))
      );
    } else if (chartStyle === "renko") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(buildRenko(bars));
    } else if (chartStyle === "point-figure") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickVisible: false,
        borderVisible: true,
      });
      mainSeries.setData(buildPointAndFigure(bars));
    } else if (chartStyle === "kagi") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickVisible: false,
        borderVisible: true,
      });
      mainSeries.setData(buildKagi(bars));
    } else if (chartStyle === "range-bar") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(buildRangeBars(bars));
    } else if (chartStyle === "three-line-break") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickVisible: false,
        borderVisible: true,
      });
      mainSeries.setData(buildThreeLineBreak(bars));
    } else if (chartStyle === "equivolume") {
      mainSeries = chart.addCandlestickSeries({
        borderVisible: true,
        wickVisible: true,
      });
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
      mainSeries.setData(equivData);
    } else if (chartStyle === "tick") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(buildTickChart(bars));
    } else if (chartStyle === "volume-profile") {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(
        bars.map((bar) => ({
          time: toUtcTimestamp(bar.timestamp),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))
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
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(
        bars.map((bar) => ({
          time: toUtcTimestamp(bar.timestamp),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))
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
      mainSeries = chart.addAreaSeries({
        topColor: "rgba(236, 72, 153, 0.3)",
        bottomColor: "rgba(236, 72, 153, 0.0)",
        lineColor: "#EC4899",
        lineWidth: 2,
      });
      mainSeries.setData(buildSpread(bars));
    } else if (chartStyle === "relative-strength") {
      mainSeries = chart.addLineSeries({
        color: "#8B5CF6",
        lineWidth: 2,
      });
      mainSeries.setData(buildRelativeStrength(bars));
    } else if (chartStyle === "mountain") {
      mainSeries = chart.addAreaSeries({
        topColor: "rgba(0, 212, 245, 0.4)",
        bottomColor: "rgba(0, 212, 245, 0.0)",
        lineColor: "#00D4F5",
        lineWidth: 3,
      });
      mainSeries.setData(
        bars.map((bar) => ({ time: toUtcTimestamp(bar.timestamp), value: bar.close }))
      );
    } else {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B5C",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B5C",
        borderVisible: false,
      });
      mainSeries.setData(
        bars.map((bar) => ({
          time: toUtcTimestamp(bar.timestamp),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))
      );
    }

    if (mainSeries && markers.length > 0) {
      mainSeries.setMarkers(markers);
    }

    // Standard volume histogram overlay at bottom
    const volumeSeries = chart.addHistogramSeries({
      priceScaleId: "",
      priceFormat: { type: "volume" },
      color: "rgba(0,212,245,0.45)",
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    const volumeData: HistogramData[] = bars.map((bar) => ({
      time: toUtcTimestamp(bar.timestamp),
      value: bar.volume,
      color: bar.close >= bar.open ? "rgba(0,230,118,0.3)" : "rgba(255,59,92,0.3)",
    }));
    volumeSeries.setData(volumeData);

    const closes = bars.map((bar) => bar.close);
    const times = bars.map((bar) => toUtcTimestamp(bar.timestamp));

    if (ema9) {
      const ema9Data = buildEma(closes, 9);
      const ema9Series = chart.addLineSeries({
        color: "#00D4F5",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      ema9Series.setData(times.map((time, idx) => ({ time, value: ema9Data[idx] ?? closes[idx] })));
    }

    if (ema21) {
      const ema21Data = buildEma(closes, 21);
      const ema21Series = chart.addLineSeries({
        color: "#8B5CF6",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      ema21Series.setData(
        times.map((time, idx) => ({ time, value: ema21Data[idx] ?? closes[idx] }))
      );
    }

    if (ema50) {
      const ema50Data = buildEma(closes, 50);
      const ema50Series = chart.addLineSeries({
        color: "#FFB800",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      ema50Series.setData(
        times.map((time, idx) => ({ time, value: ema50Data[idx] ?? closes[idx] }))
      );
    }

    if (ema200) {
      const ema200Data = buildEma(closes, 200);
      const ema200Series = chart.addLineSeries({
        color: "#EC4899",
        lineWidth: 2,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      ema200Series.setData(
        times.map((time, idx) => ({ time, value: ema200Data[idx] ?? closes[idx] }))
      );
    }

    if (sma20) {
      const sma20Data = buildSma(closes, 20);
      const sma20Series = chart.addLineSeries({
        color: "#3B82F6",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      sma20Series.setData(
        times.map((time, idx) => ({ time, value: sma20Data[idx] ?? closes[idx] }))
      );
    }

    if (sma50) {
      const sma50Data = buildSma(closes, 50);
      const sma50Series = chart.addLineSeries({
        color: "#EF4444",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      sma50Series.setData(
        times.map((time, idx) => ({ time, value: sma50Data[idx] ?? closes[idx] }))
      );
    }

    if (sma100) {
      const sma100Data = buildSma(closes, 100);
      const sma100Series = chart.addLineSeries({
        color: "#10B981",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      sma100Series.setData(
        times.map((time, idx) => ({ time, value: sma100Data[idx] ?? closes[idx] }))
      );
    }

    if (bollingerBands) {
      const bb = buildBollingerBands(closes, 20, 2);
      const bbUpperSeries = chart.addLineSeries({
        color: "rgba(0, 212, 245, 0.4)",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      const bbBasisSeries = chart.addLineSeries({
        color: "rgba(0, 212, 245, 0.2)",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      const bbLowerSeries = chart.addLineSeries({
        color: "rgba(0, 212, 245, 0.4)",
        lineWidth: 1,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });

      bbUpperSeries.setData(
        times.map((time, idx) => ({ time, value: bb.upper[idx] ?? closes[idx] }))
      );
      bbBasisSeries.setData(
        times.map((time, idx) => ({ time, value: bb.middle[idx] ?? closes[idx] }))
      );
      bbLowerSeries.setData(
        times.map((time, idx) => ({ time, value: bb.lower[idx] ?? closes[idx] }))
      );
    }

    if (predictions && predictions.length > 0 && chartStyle !== "volume") {
      const lastBar = bars[bars.length - 1];
      if (lastBar) {
        const lastTime = toUtcTimestamp(lastBar.timestamp);
        const lastClose = lastBar.close;

        // Draw prediction median line
        const predLineSeries = chart.addLineSeries({
          color: "rgba(0, 212, 245, 0.85)",
          lineWidth: 2,
          lineStyle: 1, // Dashed
          title: "AI Forecast",
        });

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

        // Ensure timestamps are strictly increasing
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
          const upperSeries = chart.addLineSeries({
            color: "rgba(0, 212, 245, 0.4)",
            lineWidth: 1,
            lineStyle: 2, // Dotted
            title: "Forecast Upper",
          });
          const lowerSeries = chart.addLineSeries({
            color: "rgba(0, 212, 245, 0.4)",
            lineWidth: 1,
            lineStyle: 2, // Dotted
            title: "Forecast Lower",
          });

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

    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      if (!rootRef.current || !chartRef.current) {
        return;
      }
      chartRef.current.applyOptions({ width: rootRef.current.clientWidth });
    });

    observer.observe(rootRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [
    bars,
    height,
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
  ]);

  return <div ref={rootRef} className="h-full w-full" />;
}
