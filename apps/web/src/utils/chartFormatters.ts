import { type UTCTimestamp, type CandlestickData, type LineData } from "lightweight-charts";

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
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
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

export function buildBollingerBands(values: number[], period: number = 20, multiplier: number = 2): BollingerBandsPoints {
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
    if (rangeBars.length === 0 || (lastBarInList && lastBarInList.time !== lastTime)) {
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

export function buildTickChart(bars: PriceBar[], ticksPerBar = 5): CandlestickData[] {
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
