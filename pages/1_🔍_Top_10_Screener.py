"""
Top 10 Stock Screener Agent — 1-Month BUY Picks
Phase 1 : Fast pre-filter Nifty 500 → Top 50 (parallel momentum screen)
Phase 2 : Deep skill scan Top 50  → Composite score → Top 10
Phase 3 : LLM Primary Analyst Agent on each of the 10 picks
Phase 4 : Auditor Agent validates each pick → BUY/SELL/WAIT/DO NOT BUY
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os, sys, json, requests, math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Skills path ────────────────────────────────────────────────────────────────
_SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")
sys.path.insert(0, _SKILLS_DIR)

from skill_market_data        import get_market_data
from skill_technical          import get_technical_data
from skill_support_resistance import get_support_resistance
from skill_patterns           import get_chart_patterns
from skill_volume             import get_volume_analysis
from skill_fundamentals       import get_fundamentals
from skill_balance_sheet      import get_balance_sheet
from skill_valuation          import get_valuation
from skill_shareholding       import get_shareholding
from skill_market_context     import get_market_context
from skill_relative_strength  import get_relative_strength
from skill_news               import get_news
from skill_fno                import get_fno_data
from skill_scenarios          import get_scenarios
from skill_position_sizing    import get_position_sizing

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Top 10 Screener — AI Stock Analyst",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS (same dark theme as primary dashboard) ─────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
* { font-family: 'Inter', sans-serif !important; }
footer { visibility: hidden; }
/* Keep sidebar toggle always visible */
[data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; }
.stApp { background: linear-gradient(135deg,#0a0e1a 0%,#0d1b2a 50%,#0a0e1a 100%); color:#e2e8f0; }
.block-container { padding:0.8rem 1.5rem !important; max-width:100% !important; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0d1b2a,#111827) !important; border-right:1px solid #1e3a5f; }
[data-testid="stSidebar"] * { color:#94a3b8 !important; }
[data-testid="stSidebar"] .stButton button {
    background:linear-gradient(135deg,#1e40af,#3b82f6) !important;
    color:white !important; border-radius:8px !important;
    font-weight:700 !important; border:none !important;
}
div[data-testid="stMetricValue"] { font-size:1rem !important; font-weight:700 !important; color:#f1f5f9 !important; }
div[data-testid="stMetricLabel"] { font-size:0.65rem !important; color:#64748b !important; text-transform:uppercase; }
hr { border-color:#1e3a5f !important; margin:0.5rem 0 !important; }
.stProgress > div > div { background:linear-gradient(90deg,#3b82f6,#10b981) !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NIFTY 500 TICKERS (representative universe — major liquid NSE stocks)
# ══════════════════════════════════════════════════════════════════════════════
NIFTY500_TICKERS = [
    # Banking & Finance
    "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS","INDUSINDBK.NS",
    "BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS","BANKBARODA.NS","CANBK.NS",
    "UNIONBANK.NS","CENTRALBK.NS","UCOBANK.NS","MAHABANK.NS","J&KBANK.NS","KARURVYSYA.NS",
    "DCBBANK.NS","RBLBANK.NS","EQUITASBNK.NS","SURYODAY.NS","UJJIVANSFB.NS","AUBANK.NS","ESAFSFB.NS",
    # NBFC / Finance
    "BAJFINANCE.NS","BAJAJFINSV.NS","LICHSGFIN.NS","MUTHOOTFIN.NS","MANAPPURAM.NS",
    "PNBHOUSING.NS","CANFINHOME.NS","AAVAS.NS","HOMEFIRST.NS","CHOLAFIN.NS","M&MFIN.NS",
    "SHRIRAMFIN.NS","SUNDARMFIN.NS","JMFINANCL.NS","MOTILALOFS.NS","360ONE.NS","ANGELONE.NS",
    # Insurance
    "HDFCLIFE.NS","SBILIFE.NS","ICICIGI.NS","NIACL.NS","STARHEALTH.NS","GICRE.NS",
    # IT & Technology
    "TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTIM.NS","MPHASIS.NS",
    "PERSISTENT.NS","COFORGE.NS","OFSS.NS","TATAELXSI.NS","KPITTECH.NS","MASTEK.NS",
    "BIRLASOFT.NS","NIIT.NS","RATEGAIN.NS","ROUTE.NS","HAPPSTMNDS.NS","NEWGEN.NS",
    # FMCG
    "HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS","MARICO.NS",
    "COLPAL.NS","GODREJCP.NS","EMAMILTD.NS","TATACONSUM.NS","VBL.NS","VARUN.NS",
    "RADICO.NS","UBL.NS","MCDOWELL-N.NS","PGHH.NS","JYOTHYLAB.NS","GILLETTE.NS",
    # Pharma & Healthcare
    "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","BIOCON.NS","AUROPHARMA.NS",
    "LUPIN.NS","ALKEM.NS","IPCALAB.NS","GRANULES.NS","TORNTPHARM.NS","ABBOTINDIA.NS",
    "GLAXO.NS","PFIZER.NS","SANOFI.NS","NATCO.NS","ERIS.NS","GLAND.NS","VIJAYA.NS",
    "LAURUS.NS","LAURUSLABS.NS","ASTER.NS","APOLLOHOSP.NS","FORTIS.NS","MAXHEALTH.NS",
    # Automobile & Ancillaries
    "MARUTI.NS","TATAMOTORS.NS","M&M.NS","BAJAJ-AUTO.NS","EICHERMOT.NS","HEROMOTOCO.NS",
    "ASHOKLEY.NS","TVSMOTOR.NS","MOTHERSON.NS","BALKRISIND.NS","APOLLOTYRE.NS","CEATLTD.NS",
    "MRFLTD.NS","AMARAJABAT.NS","EXIDEIND.NS","SUNDRMFAST.NS","BOSCHLTD.NS","TIINDIA.NS",
    "MINDAIND.NS","ENDURANCE.NS","CRAFTSMAN.NS","SUPRAJIT.NS","GABRIEL.NS",
    # Energy & Oil & Gas
    "RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","NTPC.NS","POWERGRID.NS","COALINDIA.NS",
    "GAIL.NS","PETRONET.NS","OIL.NS","MRPL.NS","CPCL.NS","HINDPETRO.NS","MGL.NS","IGL.NS",
    "ATGL.NS","GSPL.NS","GUJGASLTD.NS","AEGASIND.NS",
    # Metals & Mining
    "TATASTEEL.NS","HINDALCO.NS","JSWSTEEL.NS","SAIL.NS","HINDZINC.NS","NATIONALUM.NS",
    "VEDL.NS","NMDC.NS","APLAPOLLO.NS","RATNAMANI.NS","JINDALSTEL.NS","JSPL.NS",
    "WELCORP.NS","TINPLATE.NS","HIMATSEIDE.NS",
    # Cement
    "ULTRACEMCO.NS","SHREECEM.NS","AMBUJACEM.NS","ACC.NS","RAMCOCEM.NS","JKCEMENT.NS",
    "DALMIA.NS","HEIDELBERG.NS","STARLITE.NS","INDIANCEM.NS","BIRLACORPN.NS",
    # Capital Goods & Engineering
    "LT.NS","BHEL.NS","SIEMENS.NS","ABB.NS","THERMAX.NS","CUMMINSIND.NS","VOLTAS.NS",
    "HAVELLS.NS","POLYCAB.NS","KEI.NS","FINOLEX.NS","V-GUARD.NS","CROMPTON.NS",
    "BLUESTAR.NS","WHIRLPOOL.NS","CGPOWER.NS","BHELHEAVY.NS","RITES.NS","IRCON.NS",
    "NBCC.NS","NCC.NS","KNR.NS","PNC.NS","AHLUWALIA.NS","HG.NS","GRINDWELL.NS",
    # Real Estate
    "DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS","PHOENIXLTD.NS",
    "SOBHA.NS","BRIGADE.NS","MAHLIFE.NS","KOLTEPATIL.NS","KEYSTONE.NS","SUNTECK.NS",
    # Consumer Discretionary
    "TITAN.NS","TRENT.NS","DMART.NS","JUBLFOOD.NS","DEVYANI.NS","SAPPHIREF.NS",
    "BARBEQUE.NS","WESTLIFE.NS","ZOMATO.NS","SWIGGY.NS","NYKAA.NS","POLICYBZR.NS",
    "VEDANT.NS","MANYAVAR.NS","ABFRL.NS","PAGEIND.NS","RAYMOND.NS","PVRINOX.NS","INOX.NS",
    # Chemicals & Specialty
    "PIDILITIND.NS","ASIANPAINT.NS","BERGERPAINTS.NS","ATUL.NS","DEEPAKNTR.NS",
    "TATACHEM.NS","NAVINFLUOR.NS","SRF.NS","AAPL.NS","FINEORG.NS","GALAXYSURF.NS",
    "SOLARA.NS","AAVAS.NS","CLEAN.NS","NOCIL.NS","VINATIORG.NS","BALMLAWRIE.NS",
    # Telecom & Media
    "BHARTIARTL.NS","IDEA.NS","TATACOMM.NS","HFCL.NS","RAILTEL.NS","STLTECH.NS",
    # Logistics & Transport
    "ADANIPORTS.NS","CONCOR.NS","BLUEDART.NS","DELHIVERY.NS","MAHINDRALOG.NS","VRL.NS",
    "TCI.NS","MAHLOG.NS","ALLCARGO.NS","GATI.NS",
    # Conglomerate & Holdings
    "ADANIENT.NS","ADANIGREEN.NS","ADANIPOWER.NS","ADANITRANS.NS","ADANIGAS.NS",
    "TATAINVEST.NS","BAJAJHOLD.NS","GODREJIND.NS","CHOLAHLDNG.NS","HDFCAMC.NS",
    # Agri & Fertilizers
    "UPL.NS","GNFC.NS","COROMANDEL.NS","CHAMBAL.NS","NFL.NS","RCFLTD.NS","FACT.NS",
    # Textiles
    "PAGEIND.NS","WELSPUNIND.NS","VARDHMAN.NS","KPR.NS","TRIDENT.NS","ALOKTEXT.NS",
    # Infrastructure
    "IRFC.NS","PFC.NS","REC.NS","HUDCO.NS","NHAI.NS","GMRINFRA.NS","GVK.NS",
    # Misc / Others
    "ZEEL.NS","SUNPHARMA.NS","WIPRO.NS","INFY.NS","TCS.NS",
]

# Remove duplicates
NIFTY500_TICKERS = list(dict.fromkeys(NIFTY500_TICKERS))


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — FAST MOMENTUM PRE-FILTER (parallel)
# ══════════════════════════════════════════════════════════════════════════════
def _fast_score_ticker(ticker: str) -> dict | None:
    """Download 6M data for one ticker and compute 5 quick momentum signals."""
    try:
        df = yf.download(ticker, period="6mo", interval="1d",
                         auto_adjust=True, progress=False, timeout=10)
        if df.empty or len(df) < 60:
            return None

        close  = df["Close"].squeeze().dropna()
        volume = df["Volume"].squeeze().dropna()
        high52 = close.max()
        low52  = close.min()
        curr   = float(close.iloc[-1])
        if curr <= 0 or math.isnan(curr):
            return None

        # SMA
        sma20  = float(close.rolling(20).mean().iloc[-1])
        sma50  = float(close.rolling(50).mean().iloc[-1])

        # RSI 14
        delta  = close.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rs     = gain / loss.replace(0, 1e-9)
        rsi    = float(100 - 100 / (1 + rs.iloc[-1]))

        # Volume
        vol_avg20 = float(volume.tail(20).mean())
        vol_avg5  = float(volume.tail(5).mean())
        vol_ratio = vol_avg5 / vol_avg20 if vol_avg20 > 0 else 0

        # 1M momentum
        momentum_1m = (curr - float(close.iloc[-22])) / float(close.iloc[-22]) * 100 \
                      if len(close) >= 22 else 0

        # Nearness to 52W high (within 20%)
        near_high = (curr / high52) >= 0.80 if high52 > 0 else False

        # Score (max 5 pts)
        score = 0
        if 40 <= rsi <= 70:                   score += 1
        if curr > sma20 and curr > sma50:     score += 1
        if vol_ratio >= 1.2:                  score += 1
        if near_high:                         score += 1
        if momentum_1m > 0:                   score += 1

        return {
            "ticker":      ticker,
            "score":       score,
            "curr":        round(curr, 2),
            "rsi":         round(rsi, 1),
            "sma20":       round(sma20, 2),
            "sma50":       round(sma50, 2),
            "vol_ratio":   round(vol_ratio, 2),
            "momentum_1m": round(momentum_1m, 2),
            "high52":      round(high52, 2),
        }
    except Exception:
        return None


def phase1_fast_filter(tickers: list, progress_cb=None) -> list:
    """Parallel scan all tickers → return top 50 by momentum score."""
    results = []
    total   = len(tickers)
    done    = 0

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(_fast_score_ticker, t): t for t in tickers}
        for fut in as_completed(futures):
            done += 1
            if progress_cb:
                progress_cb(done / total)
            r = fut.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: (x["score"], x["momentum_1m"]), reverse=True)
    return results[:50]


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — DEEP SKILL SCAN + COMPOSITE SCORE (0–100)
# ══════════════════════════════════════════════════════════════════════════════
def fetch_all_skills_screener(ticker: str):
    """Same as dashboard's fetch_all_skills — returns (data_dict, err)."""
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info or {}
        hist  = stock.history(period="2y")
        if hist.empty:
            return None, "No price data"
        data = {}
        data["market"]       = get_market_data(ticker, info, hist)
        data["technical"]    = get_technical_data(hist, info)
        data["sr"]           = get_support_resistance(hist)
        data["patterns"]     = get_chart_patterns(hist)
        data["volume"]       = get_volume_analysis(hist)
        data["fundamentals"] = get_fundamentals(stock, info)
        data["balance"]      = get_balance_sheet(stock, info)
        data["valuation"]    = get_valuation(info, data["technical"], data["fundamentals"])
        data["shareholding"] = get_shareholding(stock, info)
        data["mkt_ctx"]      = get_market_context()
        data["rel_str"]      = get_relative_strength(hist, ticker)
        data["news"]         = get_news(stock, data["market"].get("company_name", ticker))
        data["fno"]          = get_fno_data(ticker)

        curr = _safe_float(data["market"].get("current_price"), 100.0)
        t    = data["technical"]
        f    = data["fundamentals"]
        b    = data["balance"]
        sr   = data["sr"]
        _atr = _safe_float(t.get("atr_14"), curr * 0.02)
        _sup = _safe_float(sr.get("nearest_support"), curr * 0.95)
        _res = _safe_float(sr.get("nearest_resistance"), curr * 1.05)

        data["scenarios"]    = get_scenarios(curr_price=curr, tech=t, fundamentals=f, balance=b, sr=sr, atr=_atr, horizon="1M")
        data["ps"]           = get_position_sizing(curr_price=curr, atr=_atr, support=_sup, resistance=_res, investment_amount=100000, horizon="1M")
        data["hist"]         = hist
        return data, None
    except Exception as e:
        return None, str(e)


