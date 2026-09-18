import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.models.paper_trading import PaperOrder, PaperPosition, PaperWallet
from app.services.paper_trading import PaperTradingService


class MockScalarResult:
    def __init__(self, items):
        self.items = items
    def scalar_one_or_none(self):
        return self.items[0] if self.items else None
    def scalars(self):
        class MockScalars:
            def __init__(self, it):
                self.it = it
            def all(self):
                return self.it
        return MockScalars(self.items)

@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db

@pytest.fixture
def test_wallet():
    return PaperWallet(
        id=uuid.uuid4(),
        user_id="test_user",
        balance=Decimal("100000.00"),
        realized_pnl=Decimal("0.00"),
        daily_loss_limit=Decimal("5000.00"),
        last_reset_date=date.today(),
        daily_realized_loss=Decimal("0.00"),
        locked_margin=Decimal("0.00"),
    )

@pytest.mark.asyncio
async def test_get_or_create_wallet_existing(mock_db, test_wallet):
    mock_db.execute.return_value = MockScalarResult([test_wallet])
    wallet = await PaperTradingService.get_or_create_wallet(mock_db, "test_user", for_update=True)
    assert wallet.balance == Decimal("100000.00")
    assert wallet.user_id == "test_user"

@pytest.mark.asyncio
async def test_get_or_create_wallet_new(mock_db):
    mock_db.execute.return_value = MockScalarResult([])
    wallet = await PaperTradingService.get_or_create_wallet(mock_db, "new_user")
    assert wallet.user_id == "new_user"
    assert wallet.balance == Decimal("100000.00")

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
async def test_get_positions(mock_get_quote, mock_db):
    pos = PaperPosition(
        id=uuid.uuid4(),
        user_id="test_user",
        symbol="RELIANCE",
        quantity=Decimal("10.0"),
        avg_buy_price=Decimal("2000.00"),
        realized_pnl=Decimal("100.00")
    )
    mock_db.execute.return_value = MockScalarResult([pos])
    mock_get_quote.return_value = {"price": 2100.0}

    positions = await PaperTradingService.get_positions(mock_db, "test_user")
    assert len(positions) == 1
    p = positions[0]
    assert p["current_price"] == 2100.0
    assert p["unrealized_pnl"] == 1000.0

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
async def test_get_positions_exception(mock_get_quote, mock_db):
    pos = PaperPosition(
        id=uuid.uuid4(),
        user_id="test_user",
        symbol="RELIANCE",
        quantity=Decimal("10.0"),
        avg_buy_price=Decimal("2000.00"),
        realized_pnl=Decimal("100.00")
    )
    mock_db.execute.return_value = MockScalarResult([pos])
    mock_get_quote.side_effect = Exception("API error")

    positions = await PaperTradingService.get_positions(mock_db, "test_user")
    assert positions[0]["current_price"] == 2000.0
    assert positions[0]["unrealized_pnl"] == 0.0

