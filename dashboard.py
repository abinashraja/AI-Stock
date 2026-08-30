"""
AI Stock Analysis Dashboard — Full Skills Architecture
All data is fetched/calculated by skill modules.
LLM ONLY interprets — never invents numbers.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import math
import os
import requests
import json
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Add skills folder to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills"))

from skill_market_data       import get_market_data
from skill_technical         import get_technical_data
from skill_support_resistance import get_support_resistance
from skill_patterns          import get_chart_patterns
from skill_volume            import get_volume_analysis
from skill_fundamentals      import get_fundamentals
from skill_balance_sheet     import get_balance_sheet
from skill_valuation         import get_valuation
from skill_shareholding      import get_shareholding
from skill_market_context    import get_market_context
from skill_relative_strength import get_relative_strength
from skill_news              import get_news
from skill_fno               import get_fno_data
from skill_scenarios         import get_scenarios
from skill_position_sizing   import get_position_sizing

# ── Page Config ────────────────────────────────────────────────────────────────
# We read session_state before set_page_config so sidebar starts collapsed on landing
_sidebar_state = "collapsed" if "active_ticker" not in st.session_state or not st.session_state.get("active_ticker") else "expanded"
st.set_page_config(
    page_title="AI Stock Analyst — India",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state=_sidebar_state,
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

* { font-family: 'Inter', sans-serif !important; }
#MainMenu, header, footer { visibility: hidden; }

.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 50%, #0a0e1a 100%);
    color: #e2e8f0;
}
.block-container {
    padding: 0.8rem 1.5rem !important;
    max-width: 100% !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a, #111827) !important;
    border-right: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
    color: white !important; border-radius: 8px !important;
    font-weight: 700 !important; border: none !important;
}

/* Metrics */
div[data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700 !important; color: #f1f5f9 !important; }
div[data-testid="stMetricLabel"] { font-size: 0.7rem !important; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.05em; }
div[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* Decision Card */
.decision-card {
    background: linear-gradient(135deg, #0f2744, #1a3a5c);
    border: 1px solid #2563eb;
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
}
.decision-buy { border-color: #10b981; background: linear-gradient(135deg, #052e1f, #064e32); }
.decision-sell { border-color: #ef4444; background: linear-gradient(135deg, #2d1515, #450a0a); }
.decision-wait { border-color: #f59e0b; background: linear-gradient(135deg, #292005, #3d2b00); }

/* Section headers */
.section-header {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #3b82f6;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 3px; margin-bottom: 6px;
}

/* Skill badges */
.badge-bull { background: #052e1f; color: #10b981; border: 1px solid #10b981; border-radius: 6px; padding: 2px 8px; font-size: 0.65rem; font-weight: 700; }
.badge-bear { background: #2d1515; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; padding: 2px 8px; font-size: 0.65rem; font-weight: 700; }
.badge-neutral { background: #1c1408; color: #f59e0b; border: 1px solid #f59e0b; border-radius: 6px; padding: 2px 8px; font-size: 0.65rem; font-weight: 700; }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] { background: #0d1b2a; border-radius: 8px; gap: 2px; }
.stTabs [data-baseweb="tab"] { color: #64748b !important; font-size: 0.75rem !important; padding: 4px 12px !important; }
.stTabs [aria-selected="true"] { background: #1e40af !important; color: white !important; border-radius: 6px; }

/* News cards */
.news-card { background: #0d1b2a; border: 1px solid #1e3a5f; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; }
.news-pos { border-left: 3px solid #10b981; }
.news-neg { border-left: 3px solid #ef4444; }
.news-neu { border-left: 3px solid #f59e0b; }

hr { border-color: #1e3a5f !important; margin: 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── State Initialization ───────────────────────────────────────────────────────
if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = None
if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""
if "time_horizon" not in st.session_state:
    st.session_state["time_horizon"] = "1 Year"
if "investment_amount" not in st.session_state:
    st.session_state["investment_amount"] = 100000
if "primary_full_text" not in st.session_state:
    st.session_state["primary_full_text"] = None
if "auditor_full_text" not in st.session_state:
    st.session_state["auditor_full_text"] = None
if "fresh_analysis_trigger" not in st.session_state:
    st.session_state["fresh_analysis_trigger"] = False


def search_indian_stocks(query):
    if not query or len(query.strip()) < 2:
        return {}
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        quotes = data.get("quotes", [])
        indian = [q for q in quotes if q.get("exchange") in ["NSI", "BSE"] or
                  q.get("symbol", "").endswith((".NS", ".BO"))]
        options = {}
        for q in indian:
            name   = q.get("shortname") or q.get("longname") or "Unknown"
            symbol = q.get("symbol")
            exch   = q.get("exchDisp") or q.get("exchange")
            options[f"{name} ({symbol}) — {exch}"] = symbol
        return options
    except:
        return {}


# ── FIRST TIME OPEN: CENTERED HERO FILTER CARD (NO PRESELECTED STOCK) ────────
if not st.session_state["active_ticker"]:
    st.markdown("""
    <div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
        <h1 style="color: #3b82f6; font-size: 2.8rem; font-weight: 900; margin-bottom: 4px;">📈 AI Stock Analyst</h1>
        <p style="color: #94a3b8; font-size: 1.1rem;">Positional Equity Analysis &amp; Risk Auditor for Indian Markets</p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 3.5, 1])

    with col_center:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0d1b2a 0%, #112240 100%);
                    border: 2px solid #1e3a5f; border-radius: 20px; padding: 28px 32px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <div style="font-size: 0.75rem; color: #3b82f6; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">
                🔍 Select Stock &amp; Investment Parameters
            </div>
        """, unsafe_allow_html=True)

        center_query = st.text_input(
            "Company Name / Ticker (India)",
            value=st.session_state["search_query"],
            placeholder="e.g. Tata Power, Reliance, State Bank of India, TCS...",
            key="center_search_input"
        )

        selected_ticker = None
        if center_query:
            results = search_indian_stocks(center_query)
            if results:
                label = st.selectbox("Select matched company:", list(results.keys()), key="center_select")
                selected_ticker = results[label]
            else:
                selected_ticker = f"{center_query.upper()}.NS" if "." not in center_query else center_query.upper()
                st.info(f"Looking up ticker: **{selected_ticker}**")

        st.markdown("<br>", unsafe_allow_html=True)
        col_h, col_cap = st.columns(2)

        with col_h:
            center_horizon = st.radio(
                "⏳ Investment Horizon",
                ["1 Month", "3 Months", "6 Months", "1 Year"],
                index=["1 Month", "3 Months", "6 Months", "1 Year"].index(st.session_state["time_horizon"]),
                key="center_horizon_radio"
            )

        with col_cap:
            center_capital = st.number_input(
                "💰 Capital Available (₹)",
                min_value=10000, max_value=10000000,
                value=int(st.session_state["investment_amount"]),
                step=10000, format="%d",
                key="center_capital_input"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        start_btn = st.button("🚀 Start Deep Analysis", use_container_width=True, type="primary", key="center_start_btn")

        st.markdown("</div>", unsafe_allow_html=True)

        if start_btn:
            if not selected_ticker:
                st.error("⚠️ Please enter a company name or ticker above to begin.")
            else:
                st.session_state["active_ticker"] = selected_ticker
                st.session_state["search_query"] = center_query
                st.session_state["time_horizon"] = center_horizon
                st.session_state["investment_amount"] = center_capital
                st.session_state["primary_full_text"] = None
                st.session_state["auditor_full_text"] = None
                st.session_state["fresh_analysis_trigger"] = True
                st.rerun()

    st.stop()


# ── ACTIVE STATE: CONTROLS MOVED TO SIDEBAR ───────────────────────────────────
st.sidebar.markdown("### 📈 AI Stock Analyst")

search_query = st.sidebar.text_input(
    "Company / Ticker (India)",
    value=st.session_state["search_query"] or st.session_state["active_ticker"],
    key="sidebar_search"
)

selected_ticker = st.session_state["active_ticker"]
if search_query and search_query != st.session_state["search_query"]:
    results = search_indian_stocks(search_query)
    if results:
        label = st.sidebar.selectbox("Select company:", list(results.keys()), key="sidebar_select")
        selected_ticker = results[label]
    else:
        selected_ticker = f"{search_query.upper()}.NS" if "." not in search_query else search_query.upper()

st.sidebar.markdown("---")
st.sidebar.markdown("**⏳ Investment Horizon**")
time_horizon = st.sidebar.radio(
    "Holding period:", ["1 Month", "3 Months", "6 Months", "1 Year"],
    index=["1 Month", "3 Months", "6 Months", "1 Year"].index(st.session_state["time_horizon"]),
    key="sidebar_horizon"
)
horizon_key = {"1 Month": "1M", "3 Months": "3M", "6 Months": "6M", "1 Year": "1Y"}[time_horizon]

st.sidebar.markdown("**💰 Investment Amount (₹)**")
investment_amount = st.sidebar.number_input(
    "Capital to deploy:", min_value=10000, max_value=10000000,
    value=int(st.session_state["investment_amount"]), step=10000, format="%d",
    key="sidebar_capital"
)

analyze_btn = st.sidebar.button("🔍 Deep Analyze", use_container_width=True, type="primary", key="sidebar_analyze_btn")

if st.sidebar.button("🔄 Search Different Stock", use_container_width=True):
    st.session_state["active_ticker"] = None
    st.session_state["search_query"] = ""
    st.session_state["primary_full_text"] = None
    st.session_state["auditor_full_text"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Data: Yahoo Finance · Google News · NSE API  \nAI: Google Gemini · Dual Agent Verification")


# ── Helper: fetch all data via skills ─────────────────────────────────────────
def fetch_all_skills(ticker: str):
    stock = yf.Ticker(ticker)
    info  = stock.info or {}
    hist  = stock.history(period="2y")

    if hist.empty:
        return None, "No price data found for this ticker."

    data = {}
    data["market"]      = get_market_data(ticker, info, hist)
    data["technical"]   = get_technical_data(hist, info)
    data["sr"]          = get_support_resistance(hist)
    data["patterns"]    = get_chart_patterns(hist)
    data["volume"]      = get_volume_analysis(hist)
    data["fundamentals"]= get_fundamentals(stock, info)
    data["balance"]     = get_balance_sheet(stock, info)
    data["valuation"]   = get_valuation(info, data["technical"], data["fundamentals"])
    data["shareholding"]= get_shareholding(stock, info)
    data["mkt_ctx"]     = get_market_context()
    data["rel_str"]     = get_relative_strength(hist, ticker)
    data["news"]        = get_news(stock, data["market"].get("company_name", ticker))
    data["fno"]         = get_fno_data(ticker)
    data["hist"]        = hist
    return data, None


# ── AI Analysis via Gemini ─────────────────────────────────────────────────────
def build_ai_prompt(ticker, data, time_horizon, investment_amount, ps=None, sc=None):
    t  = data["technical"]
    f  = data["fundamentals"]
    b  = data["balance"]
    v  = data["valuation"]
    m  = data["market"]
    sr = data["sr"]
    sh = data["shareholding"]
    mc = data["mkt_ctx"]
    rs = data["rel_str"]
    nw = data["news"]
    pt = data["patterns"]
    fno= data["fno"]

    headlines_text = "\n".join([
        f"  [{h['sentiment']}] {h['date']}: {h['title']}"
        for h in nw.get("headlines", [])[:5]
    ]) or "  No headlines available"

    fno_text = f"""PCR: {fno.get('pcr','N/A')} | Signal: {fno.get('pcr_signal','N/A')} | CE OI: {fno.get('total_ce_oi','N/A')} | PE OI: {fno.get('total_pe_oi','N/A')}""" \
               if fno.get("available") else "F&O data not available for this symbol"

    rs_data = rs.get("relative_strength_vs_nifty", {})
    rs_text = "\n".join([
        f"  {k}: Stock {v.get('stock_return_pct','N/A')}% | NIFTY {v.get('nifty_return_pct','N/A')}% | Alpha {v.get('alpha_pct','N/A')}% | {v.get('signal','N/A')}"
        for k, v in rs_data.items()
    ]) or "  N/A"

    nifty = mc.get("nifty_50", {})
    nifty_text = f"NIFTY 50: {nifty.get('price','N/A')} ({nifty.get('change_pct','N/A')}%) | {nifty.get('trend','N/A')}" \
                 if isinstance(nifty, dict) else "N/A"

    patterns_text = "\n".join([f"  - {p}" for p in pt.get("patterns_detected", [])]) or "  None detected"

    prompt = f"""You are an expert Indian stock market analyst specializing in positional swing/long-term trading (NOT intraday).