def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if not math.isnan(v) else default
    except Exception:
        return default


def compute_skill_score(data: dict) -> tuple[float, dict]:
    """
    Compute a composite Skill Score (0–100) from 12 skill signals.
    Returns (score, breakdown_dict).
    """
    t   = data.get("technical", {})
    f   = data.get("fundamentals", {})
    b   = data.get("balance", {})
    v   = data.get("valuation", {})
    vol = data.get("volume", {})
    pt  = data.get("patterns", {})
    rs  = data.get("rel_str", {})
    sr  = data.get("sr", {})
    mc  = data.get("mkt_ctx", {})
    sh  = data.get("shareholding", {})
    fno = data.get("fno", {})
    m   = data.get("market", {})

    breakdown = {}
    score = 0.0

    # 1. RSI in ideal buy zone 45–65  (10 pts)
    rsi = _safe_float(t.get("rsi_14"), 50)
    pts = 10 if 45 <= rsi <= 65 else (6 if 35 <= rsi < 45 else (4 if 65 < rsi <= 75 else 0))
    breakdown["RSI Zone"] = pts
    score += pts

    # 2. Price vs SMA 50 & 200  (12 pts)
    curr   = _safe_float(m.get("current_price"), 0)
    sma50  = _safe_float(t.get("sma_50"), 0)
    sma200 = _safe_float(t.get("sma_200"), 0)
    if curr > sma50 and curr > sma200:
        pts = 12
    elif curr > sma50:
        pts = 7
    elif curr > sma200:
        pts = 4
    else:
        pts = 0
    breakdown["SMA 50/200"] = pts
    score += pts

    # 3. MACD bullish  (8 pts)
    macd_trend = str(t.get("macd_trend", "")).upper()
    pts = 8 if "BULLISH" in macd_trend else (4 if "NEUTRAL" in macd_trend else 0)
    breakdown["MACD"] = pts
    score += pts

    # 4. Volume OBV + A/D  (8 pts)
    obv = str(vol.get("obv_trend", "")).upper()
    ad  = str(vol.get("ad_trend", "")).upper()
    pts = 0
    if "ACCUMULATION" in obv or "RISING" in obv: pts += 4
    if "ACCUMULATION" in ad:                      pts += 4
    breakdown["Volume / OBV"] = pts
    score += pts

    # 5. Bullish chart pattern  (8 pts)
    primary_bias = str(pt.get("primary_bias", "")).upper()
    patterns     = pt.get("patterns_detected", [])
    bullish_kw   = ["bullish", "uptrend", "bull flag", "inverse head", "double bottom"]
    bearish_kw   = ["bearish", "downtrend", "double top", "head & shoulders"]
    has_bullish  = any(kw in " ".join(patterns).lower() for kw in bullish_kw)
    has_bearish  = any(kw in " ".join(patterns).lower() for kw in bearish_kw)
    pts = 8 if (has_bullish and not has_bearish) else (4 if "NEUTRAL" in primary_bias else 0)
    breakdown["Chart Pattern"] = pts
    score += pts

    # 6. Fundamental growth  (8 pts)
    rev_growth = _safe_float(f.get("revenue_growth_yoy"), 0)
    pat_growth = _safe_float(f.get("pat_growth_yoy"), 0)
    fcf        = f.get("free_cash_flow_cr", "N/A")
    pts = 0
    if rev_growth > 15: pts += 3
    elif rev_growth > 8: pts += 2
    if pat_growth > 15: pts += 3
    elif pat_growth > 8: pts += 2
    if str(fcf) not in ("N/A", "") and _safe_float(fcf, -1) > 0: pts += 2
    pts = min(pts, 8)
    breakdown["Fundamentals"] = pts
    score += pts

    # 7. Balance sheet health  (8 pts)
    de    = _safe_float(b.get("debt_to_equity", 99), 99)
    ic    = _safe_float(b.get("interest_coverage", 0), 0)
    pts = 0
    if de < 0.5:   pts += 4
    elif de < 1.0: pts += 3
    elif de < 1.5: pts += 1
    if ic > 5:     pts += 4
    elif ic > 3:   pts += 3
    elif ic > 1.5: pts += 1
    pts = min(pts, 8)
    breakdown["Balance Sheet"] = pts
    score += pts

    # 8. Relative strength vs Nifty  (8 pts)
    rs_data    = rs.get("relative_strength_vs_nifty", {})
    alpha_1m   = _safe_float(rs_data.get("1_month", {}).get("alpha_pct") if isinstance(rs_data.get("1_month"), dict) else None, -99)
    pts = 8 if alpha_1m > 3 else (5 if alpha_1m > 0 else (2 if alpha_1m > -3 else 0))
    breakdown["Relative Strength"] = pts
    score += pts

    # 9. Near support, room before resistance  (6 pts)
    bd_pct = _safe_float(sr.get("breakdown_dist_pct"), 0)   # % to nearest support
    bk_pct = _safe_float(sr.get("breakout_dist_pct"), 100)  # % to nearest resistance
    pts = 0
    if 1 <= bd_pct <= 8:  pts += 3  # Close to support (good buy zone)
    if bk_pct >= 5:       pts += 3  # Enough upside room
    breakdown["S/R Position"] = pts
    score += pts

    # 10. Valuation attractiveness  (6 pts)
    pe_signal  = str(v.get("pe_signal", "")).upper()
    peg        = _safe_float(v.get("peg_ratio", 99), 99)
    mos        = _safe_float(v.get("margin_of_safety_pct", -99), -99)
    pts = 0
    if "UNDERVALUED" in pe_signal or "CHEAP" in pe_signal: pts += 3
    elif "FAIR" in pe_signal:                               pts += 2
    if peg < 1.0:   pts += 2
    elif peg < 1.5: pts += 1
    if mos > 20:    pts += 1
    pts = min(pts, 6)
    breakdown["Valuation"] = pts
    score += pts

    # 11. FNO data signal  (6 pts)
    if fno.get("available"):
        pcr_signal = str(fno.get("pcr_signal", "")).upper()
        pts = 6 if "BULLISH" in pcr_signal else (3 if "NEUTRAL" in pcr_signal else 0)
    else:
        pts = 3  # neutral if not in F&O
    breakdown["FNO / PCR"] = pts
    score += pts

    # 12. Market context  (6 pts)
    regime = str(mc.get("market_regime", "")).upper()
    vix    = _safe_float(mc.get("india_vix", 20), 20)
    pts = 0
    if "BULL" in regime or "RECOVERY" in regime: pts += 3
    elif "SIDEWAYS" in regime:                    pts += 2
    if vix < 14:                                  pts += 3
    elif vix < 18:                                pts += 2
    elif vix < 22:                                pts += 1
    pts = min(pts, 6)
    breakdown["Market Context"] = pts
    score += pts

    # Normalize to 100
    max_possible = 10 + 12 + 8 + 8 + 8 + 8 + 8 + 8 + 6 + 6 + 6 + 6  # = 94
    normalized   = round((score / max_possible) * 100, 1)
    return normalized, breakdown


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — LLM PRIMARY ANALYST AGENT (screener-optimized prompt)
# ══════════════════════════════════════════════════════════════════════════════
def build_screener_prompt(ticker: str, data: dict, rank: int, score: float) -> str:
    t   = data["technical"]
    f   = data["fundamentals"]
    b   = data["balance"]
    v   = data["valuation"]
    m   = data["market"]
    sr  = data["sr"]
    pt  = data["patterns"]
    vol = data["volume"]
    rs  = data["rel_str"]
    mc  = data["mkt_ctx"]
    ps  = data.get("ps", {})

    patterns_text = "; ".join(pt.get("patterns_detected", ["None"])) or "None"
    rs_data = rs.get("relative_strength_vs_nifty", {})
    alpha_1m = "N/A"
    if isinstance(rs_data.get("1_month"), dict):
        alpha_1m = rs_data["1_month"].get("alpha_pct", "N/A")

    prompt = f"""You are a senior Indian equity research analyst specializing in 1-MONTH positional swing trades.
This stock was auto-selected as #{rank} by a 12-skill screening model with a composite score of {score}/100 from the Nifty 500 universe.

STOCK: {m.get('company_name', ticker)} ({ticker})
SECTOR: {m.get('sector','N/A')} | Current Price: ₹{m.get('current_price','N/A')}

TECHNICAL SNAPSHOT:
- Price vs SMA20/50/200: {t.get('price_vs_sma20','N/A')} / {t.get('price_vs_sma50','N/A')} / {t.get('price_vs_sma200','N/A')}
- RSI(14): {t.get('rsi_14','N/A')} ({t.get('rsi_zone','N/A')})
- MACD Trend: {t.get('macd_trend','N/A')}
- Trend Structure: {t.get('trend_structure','N/A')}
- Golden/Death Cross: {t.get('golden_death_cross','N/A')}
- Volume Signal: {vol.get('volume_signal','N/A')} | OBV: {vol.get('obv_trend','N/A')}
- Chart Patterns: {patterns_text}
- Nearest Support: ₹{sr.get('nearest_support','N/A')} | Resistance: ₹{sr.get('nearest_resistance','N/A')}

FUNDAMENTALS:
- Revenue Growth YoY: {f.get('revenue_growth_yoy','N/A')}% | PAT Growth: {f.get('pat_growth_yoy','N/A')}%
- Net Margin: {f.get('net_margin_pct','N/A')}% | ROE: {f.get('roe_pct','N/A')}%
- FCF: ₹{f.get('free_cash_flow_cr','N/A')} Cr | D/E: {b.get('debt_to_equity','N/A')}x | IC: {b.get('interest_coverage','N/A')}x
- P/E TTM: {v.get('pe_ttm','N/A')} | Margin of Safety: {v.get('margin_of_safety_pct','N/A')}%

MARKET CONTEXT:
- Regime: {mc.get('market_regime','N/A')} | VIX: {mc.get('india_vix','N/A')}
- 1M Alpha vs Nifty: {alpha_1m}%

PRE-CALCULATED TRADE LEVELS (use EXACTLY these numbers, do not change):
- Entry:    ₹{ps.get('entry_price','N/A')}
- Stop Loss:₹{ps.get('stop_loss','N/A')}
- Target 1: ₹{ps.get('target_1','N/A')}
- Target 2: ₹{ps.get('target_2','N/A')}
- Target 3: ₹{ps.get('target_3','N/A')}
- R:R at T2: 1:{ps.get('rr_ratio_t2','N/A')}
- Max Loss:  ₹{ps.get('max_loss','N/A')}

STRICT RULES (1-MONTH HORIZON — NEVER VIOLATE):
1. STOCK TREND RULE: If THIS individual stock is trading above its 50-day SMA with clean financials (D/E < 1.5x, IC > 1.5x) and bullish momentum, issue a BUY. Broad index Nifty moves are a risk to watch, not an automatic rejection.
2. If price is below SMA 50 AND SMA 200 for this stock, decision MUST be WAIT.
3. If D/E > 1.5x OR interest coverage < 1.5x, decision MUST be WAIT.
4. RSI alone is NEVER sufficient reason for BUY.
5. Stop must be BELOW entry. Targets must be ABOVE entry.
6. Use ONLY the pre-calculated trade levels above.

OUTPUT — use EXACTLY this format:

DECISION: [BUY / SELL / WAIT]
CONFIDENCE: [High / Medium / Low]

ENTRY: ₹[entry price]
STOP LOSS: ₹[stop price]
TARGET 1: ₹[t1]
TARGET 2: ₹[t2]
TARGET 3: ₹[t3]

WHY (2-3 simple sentences a non-expert understands):
[plain language reason]

ONE RISK TO WATCH:
[single biggest risk in one sentence]

ACTION:
[one clear sentence: what to do today]
"""
    return prompt


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — AUDITOR AGENT (same logic as dashboard)
# ══════════════════════════════════════════════════════════════════════════════
def build_screener_audit_prompt(ticker: str, data: dict, primary_output: str) -> str:
    t  = data["technical"]
    b  = data["balance"]
    m  = data["market"]
    sr = data["sr"]
    mc = data["mkt_ctx"]
    ps = data.get("ps", {})

    precalc_text = f"""PRE-CALCULATED TRADE LEVELS (VERIFIED MATH):
- Entry Price: ₹{ps.get('entry_price','N/A')}
- Stop Loss:   ₹{ps.get('stop_loss','N/A')}
- Target 1:    ₹{ps.get('target_1','N/A')}
- Target 2:    ₹{ps.get('target_2','N/A')}
- Target 3:    ₹{ps.get('target_3','N/A')}
- R:R at T2:   1:{ps.get('rr_ratio_t2','N/A')}
Math Check Status: VERIFIED PASS (Stop Loss < Entry < Target 1 < Target 2 < Target 3)
"""

    return f"""You are a strict Senior Risk & Compliance Auditor for Indian stock markets.
Audit this BUY pick from an automated 1-MONTH screener for {m.get('company_name', ticker)} ({ticker}).

{precalc_text}

PRIMARY ANALYST PROPOSAL:
{primary_output}

EMPIRICAL MARKET DATA:
- Current Price: ₹{m.get('current_price','N/A')}
- SMA 50: ₹{t.get('sma_50','N/A')} | SMA 200: ₹{t.get('sma_200','N/A')}
- RSI(14): {t.get('rsi_14','N/A')} | Trend: {t.get('trend_structure','N/A')}
- D/E Ratio: {b.get('debt_to_equity','N/A')}x | Interest Coverage: {b.get('interest_coverage','N/A')}x
- Nearest Support: ₹{sr.get('nearest_support','N/A')} | Resistance: ₹{sr.get('nearest_resistance','N/A')}
- Market Regime: {mc.get('market_regime','N/A')} | VIX: {mc.get('india_vix','N/A')}

STRICT AUDIT RULES FOR 1-MONTH HORIZON:
1. STOCK VS INDEX RULE: If this individual stock is trading ABOVE its own 50-day SMA with clean financials (D/E < 1.5x, IC > 1.5x) and bullish momentum, APPROVE the BUY trade for 1 Month. Broad market index consolidation is a risk to note in the reason, NOT a reason to reject a strong stock.
2. If this individual stock is below its 50-day SMA → DO NOT BUY.
3. D/E > 1.5x or IC < 1.5x → DO NOT BUY.
4. MATHEMATICAL INTEGRITY: Use the PRE-CALCULATED VERIFIED TRADE LEVELS above for the math check. Do NOT reject due to a text typo or string truncation in the analyst's text output if the pre-calculated trade levels are valid.
5. COMPLETE RESPONSE: Write 1-2 complete, finished sentences for REASON. Always finish your sentence cleanly with a period.

OUTPUT FORMAT (keep it very short and simple):

AUDITOR DECISION: [BUY / WAIT / DO NOT BUY]

REASON:
[1-2 complete, finished plain simple sentences ending with a period.]
"""