@pytest.mark.asyncio
@patch("app.services.paper_trading.PaperTradingService.get_positions", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_get_pnl(mock_get_wallet, mock_get_positions, mock_db, test_wallet):
    test_wallet.last_reset_date = date.today() - timedelta(days=1)
    mock_get_wallet.return_value = test_wallet
    mock_get_positions.return_value = [
        {"current_price": 2100.0, "quantity": 10.0, "unrealized_pnl": 1000.0}
    ]

    pnl = await PaperTradingService.get_pnl(mock_db, "test_user")
    assert pnl["cash_balance"] == 100000.0
    assert pnl["total_holdings_value"] == 21000.0
    assert pnl["total_equity"] == 121000.0

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.MarketDataService._normalize_symbol")
@patch("app.services.paper_trading.compute_indian_costs")
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_market_buy_new_position(mock_get_wallet, mock_get_pnl, mock_compute, mock_norm, mock_get_quote, mock_db, test_wallet):
    mock_get_wallet.return_value = test_wallet
    mock_get_pnl.return_value = {"total_equity": 100000.0}
    mock_norm.return_value = "RELIANCE"
    mock_get_quote.return_value = {"price": 1000.0}
    mock_compute.return_value = {"brokerage": 20.0, "stt": 1.0, "slippage": 5.0, "txn_charge": 0.5, "sebi_fee": 0.1, "gst": 3.0, "stamp_duty": 0.1}

    # db.execute is called for finding position. return none
    mock_db.execute.return_value = MockScalarResult([])

    order = await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "BUY", 10.0, "MARKET")
    assert order.status == "FILLED"

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.MarketDataService._normalize_symbol")
@patch("app.services.paper_trading.compute_indian_costs")
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_market_buy_existing_position(mock_get_wallet, mock_get_pnl, mock_compute, mock_norm, mock_get_quote, mock_db, test_wallet):
    mock_get_wallet.return_value = test_wallet
    mock_get_pnl.return_value = {"total_equity": 100000.0}
    mock_norm.return_value = "RELIANCE"
    mock_get_quote.return_value = {"price": 1000.0}
    mock_compute.return_value = {"brokerage": 20.0, "stt": 1.0, "slippage": 5.0, "txn_charge": 0.5, "sebi_fee": 0.1, "gst": 3.0, "stamp_duty": 0.1}

    pos = PaperPosition(quantity=Decimal("5.0"), avg_buy_price=Decimal("900.0"))
    mock_db.execute.return_value = MockScalarResult([pos])

    order = await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "BUY", 10.0, "MARKET")
    assert pos.quantity == Decimal("15.0")

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.MarketDataService._normalize_symbol")
@patch("app.services.paper_trading.compute_indian_costs")
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_market_sell(mock_get_wallet, mock_get_pnl, mock_compute, mock_norm, mock_get_quote, mock_db, test_wallet):
    mock_get_wallet.return_value = test_wallet
    mock_get_pnl.return_value = {"total_equity": 100000.0}
    mock_norm.return_value = "RELIANCE"
    mock_get_quote.return_value = {"price": 1000.0}
    mock_compute.return_value = {"brokerage": 20.0, "stt": 1.0, "slippage": 5.0, "txn_charge": 0.5, "sebi_fee": 0.1, "gst": 3.0, "stamp_duty": 0.1}

    pos = PaperPosition(quantity=Decimal("15.0"), avg_buy_price=Decimal("900.0"), realized_pnl=Decimal("0.0"))
    mock_db.execute.return_value = MockScalarResult([pos])

    order = await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "SELL", 10.0, "MARKET")
    assert pos.quantity == Decimal("5.0")

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.MarketDataService._normalize_symbol")
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_limit_buy(mock_get_wallet, mock_get_pnl, mock_norm, mock_get_quote, mock_db, test_wallet):
    mock_get_wallet.return_value = test_wallet
    mock_get_pnl.return_value = {"total_equity": 100000.0}
    mock_norm.return_value = "RELIANCE"
    mock_get_quote.return_value = {"price": 1000.0}

    order = await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "BUY", 10.0, "LIMIT", limit_price=900.0)
    assert order.status == "PENDING"

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.MarketDataService._normalize_symbol")
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_limit_sell(mock_get_wallet, mock_get_pnl, mock_norm, mock_get_quote, mock_db, test_wallet):
    mock_get_wallet.return_value = test_wallet
    mock_get_pnl.return_value = {"total_equity": 100000.0}
    mock_norm.return_value = "RELIANCE"
    mock_get_quote.return_value = {"price": 1000.0}

    pos = PaperPosition(quantity=Decimal("15.0"), avg_buy_price=Decimal("900.0"), realized_pnl=Decimal("0.0"))
    mock_db.execute.return_value = MockScalarResult([pos])

    order = await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "SELL", 10.0, "LIMIT", limit_price=1100.0)
    assert order.status == "PENDING"

