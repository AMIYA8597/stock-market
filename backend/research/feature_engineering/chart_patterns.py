"""Custom Chart Pattern and Extrema Detector.

Computes swing highs/lows, support/resistance zones, pivot points,
Volume Profile POC, and classic chart formations (double top/bottom,
head-and-shoulders, triangles, wedges, flags, cup-and-handle)
using slope and swing analysis on historical OHLCV data.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from research.feature_engineering.base import FeatureBuilder

logger = logging.getLogger(__name__)


class ChartPatternsBuilder(FeatureBuilder):
    """Detects classical chart formations (double tops/bottoms, head and shoulders, triangles)
    using swing-high and swing-low slope analysis in a causality-safe way.
    """

    name = "chart_patterns"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy()
        n = len(df)
        
        # Initialize output columns
        df["pattern_double_top"] = 0.0
        df["pattern_double_bottom"] = 0.0
        df["pattern_head_shoulders"] = 0.0
        df["pattern_inv_head_shoulders"] = 0.0
        df["pattern_ascending_triangle"] = 0.0
        df["pattern_descending_triangle"] = 0.0
        df["pattern_symmetrical_triangle"] = 0.0
        
        # We need a minimum of 20 bars to look back for swing points
        if n < 20:
            return df
            
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        
        # Strength of swing point (lookback/lookahead of 2 bars to confirm a swing point)
        strength = 2
        
        # We compute patterns in a loop to ensure causality-safety
        for t in range(15, n):
            # Find swing highs and lows confirmed up to time t
            # A swing high at i is confirmed at i + strength <= t
            swing_highs = []
            swing_lows = []
            
            for i in range(strength, t - strength + 1):
                # Check swing high
                is_high = True
                for offset in range(-strength, strength + 1):
                    if offset != 0 and highs[i + offset] >= highs[i]:
                        is_high = False
                        break
                if is_high:
                    swing_highs.append((i, highs[i]))
                    
                # Check swing low
                is_low = True
                for offset in range(-strength, strength + 1):
                    if offset != 0 and lows[i + offset] <= lows[i]:
                        is_low = False
                        break
                if is_low:
                    swing_lows.append((i, lows[i]))
            
            # Require at least 2 swing highs and 2 swing lows to detect patterns
            if len(swing_highs) < 2 or len(swing_lows) < 2:
                continue
                
            # 1. Double Top
            # Last two swing highs
            h2_idx, h2_val = swing_highs[-1]
            h1_idx, h1_val = swing_highs[-2]
            # Find the lowest low between the two highs
            lows_between = [l_val for l_idx, l_val in swing_lows if h1_idx < l_idx < h2_idx]
            if lows_between and abs(h2_val - h1_val) / h1_val < 0.02:
                lowest_low = min(lows_between)
                # Confirmation: close breaks below the lowest low between the tops
                if closes[t] < lowest_low:
                    df.at[df.index[t], "pattern_double_top"] = 1.0
                    
            # 2. Double Bottom
            l2_idx, l2_val = swing_lows[-1]
            l1_idx, l1_val = swing_lows[-2]
            highs_between = [h_val for h_idx, h_val in swing_highs if l1_idx < h_idx < l2_idx]
            if highs_between and abs(l2_val - l1_val) / l1_val < 0.02:
                highest_high = max(highs_between)
                if closes[t] > highest_high:
                    df.at[df.index[t], "pattern_double_bottom"] = 1.0
                    
            # 3. Head and Shoulders
            if len(swing_highs) >= 3:
                h3_idx, h3_val = swing_highs[-1]
                h2_idx, h2_val = swing_highs[-2]
                h1_idx, h1_val = swing_highs[-3]
                # Head must be higher than shoulders
                if h2_val > h1_val and h2_val > h3_val and abs(h1_val - h3_val) / h1_val < 0.03:
                    # Neckline support is the low between H1 and H2, and H2 and H3
                    lows_between_head = [l_val for l_idx, l_val in swing_lows if h1_idx < l_idx < h3_idx]
                    if lows_between_head:
                        neckline = min(lows_between_head)
                        if closes[t] < neckline:
                            df.at[df.index[t], "pattern_head_shoulders"] = 1.0
                            
            # 4. Inverse Head and Shoulders
            if len(swing_lows) >= 3:
                l3_idx, l3_val = swing_lows[-1]
                l2_idx, l2_val = swing_lows[-2]
                l1_idx, l1_val = swing_lows[-3]
                if l2_val < l1_val and l2_val < l3_val and abs(l1_val - l3_val) / l1_val < 0.03:
                    highs_between_head = [h_val for h_idx, h_val in swing_highs if l1_idx < h_idx < l3_idx]
                    if highs_between_head:
                        neckline = max(highs_between_head)
                        if closes[t] > neckline:
                            df.at[df.index[t], "pattern_inv_head_shoulders"] = 1.0
                            
            # 5. Triangles
            # Triangles require at least 3 swing highs and 3 swing lows
            if len(swing_highs) >= 3 and len(swing_lows) >= 3:
                h3_idx, h3_val = swing_highs[-1]
                h2_idx, h2_val = swing_highs[-2]
                h1_idx, h1_val = swing_highs[-3]
                
                l3_idx, l3_val = swing_lows[-1]
                l2_idx, l2_val = swing_lows[-2]
                l1_idx, l1_val = swing_lows[-3]
                
                # Check slopes
                highs_slope = (h3_val - h1_val) / (h3_idx - h1_idx + 1e-6)
                lows_slope = (l3_val - l1_val) / (l3_idx - l1_idx + 1e-6)
                
                # Symmetrical Triangle: falling highs and rising lows
                if highs_slope < -0.0005 and lows_slope > 0.0005:
                    df.at[df.index[t], "pattern_symmetrical_triangle"] = 1.0
                # Ascending Triangle: flat highs and rising lows
                elif abs(highs_slope) < 0.0005 and lows_slope > 0.0005:
                    df.at[df.index[t], "pattern_ascending_triangle"] = 1.0
                # Descending Triangle: falling highs and flat lows
                elif highs_slope < -0.0005 and abs(lows_slope) < 0.0005:
                    df.at[df.index[t], "pattern_descending_triangle"] = 1.0
                    
        return df


class ChartPatternDetector:
    """Detects swing levels, zones, pivots, and chart patterns."""

    def __init__(self, window: int = 5):
        self.window = window

    def get_swing_levels(self, df: pd.DataFrame) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """Identify swing highs and swing lows.
        
        Returns lists of (index_position, price_value) tuples.
        """
        highs = df["high"].values
        lows = df["low"].values
        n = len(df)
        
        swing_highs = []
        swing_lows = []
        
        for i in range(self.window, n - self.window):
            # Check swing high
            is_high = True
            for w in range(-self.window, self.window + 1):
                if highs[i + w] > highs[i]:
                    is_high = False
                    break
            if is_high:
                swing_highs.append((i, float(highs[i])))
                
            # Check swing low
            is_low = True
            for w in range(-self.window, self.window + 1):
                if lows[i + w] < lows[i]:
                    is_low = False
                    break
            if is_low:
                swing_lows.append((i, float(lows[i])))
                
        return swing_highs, swing_lows

    def compute_pivots(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute Classical and Fibonacci Pivot Points from the last bar."""
        last_row = df.iloc[-1]
        h = float(last_row["high"])
        l = float(last_row["low"])
        c = float(last_row["close"])
        
        p = (h + l + c) / 3.0
        
        # Classical
        r1 = 2 * p - l
        s1 = 2 * p - h
        r2 = p + (h - l)
        s2 = p - (h - l)
        r3 = h + 2 * (p - l)
        s3 = l - 2 * (h - p)
        
        # Fibonacci
        fib_r1 = p + 0.382 * (h - l)
        fib_s1 = p - 0.382 * (h - l)
        fib_r2 = p + 0.618 * (h - l)
        fib_s2 = p - 0.618 * (h - l)
        fib_r3 = p + 1.000 * (h - l)
        fib_s3 = p - 1.000 * (h - l)
        
        return {
            "pivot": p,
            "r1": r1, "s1": s1,
            "r2": r2, "s2": s2,
            "r3": r3, "s3": s3,
            "fib_r1": fib_r1, "fib_s1": fib_s1,
            "fib_r2": fib_r2, "fib_s2": fib_s2,
            "fib_r3": fib_r3, "fib_s3": fib_s3,
        }

    def compute_volume_profile(self, df: pd.DataFrame, bins: int = 20) -> Dict[str, Any]:
        """Compute Volume Profile and find Point of Control (POC)."""
        closes = df["close"].values
        volumes = df["volume"].values
        
        min_p = float(np.min(closes))
        max_p = float(np.max(closes))
        
        if min_p == max_p:
            return {"poc": min_p, "bins": []}
            
        bin_edges = np.linspace(min_p, max_p, bins + 1)
        bin_vols = np.zeros(bins)
        
        for price, vol in zip(closes, volumes):
            # Find which bin this price belongs to
            for b in range(bins):
                if bin_edges[b] <= price <= bin_edges[b+1]:
                    bin_vols[b] += vol
                    break
                    
        poc_idx = int(np.argmax(bin_vols))
        poc = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2)
        
        profile_bins = []
        for b in range(bins):
            profile_bins.append({
                "low": float(bin_edges[b]),
                "high": float(bin_edges[b+1]),
                "volume": float(bin_vols[b])
            })
            
        return {
            "poc": poc,
            "profile": profile_bins
        }

    def detect_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect chart patterns using swing highs and swing lows."""
        sh, sl = self.get_swing_levels(df)
        
        # We need a minimum number of swing points to detect complex shapes
        patterns = []
        pattern_score = 0.0  # +1 bullish, -1 bearish
        
        current_close = float(df["close"].iloc[-1])
        
        # 1. Double Top (M-Shape) / Double Bottom (W-Shape)
        if len(sh) >= 2:
            sh1_idx, sh1_val = sh[-2]
            sh2_idx, sh2_val = sh[-1]
            # Check if highs are within 1.5%
            pct_diff = abs(sh1_val - sh2_val) / max(sh1_val, sh2_val)
            if pct_diff <= 0.015 and sh2_idx > sh1_idx:
                # Find intermediate trough (swing low)
                between_sl = [l for l in sl if sh1_idx < l[0] < sh2_idx]
                if between_sl:
                    trough_val = min(l[1] for l in between_sl)
                    if current_close < trough_val:  # breakout below neckline
                        patterns.append("DOUBLE_TOP")
                        pattern_score -= 0.35

        if len(sl) >= 2:
            sl1_idx, sl1_val = sl[-2]
            sl2_idx, sl2_val = sl[-1]
            pct_diff = abs(sl1_val - sl2_val) / max(sl1_val, sl2_val)
            if pct_diff <= 0.015 and sl2_idx > sl1_idx:
                between_sh = [h for h in sh if sl1_idx < h[0] < sl2_idx]
                if between_sh:
                    peak_val = max(h[1] for h in between_sh)
                    if current_close > peak_val:  # breakout above neckline
                        patterns.append("DOUBLE_BOTTOM")
                        pattern_score += 0.35

        # 2. Head and Shoulders (HNS) / Inverse HNS
        if len(sh) >= 3:
            s1 = sh[-3][1] # Left shoulder
            head = sh[-2][1] # Head
            s2 = sh[-1][1] # Right shoulder
            
            if head > s1 and head > s2 and abs(s1 - s2) / max(s1, s2) <= 0.03:
                # Neckline support check
                between_lows = [l for l in sl if sh[-3][0] < l[0] < sh[-1][0]]
                if len(between_lows) >= 2:
                    neckline_val = min(l[1] for l in between_lows)
                    if current_close < neckline_val:
                        patterns.append("HEAD_AND_SHOULDERS")
                        pattern_score -= 0.50

        if len(sl) >= 3:
            s1 = sl[-3][1] # Left shoulder
            head = sl[-2][1] # Head
            s2 = sl[-1][1] # Right shoulder
            
            if head < s1 and head < s2 and abs(s1 - s2) / max(s1, s2) <= 0.03:
                between_highs = [h for h in sh if sl[-3][0] < h[0] < sl[-1][0]]
                if len(between_highs) >= 2:
                    neckline_val = max(h[1] for h in between_highs)
                    if current_close > neckline_val:
                        patterns.append("INVERSE_HEAD_AND_SHOULDERS")
                        pattern_score += 0.50

        # 3. Triangles (Ascending, Descending, Symmetrical)
        # We perform regression or slope checks on last 3 swing points
        if len(sh) >= 2 and len(sl) >= 2:
            high_indices = [h[0] for h in sh[-3:]]
            high_vals = [h[1] for h in sh[-3:]]
            low_indices = [l[0] for l in sl[-3:]]
            low_vals = [l[1] for l in sl[-3:]]
            
            sh_slope = np.polyfit(high_indices, high_vals, 1)[0] if len(high_vals) >= 2 else 0.0
            sl_slope = np.polyfit(low_indices, low_vals, 1)[0] if len(low_vals) >= 2 else 0.0
            
            # Symmetrical (Highs sloping down, Lows sloping up)
            if sh_slope < -1e-4 and sl_slope > 1e-4:
                patterns.append("SYMMETRICAL_TRIANGLE")
                pattern_score += 0.10 * np.sign(current_close - float(df["close"].iloc[-5])) # direction of breakout
            # Ascending (Highs flat, Lows sloping up)
            elif abs(sh_slope) < 2e-4 and sl_slope > 1e-4:
                patterns.append("ASCENDING_TRIANGLE")
                pattern_score += 0.25
            # Descending (Highs sloping down, Lows flat)
            elif sh_slope < -1e-4 and abs(sl_slope) < 2e-4:
                patterns.append("DESCENDING_TRIANGLE")
                pattern_score -= 0.25
                
            # 4. Wedges (Converging in same direction)
            # Rising Wedge (both sloping up, but highs flattening, bearish)
            if sh_slope > 1e-4 and sl_slope > 1e-4 and sh_slope < sl_slope:
                patterns.append("RISING_WEDGE")
                pattern_score -= 0.30
            # Falling Wedge (both sloping down, but lows flattening, bullish)
            elif sh_slope < -1e-4 and sl_slope < -1e-4 and sh_slope > sl_slope:
                patterns.append("FALLING_WEDGE")
                pattern_score += 0.30

        # 5. Cup and Handle
        # U-shaped trough over past 40 days, followed by a slight down-consolidation
        if len(df) >= 40:
            past_40 = df["close"].values[-40:]
            left_rim = past_40[0]
            right_rim = past_40[-10]
            mid_trough = np.min(past_40[:-10])
            trough_idx = int(np.argmin(past_40[:-10]))
            
            # Cup condition
            if abs(left_rim - right_rim) / max(left_rim, right_rim) <= 0.05 and mid_trough < min(left_rim, right_rim) * 0.90:
                if 10 < trough_idx < 30: # trough is centered
                    # Handle condition (slight pullback in last 10 days)
                    handle_prices = past_40[-10:]
                    handle_max = np.max(handle_prices)
                    if handle_max <= right_rim * 1.02 and current_close > handle_prices[-5]:
                        patterns.append("CUP_AND_HANDLE")
                        pattern_score += 0.40

        # Support & Resistance density zones
        sr_zones = []
        try:
            from app.services.sr_service import SupportResistanceEngine
            zones_res = SupportResistanceEngine.detect_classical_zones(df)
            sr_zones = [z["avg"] for z in zones_res]
        except Exception as e:
            all_swings = [s[1] for s in sh] + [s[1] for s in sl]
            if all_swings:
                hist, bin_edges = np.histogram(all_swings, bins=10)
                top_bins = np.argsort(hist)[::-1][:3] # top 3 density clusters
                for b in top_bins:
                    zone_center = (bin_edges[b] + bin_edges[b + 1]) / 2.0
                    sr_zones.append(float(zone_center))
            else:
                sr_zones = [current_close * 0.95, current_close * 1.05]

        return {
            "pattern_score": float(np.clip(pattern_score, -1.0, 1.0)),
            "patterns_detected": patterns,
            "support_resistance_zones": sorted(sr_zones),
            "pivots": self.compute_pivots(df),
            "volume_profile": self.compute_volume_profile(df),
        }