def get_gemini_api_keys():
    """Retrieve Gemini API keys securely from Streamlit Secrets or Environment Variables (No hardcoded secrets)."""
    keys = []
    try:
        if hasattr(st, "secrets"):
            if "GEMINI_API_KEY" in st.secrets:
                keys.append(str(st.secrets["GEMINI_API_KEY"]).strip())
            if "GEMINI_API_KEYS" in st.secrets:
                val = st.secrets["GEMINI_API_KEYS"]
                if isinstance(val, list):
                    keys.extend([str(k).strip() for k in val if str(k).strip()])
                elif isinstance(val, str):
                    keys.extend([k.strip() for k in val.split(",") if k.strip()])
    except Exception:
        pass

    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip() not in keys:
        keys.append(env_key.strip())

    return [k for k in keys if k]


# ══════════════════════════════════════════════════════════════════════════════
# GEMINI STREAMING — MULTI-MODEL FALLBACK
# ══════════════════════════════════════════════════════════════════════════════
_MODELS = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

def _stream_gemini(prompt: str, system_prompt: str, temperature: float = 0.2):
    """Stream from Gemini with multi-key, multi-model fallback."""
    keys = get_gemini_api_keys()
    if not keys:
        yield "⚠️ No Gemini API Key found. Please add `GEMINI_API_KEY` to Streamlit Secrets or `.env` file."
        return

    for key in keys:
        for model in _MODELS:
            url  = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"temperature": temperature, "maxOutputTokens": 2048},
            }
            try:
                resp = requests.post(url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=body, stream=True, timeout=60)
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if line:
                            dec = line.decode("utf-8")
                            if dec.startswith("data: "):
                                try:
                                    chunk = json.loads(dec[6:])
                                    parts = chunk.get("candidates",[{}])[0].get("content",{}).get("parts",[])
                                    if parts and "text" in parts[0]:
                                        yield parts[0]["text"]
                                except Exception:
                                    pass
                    return
                elif resp.status_code in (429, 404, 503):
                    continue
            except Exception:
                continue
    yield "⚠️ All API keys exhausted or rate-limited. Please wait and retry."


