/**
 * Technical indicators calculation engine.
 * Computes math arrays for overlays and synced panels from OHLCV candles.
 */

export interface Candle {
  time: number | string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface IndicatorResult {
  rsi?: { time: number | string; value: number }[];
  macd?: {
    time: number | string;
    macd: number;
    signal: number;
    histogram: number;
  }[];
  vwap?: { time: number | string; value: number }[];
  atr?: { time: number | string; value: number }[];
  superTrend?: {
    time: number | string;
    value: number;
    trend: 'up' | 'down';
  }[];
  ichimoku?: {
    time: number | string;
    tenkan: number;
    kijun: number;
    senkouA: number;
    senkouB: number;
    chikou: number;
  }[];
  smc?: {
    orderBlocks: {
      id: string;
      type: 'bullish' | 'bearish';
      top: number;
      bottom: number;
      startTime: number | string;
      endTime?: number | string;
      isMitigated: boolean;
    }[];
    fairValueGaps: {
      id: string;
      type: 'bullish' | 'bearish';
      top: number;
      bottom: number;
      time: number | string;
      isFilled: boolean;
    }[];
    liquidityZones: {
      id: string;
      type: 'bsl' | 'ssl';
      level: number;
      time: number | string;
      isSwept: boolean;
    }[];
    marketStructure: {
      time: number | string;
      type: 'BOS' | 'CHoCH';
      direction: 'bullish' | 'bearish';
      level: number;
    }[];
  };
}

/**
 * Calculate Exponential Moving Average (EMA).
 */
export function calculateEMA(data: number[], period: number): number[] {
  const ema: number[] = [];
  if (data.length === 0) return ema;
  const k = 2 / (period + 1);
  let prevEma = data[0] ?? 0;
  ema.push(prevEma);

  for (let i = 1; i < data.length; i++) {
    const val = data[i] ?? 0;
    const curEma = val * k + prevEma * (1 - k);
    ema.push(curEma);
    prevEma = curEma;
  }
  return ema;
}

/**
 * Calculate Wilder's Smoothing.
 */
export function calculateWilderSmoothing(data: number[], period: number): number[] {
  const smoothed: number[] = [];
  if (data.length === 0) return smoothed;
  let sum = 0;
  
  // Initial SMA
  const initialPeriod = Math.min(period, data.length);
  for (let i = 0; i < initialPeriod; i++) {
    sum += data[i] ?? 0;
  }
  let prevVal = sum / initialPeriod;
  
  for (let i = 0; i < data.length; i++) {
    const val = data[i] ?? 0;
    if (i < period - 1) {
      smoothed.push(val); // placeholder
    } else if (i === period - 1) {
      smoothed.push(prevVal);
    } else {
      const curVal = (prevVal * (period - 1) + val) / period;
      smoothed.push(curVal);
      prevVal = curVal;
    }
  }
  return smoothed;
}

/**
 * Compute all selected technical indicators from a list of candles.
 */
export function computeIndicators(candles: Candle[], selected: {
  rsi?: boolean;
  macd?: boolean;
  vwap?: boolean;
  atr?: boolean;
  superTrend?: boolean;
  ichimoku?: boolean;
  smc?: boolean;
}): IndicatorResult {
  const result: IndicatorResult = {};
  if (candles.length < 2) return result;

  const closes = candles.map(c => c.close);
  const highs = candles.map(c => c.high);
  const lows = candles.map(c => c.low);

  // 1. RSI (14)
  if (selected.rsi) {
    const gains: number[] = [0];
    const losses: number[] = [0];
    for (let i = 1; i < closes.length; i++) {
      const diff = (closes[i] ?? 0) - (closes[i - 1] ?? 0);
      gains.push(diff > 0 ? diff : 0);
      losses.push(diff < 0 ? -diff : 0);
    }

    const avgGains = calculateWilderSmoothing(gains, 14);
    const avgLosses = calculateWilderSmoothing(losses, 14);

    const rsiList = candles.map((c, i) => {
      const avgGain = avgGains[i] ?? 0;
      const avgLoss = avgLosses[i] ?? 0;
      if (avgLoss === 0) return { time: c.time, value: 100 };
      const rs = avgGain / avgLoss;
      return { time: c.time, value: Math.round((100 - 100 / (1 + rs)) * 100) / 100 };
    });

    result.rsi = rsiList.slice(14); // Trim initialization period
  }

  // 2. MACD (12, 26, 9)
  if (selected.macd) {
    const ema12 = calculateEMA(closes, 12);
    const ema26 = calculateEMA(closes, 26);
    const macdLine = ema12.map((val, i) => val - (ema26[i] ?? 0));
    const signalLine = calculateEMA(macdLine, 9);
    
    result.macd = candles.map((c, i) => {
      const macdVal = macdLine[i] ?? 0;
      const signalVal = signalLine[i] ?? 0;
      return {
        time: c.time,
        macd: Math.round(macdVal * 100) / 100,
        signal: Math.round(signalVal * 100) / 100,
        histogram: Math.round((macdVal - signalVal) * 100) / 100
      };
    }).slice(26);
  }

  // 3. VWAP
  if (selected.vwap) {
    let cumTPV = 0;
    let cumVol = 0;
    let lastDate = '';

    result.vwap = candles.map((c) => {
      const tp = (c.high + c.low + c.close) / 3;
      const vol = c.volume || 0;
      
      const dateStr = typeof c.time === 'number'
        ? new Date(c.time * 1000).toDateString()
        : String(c.time);

      if (dateStr !== lastDate) {
        cumTPV = 0;
        cumVol = 0;
        lastDate = dateStr;
      }

      cumTPV += tp * vol;
      cumVol += vol;
      return {
        time: c.time,
        value: Math.round((cumVol > 0 ? cumTPV / cumVol : tp) * 100) / 100
      };
    });
  }

  // 4. ATR (14)
  const tr: number[] = [(highs[0] ?? 0) - (lows[0] ?? 0)];
  for (let i = 1; i < candles.length; i++) {
    const h = highs[i] ?? 0;
    const l = lows[i] ?? 0;
    const prevC = closes[i - 1] ?? 0;
    tr.push(Math.max(
      h - l,
      Math.abs(h - prevC),
      Math.abs(l - prevC)
    ));
  }
  const atrList = calculateWilderSmoothing(tr, 14);

  if (selected.atr) {
    result.atr = candles.map((c, i) => ({
      time: c.time,
      value: Math.round((atrList[i] ?? 0) * 100) / 100
    })).slice(14);
  }

  // 5. SuperTrend (10, 3)
  if (selected.superTrend) {
    const stTr: number[] = [(highs[0] ?? 0) - (lows[0] ?? 0)];
    for (let i = 1; i < candles.length; i++) {
      const h = highs[i] ?? 0;
      const l = lows[i] ?? 0;
      const prevC = closes[i - 1] ?? 0;
      stTr.push(Math.max(
        h - l,
        Math.abs(h - prevC),
        Math.abs(l - prevC)
      ));
    }
    const atr10 = calculateWilderSmoothing(stTr, 10);
    const superTrend: { time: number | string; value: number; trend: 'up' | 'down' }[] = [];
    
    let trend: 'up' | 'down' = 'up';
    let prevLowerBand = ((highs[0] ?? 0) + (lows[0] ?? 0)) / 2;
    let prevUpperBand = ((highs[0] ?? 0) + (lows[0] ?? 0)) / 2;

    for (let i = 0; i < candles.length; i++) {
      const c = candles[i];
      if (!c) continue;
      if (i < 10) {
        superTrend.push({ time: c.time, value: c.close, trend: 'up' });
        continue;
      }
      const mid = (c.high + c.low) / 2;
      const offset = 3 * (atr10[i] ?? 0);
      const basicLower = mid - offset;
      const basicUpper = mid + offset;

      const prevC = closes[i - 1] ?? 0;
      const finalLower = (basicLower > prevLowerBand || prevC < prevLowerBand) ? basicLower : prevLowerBand;
      const finalUpper = (basicUpper < prevUpperBand || prevC > prevUpperBand) ? basicUpper : prevUpperBand;

      if (trend === 'up' && c.close < finalLower) {
        trend = 'down';
      } else if (trend === 'down' && c.close > finalUpper) {
        trend = 'up';
      }

      const stVal = trend === 'up' ? finalLower : finalUpper;
      superTrend.push({
        time: c.time,
        value: Math.round(stVal * 100) / 100,
        trend
      });

      prevLowerBand = finalLower;
      prevUpperBand = finalUpper;
    }
    result.superTrend = superTrend.slice(10);
  }

  // 6. Ichimoku Cloud (9, 26, 52)
  if (selected.ichimoku) {
    const ichimokuList: {
      time: number | string;
      tenkan: number;
      kijun: number;
      senkouA: number;
      senkouB: number;
      chikou: number;
    }[] = [];

    const getExtrema = (start: number, end: number) => {
      let maxH = highs[start] ?? 0;
      let minL = lows[start] ?? 0;
      for (let i = start + 1; i <= end; i++) {
        const h = highs[i] ?? 0;
        const l = lows[i] ?? 0;
        if (h > maxH) maxH = h;
        if (l < minL) minL = l;
      }
      return { maxH, minL };
    };

    for (let i = 0; i < candles.length; i++) {
      const tenkanPeriod = 9;
      const kijunPeriod = 26;
      const senkouBPeriod = 52;

      let tenkan = 0;
      let kijun = 0;
      let senkouB = 0;

      if (i >= tenkanPeriod - 1) {
        const ext = getExtrema(i - tenkanPeriod + 1, i);
        tenkan = (ext.maxH + ext.minL) / 2;
      }
      if (i >= kijunPeriod - 1) {
        const ext = getExtrema(i - kijunPeriod + 1, i);
        kijun = (ext.maxH + ext.minL) / 2;
      }
      if (i >= senkouBPeriod - 1) {
        const ext = getExtrema(i - senkouBPeriod + 1, i);
        senkouB = (ext.maxH + ext.minL) / 2;
      }

      const senkouA = tenkan && kijun ? (tenkan + kijun) / 2 : 0;
      const chikou = i + 26 < closes.length ? (closes[i + 26] ?? 0) : (closes[closes.length - 1] ?? 0); // future index representation

      ichimokuList.push({
        time: candles[i]?.time ?? 0,
        tenkan: Math.round(tenkan * 100) / 100,
        kijun: Math.round(kijun * 100) / 100,
        senkouA: Math.round(senkouA * 100) / 100,
        senkouB: Math.round(senkouB * 100) / 100,
        chikou: Math.round(chikou * 100) / 100,
      });
    }
    result.ichimoku = ichimokuList.slice(52);
  }

  // 7. Smart Money Concepts (SMC)
  if (selected.smc) {
    const orderBlocks: {
      id: string;
      type: "bullish" | "bearish";
      top: number;
      bottom: number;
      startTime: number | string;
      endTime?: number | string;
      isMitigated: boolean;
    }[] = [];
    const fairValueGaps: {
      id: string;
      type: "bullish" | "bearish";
      top: number;
      bottom: number;
      time: number | string;
      isFilled: boolean;
    }[] = [];
    const liquidityZones: {
      id: string;
      type: "bsl" | "ssl";
      level: number;
      time: number | string;
      isSwept: boolean;
    }[] = [];
    const marketStructure: {
      time: number | string;
      type: "BOS" | "CHoCH";
      direction: "bullish" | "bearish";
      level: number;
    }[] = [];

    // Local Swing Detection Window (size = 5)
    const windowSize = 5;
    const swingHighs: { idx: number; val: number }[] = [];
    const swingLows: { idx: number; val: number }[] = [];

    for (let i = windowSize; i < candles.length - windowSize; i++) {
      let isHigh = true;
      let isLow = true;
      const h_i = highs[i] ?? 0;
      const l_i = lows[i] ?? 0;
      for (let j = -windowSize; j <= windowSize; j++) {
        if ((highs[i + j] ?? 0) > h_i) isHigh = false;
        if ((lows[i + j] ?? 0) < l_i) isLow = false;
      }
      if (isHigh) swingHighs.push({ idx: i, val: h_i });
      if (isLow) swingLows.push({ idx: i, val: l_i });
    }

    // A. Liquidity Zones
    swingHighs.forEach((sh) => {
      const isSwept = closes.slice(sh.idx + 1).some(c => c > sh.val);
      liquidityZones.push({
        id: `bsl-${sh.idx}`,
        type: "bsl",
        level: sh.val,
        time: candles[sh.idx]?.time ?? 0,
        isSwept
      });
    });

    swingLows.forEach((sl) => {
      const isSwept = closes.slice(sl.idx + 1).some(c => c < sl.val);
      liquidityZones.push({
        id: `ssl-${sl.idx}`,
        type: "ssl",
        level: sl.val,
        time: candles[sl.idx]?.time ?? 0,
        isSwept
      });
    });

    // B. Market Structure & Order Blocks
    let currentTrend: 'bullish' | 'bearish' | null = null;
    let lastHighLevel = 0;
    let lastLowLevel = 9999999;

    for (let i = windowSize * 2; i < candles.length; i++) {
      const c = candles[i];
      if (!c) continue;
      
      // Look back for breaking swing highs/lows
      const relevantHighs = swingHighs.filter(sh => sh.idx < i && sh.val > lastHighLevel);
      const relevantLows = swingLows.filter(sl => sl.idx < i && sl.val < lastLowLevel);

      if (relevantHighs.length > 0) {
        const lastSH = relevantHighs[relevantHighs.length - 1];
        if (lastSH && c.close > lastSH.val) {
          const type = currentTrend === 'bearish' ? 'CHoCH' : 'BOS';
          marketStructure.push({
            time: c.time,
            type,
            direction: 'bullish',
            level: lastSH.val
          });
          currentTrend = 'bullish';
          lastHighLevel = lastSH.val;

          // Bullish Order Block: last bearish candle before this breakout/displacement
          // Let's locate the last bearish candle in the range [lastSH.idx, i]
          let obIdx = -1;
          for (let k = i - 1; k >= lastSH.idx; k--) {
            const candK = candles[k];
            if (candK && (closes[k] ?? 0) < candK.open) {
              obIdx = k;
              break;
            }
          }
          if (obIdx !== -1) {
            const obCandle = candles[obIdx];
            if (obCandle) {
              orderBlocks.push({
                id: `ob-bull-${obIdx}`,
                type: 'bullish',
                top: obCandle.high,
                bottom: obCandle.low,
                startTime: obCandle.time,
                isMitigated: closes.slice(i + 1).some(cl => cl < obCandle.low)
              });
            }
          }
        }
      }

      if (relevantLows.length > 0) {
        const lastSL = relevantLows[relevantLows.length - 1];
        if (lastSL && c.close < lastSL.val) {
          const type = currentTrend === 'bullish' ? 'CHoCH' : 'BOS';
          marketStructure.push({
            time: c.time,
            type,
            direction: 'bearish',
            level: lastSL.val
          });
          currentTrend = 'bearish';
          lastLowLevel = lastSL.val;

          // Bearish Order Block: last bullish candle in range [lastSL.idx, i]
          let obIdx = -1;
          for (let k = i - 1; k >= lastSL.idx; k--) {
            const candK = candles[k];
            if (candK && (closes[k] ?? 0) > candK.open) {
              obIdx = k;
              break;
            }
          }
          if (obIdx !== -1) {
            const obCandle = candles[obIdx];
            if (obCandle) {
              orderBlocks.push({
                id: `ob-bear-${obIdx}`,
                type: 'bearish',
                top: obCandle.high,
                bottom: obCandle.low,
                startTime: obCandle.time,
                isMitigated: closes.slice(i + 1).some(cl => cl > obCandle.high)
              });
            }
          }
        }
      }

      // C. Fair Value Gaps (FVG)
      // Formed by 3 candles: i-2, i-1, i
      if (i >= 2) {
        const prev2 = candles[i - 2];
        const prev1 = candles[i - 1];
        const cur = candles[i];

        if (cur && prev1 && prev2) {
          // Bullish FVG: Low of candle i > High of candle i-2
          if (cur.low > prev2.high && (prev1.close - prev1.open) > (atrList[i] ?? 0) * 0.5) {
            const isFilled = closes.slice(i + 1).some(cl => cl < prev2.high);
            fairValueGaps.push({
              id: `fvg-bull-${i - 1}`,
              type: 'bullish',
              top: cur.low,
              bottom: prev2.high,
              time: prev1.time,
              isFilled
            });
          }
          // Bearish FVG: High of candle i < Low of candle i-2
          else if (cur.high < prev2.low && (prev1.open - prev1.close) > (atrList[i] ?? 0) * 0.5) {
            const isFilled = closes.slice(i + 1).some(cl => cl > prev2.low);
            fairValueGaps.push({
              id: `fvg-bear-${i - 1}`,
              type: 'bearish',
              top: prev2.low,
              bottom: cur.high,
              time: prev1.time,
              isFilled
            });
          }
        }
      }
    }

    result.smc = {
      orderBlocks: orderBlocks.filter(ob => !ob.isMitigated).slice(-5), // only return top 5 valid OBs
      fairValueGaps: fairValueGaps.filter(fvg => !fvg.isFilled).slice(-5),
      liquidityZones: liquidityZones.slice(-10),
      marketStructure: marketStructure.slice(-10)
    };
  }

  return result;
}
