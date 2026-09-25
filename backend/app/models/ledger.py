from datetime import datetime, date
import uuid
from sqlalchemy import Boolean, DateTime, String, ForeignKey, Numeric, UniqueConstraint, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database.connection import Base

class PaperAccount(Base):
    __tablename__ = "paper_accounts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    base_currency: Mapped[str] = mapped_column(String(10), default="INR")
    starting_balance: Mapped[float] = mapped_column(Numeric(18, 2), default=100000.0)
    current_status: Mapped[str] = mapped_column(String(50), default="active")
    
    # State tracking that doesn't violate strict ledger for cash
    locked_margin: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00)
    daily_loss_limit: Mapped[float] = mapped_column(Numeric(18, 2), default=5000.00)
    daily_realized_loss: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00)
    last_reset_date: Mapped[date] = mapped_column(Date, default=date.today)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class PaperLedgerEntry(Base):
    __tablename__ = "paper_ledger_entries"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. INITIAL_BALANCE, TRADE_EXECUTION, DEPOSIT, WITHDRAWAL
    amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False) # positive for deposit/credit, negative for withdrawal/debit
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[str | None] = mapped_column(String(100))
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("instruments.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class PaperOrder(Base):
    __tablename__ = "paper_orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False) # BUY, SELL
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(18, 6)) # Execution price
    order_type: Mapped[str] = mapped_column(String(20), nullable=False) # MARKET, LIMIT
    limit_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING") # PENDING, FILLED, CANCELLED, REJECTED
    brokerage: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    stt: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    slippage: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    net_amount: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    signal_relation: Mapped[str | None] = mapped_column(String(50)) # AGREEMENT, AGAINST, INDEPENDENT
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class PaperPosition(Base):
    __tablename__ = "paper_positions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    avg_buy_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 6), default=0.00)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_paper_pos_user_symbol"),)
