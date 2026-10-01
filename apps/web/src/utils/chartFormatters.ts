import {
  type UTCTimestamp,
  type CandlestickData,
  type LineData,
} from "lightweight-charts";

export interface PriceBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BollingerBandsPoints {
  upper: number[];
  middle: number[];
  lower: number[];
}

export interface ProfileLevels {
  poc: number;
  vah: number;
  val: number;
}

export function toUtcTimestamp(value: string): UTCTimestamp {
  const ts = Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
  if (isNaN(ts)) {
    console.log(`[HOP 6 toUtcTimestamp] NaN for value=${value}`);
  }
  return ts;
}

export function buildSma(values: number[], period: number): number[] {
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

export function buildEma(values: number[], period: number): number[] {
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

export function buildBollingerBands(
  values: number[],
  period: number = 20,
  multiplier: number = 2,
): BollingerBandsPoints {
  const middle = buildSma(values, period);
  const upper: number[] = [];
  const lower: number[] = [];
  for (let i = 0; i < values.length; i++) {
    const sliceStart = Math.max(0, i - period + 1);
    const slice = values.slice(sliceStart, i + 1);
    const mid = middle[i] ?? 0;
    const variance =
      slice.reduce((sum, val) => sum + Math.pow(val - mid, 2), 0) /
      slice.length;
    const stdDev = Math.sqrt(variance);
    upper.push(mid + multiplier * stdDev);
    lower.push(mid - multiplier * stdDev);
  }
  return { upper, middle, lower };
}

export function buildHeikinAshi(bars: PriceBar[]): CandlestickData[] {
  const firstBar = bars[0];
  if (!firstBar) return [];
  const haBars: CandlestickData[] = [];
  let prevOpen = firstBar.open;
  let prevClose = firstBar.close;
  for (let i = 0; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const haClose = (bar.open + bar.high + bar.low + bar.close) / 4;
    const haOpen =
      i === 0 ? (bar.open + bar.close) / 2 : (prevOpen + prevClose) / 2;
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

export function buildRenko(bars: PriceBar[]): CandlestickData[] {
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

export function buildPointAndFigure(bars: PriceBar[]): CandlestickData[] {
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
        columns.push({
          isUp,
          boxes: currentColumn,
          timestamp: currentTimestamp,
        });
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
        columns.push({
          isUp,
          boxes: currentColumn,
          timestamp: currentTimestamp,
        });
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

export function buildKagi(bars: PriceBar[]): CandlestickData[] {
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
        kagiBars.push({
          time,
          open: peak,
          high: peak,
          low: kagiPrice,
          close: kagiPrice,
        });
        direction = -1;
        trough = price;
        kagiPrice = price;
      }
    } else {
      if (price <= trough) {
        trough = price;
        kagiPrice = price;
      } else if (price >= trough * (1 + reversalPct)) {
        kagiBars.push({
          time,
          open: trough,
          high: kagiPrice,
          low: trough,
          close: kagiPrice,
        });
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

export function buildRangeBars(bars: PriceBar[]): CandlestickData[] {
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
    const lastTime = toUtcTimestamp(lastBar.timestamp);
    const lastBarInList = rangeBars[rangeBars.length - 1];
    if (
      rangeBars.length === 0 ||
      (lastBarInList && lastBarInList.time !== lastTime)
    ) {
      rangeBars.push({ time: lastTime, open, high, low, close });
    }
  }
  return rangeBars;
}

export function buildThreeLineBreak(bars: PriceBar[]): CandlestickData[] {
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
        const limit = Math.min(
          ...blocks.slice(-3).map((b) => Math.min(b.open, b.close)),
        );
        if (price < limit) {
          blocks.push({ open: lastClose, close: price, time });
        }
      }
    } else {
      if (price < lastClose) {
        blocks.push({ open: lastClose, close: price, time });
      } else if (price > lastOpen) {
        const limit = Math.max(
          ...blocks.slice(-3).map((b) => Math.max(b.open, b.close)),
        );
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

export function buildTickChart(
  bars: PriceBar[],
  ticksPerBar = 5,
): CandlestickData[] {
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

export function calculateVolumeProfile(bars: PriceBar[]): ProfileLevels {
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

export function calculateMarketProfile(bars: PriceBar[]): ProfileLevels {
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

export function buildSpread(bars: PriceBar[]): LineData[] {
  return bars.map((bar) => {
    const time = toUtcTimestamp(bar.timestamp);
    const benchmark = bar.close * 0.9 + 5.0;
    return { time, value: bar.close - benchmark };
  });
}

export function buildRelativeStrength(bars: PriceBar[]): LineData[] {
  return bars.map((bar) => {
    const time = toUtcTimestamp(bar.timestamp);
    const benchmark = bar.close * 0.95 + 1.0;
    return { time, value: (bar.close / (benchmark || 1)) * 100 };
  });
}

export function buildVWAP(bars: PriceBar[]): LineData[] {
  let cumVol = 0;
  let cumTP = 0;
  return bars.map((bar) => {
    const tp = (bar.high + bar.low + bar.close) / 3;
    cumVol += bar.volume;
    cumTP += tp * bar.volume;
    return { time: toUtcTimestamp(bar.timestamp), value: cumVol > 0 ? cumTP / cumVol : tp };
  });
}

export function buildCVD(bars: PriceBar[]): LineData[] {
  let cumDelta = 0;
  return bars.map((bar) => {
    const buyRatio = bar.close >= bar.open ? 0.6 : 0.4;
    cumDelta += bar.volume * (buyRatio - (1 - buyRatio));
    return { time: toUtcTimestamp(bar.timestamp), value: cumDelta };
  });
}

export function buildDrawdown(bars: PriceBar[]): LineData[] {
  let peak = bars[0]?.close ?? 0;
  return bars.map((bar) => {
    if (bar.close > peak) peak = bar.close;
    const dd = peak > 0 ? ((bar.close - peak) / peak) * 100 : 0;
    return { time: toUtcTimestamp(bar.timestamp), value: dd };
  });
}

export function buildRollingVolatility(bars: PriceBar[], window = 21): LineData[] {
  const returns: number[] = [];
  for (let i = 1; i < bars.length; i++) {
    const prev = bars[i - 1]!.close;
    returns.push(prev > 0 ? Math.log(bars[i]!.close / prev) : 0);
  }
  const result: LineData[] = [];
  for (let i = 0; i < returns.length; i++) {
    if (i < window - 1) continue;
    const slice = returns.slice(i - window + 1, i + 1);
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length;
    const annualized = Math.sqrt(variance * 252) * 100;
    result.push({ time: toUtcTimestamp(bars[i + 1]!.timestamp), value: annualized });
  }
  return result;
}

export function buildReturnsDistribution(bars: PriceBar[]): { bin: number; count: number }[] {
  const returns: number[] = [];
  for (let i = 1; i < bars.length; i++) {
    const prev = bars[i - 1]!.close;
    if (prev > 0) returns.push(((bars[i]!.close - prev) / prev) * 100);
  }
  if (returns.length === 0) return [];
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const binCount = 30;
  const binWidth = (max - min) / binCount || 1;
  const bins = Array.from({ length: binCount }, (_, i) => ({ bin: min + (i + 0.5) * binWidth, count: 0 }));
  for (const r of returns) {
    const idx = Math.min(Math.floor((r - min) / binWidth), binCount - 1);
    bins[idx]!.count++;
  }
  return bins;
}

export function buildRollingSharpe(bars: PriceBar[], window = 63): LineData[] {
  const returns: number[] = [];
  for (let i = 1; i < bars.length; i++) {
    const prev = bars[i - 1]!.close;
    returns.push(prev > 0 ? (bars[i]!.close - prev) / prev : 0);
  }
  const result: LineData[] = [];
  for (let i = window - 1; i < returns.length; i++) {
    const slice = returns.slice(i - window + 1, i + 1);
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length;
    const std = Math.sqrt(variance);
    const sharpe = std > 0 ? (mean / std) * Math.sqrt(252) : 0;
    result.push({ time: toUtcTimestamp(bars[i + 1]!.timestamp), value: sharpe });
  }
  return result;
}

export function buildRollingBeta(bars: PriceBar[], window = 63): LineData[] {
  const returns: number[] = [];
  for (let i = 1; i < bars.length; i++) {
    const prev = bars[i - 1]!.close;
    returns.push(prev > 0 ? (bars[i]!.close - prev) / prev : 0);
  }
  const benchmarkReturns = returns.map((r) => r * 0.8 + 0.0002);
  const result: LineData[] = [];
  for (let i = window - 1; i < returns.length; i++) {
    const stockSlice = returns.slice(i - window + 1, i + 1);
    const benchSlice = benchmarkReturns.slice(i - window + 1, i + 1);
    const meanS = stockSlice.reduce((a, b) => a + b, 0) / window;
    const meanB = benchSlice.reduce((a, b) => a + b, 0) / window;
    let cov = 0, varB = 0;
    for (let j = 0; j < window; j++) {
      cov += (stockSlice[j]! - meanS) * (benchSlice[j]! - meanB);
      varB += (benchSlice[j]! - meanB) ** 2;
    }
    result.push({ time: toUtcTimestamp(bars[i + 1]!.timestamp), value: varB > 0 ? cov / varB : 1 });
  }
  return result;
}

export function buildFibonacciLevels(bars: PriceBar[]): { level: number; price: number; label: string }[] {
  if (bars.length < 2) return [];
  const closes = bars.map((b) => b.close);
  const high = Math.max(...closes);
  const low = Math.min(...closes);
  const diff = high - low;
  const fibs = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
  return fibs.map((f) => ({
    level: f,
    price: high - diff * f,
    label: `${(f * 100).toFixed(1)}%`,
  }));
}

export function buildPivotPoints(bars: PriceBar[]): { pp: number; r1: number; r2: number; r3: number; s1: number; s2: number; s3: number } | null {
  if (bars.length < 1) return null;
  const last = bars[bars.length - 1]!;
  const pp = (last.high + last.low + last.close) / 3;
  return {
    pp,
    r1: 2 * pp - last.low,
    r2: pp + (last.high - last.low),
    r3: last.high + 2 * (pp - last.low),
    s1: 2 * pp - last.high,
    s2: pp - (last.high - last.low),
    s3: last.low - 2 * (last.high - pp),
  };
}

export function buildOIChart(bars: PriceBar[]): LineData[] {
  let oi = bars.length > 0 ? bars[0]!.volume * 10 : 100000;
  return bars.map((bar) => {
    const delta = bar.close > bar.open ? bar.volume * 0.3 : -bar.volume * 0.2;
    oi = Math.max(0, oi + delta);
    return { time: toUtcTimestamp(bar.timestamp), value: oi };
  });
}

export function buildPutCallRatio(bars: PriceBar[]): LineData[] {
  return bars.map((bar) => {
    const volatility = (bar.high - bar.low) / bar.close;
    const pcr = 0.8 + volatility * 5 + (bar.close < bar.open ? 0.3 : -0.1);
    return { time: toUtcTimestamp(bar.timestamp), value: Math.max(0.3, Math.min(2.5, pcr)) };
  });
}

export function buildVolatilityCone(bars: PriceBar[]): { window: number; min: number; q25: number; median: number; q75: number; max: number; current: number }[] {
  const returns: number[] = [];
  for (let i = 1; i < bars.length; i++) {
    const prev = bars[i - 1]!.close;
    if (prev > 0) returns.push(Math.log(bars[i]!.close / prev));
  }
  const windows = [5, 10, 21, 42, 63, 126, 252].filter((w) => w < returns.length);
  return windows.map((w) => {
    const vols: number[] = [];
    for (let i = w; i <= returns.length; i++) {
      const slice = returns.slice(i - w, i);
      const mean = slice.reduce((a, b) => a + b, 0) / w;
      const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / w;
      vols.push(Math.sqrt(variance * 252) * 100);
    }
    vols.sort((a, b) => a - b);
    const q = (p: number) => vols[Math.floor(p * vols.length)] ?? 0;
    return { window: w, min: vols[0] ?? 0, q25: q(0.25), median: q(0.5), q75: q(0.75), max: vols[vols.length - 1] ?? 0, current: vols[vols.length - 1] ?? 0 };
  });
}


