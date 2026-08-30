"""
SKILL: Technical Analysis
Calculates all technical indicators from price history locally.
Source: yfinance price history (calculated with pandas/numpy)
"""
import pandas as pd
import numpy as np


def get_technical_data(hist: pd.DataFrame, info: dict) -> dict:
    try:
        df = hist.copy()
        closes = df["Close"].dropna()
        highs  = df["High"].dropna()
        lows   = df["Low"].dropna()
        vols   = df["Volume"].dropna()
        n = len(closes)

        def safe_val(series, idx=-1):
            try:
                v = series.iloc[idx]
                f = float(v)
                return round(f, 2) if not (np.isnan(f) or np.isinf(f)) else "N/A"
            except:
                return "N/A"

        # ── SMAs ──────────────────────────────────────────────────────────────
        sma20  = closes.rolling(20).mean()
        sma50  = closes.rolling(50).mean()
        sma100 = closes.rolling(100).mean()
        sma200 = closes.rolling(200).mean()

        curr_price = safe_val(closes)
        s20  = safe_val(sma20)
        s50  = safe_val(sma50)
        s100 = safe_val(sma100)
        s200 = safe_val(sma200)

        # Trend structure
        def trend_vs_sma(price, sma):
            if price == "N/A" or sma == "N/A": return "N/A"
            return "ABOVE" if price > sma else "BELOW"

        # Golden / Death cross (50 vs 200)
        cross = "N/A"
        if s50 != "N/A" and s200 != "N/A":
            cross = "GOLDEN CROSS (Bullish)" if s50 > s200 else "DEATH CROSS (Bearish)"

        # ── RSI (14) ──────────────────────────────────────────────────────────
        rsi = "N/A"
        if n >= 15:
            delta = closes.diff().dropna()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1e-9)
            rsi_series = 100 - (100 / (1 + rs))
            rsi = safe_val(rsi_series)
            if rsi != "N/A" and not (5 < rsi < 95):
                rsi = "N/A"  # sanity check

        # ── MACD ─────────────────────────────────────────────────────────────
        macd_line = "N/A"; macd_signal = "N/A"; macd_hist = "N/A"; macd_cross = "N/A"
        if n >= 27:
            ema12 = closes.ewm(span=12, adjust=False).mean()
            ema26 = closes.ewm(span=26, adjust=False).mean()
            macd_s = ema12 - ema26
            signal_s = macd_s.ewm(span=9, adjust=False).mean()
            hist_s = macd_s - signal_s
            macd_line   = safe_val(macd_s)
            macd_signal = safe_val(signal_s)
            macd_hist   = safe_val(hist_s)
            if macd_line != "N/A" and macd_signal != "N/A":
                macd_cross = "BULLISH" if macd_line > macd_signal else "BEARISH"

        # ── ATR (14) ──────────────────────────────────────────────────────────
        atr = "N/A"
        if n >= 15:
            tr = pd.concat([
                highs - lows,
                (highs - closes.shift()).abs(),
                (lows  - closes.shift()).abs()
            ], axis=1).max(axis=1)
            atr = safe_val(tr.rolling(14).mean())

        # ── Bollinger Bands (20, 2σ) ──────────────────────────────────────────
        bb_upper = bb_lower = bb_pct = "N/A"
        if n >= 20:
            std20 = closes.rolling(20).std()
            bb_upper = safe_val(sma20 + 2 * std20)
            bb_lower = safe_val(sma20 - 2 * std20)
            if curr_price != "N/A" and bb_upper != "N/A" and bb_lower != "N/A":
                rng = bb_upper - bb_lower
                bb_pct = round((curr_price - bb_lower) / rng * 100, 1) if rng else "N/A"

        # ── ADX (14) ─────────────────────────────────────────────────────────
        adx = "N/A"
        if n >= 28:
            up_move   = highs.diff()
            down_move = -lows.diff()
            plus_dm  = up_move.where((up_move > down_move) & (up_move > 0), 0)
            minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
            tr_s = pd.concat([highs - lows, (highs - closes.shift()).abs(), (lows - closes.shift()).abs()], axis=1).max(axis=1)
            atr14 = tr_s.rolling(14).mean().replace(0, 1e-9)
            plus_di  = 100 * plus_dm.rolling(14).mean()  / atr14
            minus_di = 100 * minus_dm.rolling(14).mean() / atr14
            dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-9))
            adx = safe_val(dx.rolling(14).mean())

        # ── Stochastic (14,3) ─────────────────────────────────────────────────
        stoch_k = stoch_d = "N/A"
        if n >= 17:
            low14  = lows.rolling(14).min()
            high14 = highs.rolling(14).max()
            k = 100 * (closes - low14) / (high14 - low14).replace(0, 1e-9)
            d = k.rolling(3).mean()
            stoch_k = safe_val(k)
            stoch_d = safe_val(d)

        # ── VWAP (last 20 days) ───────────────────────────────────────────────
        vwap = "N/A"
        try:
            typical = (highs + lows + closes) / 3
            vwap_val = (typical * vols).rolling(20).sum() / vols.rolling(20).sum()
            vwap = safe_val(vwap_val)
        except:
            pass

        # ── Trend Structure (HH/HL or LH/LL) ─────────────────────────────────
        trend_structure = "N/A"
        if n >= 40:
            recent = closes.tail(40)
            pivots = recent.rolling(5, center=True).max()
            local_highs = recent[recent == pivots].dropna()
            if len(local_highs) >= 2:
                if local_highs.iloc[-1] > local_highs.iloc[-2]:
                    trend_structure = "HIGHER HIGHS (Bullish)"
                else:
                    trend_structure = "LOWER HIGHS (Bearish)"

        return {
            "current_price": curr_price,
            "sma_20":  s20,
            "sma_50":  s50,
            "sma_100": s100,
            "sma_200": s200,
            "price_vs_sma20":  trend_vs_sma(curr_price, s20),
            "price_vs_sma50":  trend_vs_sma(curr_price, s50),
            "price_vs_sma100": trend_vs_sma(curr_price, s100),
            "price_vs_sma200": trend_vs_sma(curr_price, s200),
            "golden_death_cross": cross,
            "rsi_14":           rsi,
            "rsi_zone":         ("OVERSOLD (<30)" if rsi != "N/A" and rsi < 30
                                 else "ACCUMULATION (30-50)" if rsi != "N/A" and rsi < 50
                                 else "BULLISH (50-65)" if rsi != "N/A" and rsi < 65
                                 else "STRONG (65-75)" if rsi != "N/A" and rsi < 75
                                 else "OVERBOUGHT (>75)" if rsi != "N/A"
                                 else "N/A"),
            "macd_line":    macd_line,
            "macd_signal":  macd_signal,
            "macd_hist":    macd_hist,
            "macd_trend":   macd_cross,
            "atr_14":       atr,
            "bb_upper":     bb_upper,
            "bb_lower":     bb_lower,
            "bb_pct":       bb_pct,
            "adx_14":       adx,
            "adx_strength": ("WEAK (<20)" if adx != "N/A" and adx < 20
                             else "MODERATE (20-25)" if adx != "N/A" and adx < 25
                             else "STRONG (25-40)" if adx != "N/A" and adx < 40
                             else "VERY STRONG (>40)" if adx != "N/A"
                             else "N/A"),
            "stoch_k":      stoch_k,
            "stoch_d":      stoch_d,
            "vwap_20d":     vwap,
            "trend_structure": trend_structure,
        }
    except Exception as e:
        return {"error": str(e)}
