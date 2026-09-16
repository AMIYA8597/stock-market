from research.backtesting.cost_model import compute_indian_costs


def test_compute_indian_costs():
    """Verify brokerage cap (₹20), STT, exchange fees, SEBI, GST, stamp duty match hand-calculated results."""
    # Test 1: Small trade where 0.1% is less than ₹20
    # Gross = 10000 (e.g., 100 shares @ 100)
    cost = compute_indian_costs(
        gross_amount=10000.0, side="BUY", is_delivery=True, slippage_pct=0.0
    )

    turnover = 10000.0
    expected_brokerage = min(20.0, turnover * 0.001)  # 10.0
    expected_stt = turnover * 0.001  # 10.0 for BUY delivery
    expected_exchange_fee = turnover * 0.0000345  # 0.345
    expected_sebi_fee = turnover * 0.000001  # 0.01

    expected_gst = (
        expected_brokerage + expected_exchange_fee + expected_sebi_fee
    ) * 0.18  # (10 + 0.345 + 0.01) * 0.18 = 1.8639
    expected_stamp_duty = turnover * 0.00015  # 1.5
    expected_slippage = 0.0

    expected_total = (
        expected_brokerage
        + expected_stt
        + expected_exchange_fee
        + expected_sebi_fee
        + expected_gst
        + expected_stamp_duty
        + expected_slippage
    )

    assert cost["brokerage"] == expected_brokerage
    assert cost["stt"] == expected_stt
    assert cost["txn_charge"] == expected_exchange_fee
    assert cost["sebi_fee"] == expected_sebi_fee
    assert round(cost["gst"], 4) == round(expected_gst, 4)
    assert cost["stamp_duty"] == expected_stamp_duty
    assert round(cost["total_cost"], 4) == round(expected_total, 4)

    # Test 2: Large trade where brokerage caps at ₹20
    # Gross = 1,000,000
    cost2 = compute_indian_costs(
        gross_amount=1000000.0, side="SELL", is_delivery=True, slippage_pct=0.0
    )
    turnover2 = 1000000.0
    expected_brokerage2 = 20.0
    expected_stt2 = turnover2 * 0.001
    expected_exchange_fee2 = turnover2 * 0.0000345
    expected_sebi_fee2 = turnover2 * 0.000001
    expected_gst2 = (expected_brokerage2 + expected_exchange_fee2 + expected_sebi_fee2) * 0.18
    expected_stamp_duty2 = 0.0  # Stamp duty only applies on BUY
    expected_slippage2 = 0.0

    expected_total2 = (
        expected_brokerage2
        + expected_stt2
        + expected_exchange_fee2
        + expected_sebi_fee2
        + expected_gst2
        + expected_stamp_duty2
        + expected_slippage2
    )

    assert cost2["brokerage"] == expected_brokerage2
    assert round(cost2["total_cost"], 4) == round(expected_total2, 4)
