import { type UTCTimestamp, type SeriesMarker } from "lightweight-charts";

interface PriceBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

function toUtcTimestamp(value: string): UTCTimestamp {
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
}

export function detectPatterns(bars: PriceBar[]): SeriesMarker<UTCTimestamp>[] {
  const markers: SeriesMarker<UTCTimestamp>[] = [];

  for (let i = 0; i < bars.length; i++) {
    const bar = bars[i];
    if (!bar) continue;

    const open = bar.open;
    const high = bar.high;
    const low = bar.low;
    const close = bar.close;

    const range = high - low;
    const bodySize = Math.abs(close - open);
    const upperWick = high - Math.max(open, close);
    const lowerWick = Math.min(open, close) - low;
    const time = toUtcTimestamp(bar.timestamp);

    if (range <= 0) continue;

    const isBullish = close > open;
    const isBearish = close < open;

    // Trend calculation helper based on the previous 5 bars
    let isUptrend = false;
    let isDowntrend = false;
    if (i >= 5) {
      const prev5 = bars.slice(i - 5, i);
      const closes = prev5.map((b) => b.close);
      const avg = closes.reduce((sum, v) => sum + v, 0) / 5;
      isUptrend = close > avg;
      isDowntrend = close < avg;
    }

    // 1. Dragonfly Doji (open, high, close near high, long lower wick)
    if (bodySize <= range * 0.05 && lowerWick >= range * 0.6 && upperWick <= range * 0.1) {
      markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#FFEB3B", text: "Dragonfly Doji" });
      continue;
    }

    // 2. Gravestone Doji (open, low, close near low, long upper wick)
    if (bodySize <= range * 0.05 && upperWick >= range * 0.6 && lowerWick <= range * 0.1) {
      markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#FFC107", text: "Gravestone Doji" });
      continue;
    }

    // 3. Doji
    if (bodySize <= range * 0.05) {
      markers.push({ time, position: "inBar", shape: "circle", color: "#FFEB3B", text: "Doji" });
      continue;
    }

    // 4. Marubozu (Solid body with no or minimal wicks)
    if (bodySize >= range * 0.95) {
      markers.push({ time, position: "inBar", shape: "square", color: isBullish ? "#8E24AA" : "#D81B60", text: "Marubozu" });
      continue;
    }

    // 5. Hammer (Long lower wick, small body at the top, typically in downtrend)
    if (lowerWick >= bodySize * 2 && upperWick <= range * 0.1 && (isDowntrend || !isUptrend)) {
      markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#00E676", text: "Hammer" });
      continue;
    }

    // 6. Hanging Man (Same structure as Hammer, but in uptrend)
    if (lowerWick >= bodySize * 2 && upperWick <= range * 0.1 && isUptrend) {
      markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#FF3B5C", text: "Hanging Man" });
      continue;
    }

    // 7. Inverted Hammer (Long upper wick, small body at bottom, typically in downtrend)
    if (upperWick >= bodySize * 2 && lowerWick <= range * 0.1 && (isDowntrend || !isUptrend)) {
      markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#00E5FF", text: "Inv Hammer" });
      continue;
    }

    // 8. Shooting Star (Same structure as Inverted Hammer, but in uptrend)
    if (upperWick >= bodySize * 2 && lowerWick <= range * 0.1 && isUptrend) {
      markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#E040FB", text: "Shooting Star" });
      continue;
    }

    // 9. Spinning Top (Small body, long and relatively equal wicks)
    if (bodySize > range * 0.05 && bodySize <= range * 0.3 && Math.abs(upperWick - lowerWick) <= range * 0.2) {
      markers.push({ time, position: "inBar", shape: "circle", color: "#3F51B5", text: "Spinning Top" });
      continue;
    }

    // 2-bar patterns
    if (i > 0) {
      const prevBar = bars[i - 1];
      if (prevBar) {
        const prevOpen = prevBar.open;
        const prevClose = prevBar.close;
        const prevBodySize = Math.abs(prevClose - prevOpen);
        const prevIsBearish = prevClose < prevOpen;
        const prevIsBullish = prevClose > prevOpen;

        // 10. Tweezer Bottom (identical lows)
        if (Math.abs(low - prevBar.low) / (low || 1) <= 0.0015 && isBullish && prevIsBearish) {
          markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#00D4F5", text: "Tweezer Bottom" });
          continue;
        }

        // 11. Tweezer Top (identical highs)
        if (Math.abs(high - prevBar.high) / (high || 1) <= 0.0015 && isBearish && prevIsBullish) {
          markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#EC4899", text: "Tweezer Top" });
          continue;
        }

        // 12. Bullish Engulfing
        if (prevIsBearish && isBullish && open <= prevClose && close >= prevOpen && bodySize > prevBodySize) {
          markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#00E676", text: "Bullish Engulfing" });
          continue;
        }

        // 13. Bearish Engulfing
        if (prevIsBullish && isBearish && open >= prevClose && close <= prevOpen && bodySize > prevBodySize) {
          markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#FF3B5C", text: "Bearish Engulfing" });
          continue;
        }

        // 14. Piercing Line (closes above 50% of the previous bearish candle's body)
        if (prevIsBearish && isBullish && open < prevClose && close >= prevOpen - prevBodySize * 0.5 && close < prevOpen) {
          markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#4CAF50", text: "Piercing Line" });
          continue;
        }

        // 15. Dark Cloud Cover (closes below 50% of the previous bullish candle's body)
        if (prevIsBullish && isBearish && open > prevClose && close <= prevOpen + prevBodySize * 0.5 && close > prevOpen) {
          markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#FF9800", text: "Dark Cloud Cover" });
          continue;
        }

        // 16. Harami Pattern (current body completely inside previous body)
        if (
          Math.max(open, close) <= Math.max(prevOpen, prevClose) &&
          Math.min(open, close) >= Math.min(prevOpen, prevClose)
        ) {
          const text = (isBullish && prevIsBearish) ? "Bullish Harami" : (isBearish && prevIsBullish) ? "Bearish Harami" : "Harami";
          markers.push({
            time,
            position: "inBar",
            shape: "circle",
            color: isBullish ? "#4CAF50" : "#F44336",
            text,
          });
          continue;
        }
      }
    }

    // 3-bar patterns
    if (i > 1) {
      const prev1 = bars[i - 1];
      const prev2 = bars[i - 2];
      if (prev1 && prev2) {
        const p2Open = prev2.open;
        const p2Close = prev2.close;
        const p1Open = prev1.open;
        const p1Close = prev1.close;

        const p2Body = Math.abs(p2Close - p2Open);
        const p1Body = Math.abs(p1Close - p1Open);

        // 17. Morning Star (bearish trend reversal)
        if (
          p2Close < p2Open && // P2 is long bearish
          p1Body < p2Body * 0.3 && // P1 is small body (star)
          isBullish && // Current is bullish
          close > p2Close + p2Body * 0.5 // Closes well inside P2 body
        ) {
          markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#00E676", text: "Morning Star" });
          continue;
        }

        // 18. Evening Star (bullish trend reversal)
        if (
          p2Close > p2Open && // P2 is long bullish
          p1Body < p2Body * 0.3 && // P1 is small body (star)
          isBearish && // Current is bearish
          close < p2Close - p2Body * 0.5 // Closes well inside P2 body
        ) {
          markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#FF3B5C", text: "Evening Star" });
          continue;
        }

        // 19. Three White Soldiers (three consecutive strong bullish days)
        if (
          prev2.close > prev2.open &&
          prev1.close > prev1.open &&
          isBullish &&
          prev1.close > prev2.close &&
          close > prev1.close &&
          prev1.open >= prev2.open && prev1.open <= prev2.close &&
          open >= prev1.open && open <= prev1.close
        ) {
          markers.push({ time, position: "belowBar", shape: "arrowUp", color: "#00E676", text: "3 Soldiers" });
          continue;
        }

        // 20. Three Black Crows (three consecutive strong bearish days)
        if (
          prev2.close < prev2.open &&
          prev1.close < prev1.open &&
          isBearish &&
          prev1.close < prev2.close &&
          close < prev1.close &&
          prev1.open <= prev2.open && prev1.open >= prev2.close &&
          open <= prev1.open && open >= prev1.close
        ) {
          markers.push({ time, position: "aboveBar", shape: "arrowDown", color: "#FF3B5C", text: "3 Crows" });
          continue;
        }
      }
    }
  }

  return markers;
}