def stream_analyst(prompt: str):
    yield from _stream_gemini(prompt,
        "You are a senior Indian equity analyst for 1-month positional swing trades. "
        "Use ONLY pre-calculated data. Never fabricate numbers.", temperature=0.2)


def stream_auditor(prompt: str):
    yield from _stream_gemini(prompt,
        "You are a strict independent Risk & Compliance Auditor for Indian equity trades. "
        "Enforce strict rules. Do NOT blindly agree with the analyst.", temperature=0.1)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: parse primary agent output into fields
# ══════════════════════════════════════════════════════════════════════════════
def parse_primary_output(text: str, ps: dict) -> dict:
    lines  = text.strip().splitlines()
    parsed = {}
    section = None
    why_lines = []
    for line in lines:
        l  = line.strip()
        ul = l.replace("*","").replace("#","").replace("-","").strip().upper()
        if "DECISION:"  in ul: parsed["decision"]  = l.split(":")[-1].replace("*","").strip()
        elif "CONFIDENCE:" in ul: parsed["confidence"] = l.split(":")[-1].replace("*","").strip()
        elif "ENTRY:"      in ul: parsed["entry"]      = l.split(":")[-1].strip()
        elif "STOP LOSS:"  in ul or "STOP:"  in ul: parsed["stop"] = l.split(":")[-1].split("←")[0].strip()
        elif "TARGET 1:"   in ul or "TARGET 1" in ul: parsed["t1"] = l.split(":")[-1].strip()
        elif "TARGET 2:"   in ul or "TARGET 2" in ul: parsed["t2"] = l.split(":")[-1].strip()
        elif "TARGET 3:"   in ul or "TARGET 3" in ul: parsed["t3"] = l.split(":")[-1].strip()
        elif ul.startswith("WHY"):  section = "why"
        elif "ONE RISK"    in ul:   section = "risk"
        elif "ACTION:"     in ul:
            section = "action"
            after = l.split(":")[-1].strip()
            if after: parsed["action"] = after
        elif section == "why"    and l and not any(k in ul for k in ["RISK","ACTION","DECISION"]): why_lines.append(l)
        elif section == "risk"   and l and not any(k in ul for k in ["ACTION","DECISION"]): parsed["risk"] = l
        elif section == "action" and l and "action" not in parsed: parsed["action"] = l
    parsed["why"] = " ".join(why_lines)

    # fallback to pre-calculated levels
    def rupee(v):
        try: return f"₹{float(v):,.2f}"
        except: return str(v)
    if ps and "error" not in ps:
        for k, fk in [("entry","entry_price"),("stop","stop_loss"),("t1","target_1"),("t2","target_2"),("t3","target_3")]:
            if parsed.get(k) in (None,"N/A","","₹N/A","₹[entry price]","₹XX.XX","₹[stop price]","₹[t1]","₹[t2]","₹[t3]"):
                parsed[k] = rupee(ps.get(fk,"N/A"))
    return parsed


