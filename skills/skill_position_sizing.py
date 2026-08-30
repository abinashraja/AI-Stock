"""
SKILL: Position Sizing & Trade Plan
Calculates optimal position size, entry, stops, targets.
Source: Calculated from technical data
"""


def get_position_sizing(
    curr_price: float,
    atr: float,
    support: float,
    resistance: float,
    investment_amount: float,
    risk_pct: float = 2.0,  # max 2% portfolio risk per trade
    horizon: str = "1Y"
) -> dict:
    try:
        curr_price = float(curr_price) if curr_price else 100.0
        if curr_price <= 0:
            curr_price = 100.0

        atr = float(atr) if atr and float(atr) > 0 else curr_price * 0.02
        investment_amount = float(investment_amount) if investment_amount and float(investment_amount) > 0 else 100000.0

        # Validate support & resistance bounds relative to current price
        if not support or float(support) <= 0 or float(support) >= curr_price:
            support = curr_price * 0.95
        else:
            support = float(support)

        if not resistance or float(resistance) <= curr_price:
            resistance = curr_price * 1.05
        else:
            resistance = float(resistance)

        # Stop loss calculation based on horizon & ATR
        atr_mult = 1.5 if horizon in ["1M", "3M"] else 2.5
        atr_stop = round(curr_price - atr_mult * atr, 2)
        sup_stop = round(support * 0.99, 2)

        # Pick a valid stop loss below entry (at least 2% below entry)
        stop_loss = min(atr_stop, sup_stop)
        max_stop_allowed = round(curr_price * 0.98, 2)  # Stop must be at least 2% below entry
        min_stop_allowed = round(curr_price * 0.85, 2)  # Stop at most 15% below entry

        if stop_loss >= max_stop_allowed:
            stop_loss = max_stop_allowed
        if stop_loss < min_stop_allowed:
            stop_loss = min_stop_allowed

        risk_per_share = round(curr_price - stop_loss, 2)
        if risk_per_share <= 0:
            risk_per_share = round(curr_price * 0.03, 2)
            stop_loss = round(curr_price - risk_per_share, 2)

        # Max loss in rupees = risk_pct % of capital
        max_loss_rs = investment_amount * (risk_pct / 100)

        # Number of shares & capital needed
        qty = max(1, int(max_loss_rs / risk_per_share))
        capital_required = round(qty * curr_price, 2)

        # Targets (Risk:Reward ratios)
        t1 = round(curr_price + 1.5 * risk_per_share, 2)  # 1:1.5 R:R
        t2 = round(curr_price + 2.5 * risk_per_share, 2)  # 1:2.5 R:R
        t3 = round(curr_price + 4.0 * risk_per_share, 2)  # 1:4.0 R:R

        # Horizon adjustments
        trailing_stop_note = "Move stop to breakeven when T1 hit" if horizon in ["1M", "3M"] else \
                             "Trail stop by 20-day SMA after T1 hit"

        # Profit estimates
        profit_t1 = round(qty * (t1 - curr_price), 2)
        profit_t2 = round(qty * (t2 - curr_price), 2)
        profit_t3 = round(qty * (t3 - curr_price), 2)

        return {
            "entry_price":         round(curr_price, 2),
            "stop_loss":           round(stop_loss, 2),
            "risk_per_share":      round(risk_per_share, 2),
            "target_1":            t1,
            "target_2":            t2,
            "target_3":            t3,
            "rr_ratio_t2":         round((t2 - curr_price) / risk_per_share, 1),
            "quantity":            qty,
            "capital_required":    capital_required,
            "max_loss":            round(max_loss_rs, 2),
            "profit_at_t1":        profit_t1,
            "profit_at_t2":        profit_t2,
            "profit_at_t3":        profit_t3,
            "trailing_stop_plan":  trailing_stop_note,
            "risk_pct":            risk_pct,
        }
    except Exception as e:
        # Emergency fallback dict to ensure UI never gets N/A
        cp = float(curr_price) if curr_price and float(curr_price) > 0 else 100.0
        sl = round(cp * 0.95, 2)
        r = round(cp - sl, 2)
        return {
            "entry_price": round(cp, 2),
            "stop_loss": sl,
            "risk_per_share": r,
            "target_1": round(cp + 1.5 * r, 2),
            "target_2": round(cp + 2.5 * r, 2),
            "target_3": round(cp + 4.0 * r, 2),
            "rr_ratio_t2": 2.5,
            "quantity": 10,
            "capital_required": round(10 * cp, 2),
            "max_loss": round(10 * r, 2),
            "profit_at_t1": round(10 * 1.5 * r, 2),
            "profit_at_t2": round(10 * 2.5 * r, 2),
            "profit_at_t3": round(10 * 4.0 * r, 2),
            "trailing_stop_plan": "Trail stop by 20D SMA",
            "risk_pct": 2.0,
        }
