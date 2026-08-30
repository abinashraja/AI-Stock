"""
SKILL: Fundamentals
Revenue, PAT, EPS, margins, ROE, ROCE, FCF from yfinance financials.
Source: yfinance
"""
import pandas as pd
import numpy as np


def safe_cr(val):
    """Convert raw INR to Crores (1 Cr = 10M)"""
    try:
        v = float(val)
        if abs(v) > 1e6:
            return round(v / 1e7, 2)  # to Crores
        return round(v, 2)
    except:
        return "N/A"


def pct_growth(new, old):
    try:
        if old and old != 0:
            return round((new - old) / abs(old) * 100, 2)
        return "N/A"
    except:
        return "N/A"


def get_fundamentals(stock, info: dict) -> dict:
    try:
        fin  = stock.financials    # income statement (annual)
        cf   = stock.cashflow      # cash flow
        bs   = stock.balance_sheet # balance sheet

        def row(df, *keys):
            for k in keys:
                try:
                    r = df.loc[k]
                    return r.dropna()
                except:
                    pass
            return pd.Series(dtype=float)

        # Revenue
        rev = row(fin, "Total Revenue", "Revenue")
        rev_latest = safe_cr(rev.iloc[0])  if len(rev) >= 1 else "N/A"
        rev_prev   = safe_cr(rev.iloc[1])  if len(rev) >= 2 else "N/A"
        rev_growth = pct_growth(rev.iloc[0], rev.iloc[1]) if len(rev) >= 2 else "N/A"
        rev_3yr    = pct_growth(rev.iloc[0], rev.iloc[3]) if len(rev) >= 4 else "N/A"

        # Net Profit / PAT
        pat = row(fin, "Net Income", "Net Income Common Stockholders")
        pat_latest = safe_cr(pat.iloc[0]) if len(pat) >= 1 else "N/A"
        pat_prev   = safe_cr(pat.iloc[1]) if len(pat) >= 2 else "N/A"
        pat_growth = pct_growth(pat.iloc[0], pat.iloc[1]) if len(pat) >= 2 else "N/A"

        # EBITDA
        ebitda = row(fin, "EBITDA", "Normalized EBITDA")
        ebitda_latest = safe_cr(ebitda.iloc[0]) if len(ebitda) >= 1 else "N/A"

        # Gross / Operating / Net Margins
        gross_margin = round(info.get("grossMargins", 0) * 100, 2) if info.get("grossMargins") else "N/A"
        op_margin    = round(info.get("operatingMargins", 0) * 100, 2) if info.get("operatingMargins") else "N/A"
        net_margin   = round(info.get("profitMargins", 0) * 100, 2) if info.get("profitMargins") else "N/A"

        # ROE / ROA / ROCE
        roe  = round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else "N/A"
        roa  = round(info.get("returnOnAssets", 0) * 100, 2) if info.get("returnOnAssets") else "N/A"

        # EPS
        eps_ttm   = info.get("trailingEps", "N/A")
        eps_fwd   = info.get("forwardEps", "N/A")
        eps_growth = pct_growth(eps_fwd, eps_ttm) if eps_ttm and eps_fwd and eps_ttm != "N/A" else "N/A"

        # Free Cash Flow
        ocf = row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = row(cf, "Capital Expenditure", "Purchase Of Property Plant Equipment")
        fcf = "N/A"
        if len(ocf) >= 1 and len(capex) >= 1:
            try:
                fcf = safe_cr(float(ocf.iloc[0]) + float(capex.iloc[0]))
            except:
                fcf = "N/A"

        # Revenue CAGR (if 4 years available)
        rev_cagr = "N/A"
        if len(rev) >= 4:
            try:
                rev_cagr = round(((float(rev.iloc[0]) / float(rev.iloc[3])) ** (1/3) - 1) * 100, 2)
            except:
                pass

        return {
            "revenue_latest_cr":   rev_latest,
            "revenue_prev_cr":     rev_prev,
            "revenue_growth_yoy":  rev_growth,
            "revenue_cagr_3yr":    rev_cagr,
            "pat_latest_cr":       pat_latest,
            "pat_prev_cr":         pat_prev,
            "pat_growth_yoy":      pat_growth,
            "ebitda_latest_cr":    ebitda_latest,
            "gross_margin_pct":    gross_margin,
            "operating_margin_pct": op_margin,
            "net_margin_pct":      net_margin,
            "roe_pct":             roe,
            "roa_pct":             roa,
            "eps_ttm":             eps_ttm,
            "eps_forward":         eps_fwd,
            "eps_growth_pct":      eps_growth,
            "free_cash_flow_cr":   fcf,
        }
    except Exception as e:
        return {"error": str(e)}