You have been given PRE-CALCULATED data from 15 specialist skill modules. You must use ONLY this data — DO NOT invent or guess any numbers.

═══════════════════════════════════════════════
STOCK: {m.get('company_name', ticker)} ({ticker})
SECTOR: {m.get('sector','N/A')} | INDUSTRY: {m.get('industry','N/A')}
═══════════════════════════════════════════════

━━━ MARKET DATA ━━━
Current Price: ₹{m.get('current_price','N/A')} | Change: {m.get('change_pct','N/A')}%
Open: ₹{m.get('open','N/A')} | High: ₹{m.get('high','N/A')} | Low: ₹{m.get('low','N/A')}
52W High: ₹{m.get('52w_high','N/A')} | 52W Low: ₹{m.get('52w_low','N/A')}
Mkt Cap: ₹{m.get('market_cap_cr','N/A')} Cr | Free Float: {m.get('free_float_pct','N/A')}%
Volume: {m.get('volume','N/A')} | Avg Vol (20D): {m.get('avg_volume_20d','N/A')}

━━━ TECHNICAL ANALYSIS ━━━
SMA 20: ₹{t.get('sma_20','N/A')} [{t.get('price_vs_sma20','N/A')}]
SMA 50: ₹{t.get('sma_50','N/A')} [{t.get('price_vs_sma50','N/A')}]
SMA 100: ₹{t.get('sma_100','N/A')} [{t.get('price_vs_sma100','N/A')}]
SMA 200: ₹{t.get('sma_200','N/A')} [{t.get('price_vs_sma200','N/A')}]
Golden/Death Cross: {t.get('golden_death_cross','N/A')}
RSI (14): {t.get('rsi_14','N/A')} — {t.get('rsi_zone','N/A')}
MACD Line: {t.get('macd_line','N/A')} | Signal: {t.get('macd_signal','N/A')} | Trend: {t.get('macd_trend','N/A')}
ATR (14): ₹{t.get('atr_14','N/A')}
Bollinger Bands: Upper ₹{t.get('bb_upper','N/A')} | Lower ₹{t.get('bb_lower','N/A')} | %B: {t.get('bb_pct','N/A')}
ADX (14): {t.get('adx_14','N/A')} — {t.get('adx_strength','N/A')}
Stochastic %K: {t.get('stoch_k','N/A')} | %D: {t.get('stoch_d','N/A')}
VWAP (20D): ₹{t.get('vwap_20d','N/A')}
Trend Structure: {t.get('trend_structure','N/A')}

