"""
SKILL: Support & Resistance
Detects key support/resistance levels using pivot points and price action.
Source: yfinance price history
"""
import pandas as pd
import numpy as np


def get_support_resistance(hist: pd.DataFrame) -> dict:
    try:
        df = hist.copy().dropna()
        closes = df["Close"]
        highs  = df["High"]
        lows   = df["Low"]

        curr = float(closes.iloc[-1])

        # ── Classic Pivot Points (last full week) ─────────────────────────────
        h = float(highs.tail(5).max())
        l = float(lows.tail(5).min())
        c = float(closes.iloc[-1])
        pivot  = round((h + l + c) / 3, 2)
        r1 = round(2 * pivot - l, 2)
        r2 = round(pivot + (h - l), 2)
        r3 = round(h + 2 * (pivot - l), 2)
        s1 = round(2 * pivot - h, 2)
        s2 = round(pivot - (h - l), 2)
        s3 = round(l - 2 * (h - pivot), 2)

        # ── Swing Highs/Lows (price action levels) ────────────────────────────
        # A swing high = candle where high > 2 neighbours on each side
        swing_highs = []
        swing_lows  = []
        arr_h = highs.values
        arr_l = lows.values
        for i in range(2, len(arr_h) - 2):
            if arr_h[i] > arr_h[i-1] and arr_h[i] > arr_h[i-2] and arr_h[i] > arr_h[i+1] and arr_h[i] > arr_h[i+2]:
                swing_highs.append(round(float(arr_h[i]), 2))
            if arr_l[i] < arr_l[i-1] and arr_l[i] < arr_l[i-2] and arr_l[i] < arr_l[i+1] and arr_l[i] < arr_l[i+2]:
                swing_lows.append(round(float(arr_l[i]), 2))

        # Cluster nearby levels (within 1%)
        def cluster(levels, tolerance=0.01):
            levels = sorted(set(levels))
            clusters = []
            current = []
            for lvl in levels:
                if not current or lvl <= current[-1] * (1 + tolerance):
                    current.append(lvl)
                else:
                    clusters.append(round(np.mean(current), 2))
                    current = [lvl]
            if current:
                clusters.append(round(np.mean(current), 2))
            return clusters

        clustered_highs = cluster(swing_highs)
        clustered_lows  = cluster(swing_lows)

        # Split into above/below current price
        resistances = sorted([x for x in clustered_highs if x > curr])
        supports    = sorted([x for x in clustered_lows  if x < curr], reverse=True)

        # Nearest breakout (first resistance above) and breakdown (first support below)
        breakout_level   = resistances[0] if resistances else round(curr * 1.05, 2)
        breakdown_level  = supports[0]    if supports    else round(curr * 0.95, 2)

        # Distance %
        def dist_pct(level):
            return round((level - curr) / curr * 100, 2)

        return {
            "current_price":         round(curr, 2),
            "pivot_point":           pivot,
            "resistance_1":          r1,
            "resistance_2":          r2,
            "resistance_3":          r3,
            "support_1":             s1,
            "support_2":             s2,
            "support_3":             s3,
            "major_resistances":     resistances[:4],
            "major_supports":        supports[:4],
            "breakout_level":        breakout_level,
            "breakout_dist_pct":     dist_pct(breakout_level),
            "breakdown_level":       breakdown_level,
            "breakdown_dist_pct":    dist_pct(breakdown_level),
            "nearest_resistance":    resistances[0] if resistances else "N/A",
            "nearest_support":       supports[0]    if supports    else "N/A",
        }
    except Exception as e:
        return {"error": str(e)}
