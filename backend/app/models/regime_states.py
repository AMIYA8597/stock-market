"""HMM regime detection output model.

Market regime classification (bull, bear, sideways, crisis) with
state probabilities and conditional volatility forecasts.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ARRAY, DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class RegimeState(Base):
    """Hidden Markov Model regime detection output.

    Fields:
        time (datetime): Regime timestamp (UTC), primary key.
        viterbi_state (int): Most likely state (0=bull, 1=bear, 2=sideways, 3=crisis).
        state_probs (list[Decimal]): Forward-backward smoothed state probabilities [P_bull, P_bear, P_sideways, P_crisis].
        conditional_vol (Decimal): GARCH(1,1) conditional volatility forecast (1-day).
        vol_forecast_5d (Decimal): 5-day conditional volatility forecast.
        vol_forecast_21d (Decimal): 21-day conditional volatility forecast.

    Primary Key: time
    Indexes: Implicit on primary key

    Regime States:
        0 = BULL: Rising prices, low volatility, positive returns
        1 = BEAR: Declining prices, medium volatility, negative returns
        2 = SIDEWAYS: Oscillating prices, medium volatility, near-zero returns
        3 = CRISIS: High volatility, sharp declines, large negative returns

    Probabilities:
        - state_probs is a 4-element array summing to 1.0
        - Viterbi state is argmax of state_probs
        - Probabilities reflect regime transition uncertainty

    Volatility Forecasts:
        - All forecasts are annualized percentage volatility
        - Computed per-state from GARCH(1,1) estimation
        - Used for position sizing and risk management
    """

    __tablename__ = "regime_states"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        primary_key=True,
        doc="Regime timestamp (UTC)",
    )
    viterbi_state: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Most likely regime state (0=bull, 1=bear, 2=sideways, 3=crisis)",
    )
    state_probs: Mapped[list[Decimal]] = mapped_column(
        ARRAY(Numeric(6, 4)),
        nullable=False,
        doc="State probabilities [P_bull, P_bear, P_sideways, P_crisis]",
    )
    conditional_vol: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        doc="GARCH(1,1) 1-day conditional volatility forecast (annualized %)",
    )
    vol_forecast_5d: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="5-day conditional volatility forecast (annualized %)",
    )
    vol_forecast_21d: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="21-day conditional volatility forecast (annualized %)",
    )

    def __repr__(self) -> str:
        return f"<RegimeState(time='{self.time}', state={self.viterbi_state}, vol={self.conditional_vol})>"
