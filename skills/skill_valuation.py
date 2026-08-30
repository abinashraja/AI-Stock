"""
SKILL: Valuation Analysis
P/E, P/B, EV/EBITDA, PEG, fair value estimate.
Source: yfinance info
"""
import math


def get_valuation(info: dict, tech: dict, fundamentals: dict) -> dict:
    try:
        curr_price = tech.get("current_price", "N/A")
        if curr_price == "N/A":
            return {"error": "No current price"}
        curr_price = float(curr_price)

        # P/E
        pe_ttm     = info.get("trailingPE")
        pe_fwd     = info.get("forwardPE")
        pb         = info.get("priceToBook")
        peg        = info.get("pegRatio")
        ev_ebitda  = info.get("enterpriseToEbitda")
        ps_ratio   = info.get("priceToSalesTrailing12Months")
        book_val   = info.get("bookValue")

        # Safe round
        def sr(v, d=2):
            try: return round(float(v), d)
            except: return "N/A"

        pe_ttm    = sr(pe_ttm)
        pe_fwd    = sr(pe_fwd)
        pb        = sr(pb)
        peg       = sr(peg)
        ev_ebitda = sr(ev_ebitda)
        ps_ratio  = sr(ps_ratio)
        book_val  = sr(book_val)

        # P/E valuation signal
        pe_signal = "N/A"
        if pe_ttm != "N/A":
            if pe_ttm < 15:   pe_signal = "CHEAP"
            elif pe_ttm < 25: pe_signal = "FAIR"
            elif pe_ttm < 40: pe_signal = "EXPENSIVE"
            else:             pe_signal = "VERY EXPENSIVE"

        # PEG signal
        peg_signal = "N/A"
        if peg != "N/A":
            if peg < 0:   peg_signal = "NEGATIVE (loss-making growth concern)"
            elif peg < 1: peg_signal = "UNDERVALUED (growth at discount)"
            elif peg < 2: peg_signal = "FAIRLY VALUED"
            else:         peg_signal = "OVERVALUED for growth rate"

        # Graham Number (rough intrinsic value estimate)
        eps_ttm  = info.get("trailingEps")
        graham_val = "N/A"
        if eps_ttm and book_val and eps_ttm != "N/A" and book_val != "N/A":
            try:
                gv = math.sqrt(22.5 * float(eps_ttm) * float(book_val))
                graham_val = round(gv, 2)
            except:
                pass

        margin_of_safety = "N/A"
        if graham_val != "N/A":
            mos = (graham_val - curr_price) / graham_val * 100
            margin_of_safety = round(mos, 1)

        # DCF simplified (using analyst target)
        analyst_target = info.get("targetMeanPrice")
        analyst_upside  = "N/A"
        if analyst_target:
            analyst_upside = round((float(analyst_target) - curr_price) / curr_price * 100, 1)

        return {
            "pe_ttm":             pe_ttm,
            "pe_forward":         pe_fwd,
            "pe_signal":          pe_signal,
            "pb_ratio":           pb,
            "ps_ratio":           ps_ratio,
            "peg_ratio":          peg,
            "peg_signal":         peg_signal,
            "ev_ebitda":          ev_ebitda,
            "book_value":         book_val,
            "graham_number":      graham_val,
            "margin_of_safety_pct": margin_of_safety,
            "analyst_target":     sr(analyst_target),
            "analyst_upside_pct": analyst_upside,
            "analyst_count":      info.get("numberOfAnalystOpinions", "N/A"),
            "analyst_recommendation": info.get("recommendationKey", "N/A").upper() if info.get("recommendationKey") else "N/A",
        }
    except Exception as e:
        return {"error": str(e)}