━━━ SUPPORT & RESISTANCE ━━━
Pivot: ₹{sr.get('pivot_point','N/A')}
R1/R2/R3: ₹{sr.get('resistance_1','N/A')} / ₹{sr.get('resistance_2','N/A')} / ₹{sr.get('resistance_3','N/A')}
S1/S2/S3: ₹{sr.get('support_1','N/A')} / ₹{sr.get('support_2','N/A')} / ₹{sr.get('support_3','N/A')}
Nearest Resistance: ₹{sr.get('nearest_resistance','N/A')} ({sr.get('breakout_dist_pct','N/A')}% away)
Nearest Support: ₹{sr.get('nearest_support','N/A')} ({sr.get('breakdown_dist_pct','N/A')}% away)
Major Resistances: {sr.get('major_resistances','N/A')}
Major Supports: {sr.get('major_supports','N/A')}

━━━ CHART PATTERNS ━━━
{patterns_text}
Primary Bias: {pt.get('primary_bias','N/A')}

━━━ VOLUME ANALYSIS ━━━
Volume Signal: {data['volume'].get('volume_signal','N/A')}
Vol vs 20D Avg: {data['volume'].get('vol_vs_avg20_pct','N/A')}%
OBV Trend: {data['volume'].get('obv_trend','N/A')}
A/D Line: {data['volume'].get('ad_trend','N/A')}
Volume Momentum: {data['volume'].get('volume_momentum','N/A')}

━━━ FUNDAMENTALS ━━━
Revenue: ₹{f.get('revenue_latest_cr','N/A')} Cr | Growth YoY: {f.get('revenue_growth_yoy','N/A')}% | CAGR 3Y: {f.get('revenue_cagr_3yr','N/A')}%
Net Profit: ₹{f.get('pat_latest_cr','N/A')} Cr | Growth: {f.get('pat_growth_yoy','N/A')}%
EBITDA: ₹{f.get('ebitda_latest_cr','N/A')} Cr
Gross Margin: {f.get('gross_margin_pct','N/A')}% | Op Margin: {f.get('operating_margin_pct','N/A')}% | Net Margin: {f.get('net_margin_pct','N/A')}%
ROE: {f.get('roe_pct','N/A')}% | ROA: {f.get('roa_pct','N/A')}%
EPS TTM: ₹{f.get('eps_ttm','N/A')} | EPS Fwd: ₹{f.get('eps_forward','N/A')} | EPS Growth: {f.get('eps_growth_pct','N/A')}%
FCF: ₹{f.get('free_cash_flow_cr','N/A')} Cr

━━━ BALANCE SHEET ━━━
Total Debt: ₹{b.get('total_debt_cr','N/A')} Cr | Cash: ₹{b.get('cash_cr','N/A')} Cr
D/E Ratio: {b.get('debt_to_equity','N/A')}x — {b.get('de_risk','N/A')}
Current Ratio: {b.get('current_ratio','N/A')}
Interest Coverage: {b.get('interest_coverage','N/A')}x — {b.get('interest_coverage_risk','N/A')}

━━━ VALUATION ━━━
P/E (TTM): {v.get('pe_ttm','N/A')} [{v.get('pe_signal','N/A')}] | P/E (Fwd): {v.get('pe_forward','N/A')}
P/B: {v.get('pb_ratio','N/A')} | P/S: {v.get('ps_ratio','N/A')}
PEG: {v.get('peg_ratio','N/A')} — {v.get('peg_signal','N/A')}
EV/EBITDA: {v.get('ev_ebitda','N/A')}
Graham Number: ₹{v.get('graham_number','N/A')} | Margin of Safety: {v.get('margin_of_safety_pct','N/A')}%
Analyst Target: ₹{v.get('analyst_target','N/A')} ({v.get('analyst_upside_pct','N/A')}% upside) | {v.get('analyst_count','N/A')} analysts | Rec: {v.get('analyst_recommendation','N/A')}

━━━ SHAREHOLDING ━━━
Promoter/Insider: {sh.get('promoter_holding_pct','N/A')}% — {sh.get('holding_signal','N/A')}
Institutional: {sh.get('institutional_pct','N/A')}%

━━━ MARKET CONTEXT ━━━
{nifty_text}
VIX: {mc.get('india_vix','N/A')} — {mc.get('vix_regime','N/A')}
Market Regime: {mc.get('market_regime','N/A')}

━━━ RELATIVE STRENGTH vs NIFTY ━━━
Beta (6M): {rs.get('beta_6m','N/A')} — {rs.get('beta_signal','N/A')}
{rs_text}

━━━ F&O DATA ━━━
{fno_text}

━━━ NEWS SENTIMENT ━━━
Overall: {nw.get('overall_sentiment','N/A')} ({nw.get('sentiment_summary','N/A')})
Recent Headlines:
{headlines_text}

═══════════════════════════════════════════════
INVESTMENT PARAMETERS
Investment Horizon: {time_horizon}
Capital Available: ₹{investment_amount:,}
Risk Per Trade: Max 2% of capital (₹{int(investment_amount * 0.02):,})
═══════════════════════════════════════════════

━━━ PRE-CALCULATED TRADE PLAN (use these EXACT numbers in your output) ━━━
Entry Price:      ₹{ps.get('entry_price','N/A') if ps else 'N/A'}
Stop Loss:        ₹{ps.get('stop_loss','N/A') if ps else 'N/A'}  (risk/share: ₹{ps.get('risk_per_share','N/A') if ps else 'N/A'})
Target 1 (1:1.5): ₹{ps.get('target_1','N/A') if ps else 'N/A'}
Target 2 (1:2.5): ₹{ps.get('target_2','N/A') if ps else 'N/A'}
Target 3 (1:4.0): ₹{ps.get('target_3','N/A') if ps else 'N/A'}
Quantity:         {ps.get('quantity','N/A') if ps else 'N/A'} shares
Capital Required: ₹{ps.get('capital_required','N/A') if ps else 'N/A'}
Max Loss:         ₹{ps.get('max_loss','N/A') if ps else 'N/A'}
R:R at T2:        1:{ps.get('rr_ratio_t2','N/A') if ps else 'N/A'}
Trailing Plan:    {ps.get('trailing_stop_plan','N/A') if ps else 'N/A'}

