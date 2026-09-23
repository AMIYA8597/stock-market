import re

with open("backend/app/services/paper_trading.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace:
#         if filled_count > 0:
#             await db.commit()
#         return filled_count
# with ledger logic inside the loop!

# Let's just find the loop logic:
#             order.timestamp = datetime.now(UTC)
#             filled_count += 1
#             logger.info(
#                 f"FILLED pending limit order {order.id} for user {order.user_id} at {execute_price}"
#             )

replacement = """
            order.timestamp = datetime.now(UTC)
            filled_count += 1
            logger.info(
                f"FILLED pending limit order {order.id} for user {order.user_id} at {execute_price}"
            )

            account_stmt = select(PaperAccount).where(PaperAccount.user_id == order.user_id)
            account_res = await db.execute(account_stmt)
            account = account_res.scalar_one_or_none()
            if account:
                entry_amount = -float(net_amount) if order.side == "BUY" else float(net_amount)
                ledger_entry = PaperLedgerEntry(
                    account_id=account.id,
                    entry_type="TRADE_EXECUTION",
                    amount=entry_amount,
                    currency="INR",
                    reference_type="PAPER_ORDER",
                    reference_id=str(order.id)
                )
                db.add(ledger_entry)
"""

code = code.replace(
    """            order.timestamp = datetime.now(UTC)
            filled_count += 1
            logger.info(
                f"FILLED pending limit order {order.id} for user {order.user_id} at {execute_price}"
            )""",
    replacement
)

with open("backend/app/services/paper_trading.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patched paper_trading.py for LIMIT order ledger entries.")