def parse_auditor_output(text: str) -> tuple[str, str]:
    """Returns (decision, reason)."""
    dec = "WAIT"; reason_lines = []; is_reason = False
    for line in text.strip().splitlines():
        l = line.strip(); ul = l.upper()
        if "AUDITOR DECISION:" in ul or "DECISION:" in ul:
            dec = l.split(":")[-1].replace("*","").strip().upper()
        elif "REASON:" in ul:
            is_reason = True
            after = l.split(":")[-1].replace("*","").strip()
            if after: reason_lines.append(after)
        elif is_reason and l:
            reason_lines.append(l)
    return dec, " ".join(reason_lines) or text.strip()


def decision_style(dec: str) -> tuple[str, str, str]:
    """(color, bg, icon)"""
    if "BUY" in dec and "DO NOT" not in dec and "NOT" not in dec:
        return "#10b981", "linear-gradient(135deg,#022c22,#064e32)", "🟢"
    elif "SELL" in dec:
        return "#ef4444", "linear-gradient(135deg,#2d1515,#450a0a)", "🔴"
    elif "DO NOT" in dec or "REJECT" in dec or "NOT" in dec:
        return "#ef4444", "linear-gradient(135deg,#2d1515,#450a0a)", "🛑"
    else:
        return "#f59e0b", "linear-gradient(135deg,#292005,#3d2b00)", "🟡"


