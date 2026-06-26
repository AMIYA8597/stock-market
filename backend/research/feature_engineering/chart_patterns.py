"""Chart pattern detection using swing highs/lows slope analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from research.feature_engineering.base import FeatureBuilder

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
