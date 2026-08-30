"""
SKILL: Balance Sheet Analysis
Debt, D/E, interest coverage, working capital, cash.
Source: yfinance
"""
import pandas as pd
import numpy as np


def safe_cr(val):
    try:
        v = float(val)
        return round(v / 1e7, 2) if abs(v) > 1e6 else round(v, 2)
    except:
        return "N/A"


def get_balance_sheet(stock, info: dict) -> dict:
    try:
        bs  = stock.balance_sheet
        fin = stock.financials

        def row(df, *keys):
            for k in keys:
                try:
                    r = df.loc[k]
                    return r.dropna()
                except:
                    pass
            return pd.Series(dtype=float)

        # Debt
        total_debt = row(bs, "Total Debt", "Long Term Debt")
        short_debt  = row(bs, "Current Debt", "Short Term Debt", "Short Long Term Debt")
        total_debt_val = safe_cr(total_debt.iloc[0]) if len(total_debt) >= 1 else "N/A"
        short_debt_val = safe_cr(short_debt.iloc[0]) if len(short_debt) >= 1 else "N/A"

        # Equity
        equity = row(bs, "Stockholders Equity", "Total Stockholder Equity")
        equity_val = safe_cr(equity.iloc[0]) if len(equity) >= 1 else "N/A"

        # D/E Ratio — use info if available, else calculate
        de_ratio = "N/A"
        raw_de = info.get("debtToEquity")
        if raw_de:
            de_ratio = round(float(raw_de) / 100, 2)  # yfinance gives 156 meaning 1.56x
        elif equity_val != "N/A" and total_debt_val != "N/A" and equity_val != 0:
            try:
                de_ratio = round(float(total_debt_val) / float(equity_val), 2)
            except:
                de_ratio = "N/A"

        de_risk = "LOW" if de_ratio != "N/A" and de_ratio < 0.5 else \
                  "MODERATE" if de_ratio != "N/A" and de_ratio < 1.0 else \
                  "HIGH" if de_ratio != "N/A" and de_ratio < 2.0 else \
                  "VERY HIGH" if de_ratio != "N/A" else "N/A"

        # Cash & Cash Equivalents
        cash = row(bs, "Cash And Cash Equivalents", "Cash", "Cash And Short Term Investments")
        cash_val = safe_cr(cash.iloc[0]) if len(cash) >= 1 else "N/A"

        # Current Ratio
        curr_assets = row(bs, "Current Assets", "Total Current Assets")
        curr_liab   = row(bs, "Current Liabilities", "Total Current Liabilities")
        current_ratio = "N/A"
        if len(curr_assets) >= 1 and len(curr_liab) >= 1:
            try:
                current_ratio = round(float(curr_assets.iloc[0]) / float(curr_liab.iloc[0]), 2)
            except:
                pass

        # Interest Coverage
        ebit = row(fin, "EBIT", "Operating Income")
        interest = row(fin, "Interest Expense")
        interest_coverage = "N/A"
        if len(ebit) >= 1 and len(interest) >= 1:
            try:
                ic = float(ebit.iloc[0]) / abs(float(interest.iloc[0]))
                interest_coverage = round(ic, 2)
            except:
                pass

        ic_risk = "N/A"
        if interest_coverage != "N/A":
            ic_risk = "STRONG (>3x)" if interest_coverage > 3 else \
                      "ADEQUATE (1.5-3x)" if interest_coverage > 1.5 else \
                      "WEAK (<1.5x — distress risk)"

        return {
            "total_debt_cr":      total_debt_val,
            "short_term_debt_cr": short_debt_val,
            "equity_cr":          equity_val,
            "debt_to_equity":     de_ratio,
            "de_risk":            de_risk,
            "cash_cr":            cash_val,
            "current_ratio":      current_ratio,
            "interest_coverage":  interest_coverage,
            "interest_coverage_risk": ic_risk,
        }
    except Exception as e:
        return {"error": str(e)}