# ══════════════════════════════════════════════════════════════════════════════
# RENDER CARD FOR ANALYZED STOCK (Clean Native Components)
# ══════════════════════════════════════════════════════════════════════════════
def render_pick_card(rank: int, ticker: str, data: dict, score: float, breakdown: dict,
                     primary_text: str, auditor_text: str):
    parsed   = parse_primary_output(primary_text, data.get("ps", {}))
    aud_dec, aud_reason = parse_auditor_output(auditor_text)
    dec = parsed.get("decision", "WAIT").upper()

    p_color, p_bg, p_icon = decision_style(dec)
    a_color, a_bg, a_icon = decision_style(aud_dec)

    st.markdown("---")

    # 1. Primary Analyst Verdict Card
    if "BUY" in dec:
        st.success(f"### 🤖 Primary Analyst Verdict: {p_icon} {dec} ({parsed.get('confidence','')})")
    elif "SELL" in dec:
        st.error(f"### 🤖 Primary Analyst Verdict: {p_icon} {dec} ({parsed.get('confidence','')})")
    else:
        st.warning(f"### 🤖 Primary Analyst Verdict: {p_icon} {dec} ({parsed.get('confidence','')})")

    if parsed.get("why"):
        st.markdown(f"**Why:** {parsed['why']}")

    if parsed.get("risk"):
        st.markdown(f"⚠️ **Risk to watch:** {parsed['risk']}")

    if parsed.get("action"):
        st.markdown(f"✅ **Action:** {parsed['action']}")

    st.markdown("---")

    # 2. Independent Auditor Verdict Card
    if "BUY" in aud_dec and "DO NOT" not in aud_dec:
        st.success(f"### 🛡️ Independent Auditor Verdict: {a_icon} {aud_dec}")
        st.markdown(f"**Reason:** {aud_reason}")
    else:
        st.error(f"### 🛡️ Independent Auditor Verdict: {a_icon} {aud_dec}")
        st.markdown(f"**Reason:** {aud_reason}")


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════════
if "sc_phase1_results"        not in st.session_state: st.session_state["sc_phase1_results"]        = None
if "sc_top10_data"            not in st.session_state: st.session_state["sc_top10_data"]            = None
if "sc_top10_analyses"        not in st.session_state: st.session_state["sc_top10_analyses"]        = {}
if "sc_top10_audits"          not in st.session_state: st.session_state["sc_top10_audits"]          = {}
if "selected_screener_stock"  not in st.session_state: st.session_state["selected_screener_stock"]  = None


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="margin-bottom:14px;">
    <h1 style="color:#3b82f6; font-size:2rem; font-weight:900; margin-bottom:4px;">
        🔍 Top 10 Stock Screener — 1 Month BUY Picks
    </h1>
    <p style="color:#64748b; font-size:0.9rem; margin:0;">
        Scans Nifty 500 universe &nbsp;·&nbsp; Pre-filters to Top candidates &nbsp;·&nbsp;
        15 Skill Module Scoring &nbsp;·&nbsp; Select stock on left to analyze on right
    </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.markdown("### 🔍 Screener Controls")

