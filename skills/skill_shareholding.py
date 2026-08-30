"""
SKILL: Shareholding Pattern
Promoter %, FII %, DII %, institutional trend.
Source: yfinance
"""
import pandas as pd


def get_shareholding(stock, info: dict) -> dict:
    try:
        # Major holders: [% insider, % institutions]
        major = stock.major_holders
        pct_insider = "N/A"
        pct_inst    = "N/A"
        if major is not None and not major.empty:
            try:
                vals = major.iloc[:, 0].values
                pct_insider = round(float(str(vals[0]).replace("%", "").strip()), 2)
                pct_inst    = round(float(str(vals[1]).replace("%", "").strip()), 2)
            except:
                pass

        # Institutional holders detail
        inst = stock.institutional_holders
        top_inst = []
        if inst is not None and not inst.empty:
            for _, row in inst.head(5).iterrows():
                try:
                    name   = str(row.get("Holder", row.get("Name", "Unknown")))
                    shares = row.get("Shares", 0)
                    pct    = row.get("% Out", row.get("pctHeld", 0))
                    top_inst.append({
                        "name":   name,
                        "shares": int(shares) if shares else 0,
                        "pct":    round(float(pct) * 100, 2) if pct and float(pct) < 1 else round(float(pct), 2)
                    })
                except:
                    continue

        # Mutual fund holders (DII proxy)
        mf = stock.mutualfund_holders
        top_mf = []
        if mf is not None and not mf.empty:
            for _, row in mf.head(5).iterrows():
                try:
                    name   = str(row.get("Holder", row.get("Name", "Unknown")))
                    pct    = row.get("% Out", row.get("pctHeld", 0))
                    top_mf.append({
                        "name": name,
                        "pct":  round(float(pct) * 100, 2) if pct and float(pct) < 1 else round(float(pct), 2)
                    })
                except:
                    continue

        promoter_pct = pct_insider  # insider ≈ promoter for Indian stocks via yfinance
        fii_dii_pct  = pct_inst

        # Risk signals
        pledging_risk = "N/A"  # yfinance doesn't provide pledge data freely
        holding_signal = "N/A"
        if promoter_pct != "N/A":
            if promoter_pct > 60:
                holding_signal = "HIGH PROMOTER HOLDING (positive — skin in game)"
            elif promoter_pct > 40:
                holding_signal = "MODERATE PROMOTER HOLDING"
            else:
                holding_signal = "LOW PROMOTER HOLDING (concern)"

        return {
            "promoter_holding_pct":  promoter_pct,
            "institutional_pct":     fii_dii_pct,
            "holding_signal":        holding_signal,
            "top_institutional":     top_inst,
            "top_mutual_funds":      top_mf,
            "pledging_data":         "Not available via free source (check NSE/BSE)",
        }
    except Exception as e:
        return {"error": str(e)}