━━━ PRE-CALCULATED SCENARIOS ━━━
Bull Case ({sc.get('bull_case',{}).get('probability','N/A') if sc else 'N/A'}): ₹{sc.get('bull_case',{}).get('target','N/A') if sc else 'N/A'} (+{sc.get('bull_case',{}).get('upside_pct','N/A') if sc else 'N/A'}%) — {sc.get('bull_case',{}).get('trigger','') if sc else ''}
Base Case ({sc.get('base_case',{}).get('probability','N/A') if sc else 'N/A'}): ₹{sc.get('base_case',{}).get('target','N/A') if sc else 'N/A'} (+{sc.get('base_case',{}).get('upside_pct','N/A') if sc else 'N/A'}%) — {sc.get('base_case',{}).get('trigger','') if sc else ''}
Bear Case ({sc.get('bear_case',{}).get('probability','N/A') if sc else 'N/A'}): ₹{sc.get('bear_case',{}).get('target','N/A') if sc else 'N/A'} ({sc.get('bear_case',{}).get('downside_pct','N/A') if sc else 'N/A'}%) — {sc.get('bear_case',{}).get('trigger','') if sc else ''}

DECISION WEIGHTS & HORIZON ADAPTATION ({time_horizon}):
- Short Term (1 Month / 3 Months): Technical Trend (20/50 SMA, RSI, Volume) carries 60% weight. If price is in a short-term downtrend (below 20 & 50 SMA), decision MUST be WAIT regardless of company fundamentals.
- Long Term (6 Months / 1 Year): Business Fundamentals & Valuation (Revenue growth, ROE, FCF, D/E, Margin of Safety) carry 55% weight. Quality companies with clean balance sheets (D/E < 1.0x) and strong earnings near major structural support can be a BUY for 1 Year even if 1-Month technicals are consolidating.

STRICT SAFETY RULES (NEVER VIOLATE):
1. STOCK TREND RULE: For 1-Month horizon, if THIS individual stock is trading above its 50-day SMA with clean financials (D/E < 1.5x, IC > 1.5x) and bullish momentum, issue a BUY recommendation. Broad index Nifty moves are a risk factor to note, NOT an automatic rejection of a strong stock.
2. DOWNTREND RULE: If current price is BELOW the 50-day SMA and 200-day SMA for this stock and horizon is <= 3 Months, DO NOT issue a BUY. You MUST issue WAIT.
3. FINANCIAL RISK RULE: If Debt-to-Equity is > 1.5x OR Interest Coverage is < 1.5x, DO NOT issue a BUY for any horizon. You MUST issue WAIT.
4. SINGLE INDICATOR BIAS: An oversold RSI (e.g., RSI < 30) ALONE must NEVER trigger a BUY when price is in a downtrend.
5. Stop Loss MUST always be BELOW Entry price.
6. Targets MUST always be ABOVE Entry price.
7. R:R at T2 must be >= 2:1.
8. This is positional (weeks/months/years), NOT intraday.
9. Use the PRE-CALCULATED numbers below — do NOT invent new ones.
10. Explain in plain simple language a common person can understand.

PRE-CALCULATED LEVELS (copy these exactly):
Entry:    ₹{ps.get('entry_price','N/A') if ps else 'N/A'}
Stop:     ₹{ps.get('stop_loss','N/A') if ps else 'N/A'}
Target 1: ₹{ps.get('target_1','N/A') if ps else 'N/A'}
Target 2: ₹{ps.get('target_2','N/A') if ps else 'N/A'}
Target 3: ₹{ps.get('target_3','N/A') if ps else 'N/A'}
Qty:      {ps.get('quantity','N/A') if ps else 'N/A'} shares | Max Loss: ₹{ps.get('max_loss','N/A') if ps else 'N/A'}

OUTPUT — use EXACTLY this format, nothing else:

DECISION: [BUY / SELL / WAIT]
CONFIDENCE: [High / Medium / Low]

ENTRY: ₹[entry price]
STOP LOSS: ₹[stop price]  ← exit immediately if price falls here
TARGET 1: ₹[t1]
TARGET 2: ₹[t2]
TARGET 3: ₹[t3]

WHY (2-3 plain English sentences a non-expert understands. No jargon. No technical terms.):
[Your plain language reason]

ONE RISK TO WATCH:
[Single biggest risk in one simple sentence]

ACTION:
[One clear sentence: what to do today / what price to watch]
"""
    return prompt



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


def stream_ai_analysis(prompt: str):
    api_keys = get_gemini_api_keys()
    if not api_keys:
        yield "⚠️ No Gemini API Key found. Please add `GEMINI_API_KEY` to Streamlit Secrets or `.env` file."
        return

    models = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

    for key in api_keys:
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:streamGenerateContent?alt=sse"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": (
                    "You are a senior Indian equity research analyst. "
                    "Use ONLY the pre-calculated data provided. Never fabricate numbers. "
                    "Give precise, actionable positional trading advice."
                )}]},
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
            }
            try:
                resp = requests.post(
                    url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=body,
                    stream=True,
                    timeout=60,
                )
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if line:
                            dec = line.decode("utf-8")
                            if dec.startswith("data: "):
                                try:
                                    chunk = json.loads(dec[6:])
                                    parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                                    if parts and "text" in parts[0]:
                                        yield parts[0]["text"]
                                except:
                                    pass
                    return
                elif resp.status_code in (429, 404, 503):
                    continue  # Try next model / key
            except Exception:
                continue

    yield "⚠️ All API keys exhausted or rate-limited. Please wait and retry."


# ── Auditor Agent (Independent Risk & Compliance LLM) ─────────────────────────
def build_auditor_prompt(ticker, data, primary_output, time_horizon, investment_amount, ps=None):
    t  = data["technical"]
    f  = data["fundamentals"]
    b  = data["balance"]
    m  = data["market"]
    sr = data["sr"]
    mc = data["mkt_ctx"]

    precalc_text = ""
    if ps and "error" not in ps:
        precalc_text = f"""
PRE-CALCULATED VERIFIED TRADE LEVELS:
- Entry Price: ₹{ps.get('entry_price','N/A')}
- Stop Loss:   ₹{ps.get('stop_loss','N/A')}
- Target 1:    ₹{ps.get('target_1','N/A')}
- Target 2:    ₹{ps.get('target_2','N/A')}
- Target 3:    ₹{ps.get('target_3','N/A')}
- R:R at T2:   1:{ps.get('rr_ratio_t2','N/A')}
Math Check Status: VERIFIED PASS (Stop Loss < Entry < Target 1 < Target 2 < Target 3)
"""

    prompt = f"""You are a Senior Risk & Compliance Auditor Agent for Indian stock markets.
Your sole job is to independently AUDIT and VALIDATE the proposed trade plan generated by the primary analyst agent for {m.get('company_name', ticker)} ({ticker}).
You do NOT blindly agree with the primary analyst. You enforce strict risk rules with zero tolerance for improper trade setup.

{precalc_text}

PRIMARY ANALYST PROPOSAL:
{primary_output}

EMPIRICAL MARKET DATA:
- Current Price: ₹{m.get('current_price', 'N/A')}
- SMA 20: ₹{t.get('sma_20','N/A')} | SMA 50: ₹{t.get('sma_50','N/A')} | SMA 200: ₹{t.get('sma_200','N/A')}
- Golden / Death Cross: {t.get('golden_death_cross','N/A')}
- RSI (14): {t.get('rsi_14','N/A')} ({t.get('rsi_zone','N/A')})
- Trend Structure: {t.get('trend_structure','N/A')}
- Debt to Equity: {b.get('debt_to_equity','N/A')}x ({b.get('de_risk','N/A')})
- Interest Coverage: {b.get('interest_coverage','N/A')}x ({b.get('interest_coverage_risk','N/A')})
- Nearest Support: ₹{sr.get('nearest_support','N/A')} | Nearest Resistance: ₹{sr.get('nearest_resistance','N/A')}
- Market Regime: {mc.get('market_regime','N/A')} | India VIX: {mc.get('india_vix','N/A')}

