import re

with open("backend/app/services/paper_trading.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace:
#         db.add(new_order)
#         await db.commit()
#         await db.refresh(new_order)
# with double entry ledger inserts:

ledger_code = """
        db.add(new_order)
        await db.flush()  # So we get new_order.id

        account_stmt = select(PaperAccount).where(PaperAccount.user_id == user_id)
        account_res = await db.execute(account_stmt)
        account = account_res.scalar_one_or_none()
        
        if account:
            # Add double entry
            entry_amount = -float(net_amount) if side == "BUY" else float(net_amount)
            ledger_entry = PaperLedgerEntry(
                account_id=account.id,
                entry_type="TRADE_EXECUTION",
                amount=entry_amount,
                currency="INR",
                reference_type="PAPER_ORDER",
                reference_id=str(new_order.id)
            )
            db.add(ledger_entry)

        await db.commit()
        await db.refresh(new_order)
"""

code = code.replace(
    "        db.add(new_order)\n        await db.commit()\n        await db.refresh(new_order)",
    ledger_code
)

with open("backend/app/services/paper_trading.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patched paper_trading.py for MARKET order ledger entries.")
