"""Backtest job results and metrics model.

Asynchronous backtest execution results including walk-forward analysis,
Monte Carlo simulation, and full performance metrics.
"""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import DateTime, Date, Numeric, String, UUID as SQLA_UUID, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class BacktestJob(Base):
    """Asynchronous backtest job and results.
    
    Fields:
        id (UUID): Unique job identifier, primary key.
        user_id (UUID): Foreign key to User.
        strategy_name (str): Name of strategy being backtested.
        strategy_params (dict): Strategy parameter JSON.
        universe (list): List of symbol tickers in backtest universe.
        date_from (date): Backtest start date.
        date_to (date): Backtest end date.
        initial_capital (Decimal): Starting capital.
        status (str): Job status (PENDING, RUNNING, DONE, FAILED).
        results (dict): Complete results JSON (equity curve, trades, metrics).
        created_at (datetime): When job was submitted (UTC).
        completed_at (datetime): When job completed (UTC, nullable).
    
    Status Values:
        - PENDING: Job queued, not yet running
        - RUNNING: Currently executing backtest
        - DONE: Completed successfully
        - FAILED: Execution error
    """

    __tablename__ = "backtest_jobs"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique backtest job identifier",
    )
    user_id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="Foreign key to users",
    )
    strategy_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Strategy name (ensemble, tft_only, ma_crossover, rsi_mrv, custom)",
    )
    strategy_params: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="Strategy parameters as JSONB",
    )
    universe: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        doc="List of symbol tickers in universe",
    )
    date_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Backtest start date",
    )
    date_to: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Backtest end date",
    )
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(16, 2),
        nullable=False,
        doc="Initial capital",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default="PENDING",
        nullable=False,
        index=True,
        doc="Job status (PENDING, RUNNING, DONE, FAILED)",
    )
    results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Complete results: metrics, equity curve, trades, walk-forward, monte carlo",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Job submission timestamp (UTC)",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Job completion timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<BacktestJob(id={self.id}, strategy='{self.strategy_name}', status='{self.status}')>"
