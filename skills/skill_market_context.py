"""
SKILL: Market Context
NIFTY 50 trend, VIX, Bank NIFTY — overall market regime.
Source: yfinance (^NSEI, ^NSEBANK, ^INDIAVIX)
"""
import yfinance as yf
import pandas as pd


def get_market_context() -> dict:
    try:
        indices = {
            "NIFTY_50":    "^NSEI",
            "BANK_NIFTY":  "^NSEBANK",
            "INDIA_VIX":   "^INDIAVIX",
            "NIFTY_IT":    "^CNXIT",
            "NIFTY_PHARMA": "^CNXPHARMA",
        }

        results = {}
        for name, sym in indices.items():
            try:
                t = yf.Ticker(sym)
                h = t.history(period="3mo")
                if h.empty:
                    results[name] = "N/A"
                    continue
                curr  = round(float(h["Close"].iloc[-1]), 2)
                prev  = round(float(h["Close"].iloc[-2]), 2)
                chg   = round((curr - prev) / prev * 100, 2)
                h_sma50 = h["Close"].rolling(50).mean()
                sma50 = round(float(h_sma50.iloc[-1]), 2) if not h_sma50.empty else "N/A"
                trend = "ABOVE 50-SMA (Bullish)" if curr > sma50 else "BELOW 50-SMA (Bearish)"
                results[name] = {
                    "price": curr, "change_pct": chg,
                    "sma50": sma50, "trend": trend
                }
            except:
                results[name] = "N/A"

        # VIX interpretation
        vix_val = "N/A"
        vix_regime = "N/A"
        if isinstance(results.get("INDIA_VIX"), dict):
            vix_val = results["INDIA_VIX"]["price"]
            if vix_val != "N/A":
                if vix_val < 12:   vix_regime = "VERY LOW FEAR — complacency risk"
                elif vix_val < 16: vix_regime = "LOW FEAR — normal market"
                elif vix_val < 20: vix_regime = "MODERATE FEAR"
                elif vix_val < 25: vix_regime = "HIGH FEAR — opportunity zone"
                else:              vix_regime = "EXTREME FEAR — wait for stability"

        # Overall market regime
        nifty = results.get("NIFTY_50", {})
        market_regime = "N/A"
        if isinstance(nifty, dict):
            if "ABOVE" in nifty.get("trend", ""):
                market_regime = "BULL MARKET — favourable for longs"
            else:
                market_regime = "BEAR MARKET — caution, prefer cash"

        return {
            "nifty_50":      results.get("NIFTY_50"),
            "bank_nifty":    results.get("BANK_NIFTY"),
            "india_vix":     vix_val,
            "vix_regime":    vix_regime,
            "nifty_it":      results.get("NIFTY_IT"),
            "nifty_pharma":  results.get("NIFTY_PHARMA"),
            "market_regime": market_regime,
        }
    except Exception as e:
        return {"error": str(e)}
