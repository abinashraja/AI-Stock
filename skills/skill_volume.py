"""
SKILL: Volume Analysis
Analyzes volume trends, accumulation/distribution, unusual activity.
Source: yfinance
"""
import pandas as pd
import numpy as np


def get_volume_analysis(hist: pd.DataFrame) -> dict:
    try:
        df = hist.copy().dropna()
        closes = df["Close"]
        vols   = df["Volume"]
        highs  = df["High"]
        lows   = df["Low"]

        curr_vol  = int(vols.iloc[-1])
        avg_vol10 = int(vols.tail(10).mean())
        avg_vol20 = int(vols.tail(20).mean())
        avg_vol50 = int(vols.tail(50).mean())

        vol_vs_avg10 = round(curr_vol / avg_vol10 * 100, 1) if avg_vol10 else 0
        vol_vs_avg20 = round(curr_vol / avg_vol20 * 100, 1) if avg_vol20 else 0

        vol_signal = "NORMAL"
        if vol_vs_avg20 > 200:
            vol_signal = "VERY HIGH VOLUME (2x avg — significant event)"
        elif vol_vs_avg20 > 150:
            vol_signal = "HIGH VOLUME (1.5x avg — strong interest)"
        elif vol_vs_avg20 < 50:
            vol_signal = "LOW VOLUME (weak conviction)"

        # ── On-Balance Volume (OBV) ───────────────────────────────────────────
        obv = [0]
        close_arr = closes.values
        vol_arr   = vols.values
        for i in range(1, len(close_arr)):
            if close_arr[i] > close_arr[i-1]:
                obv.append(obv[-1] + vol_arr[i])
            elif close_arr[i] < close_arr[i-1]:
                obv.append(obv[-1] - vol_arr[i])
            else:
                obv.append(obv[-1])
        obv_series = pd.Series(obv, index=closes.index)
        obv_trend  = "RISING (accumulation)" if obv_series.iloc[-1] > obv_series.iloc[-20] else "FALLING (distribution)"

        # ── Accumulation/Distribution Line ────────────────────────────────────
        clv = ((closes - lows) - (highs - closes)) / (highs - lows).replace(0, 1e-9)
        ad  = (clv * vols).cumsum()
        ad_trend = "ACCUMULATION" if ad.iloc[-1] > ad.iloc[-20] else "DISTRIBUTION"

        # ── Volume Price Trend ────────────────────────────────────────────────
        price_change_pct = closes.pct_change().dropna()
        vpt = (price_change_pct * vols).cumsum()
        vpt_trend = "BULLISH" if vpt.iloc[-1] > vpt.iloc[-20] else "BEARISH"

        # ── Unusual Volume days ───────────────────────────────────────────────
        unusual_days = int((vols.tail(20) > avg_vol20 * 1.5).sum())

        # ── Volume Trend (5-day vs 20-day avg) ────────────────────────────────
        vol_5d_avg = vols.tail(5).mean()
        volume_momentum = "INCREASING" if vol_5d_avg > avg_vol20 else "DECREASING"

        return {
            "current_volume":       curr_vol,
            "avg_volume_10d":       avg_vol10,
            "avg_volume_20d":       avg_vol20,
            "avg_volume_50d":       avg_vol50,
            "vol_vs_avg20_pct":     vol_vs_avg20,
            "volume_signal":        vol_signal,
            "obv_trend":            obv_trend,
            "ad_trend":             ad_trend,
            "vpt_trend":            vpt_trend,
            "volume_momentum":      volume_momentum,
            "unusual_vol_days_20":  unusual_days,
        }
    except Exception as e:
        return {"error": str(e)}