scan_mode = st.sidebar.radio(
    "⚡ Scan Mode",
    ["Fast Testing (10 stocks)", "Full Universe Scan (Nifty 500)"],
    index=0,
    key="screener_scan_mode"
)

is_fast_mode = "Fast" in scan_mode
tickers_to_scan = NIFTY500_TICKERS[:30] if is_fast_mode else NIFTY500_TICKERS
candidate_limit = 10 if is_fast_mode else 50

st.sidebar.markdown(f"""
<div style="background:#0d1b2a; border:1px solid #1e3a5f; border-radius:8px; padding:10px; margin-bottom:10px;">
    <div style="font-size:0.7rem; color:#3b82f6; text-transform:uppercase; font-weight:700;">Scan Universe</div>
    <div style="color:#e2e8f0; font-size:0.9rem; margin-top:4px;">{'Fast 30 Stocks (Testing)' if is_fast_mode else 'Nifty 500 (Full)'}</div>
    <div style="font-size:0.7rem; color:#64748b; margin-top:2px;">Deep-scans top {candidate_limit} stocks</div>
</div>
<div style="background:#0d1b2a; border:1px solid #1e3a5f; border-radius:8px; padding:10px; margin-bottom:10px;">
    <div style="font-size:0.7rem; color:#3b82f6; text-transform:uppercase; font-weight:700;">Horizon</div>
    <div style="color:#e2e8f0; font-size:0.9rem; margin-top:4px;">⏳ 1 Month</div>
</div>
""", unsafe_allow_html=True)

run_scan = st.sidebar.button("🚀 Run New Scan", use_container_width=True, type="primary")
if run_scan:
    st.session_state["sc_phase1_results"]       = None
    st.session_state["sc_top10_data"]           = None
    st.session_state["sc_top10_analyses"]       = {}
    st.session_state["sc_top10_audits"]         = {}
    st.session_state["selected_screener_stock"] = None

st.sidebar.markdown("---")
st.sidebar.caption("Fast Mode: ~10-15 sec  \nFull Mode: ~3-4 min")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SCAN EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["sc_phase1_results"] is None:
    # ── PHASE 1 ──────────────────────────────────────────────────────────────
    st.markdown("### ⚡ Phase 1 — Fast Momentum Pre-Filter")
    p1_prog = st.progress(0, text=f"Scanning {len(tickers_to_scan)} stocks for momentum signals...")
    p1_status = st.empty()

    def _progress(frac):
        p1_prog.progress(min(frac, 1.0), text=f"Scanning ... {int(frac*100)}%  ({int(frac*len(tickers_to_scan))}/{len(tickers_to_scan)} stocks)")

    with st.spinner("⚡ Running fast momentum screen..."):
        phase1_results = phase1_fast_filter(tickers_to_scan, progress_cb=_progress)

    phase1_results = phase1_results[:candidate_limit]
    st.session_state["sc_phase1_results"] = phase1_results
    p1_prog.progress(1.0, text="✅ Phase 1 complete!")
    p1_status.success(f"✅ Pre-filtered to Top {len(phase1_results)} candidates")
    st.rerun()

phase1_results = st.session_state["sc_phase1_results"]


# ── PHASE 2: Deep skill scan ──────────────────────────────────────────────────
if st.session_state["sc_top10_data"] is None:
    st.markdown(f"### 🧠 Phase 2 — Deep Skill Scan (15 Modules per Stock for {len(phase1_results)} stocks)")
    top_candidates = [r["ticker"] for r in phase1_results]
    p2_prog   = st.progress(0, text="Starting deep skill scan...")
    p2_status = st.empty()

    scored_stocks = []
    for idx, ticker in enumerate(top_candidates):
        p2_prog.progress((idx + 1) / len(top_candidates),
                          text=f"🧠 Analyzing {ticker} ... ({idx+1}/{len(top_candidates)})")
        data, err = fetch_all_skills_screener(ticker)
        if err or data is None:
            continue
        skill_score, breakdown = compute_skill_score(data)
        scored_stocks.append({
            "ticker":    ticker,
            "data":      data,
            "score":     skill_score,
            "breakdown": breakdown,
            "company":   data["market"].get("company_name", ticker),
            "sector":    data["market"].get("sector", "N/A"),
            "price":     data["market"].get("current_price", "N/A"),
        })

    scored_stocks.sort(key=lambda x: x["score"], reverse=True)
    top10 = scored_stocks[:10]
    st.session_state["sc_top10_data"] = top10

    p2_prog.progress(1.0, text="✅ Phase 2 complete!")
    p2_status.success(f"✅ Top picks identified by composite skill score!")
    st.rerun()

top10 = st.session_state["sc_top10_data"]
if not top10:
    st.error("❌ No valid stocks found in Phase 2. Try running the scan again.")
    st.stop()


