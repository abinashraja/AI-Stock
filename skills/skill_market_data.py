"""
SKILL: Market Data
Fetches current price, OHLC, 52-week H/L, volume, market cap, free float.
Source: yfinance
"""
import yfinance as yf
import pandas as pd
import math


def safe_num(val):
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except:
        return None


def get_market_data(ticker: str, info: dict, hist: pd.DataFrame) -> dict:
    try:
        closes = hist["Close"].dropna() if not hist.empty else pd.Series(dtype=float)

        curr = safe_num(info.get("currentPrice")) or safe_num(info.get("regularMarketPrice"))
        if curr is None and not closes.empty:
            curr = safe_num(closes.iloc[-1])

        prev_close = safe_num(info.get("previousClose")) or safe_num(info.get("regularMarketPreviousClose"))
        if prev_close is None and len(closes) >= 2:
            prev_close = safe_num(closes.iloc[-2])

        change_pct = ((curr - prev_close) / prev_close * 100) if (curr and prev_close and prev_close != 0) else None

        # 52-week range from history
        high_52w = None
        low_52w = None
        if not hist.empty:
            highs = hist["High"].dropna().tail(252)
            lows = hist["Low"].dropna().tail(252)
            if not highs.empty:
                high_52w = safe_num(highs.max())
            if not lows.empty:
                low_52w = safe_num(lows.min())

        if high_52w is None:
            high_52w = safe_num(info.get("fiftyTwoWeekHigh"))
        if low_52w is None:
            low_52w = safe_num(info.get("fiftyTwoWeekLow"))

        # Today's candle
        last_row = hist.iloc[-1] if not hist.empty else {}

        mkt_cap = safe_num(info.get("marketCap"))
        shares_out = safe_num(info.get("sharesOutstanding"))
        float_shares = safe_num(info.get("floatShares"))
        free_float_pct = (float_shares / shares_out * 100) if (float_shares and shares_out and shares_out != 0) else None

        vol_series = hist["Volume"].dropna() if not hist.empty else pd.Series(dtype=float)
        avg_vol_10 = safe_num(vol_series.tail(10).mean()) if not vol_series.empty else None
        avg_vol_20 = safe_num(vol_series.tail(20).mean()) if not vol_series.empty else None

        curr_vol = safe_num(last_row.get("Volume")) if not hist.empty else None

        return {
            "current_price":    round(curr, 2) if curr is not None else "N/A",
            "prev_close":       round(prev_close, 2) if prev_close is not None else "N/A",
            "change_pct":       round(change_pct, 2) if change_pct is not None else "N/A",
            "open":             round(safe_num(last_row.get("Open")), 2) if safe_num(last_row.get("Open")) is not None else "N/A",
            "high":             round(safe_num(last_row.get("High")), 2) if safe_num(last_row.get("High")) is not None else "N/A",
            "low":              round(safe_num(last_row.get("Low")), 2) if safe_num(last_row.get("Low")) is not None else "N/A",
            "close":            round(safe_num(last_row.get("Close")), 2) if safe_num(last_row.get("Close")) is not None else "N/A",
            "volume":           int(curr_vol) if curr_vol is not None else "N/A",
            "avg_volume_10d":   int(avg_vol_10) if avg_vol_10 is not None else "N/A",
            "avg_volume_20d":   int(avg_vol_20) if avg_vol_20 is not None else "N/A",
            "52w_high":         round(high_52w, 2) if high_52w is not None else "N/A",
            "52w_low":          round(low_52w, 2) if low_52w is not None else "N/A",
            "market_cap_cr":    round(mkt_cap / 1e7, 0) if mkt_cap is not None else "N/A",  # in Crores
            "shares_outstanding": int(shares_out) if shares_out is not None else "N/A",
            "free_float_pct":   round(free_float_pct, 1) if free_float_pct is not None else "N/A",
            "exchange":         info.get("exchange", "N/A"),
            "sector":           info.get("sector", "N/A"),
            "industry":         info.get("industry", "N/A"),
            "company_name":     info.get("shortName") or info.get("longName") or ticker,
        }
    except Exception as e:
        return {"error": str(e)}
