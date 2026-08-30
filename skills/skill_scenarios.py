"""
SKILL: Scenarios
Generates Bull / Base / Bear case scenarios from collected data.
"""


def get_scenarios(
    curr_price: float,
    tech: dict,
    fundamentals: dict,
    balance: dict,
    sr: dict,
    atr: float,
    horizon: str = "1Y"
) -> dict:
    try:
        atr = float(atr) if atr and atr != "N/A" else curr_price * 0.02

        # Horizon multipliers for price targets
        horizon_mult = {"1M": 1, "3M": 2, "6M": 3.5, "1Y": 6}
        mult = horizon_mult.get(horizon, 6)

        # Resistance / Support
        res = sr.get("nearest_resistance", curr_price * 1.08)
        sup = sr.get("nearest_support",    curr_price * 0.92)
        res = float(res) if res != "N/A" else curr_price * 1.08
        sup = float(sup) if sup != "N/A" else curr_price * 0.92

        # Bull case: price reaches major resistance + fundamental tailwinds
        bull_target  = round(max(res, curr_price + atr * mult * 1.5), 2)
        bull_upside  = round((bull_target - curr_price) / curr_price * 100, 1)
        bull_trigger = "Price breaks above 200 SMA + high volume + positive news"

        # Base case: moderate move based on ATR
        base_target  = round(curr_price + atr * mult, 2)
        base_upside  = round((base_target - curr_price) / curr_price * 100, 1)
        base_trigger = "Normal consolidation then gradual move up with market"

        # Bear case: breaks support
        bear_target   = round(min(sup, curr_price - atr * mult * 0.8), 2)
        bear_downside = round((bear_target - curr_price) / curr_price * 100, 1)
        bear_trigger  = "Market weakness + breaks key support + negative news"

        # Assign probabilities based on trend
        trend_above_200 = tech.get("price_vs_sma200", "BELOW") == "ABOVE"
        rsi = tech.get("rsi_14", "N/A")
        macd_bullish = tech.get("macd_trend", "BEARISH") == "BULLISH"

        bull_signals = sum([
            trend_above_200,
            macd_bullish,
            rsi != "N/A" and 45 < float(rsi) < 70 if rsi != "N/A" else False,
        ])

        if bull_signals >= 2:
            bull_prob, base_prob, bear_prob = 50, 35, 15
        elif bull_signals == 1:
            bull_prob, base_prob, bear_prob = 30, 40, 30
        else:
            bull_prob, base_prob, bear_prob = 15, 35, 50

        return {
            "bull_case": {
                "target":      bull_target,
                "upside_pct":  bull_upside,
                "probability": f"{bull_prob}%",
                "trigger":     bull_trigger,
            },
            "base_case": {
                "target":      base_target,
                "upside_pct":  base_upside,
                "probability": f"{base_prob}%",
                "trigger":     base_trigger,
            },
            "bear_case": {
                "target":     bear_target,
                "downside_pct": bear_downside,
                "probability": f"{bear_prob}%",
                "trigger":    bear_trigger,
            },
        }
    except Exception as e:
        return {"error": str(e)}