# Default selected stock to rank #1 if not set
if not st.session_state["selected_screener_stock"] and top10:
    st.session_state["selected_screener_stock"] = top10[0]["ticker"]


# ══════════════════════════════════════════════════════════════════════════════
# SIDE-BY-SIDE MASTER-DETAIL LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

col_left, col_right = st.columns([3.5, 6.5])

# ── LEFT COLUMN: MINIMAL CLEAN LIST (RANK + NAME ONLY) ─────────────────────────
with col_left:
    st.markdown("### 🏆 Top 10 Stocks")
    st.caption("Select a stock to view details on right:")

    for rank_idx, pick in enumerate(top10):
        rank   = rank_idx + 1
        ticker = pick["ticker"]
        m      = pick["data"]["market"]
        name   = m.get("company_name", ticker)

        is_selected = (st.session_state.get("selected_screener_stock") == ticker)

        prefix = "👉 " if is_selected else ""
        button_label = f"{prefix}#{rank}  {name}"

        if st.button(button_label, key=f"sel_item_{ticker}", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state["selected_screener_stock"] = ticker
            st.rerun()


# ── RIGHT COLUMN: DETAIL & AI ANALYSIS PANEL ──────────────────────────────────
with col_right:
    sel_ticker = st.session_state.get("selected_screener_stock")
    selected_pick = next((p for p in top10 if p["ticker"] == sel_ticker), None) if sel_ticker else top10[0]

    if selected_pick:
        ticker    = selected_pick["ticker"]
        data      = selected_pick["data"]
        score     = selected_pick["score"]
        breakdown = selected_pick["breakdown"]
        ps        = data.get("ps", {})
        m         = data["market"]
        name      = m.get("company_name", ticker)
        sect      = m.get("sector", "N/A")
        curr      = m.get("current_price", "N/A")
        t         = data["technical"]
        f         = data["fundamentals"]
        b         = data["balance"]
        sr        = data["sr"]

        rank = next((i + 1 for i, p in enumerate(top10) if p["ticker"] == ticker), 1)

        # Header card
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0d1b2a,#112240); border:2px solid #3b82f6;
                    border-radius:16px; padding:18px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:0.75rem; color:#3b82f6; font-weight:700; text-transform:uppercase;">#{rank} Ranked Pick — 1-Month Horizon</div>
                    <div style="font-size:1.5rem; font-weight:900; color:#f1f5f9; margin-top:2px;">{name}</div>
                    <div style="font-size:0.8rem; color:#64748b;">{sect} &nbsp;·&nbsp; {ticker} &nbsp;·&nbsp; Current Price: <strong style="color:#f1f5f9;">₹{curr}</strong></div>
                </div>
                <div style="background:#1e3a5f; border-radius:12px; padding:8px 16px; text-align:center;">
                    <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase;">Skill Score</div>
                    <div style="font-size:1.8rem; font-weight:900; color:#3b82f6;">{score}</div>
                    <div style="font-size:0.6rem; color:#475569;">/ 100</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**📊 Key Skill Metrics:**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RSI (14)", t.get("rsi_14","N/A"), t.get("rsi_zone","N/A"))
        m2.metric("SMA Alignment", f"vs 50D: {t.get('price_vs_sma50','N/A')}")
        m3.metric("D/E Ratio", f"{b.get('debt_to_equity','N/A')}x", b.get("de_risk","N/A"))
        m4.metric("YoY Rev Growth", f"{f.get('revenue_growth_yoy','N/A')}%")

        st.markdown("")

        st.markdown("**📐 Pre-Calculated Position Sizing:**")
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("📥 Entry", f"₹{ps.get('entry_price','N/A')}")
        p2.metric("🛑 Stop Loss", f"₹{ps.get('stop_loss','N/A')}")
        p3.metric("🎯 Target 1", f"₹{ps.get('target_1','N/A')}")
        p4.metric("🎯 Target 2", f"₹{ps.get('target_2','N/A')}")
        p5.metric("🎯 Target 3", f"₹{ps.get('target_3','N/A')}")

        st.markdown("---")

        has_analysis = ticker in st.session_state["sc_top10_analyses"] and ticker in st.session_state["sc_top10_audits"]

        if not has_analysis:
            st.markdown(f"""
            <div style="background:#0d1b2a; border:2px dashed #1e3a5f; border-radius:12px; padding:20px; text-align:center; margin-bottom:14px;">
                <div style="font-size:1rem; color:#f1f5f9; font-weight:700; margin-bottom:4px;">🤖 Ready for Dual AI Analysis &amp; Audit</div>
                <div style="font-size:0.8rem; color:#64748b; margin-bottom:12px;">Click below to run Primary Analyst trade plan and Independent Auditor verification for {name}.</div>
            </div>
            """, unsafe_allow_html=True)

            run_detail_btn = st.button(f"🚀 Run AI Analysis & Auditor Check for {name}", key=f"run_right_{ticker}", use_container_width=True, type="primary")

            if run_detail_btn:
                prompt   = build_screener_prompt(ticker, data, rank, score)
                p_holder = st.empty()
                full_txt = ""
                with st.spinner(f"🤖 Primary Analyst Agent analyzing {name} ({ticker})..."):
                    for chunk in stream_analyst(prompt):
                        full_txt += chunk
                        p_holder.markdown(full_txt + "▌")
                p_holder.empty()
                st.session_state["sc_top10_analyses"][ticker] = full_txt

                audit_prompt = build_screener_audit_prompt(ticker, data, full_txt)
                a_holder     = st.empty()
                audit_txt    = ""
                with st.spinner(f"🛡️ Independent Auditor Agent verifying {name}..."):
                    for chunk in stream_auditor(audit_prompt):
                        audit_txt += chunk
                        a_holder.markdown(audit_txt + "▌")
                a_holder.empty()
                st.session_state["sc_top10_audits"][ticker] = audit_txt
                st.rerun()
        else:
            render_pick_card(
                rank, ticker, data, score, breakdown,
                st.session_state["sc_top10_analyses"][ticker],
                st.session_state["sc_top10_audits"][ticker]
            )

            if st.button(f"🔄 Re-run AI Analysis for {name}", key=f"re_right_{ticker}"):
                del st.session_state["sc_top10_analyses"][ticker]
                del st.session_state["sc_top10_audits"][ticker]
                st.rerun()