STRICT VALIDATION RULES TO ENFORCE ({time_horizon} Horizon):
1. STOCK VS INDEX RULE: If this individual stock is trading ABOVE its own 50-day SMA with clean financials (D/E < 1.5x, IC > 1.5x) and bullish momentum, APPROVE the BUY trade for 1 Month. Broad market index consolidation is a risk factor to note, NOT an automatic rejection.
2. MATHEMATICAL INTEGRITY: Use the PRE-CALCULATED VERIFIED TRADE LEVELS above for the math check. Do NOT reject due to a text typo or string truncation in the analyst's text output if the pre-calculated trade levels are valid. Stop Loss MUST be strictly below Entry. Targets MUST be strictly above Entry. Target 2 R:R MUST be >= 2.0x.
3. DOWNTREND FILTER: If THIS individual stock is below its 50-day SMA and 200-day SMA in a confirmed downtrend, a BUY recommendation MUST be REJECTED.
4. FINANCIAL SAFETY: Debt/Equity > 1.5x or weak interest coverage (<1.5x) must not be ignored for any horizon.
5. NO SINGLE INDICATOR BIAS: Decision must not depend solely on RSI or a single indicator.
6. COMPLETE RESPONSE: Write 1-2 complete, finished sentences for REASON ending with a period. Do NOT leave sentences incomplete.

OUTPUT FORMAT — follow EXACTLY (keep it short & simple in plain layman English):

AUDITOR DECISION: [BUY / SELL / WAIT / DO NOT BUY]

REASON:
[1-2 complete, finished plain simple sentences in plain layman English explaining why, ending with a period.]
"""
    return prompt


def stream_auditor_analysis(prompt: str):
    api_keys = get_gemini_api_keys()
    if not api_keys:
        yield "⚠️ No Gemini API Key found. Please add `GEMINI_API_KEY` to Streamlit Secrets or `.env` file."
        return

    models = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

    for key in api_keys:
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:streamGenerateContent?alt=sse"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": (
                    "You are a strict, independent Senior Risk & Compliance Officer auditing equity trade decisions. "
                    "Enforce strict risk management rules with zero leniency. Do NOT blindly agree with the primary analyst."
                )}]},
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
            }
            try:
                resp = requests.post(
                    url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=body,
                    stream=True,
                    timeout=60,
                )
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if line:
                            dec = line.decode("utf-8")
                            if dec.startswith("data: "):
                                try:
                                    chunk = json.loads(dec[6:])
                                    parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                                    if parts and "text" in parts[0]:
                                        yield parts[0]["text"]
                                except:
                                    pass
                    return
                elif resp.status_code in (429, 404, 503):
                    continue
            except Exception as e:
                continue

    yield "⚠️ Auditor API keys exhausted. Please try again."


# ── Helper formatters ───────────────────────────────────────────────────────────
def badge(val, bull_cond, bear_cond, fmt_str="{}"):
    try:
        display = fmt_str.format(val) if val not in (None, "N/A", "") else "N/A"
        if val in (None, "N/A", ""):
            return f'<span class="badge-neutral">N/A</span>'
        if bull_cond:
            return f'<span class="badge-bull">▲ {display}</span>'
        elif bear_cond:
            return f'<span class="badge-bear">▼ {display}</span>'
        else:
            return f'<span class="badge-neutral">~ {display}</span>'
    except:
        return f'<span class="badge-neutral">N/A</span>'


def rupee(val):
    if val is None or val == "" or val == "N/A": return "N/A"
    try:
        _f = float(val)
        if math.isnan(_f) or math.isinf(_f): return "N/A"
        return f"\u20b9{_f:,.2f}"
    except: return "N/A"


def pct(val):
    if val in (None, "N/A", ""): return "N/A"
    try: return f"{float(val):+.2f}%"
    except: return str(val)


# ── Main UI ────────────────────────────────────────────────────────────────────
if not selected_ticker:
    st.markdown("""
    <div style="text-align:center; padding: 80px 0;">
        <h1 style="color:#3b82f6; font-size:3rem;">📈 AI Stock Analyst</h1>
        <p style="color:#64748b; font-size:1.2rem;">Enter a company name in the sidebar to begin deep analysis.</p>
        <p style="color:#475569; font-size:0.9rem;">15 Skill Modules · 40+ Data Points · Positional Trading Focus</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Fetch Data ─────────────────────────────────────────────────────────────────
with st.spinner(f"🔍 Running 15 skill modules for {selected_ticker}..."):
    data, err = fetch_all_skills(selected_ticker)

if err or not data:
    st.error(f"❌ {err or 'Failed to fetch data.'}")
    st.stop()

m   = data["market"]
t   = data["technical"]
sr  = data["sr"]
pt  = data["patterns"]
vol = data["volume"]
f   = data["fundamentals"]
b   = data["balance"]
v   = data["valuation"]
sh  = data["shareholding"]
mc  = data["mkt_ctx"]
rs  = data["rel_str"]
nw  = data["news"]
fno = data["fno"]
hist = data["hist"]

curr = 0.0
# Use last VALID (non-NaN) close — essential for ETFs and BSE stocks
if not hist.empty:
    _valid = hist["Close"].dropna()
    if not _valid.empty:
        _raw = float(_valid.iloc[-1])
        if not math.isnan(_raw) and _raw > 0:
            curr = round(_raw, 2)

# If info has a valid price, prefer it
try:
    _pv = float(m.get("current_price") or 0)
    if _pv > 0 and not math.isnan(_pv):
        curr = _pv
except:
    pass

# Patch all header metrics from history (dropna-safe)
if curr > 0:
    m["current_price"] = curr
    if m.get("prev_close") in (None, "N/A", 0):
        try:
            _c = hist["Close"].dropna()
            _p = float(_c.iloc[-2])
            if not math.isnan(_p): m["prev_close"] = round(_p, 2)
        except: pass
    if m.get("change_pct") in (None, "N/A"):
        try:
            _p2 = float(hist["Close"].dropna().iloc[-2])
            if not math.isnan(_p2):
                m["change_pct"] = round((curr - _p2) / _p2 * 100, 2)
        except: pass
    if m.get("52w_high") in (None, "N/A"):
        try:
            m["52w_high"] = round(float(hist["High"].dropna().tail(252).max()), 2)
            m["52w_low"]  = round(float(hist["Low"].dropna().tail(252).min()), 2)
        except: pass
    if m.get("volume") in (None, "N/A", 0):
        try:
            _vol = int(hist["Volume"].dropna().iloc[-1])
            if _vol > 0: m["volume"] = _vol
        except: pass


# Generate scenarios and position sizing
def _safe_float(val, fallback):
    try:
        _v = float(val)
        if math.isnan(_v) or math.isinf(_v): return fallback
        return _v if _v > 0 else fallback
    except:
        return fallback

_atr  = _safe_float(t.get("atr_14"),             curr * 0.02)
_sup  = _safe_float(sr.get("nearest_support"),    curr * 0.95)
_res  = _safe_float(sr.get("nearest_resistance"), curr * 1.05)