@pytest.mark.asyncio
async def test_place_order_validations(mock_db):
    with pytest.raises(ValueError, match="Side must be BUY or SELL"):
        await PaperTradingService.place_order(mock_db, "t", "R", "INVALID", 10.0, "MARKET")
    with pytest.raises(ValueError, match="Order type must be MARKET or LIMIT"):
        await PaperTradingService.place_order(mock_db, "t", "R", "BUY", 10.0, "INVALID")
    with pytest.raises(ValueError, match="Quantity must be greater than zero"):
        await PaperTradingService.place_order(mock_db, "t", "R", "BUY", 0.0, "MARKET")

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.MarketDataService._normalize_symbol")
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_risk_limit(mock_get_wallet, mock_get_pnl, mock_norm, mock_get_quote, mock_db, test_wallet):
    mock_get_wallet.return_value = test_wallet
    mock_get_pnl.return_value = {"total_equity": 100000.0}
    mock_norm.return_value = "RELIANCE"
    mock_get_quote.return_value = {"price": 60000.0}

    with pytest.raises(ValueError, match="Order size .* exceeds risk limit"):
        await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "BUY", 1.0, "MARKET")

@pytest.mark.asyncio
@patch("app.services.paper_trading.MarketDataService.get_quote", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_place_order_circuit_breaker(mock_get_wallet, mock_get_pnl, mock_get_quote, mock_db, test_wallet):
    test_wallet.daily_realized_loss = Decimal("6000.00")
    mock_get_wallet.return_value = test_wallet

    with pytest.raises(ValueError, match="Daily loss limit circuit breaker triggered"):
        await PaperTradingService.place_order(mock_db, "test_user", "RELIANCE", "BUY", 1.0, "MARKET")

@pytest.mark.asyncio
@patch("app.services.paper_trading.compute_indian_costs")
@patch("app.services.paper_trading.PaperTradingService.get_or_create_wallet", new_callable=AsyncMock)
async def test_check_and_execute_limit_orders(mock_get_wallet, mock_compute, mock_db, test_wallet):
    order = PaperOrder(
        id=uuid.uuid4(),
        user_id="test_user",
        symbol="RELIANCE",
        side="BUY",
        limit_price=Decimal("900.00"),
        quantity=Decimal("10.0"),
        status="PENDING"
    )
    # mock_db.execute is called twice: first for finding orders, second for finding position
    mock_db.execute.side_effect = [
        MockScalarResult([order]), # For orders
        MockScalarResult([])       # For position (returns none)
    ]
    mock_get_wallet.return_value = test_wallet
    mock_compute.return_value = {"brokerage": 20.0, "stt": 1.0, "slippage": 5.0, "txn_charge": 0.5, "sebi_fee": 0.1, "gst": 3.0, "stamp_duty": 0.1}

    count = await PaperTradingService.check_and_execute_limit_orders(mock_db, "RELIANCE", Decimal("800.00"))
    assert count == 1
    assert order.status == "FILLED"

@pytest.mark.asyncio
async def test_get_history(mock_db):
    order = PaperOrder(
        id=uuid.uuid4(),
        symbol="RELIANCE",
        side="BUY",
        quantity=Decimal("10.0"),
        price=Decimal("1000.0"),
        order_type="MARKET",
        status="FILLED",
        brokerage=Decimal("20.0"),
        stt=Decimal("1.0"),
        slippage=Decimal("5.0"),
        net_amount=Decimal("10026.0"),
        signal_relation="INDEPENDENT",
        timestamp=datetime.now(UTC),
        limit_price=None
    )
    mock_db.execute.return_value = MockScalarResult([order])
    history = await PaperTradingService.get_history(mock_db, "test_user")
    assert len(history) == 1
    assert history[0]["symbol"] == "RELIANCE"

@pytest.mark.asyncio
@patch("app.services.paper_trading.PaperTradingService.get_pnl", new_callable=AsyncMock)
async def test_reset_wallet(mock_get_pnl, mock_db, test_wallet):
    # db execute is called multiple times (delete positions, delete orders, select wallet)
    mock_db.execute.side_effect = [
        None, # delete pos
        None, # delete orders
        MockScalarResult([test_wallet]) # select wallet
    ]
    mock_get_pnl.return_value = {"cash_balance": 100000.0}

    res = await PaperTradingService.reset_wallet(mock_db, "test_user")
    assert test_wallet.balance == Decimal("100000.00")
