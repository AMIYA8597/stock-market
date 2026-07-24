"""Transaction cost model for Indian equity delivery backtests and paper trading."""

from __future__ import annotations


def compute_indian_costs(
    gross_amount: float,
    side: str,
    is_delivery: bool = True,
    slippage_pct: float = 0.0005,
) -> dict[str, float]:
    """Compute precise transaction costs for NSE Equity.

    Args:
        gross_amount: Price * Quantity (absolute value).
        side: "BUY" or "SELL".
        is_delivery: True for equity delivery, False for intraday (MIS).
        slippage_pct: Assumed slippage percentage.

    Returns:
        Dictionary containing individual tax components and `total_cost`.
    """
    side = side.upper()

    # 1. Brokerage
    # Discount broker assumed: ₹20 or 0.1% (Delivery) / 0.03% (Intraday) whichever is lower.
    if is_delivery:
        brokerage = min(20.0, 0.001 * gross_amount)
    else:
        brokerage = min(20.0, 0.0003 * gross_amount)

    # 2. STT (Securities Transaction Tax)
    # Delivery: 0.1% on buy & sell.
    # Intraday: 0.025% on sell only.
    if is_delivery:
        stt = 0.001 * gross_amount
    else:
        stt = 0.00025 * gross_amount if side == "SELL" else 0.0

    # 3. Exchange Transaction Charge (NSE)
    # Approx 0.00345% (or 0.00325% + GST etc, we use 0.00345%)
    txn_charge = 0.0000345 * gross_amount

    # 4. SEBI Turnover Fee
    # ₹10 per crore
    sebi_fee = 0.000001 * gross_amount

    # 5. GST (18% on Brokerage + Txn Charge + SEBI Fee)
    gst = 0.18 * (brokerage + txn_charge + sebi_fee)

    # 6. Stamp Duty
    # Delivery: 0.015% on BUY side. Intraday: 0.003% on BUY side.
    stamp_duty = 0.0
    if side == "BUY":
        stamp_duty = (0.00015 * gross_amount) if is_delivery else (0.00003 * gross_amount)

    # 7. Slippage
    slippage = slippage_pct * gross_amount

    total_cost = brokerage + stt + txn_charge + sebi_fee + gst + stamp_duty + slippage

    return {
        "brokerage": brokerage,
        "stt": stt,
        "txn_charge": txn_charge,
        "sebi_fee": sebi_fee,
        "gst": gst,
        "stamp_duty": stamp_duty,
        "slippage": slippage,
        "total_cost": total_cost,
    }