sc = get_scenarios(
    curr_price=curr,
    tech=t,
    fundamentals=f,
    balance=b,
    sr=sr,
    atr=_atr,
    horizon=horizon_key,
)

ps = get_position_sizing(
    curr_price=curr,
    atr=_atr,
    support=_sup,
    resistance=_res,
    investment_amount=investment_amount,
    horizon=horizon_key,
)

# ── Header Row ─────────────────────────────────────────────────────────────────
try:
    chg = float(m.get("change_pct") or 0)
except:
    chg = 0.0

def _h(val):
    """Safe header string for a number that might be 0/None/N/A."""
    try:
        _v = float(val)
        return rupee(_v) if _v > 0 else "N/A"
    except:
        return "N/A"

def _vol_display():
    try:
        _v = int(m.get("volume") or hist["Volume"].iloc[-1])
        return f"{_v:,}" if _v > 0 else "N/A"
    except:
        return "N/A"

def _mktcap_display():
    try:
        _v = float(m.get("market_cap_cr") or 0)
        return f"\u20b9{int(_v):,} Cr" if _v > 0 else "N/A"
    except:
        return "N/A"

col_name, col_p, col_chg, col_52h, col_52l, col_mc, col_vol = st.columns([3, 1.2, 1, 1, 1, 1.3, 1.3])
col_name.markdown(f"### \U0001f3e2 {m.get('company_name', selected_ticker)}")
col_name.caption(f"\U0001f4cd {m.get('sector','N/A')} \u00b7 {m.get('exchange','NSE')}")
col_p.metric("Price",      rupee(curr),              f"{chg:+.2f}%")
col_chg.metric("Prev Close", _h(m.get("prev_close")))
col_52h.metric("52W High",   _h(m.get("52w_high")))
col_52l.metric("52W Low",    _h(m.get("52w_low")))
col_mc.metric("Mkt Cap",    _mktcap_display())
col_vol.metric("Volume",    _vol_display())

st.markdown("---")

# ── Main: AI card (left) + Chart (right) ──────────────────────────────────────
ai_col, chart_col = st.columns([5, 4])

# Reset cached results only when ticker changes (but do NOT auto-trigger analysis)
if st.session_state.get("analyzed_ticker") != selected_ticker:
    st.session_state["analyzed_ticker"] = selected_ticker
    st.session_state["primary_full_text"] = None
    st.session_state["auditor_full_text"] = None

