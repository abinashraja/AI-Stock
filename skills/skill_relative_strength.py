"""
SKILL: Relative Strength
Compares stock performance vs NIFTY 50 across timeframes.
Source: yfinance
"""
import yfinance as yf
import pandas as pd


def get_relative_strength(hist: pd.DataFrame, ticker: str) -> dict:
    try:
        nifty = yf.Ticker("^NSEI").history(period="2y")
        if nifty.empty or hist.empty:
            return {"error": "Could not fetch comparison data"}

        stock_closes = hist["Close"].dropna()
        nifty_closes = nifty["Close"].dropna()

        def period_return(series, days):
            if len(series) < days:
                return "N/A"
            try:
                start = series.iloc[-days]
                end   = series.iloc[-1]
                return round((end - start) / start * 100, 2)
            except:
                return "N/A"

        timeframes = {"1M": 22, "3M": 63, "6M": 126, "1Y": 252}
        rs_data = {}
        for label, days in timeframes.items():
            s_ret = period_return(stock_closes, days)
            n_ret = period_return(nifty_closes, days)
            if s_ret != "N/A" and n_ret != "N/A":
                alpha = round(s_ret - n_ret, 2)
                rs_data[label] = {
                    "stock_return_pct":  s_ret,
                    "nifty_return_pct":  n_ret,
                    "alpha_pct":         alpha,
                    "signal":            "OUTPERFORMING" if alpha > 0 else "UNDERPERFORMING"
                }
            else:
                rs_data[label] = {"stock_return_pct": s_ret, "nifty_return_pct": n_ret, "alpha_pct": "N/A", "signal": "N/A"}

        # Beta (6-month daily returns)
        try:
            s_r = stock_closes.pct_change().tail(126).dropna()
            n_r = nifty_closes.pct_change().tail(126).dropna()
            combined = pd.concat([s_r, n_r], axis=1, join="inner")
            combined.columns = ["stock", "nifty"]
            cov   = combined.cov().iloc[0, 1]
            var_n = combined["nifty"].var()
            beta  = round(cov / var_n, 2) if var_n else "N/A"
        except:
            beta = "N/A"

        beta_signal = "N/A"
        if beta != "N/A":
            if beta < 0.8:   beta_signal = "LOW BETA (defensive)"
            elif beta < 1.2: beta_signal = "MARKET-LIKE BETA"
            else:            beta_signal = "HIGH BETA (volatile — amplifies market moves)"

        return {
            "relative_strength_vs_nifty": rs_data,
            "beta_6m":       beta,
            "beta_signal":   beta_signal,
        }
    except Exception as e:
        return {"error": str(e)}
