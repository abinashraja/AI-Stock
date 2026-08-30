"""
SKILL: F&O Analysis
Fetches OI, PCR, max pain from NSE public API (free).
Source: NSE India public API
"""
import requests
import json


NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def get_fno_data(symbol: str) -> dict:
    """symbol = stock symbol without .NS, e.g. TATAMOTORS"""
    # Strip .NS / .BO suffix
    clean = symbol.upper().replace(".NS", "").replace(".BO", "")

    try:
        session = requests.Session()
        # First visit NSE to get cookies
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=8)

        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={clean}"
        resp = session.get(url, headers=NSE_HEADERS, timeout=10)

        if resp.status_code != 200:
            return {"available": False, "reason": f"NSE returned {resp.status_code}"}

        data = resp.json()
        records = data.get("records", {})
        oc_data = records.get("data", [])

        if not oc_data:
            return {"available": False, "reason": "No OC data"}

        # Sum up OI across all strikes
        total_ce_oi = 0
        total_pe_oi = 0
        max_pain_data = {}  # strike -> total OI pain

        for row in oc_data:
            ce = row.get("CE", {})
            pe = row.get("PE", {})
            strike = row.get("strikePrice", 0)
            ce_oi = ce.get("openInterest", 0) or 0
            pe_oi = pe.get("openInterest", 0) or 0
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi

        # PCR
        pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi else "N/A"
        pcr_signal = "N/A"
        if pcr != "N/A":
            if pcr > 1.5:  pcr_signal = "VERY BULLISH (heavy put writing)"
            elif pcr > 1:  pcr_signal = "BULLISH"
            elif pcr > 0.7: pcr_signal = "NEUTRAL"
            else:          pcr_signal = "BEARISH (heavy call writing)"

        # Expiry
        expiry_dates = records.get("expiryDates", [])
        curr_expiry  = expiry_dates[0] if expiry_dates else "N/A"

        # Underlying price
        underlying = records.get("underlyingValue", "N/A")

        return {
            "available":        True,
            "symbol":           clean,
            "underlying_price": underlying,
            "expiry":           curr_expiry,
            "total_ce_oi":      total_ce_oi,
            "total_pe_oi":      total_pe_oi,
            "pcr":              pcr,
            "pcr_signal":       pcr_signal,
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}