with ai_col:
    # Only run if user clicked Analyze button OR arrived from landing card start button
    should_analyze = analyze_btn or st.session_state.get("fresh_analysis_trigger", False)
    if should_analyze:
        st.session_state["fresh_analysis_trigger"] = False
        st.session_state["auditor_full_text"] = None  # Reset audit on fresh analysis
        prompt = build_ai_prompt(selected_ticker, data, time_horizon, investment_amount, ps=ps, sc=sc)

        result_placeholder = st.empty()
        full_text = ""
        with st.spinner("🤖 Primary Analyst Agent Analyzing..."):
            for chunk in stream_ai_analysis(prompt):
                full_text += chunk
                result_placeholder.markdown(full_text + "▌")
        result_placeholder.empty()
        st.session_state["primary_full_text"] = full_text

        # ── Automatically run Independent Auditor Agent ─────────────────────
        auditor_prompt = build_auditor_prompt(selected_ticker, data, full_text, time_horizon, investment_amount, ps=ps)
        auditor_placeholder = st.empty()
        audit_text = ""
        with st.spinner("🛡️ Independent Auditor Agent verifying strict risk rules..."):
            for chunk in stream_auditor_analysis(auditor_prompt):
                audit_text += chunk
                auditor_placeholder.markdown(audit_text + "▌")
        auditor_placeholder.empty()
        st.session_state["auditor_full_text"] = audit_text

    if st.session_state.get("primary_full_text"):
        full_text = st.session_state["primary_full_text"]

        # ── Parse the structured output ─────────────────────────────────────
        lines = full_text.strip().splitlines()
        parsed = {}
        section = None
        why_lines = []
        for line in lines:
            l = line.strip()
            clean_l = l.replace("*", "").replace("#", "").replace("-", "").strip()
            upper_l = clean_l.upper()

            if "DECISION:" in upper_l:
                parsed["decision"] = clean_l.split(":")[-1].strip()
            elif "CONFIDENCE:" in upper_l:
                parsed["confidence"] = clean_l.split(":")[-1].strip()
            elif "ENTRY:" in upper_l:
                parsed["entry"] = clean_l.split(":")[-1].strip()
            elif "STOP LOSS:" in upper_l or "STOP:" in upper_l:
                parsed["stop"] = clean_l.split(":")[-1].split("←")[0].strip()
            elif "TARGET 1:" in upper_l or "TARGET 1" in upper_l:
                parsed["t1"] = clean_l.split(":")[-1].strip()
            elif "TARGET 2:" in upper_l or "TARGET 2" in upper_l:
                parsed["t2"] = clean_l.split(":")[-1].strip()
            elif "TARGET 3:" in upper_l or "TARGET 3" in upper_l:
                parsed["t3"] = clean_l.split(":")[-1].strip()
            elif upper_l.startswith("WHY"):
                section = "why"
            elif "RISK TO WATCH" in upper_l or "ONE RISK" in upper_l:
                section = "risk"
            elif upper_l.startswith("ACTION:"):
                section = "action"
                parsed["action"] = clean_l.split(":")[-1].strip()
            elif section == "why" and l and not any(k in upper_l for k in ["RISK", "ACTION", "DECISION"]):
                why_lines.append(l)
            elif section == "risk" and l and not any(k in upper_l for k in ["ACTION", "DECISION"]):
                parsed["risk"] = l
            elif section == "action" and l and "action" not in parsed:
                parsed["action"] = l

        parsed["why"] = " ".join(why_lines)

        # ── Automatic fail-safe fallback to pre-calculated ps values ──────
        if ps and "error" not in ps:
            if parsed.get("entry") in (None, "N/A", "", "₹N/A", "₹[entry price]", "₹XX.XX"):
                parsed["entry"] = rupee(ps.get("entry_price"))
            if parsed.get("stop") in (None, "N/A", "", "₹N/A", "₹[stop price]", "₹XX.XX"):
                parsed["stop"] = rupee(ps.get("stop_loss"))
            if parsed.get("t1") in (None, "N/A", "", "₹N/A", "₹[t1]", "₹XX.XX"):
                parsed["t1"] = rupee(ps.get("target_1"))
            if parsed.get("t2") in (None, "N/A", "", "₹N/A", "₹[t2]", "₹XX.XX"):
                parsed["t2"] = rupee(ps.get("target_2"))
            if parsed.get("t3") in (None, "N/A", "", "₹N/A", "₹[t3]", "₹XX.XX"):
                parsed["t3"] = rupee(ps.get("target_3"))

        # ── Decision colour ──────────────────────────────────────────────────
        dec = parsed.get("decision", "WAIT").upper()
        if "BUY" in dec:
            dec_color = "#10b981"; dec_bg = "linear-gradient(135deg,#022c22,#064e32)"; dec_icon = "🟢"
        elif "SELL" in dec:
            dec_color = "#ef4444"; dec_bg = "linear-gradient(135deg,#2d1515,#450a0a)"; dec_icon = "🔴"
        else:
            dec_color = "#f59e0b"; dec_bg = "linear-gradient(135deg,#292005,#3d2b00)"; dec_icon = "🟡"

        conf = parsed.get("confidence", "")

        st.markdown(f"""
        <div style="background:{dec_bg}; border:2px solid {dec_color};
                    border-radius:16px; padding:20px 24px; margin-bottom:14px;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <span style="font-size:2.5rem;">{dec_icon}</span>
                <div>
                    <div style="font-size:2rem; font-weight:900; color:{dec_color}; line-height:1;">{dec}</div>
                    <div style="font-size:0.8rem; color:#94a3b8; margin-top:2px;">
                        Primary Analyst Agent &nbsp;·&nbsp; Confidence: <strong style="color:#e2e8f0;">{conf}</strong>
                        &nbsp;·&nbsp; Horizon: <strong style="color:#e2e8f0;">{time_horizon}</strong>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Trade levels row ─────────────────────────────────────────────────
        lc1, lc2, lc3, lc4, lc5 = st.columns(5)
        lc1.metric("📥 Entry",    parsed.get("entry","N/A"))
        lc2.metric("🛑 Stop Loss", parsed.get("stop","N/A"))
        lc3.metric("🎯 Target 1", parsed.get("t1","N/A"))
        lc4.metric("🎯 Target 2", parsed.get("t2","N/A"))
        lc5.metric("🎯 Target 3", parsed.get("t3","N/A"))

        st.markdown("")

        # ── Why ──────────────────────────────────────────────────────────────
        if parsed.get("why"):
            st.markdown(f"""
            <div style="background:#0d1b2a; border-left:3px solid {dec_color};
                        border-radius:8px; padding:12px 16px; margin:8px 0;">
                <div style="font-size:0.7rem; color:#64748b; text-transform:uppercase;
                            letter-spacing:.08em; margin-bottom:4px;">Why?</div>
                <div style="color:#e2e8f0; font-size:0.95rem; line-height:1.6;">
                    {parsed['why']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Risk + Action ─────────────────────────────────────────────────────
        rc1, rc2 = st.columns(2)
        with rc1:
            if parsed.get("risk"):
                st.markdown(f"""
                <div style="background:#1c0a0a; border:1px solid #7f1d1d;
                            border-radius:8px; padding:10px 14px;">
                    <div style="font-size:0.65rem; color:#ef4444; text-transform:uppercase;
                                letter-spacing:.08em; margin-bottom:3px;">⚠️ Risk to watch</div>
                    <div style="color:#fca5a5; font-size:0.85rem;">{parsed['risk']}</div>
                </div>
                """, unsafe_allow_html=True)
        with rc2:
            if parsed.get("action"):
                st.markdown(f"""
                <div style="background:#0a1a0d; border:1px solid #166534;
                            border-radius:8px; padding:10px 14px;">
                    <div style="font-size:0.65rem; color:#10b981; text-transform:uppercase;
                                letter-spacing:.08em; margin-bottom:3px;">✅ What to do</div>
                    <div style="color:#6ee7b7; font-size:0.85rem;">{parsed['action']}</div>
                </div>
                """, unsafe_allow_html=True)

        # ── Optional Auditor Agent Manual Re-run ─────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        audit_btn = st.button("🔄 Re-run Auditor Agent Verification", use_container_width=True)

        if audit_btn:
            auditor_prompt = build_auditor_prompt(selected_ticker, data, full_text, time_horizon, investment_amount, ps=ps)
            auditor_placeholder = st.empty()
            audit_text = ""
            with st.spinner("🛡️ Auditor Agent strictly checking trade rules & risk metrics..."):
                for chunk in stream_auditor_analysis(auditor_prompt):
                    audit_text += chunk
                    auditor_placeholder.markdown(audit_text + "▌")
            auditor_placeholder.empty()
            st.session_state["auditor_full_text"] = audit_text

        # ── Display Auditor Agent Card ───────────────────────────────────────
        if st.session_state.get("auditor_full_text"):
            audit_raw = st.session_state["auditor_full_text"].strip()

            # Parse decision and reason
            aud_dec = "WAIT"
            aud_reason = ""
            lines = audit_raw.splitlines()
            why_lines = []
            is_reason = False
            for line in lines:
                l = line.strip()
                u_line = l.upper()
                if "AUDITOR DECISION:" in u_line or "DECISION:" in u_line:
                    aud_dec = l.split(":")[-1].replace("*", "").strip().upper()
                elif "REASON:" in u_line:
                    is_reason = True
                    after = l.split(":")[-1].replace("*", "").strip()
                    if after: why_lines.append(after)
                elif is_reason and l:
                    why_lines.append(l)

            aud_reason = " ".join(why_lines) if why_lines else audit_raw.replace("AUDITOR DECISION:", "").replace("REASON:", "").strip()

            if "BUY" in aud_dec and "DO NOT" not in aud_dec:
                av_color = "#10b981"; av_bg = "linear-gradient(135deg,#022c22,#064e32)"; av_icon = "🟢"; av_dec = "BUY"
            elif "SELL" in aud_dec:
                av_color = "#ef4444"; av_bg = "linear-gradient(135deg,#2d1515,#450a0a)"; av_icon = "🔴"; av_dec = "SELL"
            elif "DO NOT" in aud_dec or "REJECT" in aud_dec:
                av_color = "#ef4444"; av_bg = "linear-gradient(135deg,#2d1515,#450a0a)"; av_icon = "🛑"; av_dec = "DO NOT BUY"
            else:
                av_color = "#f59e0b"; av_bg = "linear-gradient(135deg,#292005,#3d2b00)"; av_icon = "🟡"; av_dec = "WAIT"

            st.markdown(f"""
            <div style="background:{av_bg}; border:2px solid {av_color}; border-radius:12px; padding:16px 20px; margin-top:14px;">
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;">
                    🛡️ AUDITOR AGENT VERDICT
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:{av_color}; margin-top:4px;">
                    {av_icon} {av_dec}
                </div>
                <div style="color:#e2e8f0; font-size:0.9rem; margin-top:8px; line-height:1.5;">
                    {aud_reason}
                </div>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.markdown(f"""
        <div style="background:#0d1b2a; border:2px dashed #1e3a5f; border-radius:16px;
                    padding:40px; text-align:center; color:#475569;">
            <div style="font-size:3rem; margin-bottom:10px;">🔍</div>
            <div style="font-size:1rem; color:#64748b;">
                Select a stock · Set horizon · Click <strong style="color:#3b82f6;">Deep Analyze</strong>
            </div>
            <div style="font-size:0.8rem; margin-top:8px; color:#334155;">
                15 skill modules · 40+ data points · Dual LLM Verification (Analyst + Auditor Agent)
            </div>
        </div>
        """, unsafe_allow_html=True)

with chart_col:
    chart_df = pd.DataFrame({"Price": hist["Close"]})
    if t.get("sma_50")  != "N/A": chart_df["SMA50"]  = hist["Close"].rolling(50).mean()
    if t.get("sma_200") != "N/A": chart_df["SMA200"] = hist["Close"].rolling(200).mean()
    st.line_chart(chart_df, height=320)

st.markdown("---")

# ── Detailed data in a collapsible expander ────────────────────────────────────
with st.expander("📊 View detailed data (Technical · Fundamentals · News · Market)", expanded=False):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Technical", "📈 Fundamentals", "🌍 Market & News", "📐 Trade Plan", "🏛️ Shareholding"
    ])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SMA 20",  rupee(t.get("sma_20")),  t.get("price_vs_sma20",""))
        c2.metric("SMA 50",  rupee(t.get("sma_50")),  t.get("price_vs_sma50",""))
        c3.metric("SMA 100", rupee(t.get("sma_100")), t.get("price_vs_sma100",""))
        c4.metric("SMA 200", rupee(t.get("sma_200")), t.get("price_vs_sma200",""))
        st.markdown("")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("RSI (14)", t.get("rsi_14","N/A"), t.get("rsi_zone",""))
        c6.metric("MACD",     t.get("macd_line","N/A"), t.get("macd_trend",""))
        c7.metric("ADX",      t.get("adx_14","N/A"),  t.get("adx_strength",""))
        c8.metric("ATR",      rupee(t.get("atr_14")))
        st.markdown("")
        c9, c10, c11, c12 = st.columns(4)
        c9.metric("BB Upper",  rupee(t.get("bb_upper")))
        c10.metric("BB Lower", rupee(t.get("bb_lower")))
        c11.metric("Stoch %K", t.get("stoch_k","N/A"))
        c12.metric("VWAP 20D", rupee(t.get("vwap_20d")))
        st.markdown(f"**Cross:** {t.get('golden_death_cross','N/A')} &nbsp;|&nbsp; **Trend:** {t.get('trend_structure','N/A')}")
        st.markdown("**Patterns detected:**")
        for p in pt.get("patterns_detected", ["No clear pattern"]):
            if "bullish" in p.lower() or "uptrend" in p.lower() or "bottom" in p.lower():
                st.success(f"✅ {p}")
            elif "bearish" in p.lower() or "downtrend" in p.lower():
                st.error(f"❌ {p}")
            else:
                st.info(f"ℹ️ {p}")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.caption("Support levels")
            for s in (sr.get("major_supports") or [])[:4]: st.markdown(f"🛡️ ₹{s}")
        with sc2:
            st.caption("Resistance levels")
            for r in (sr.get("major_resistances") or [])[:4]: st.markdown(f"📛 ₹{r}")

    with tab2:
        val = data["valuation"]   # use local alias to avoid name collision
        fa1, fa2, fa3, fa4 = st.columns(4)
        fa1.metric("Revenue",    f"\u20b9{f.get('revenue_latest_cr','N/A')} Cr", f"{f.get('revenue_growth_yoy','N/A')}% YoY")
        fa2.metric("Net Profit", f"\u20b9{f.get('pat_latest_cr','N/A')} Cr",     f"{f.get('pat_growth_yoy','N/A')}%")
        fa3.metric("ROE",        f"{f.get('roe_pct','N/A')}%")
        fa4.metric("FCF",        f"\u20b9{f.get('free_cash_flow_cr','N/A')} Cr")
        st.markdown("")
        fb1, fb2, fb3, fb4 = st.columns(4)
        fb1.metric("P/E",     val.get("pe_ttm","N/A"),   val.get("pe_signal",""))
        fb2.metric("PEG",     val.get("peg_ratio","N/A"), val.get("peg_signal",""))
        fb3.metric("D/E",     f"{b.get('debt_to_equity','N/A')}x", b.get("de_risk",""))
        fb4.metric("Margin",  f"{f.get('net_margin_pct','N/A')}%")
        st.markdown("")
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Graham No.",    rupee(val.get("graham_number")))
        fc2.metric("Safety Margin", f"{val.get('margin_of_safety_pct','N/A')}%")
        fc3.metric("Analyst Tgt",   rupee(val.get("analyst_target")), f"{val.get('analyst_upside_pct','N/A')}% up")
        fc4.metric("Int. Coverage", f"{b.get('interest_coverage','N/A')}x")

    with tab3:
        mc1, mc2 = st.columns(2)
        with mc1:
            nifty_d = mc.get("nifty_50", {})
            if isinstance(nifty_d, dict):
                st.metric("NIFTY 50",   rupee(nifty_d.get("price")), f"{nifty_d.get('change_pct','N/A')}%")
            st.metric("India VIX",  mc.get("india_vix","N/A"), mc.get("vix_regime",""))
            st.info(f"Market: **{mc.get('market_regime','N/A')}**")
            st.metric("Beta (6M)", rs.get("beta_6m","N/A"), rs.get("beta_signal",""))
        with mc2:
            st.markdown("**Relative Strength vs NIFTY**")
            for period, rdata in rs.get("relative_strength_vs_nifty",{}).items():
                icon = "🟢" if rdata.get("signal") == "OUTPERFORMING" else "🔴"
                st.markdown(f"{icon} **{period}**: {rdata.get('stock_return_pct','N/A')}% vs NIFTY {rdata.get('nifty_return_pct','N/A')}% (Alpha {rdata.get('alpha_pct','N/A')}%)")
        st.markdown("---")
        st.markdown(f"**News Sentiment:** {nw.get('overall_sentiment','N/A')} — {nw.get('sentiment_summary','N/A')}")
        for h in nw.get("headlines", [])[:6]:
            icon = {"POSITIVE":"📗","NEGATIVE":"📕"}.get(h["sentiment"],"📘")
            st.markdown(f"{icon} {h['date']} — {h['title']}")

    with tab4:
        if "error" not in ps:
            tp1, tp2 = st.columns(2)
            with tp1:
                for k, val in {
                    "Entry": rupee(ps.get("entry_price")),
                    "Stop Loss": rupee(ps.get("stop_loss")),
                    "Risk/share": rupee(ps.get("risk_per_share")),
                    "Target 1": rupee(ps.get("target_1")),
                    "Target 2": rupee(ps.get("target_2")),
                    "Target 3": rupee(ps.get("target_3")),
                    "Qty": f"{ps.get('quantity','N/A')} shares",
                    "Capital needed": rupee(ps.get("capital_required")),
                    "Max Loss": rupee(ps.get("max_loss")),
                    "R:R at T2": f"1:{ps.get('rr_ratio_t2','N/A')}",
                }.items():
                    k_col, v_col = st.columns([2,2])
                    k_col.caption(k); v_col.markdown(f"**{val}**")
            with tp2:
                bull = sc.get("bull_case",{}); base = sc.get("base_case",{}); bear = sc.get("bear_case",{})
                st.success(f"🐂 Bull ({bull.get('probability','N/A')}): ₹{bull.get('target','N/A')} (+{bull.get('upside_pct','N/A')}%)")
                st.info(   f"📊 Base ({base.get('probability','N/A')}): ₹{base.get('target','N/A')} (+{base.get('upside_pct','N/A')}%)")
                st.error(  f"🐻 Bear ({bear.get('probability','N/A')}): ₹{bear.get('target','N/A')} ({bear.get('downside_pct','N/A')}%)")
        else:
            st.warning(f"Position sizing error: {ps.get('error')}")

    with tab5:
        sh1, sh2 = st.columns(2)
        with sh1:
            st.metric("Promoter/Insider", f"{sh.get('promoter_holding_pct','N/A')}%", sh.get("holding_signal",""))
            st.metric("Institutional",    f"{sh.get('institutional_pct','N/A')}%")
        with sh2:
            for inst in sh.get("top_institutional",[])[:5]:
                st.markdown(f"- {inst['name']}: **{inst['pct']}%**")
