"""
SKILL: Chart Pattern Detection
Detects common chart patterns from price history.
Source: yfinance price history
"""
import pandas as pd
import numpy as np


def get_chart_patterns(hist: pd.DataFrame) -> dict:
    try:
        df = hist.copy().dropna()
        closes = df["Close"].values
        highs  = df["High"].values
        lows   = df["Low"].values
        n = len(closes)
        curr = closes[-1]

        patterns_detected = []

        # ── Helper: find swing points ──────────────────────────────────────────
        def swing_highs(arr, window=5):
            pts = []
            for i in range(window, len(arr) - window):
                if arr[i] == max(arr[i-window:i+window+1]):
                    pts.append((i, arr[i]))
            return pts

        def swing_lows(arr, window=5):
            pts = []
            for i in range(window, len(arr) - window):
                if arr[i] == min(arr[i-window:i+window+1]):
                    pts.append((i, arr[i]))
            return pts

        sh = swing_highs(highs)
        sl = swing_lows(lows)

        # ── Double Top ────────────────────────────────────────────────────────
        if len(sh) >= 2:
            t1_idx, t1_val = sh[-2]
            t2_idx, t2_val = sh[-1]
            if abs(t1_val - t2_val) / t1_val < 0.02 and t2_idx > t1_idx + 5:
                neck = min(closes[t1_idx:t2_idx])
                patterns_detected.append(f"DOUBLE TOP (bearish) — neckline ~{round(neck, 2)}")

        # ── Double Bottom ─────────────────────────────────────────────────────
        if len(sl) >= 2:
            b1_idx, b1_val = sl[-2]
            b2_idx, b2_val = sl[-1]
            if abs(b1_val - b2_val) / b1_val < 0.02 and b2_idx > b1_idx + 5:
                neck = max(closes[b1_idx:b2_idx])
                patterns_detected.append(f"DOUBLE BOTTOM (bullish) — neckline ~{round(neck, 2)}")

        # ── Head & Shoulders ─────────────────────────────────────────────────
        if len(sh) >= 3:
            l_sh, hd, r_sh = sh[-3], sh[-2], sh[-1]
            if (hd[1] > l_sh[1] and hd[1] > r_sh[1] and
                    abs(l_sh[1] - r_sh[1]) / hd[1] < 0.04):
                patterns_detected.append("HEAD & SHOULDERS (bearish reversal)")

        # ── Inverse Head & Shoulders ──────────────────────────────────────────
        if len(sl) >= 3:
            l_sh, hd, r_sh = sl[-3], sl[-2], sl[-1]
            if (hd[1] < l_sh[1] and hd[1] < r_sh[1] and
                    abs(l_sh[1] - r_sh[1]) / hd[1] < 0.04):
                patterns_detected.append("INVERSE HEAD & SHOULDERS (bullish reversal)")

        # ── Rising Channel / Flag ─────────────────────────────────────────────
        if n >= 30:
            recent_c = closes[-30:]
            x = np.arange(30)
            slope = np.polyfit(x, recent_c, 1)[0]
            if slope > 0 and (recent_c[-1] - recent_c[0]) / recent_c[0] < 0.08:
                patterns_detected.append("BULL FLAG / Rising Channel (continuation)")
            elif slope < 0 and (recent_c[0] - recent_c[-1]) / recent_c[0] < 0.08:
                patterns_detected.append("BEAR FLAG / Falling Channel (continuation)")

        # ── Consolidation (tight range) ───────────────────────────────────────
        if n >= 20:
            recent_20 = closes[-20:]
            rng_pct = (max(recent_20) - min(recent_20)) / min(recent_20) * 100
            if rng_pct < 5:
                patterns_detected.append(f"CONSOLIDATION — tight {round(rng_pct, 1)}% range (watch for breakout)")

        # ── Higher Highs / Higher Lows ────────────────────────────────────────
        if len(sh) >= 2 and len(sl) >= 2:
            hh = sh[-1][1] > sh[-2][1]
            hl = sl[-1][1] > sl[-2][1]
            lh = sh[-1][1] < sh[-2][1]
            ll = sl[-1][1] < sl[-2][1]
            if hh and hl:
                patterns_detected.append("UPTREND CONFIRMED: Higher Highs + Higher Lows")
            elif lh and ll:
                patterns_detected.append("DOWNTREND CONFIRMED: Lower Highs + Lower Lows")

        return {
            "patterns_detected": patterns_detected if patterns_detected else ["No clear pattern detected"],
            "pattern_count":     len(patterns_detected),
            "primary_bias":      (
                "BULLISH" if any("bullish" in p.lower() or "uptrend" in p.lower() or "bull flag" in p.lower() for p in patterns_detected)
                else "BEARISH" if any("bearish" in p.lower() or "downtrend" in p.lower() or "head & shoulders" in p.lower() or "double top" in p.lower() for p in patterns_detected)
                else "NEUTRAL"
            )
        }
    except Exception as e:
        return {"error": str(e)}
