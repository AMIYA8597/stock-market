from __future__ import annotations

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.connection import Base
from app.services.paper_trading import PaperTradingService


@pytest.mark.asyncio
async def test_paper_trading_workflow():
    # 1. Create a clean, private in-memory SQLite database for the unit test
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        # Only create the paper trading tables to avoid SQLite rendering errors on PostgreSQL-only columns (like ARRAY)
        await conn.run_sync(lambda connection: Base.metadata.create_all(
            bind=connection,
            tables=[
                Base.metadata.tables["paper_wallets"],
                Base.metadata.tables["paper_positions"],
                Base.metadata.tables["paper_orders"]
            ]
        ))
        
    async with async_session() as session:
        user_id = "test-unit-user"
        
        # Test 1: get_or_create_wallet
        wallet = await PaperTradingService.get_or_create_wallet(session, user_id)
        assert wallet.user_id == user_id
        assert wallet.balance == Decimal("100000.00")
        assert wallet.realized_pnl == Decimal("0.00")
        
        # Test 2: place MARKET BUY order (conftest.py mock quote is ₹2521.30)
        order = await PaperTradingService.place_order(
            db=session,
            user_id=user_id,
            symbol="RELIANCE.NS",
            side="BUY",
            quantity=5.0,
            order_type="MARKET"
        )
        assert order.status == "FILLED"
        assert order.symbol == "RELIANCE.NS"
        assert order.side == "BUY"
        assert order.quantity == Decimal("5.00")
        assert order.price > Decimal("2521.30") # due to slippage
        
        # Verify wallet cash is deducted
        wallet = await PaperTradingService.get_or_create_wallet(session, user_id)
        assert wallet.balance < Decimal("100000.00")
        
        # Verify position is created
        positions = await PaperTradingService.get_positions(session, user_id)
        assert len(positions) == 1
        assert positions[0]["symbol"] == "RELIANCE.NS"
        assert positions[0]["quantity"] == 5.0
        
        # Test 3: place MARKET SELL order
        sell_order = await PaperTradingService.place_order(
            db=session,
            user_id=user_id,
            symbol="RELIANCE.NS",
            side="SELL",
            quantity=2.0,
            order_type="MARKET"
        )
        assert sell_order.status == "FILLED"
        assert sell_order.side == "SELL"
        assert sell_order.quantity == Decimal("2.00")
        
        # Verify position quantity decreased
        positions = await PaperTradingService.get_positions(session, user_id)
        assert len(positions) == 1
        assert positions[0]["quantity"] == 3.0
        
        # Test 4: Risk guardrail (exceed 50% equity)
        # Total equity is ~100k, 50% is 50k. Ordering 30 shares @ 2521.30 is ₹75,639, exceeding risk limit.
        with pytest.raises(ValueError) as exc_info:
            await PaperTradingService.place_order(
                db=session,
                user_id=user_id,
                symbol="RELIANCE.NS",
                side="BUY",
                quantity=30.0,
                order_type="MARKET"
            )
        assert "exceeds risk limit" in str(exc_info.value)
        
        # Test 5: Daily Loss Circuit Breaker trigger
        # Manually force daily loss to exceed limit
        wallet.daily_realized_loss = Decimal("6000.00")
        await session.commit()
        
        with pytest.raises(ValueError) as cb_exc:
            await PaperTradingService.place_order(
                db=session,
                user_id=user_id,
                symbol="RELIANCE.NS",
                side="BUY",
                quantity=1.0,
                order_type="MARKET"
            )
        assert "blocked" in str(cb_exc.value) or "circuit breaker" in str(cb_exc.value).lower()
        
        # Test 6: Reset Wallet
        pnl = await PaperTradingService.reset_wallet(session, user_id)
        assert pnl["cash_balance"] == 100000.00
        assert pnl["total_holdings_value"] == 0.00
        
        positions = await PaperTradingService.get_positions(session, user_id)
        assert len(positions) == 0
        
    await engine.dispose()
