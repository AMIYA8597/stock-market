"""Historical data handler for backtesting."""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from .event_driven_backtester import DataHandler, MarketEvent, EventType

logger = logging.getLogger(__name__)


class HistoricalDataHandler(DataHandler):
    """Data handler for historical OHLCV data."""

    def __init__(self, data: Dict[str, pd.DataFrame], start_date: datetime, end_date: datetime):
        """
        Initialize with historical data.

        Args:
            data: Dict of symbol -> OHLCV DataFrame with DatetimeIndex
            start_date: Backtest start date
            end_date: Backtest end date
        """
        self.data = data
        self.start_date = start_date
        self.end_date = end_date
        self.current_date = start_date
        self.symbols_list = list(data.keys())

        # Current position in data for each symbol
        self.current_positions: Dict[str, int] = {symbol: 0 for symbol in self.symbols_list}

        # Latest bars cache
        self.latest_bars: Dict[str, pd.DataFrame] = {}

        # Validate data
        self._validate_data()

    def _validate_data(self) -> None:
        """Validate input data."""
        for symbol, df in self.data.items():
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing columns {missing_cols} for {symbol}")

            # Ensure DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError(f"DataFrame for {symbol} must have DatetimeIndex")

            # Filter date range
            df_filtered = df[(df.index >= self.start_date) & (df.index <= self.end_date)]
            if len(df_filtered) == 0:
                logger.warning(f"No data for {symbol} in date range {self.start_date} to {self.end_date}")
            self.data[symbol] = df_filtered

    def get_latest_bars(self, symbol: str, n: int = 1) -> pd.DataFrame:
        """Get latest n bars for symbol."""
        if symbol not in self.data:
            return pd.DataFrame()

        df = self.data[symbol]
        if len(df) == 0:
            return pd.DataFrame()

        # Get data up to current date
        available_data = df[df.index <= self.current_date]
        if len(available_data) == 0:
            return pd.DataFrame()

        # Return last n bars
        return available_data.tail(n).copy()

    def update_bars(self) -> List[MarketEvent]:
        """Update bars and return market events for current date."""
        events = []

        # Find next trading day
        next_date = self._get_next_trading_date()
        if next_date is None:
            return events

        self.current_date = next_date

        # Generate market events for each symbol
        for symbol in self.symbols_list:
            df = self.data[symbol]
            if len(df) == 0:
                continue

            # Get data for current date
            current_data = df[df.index == self.current_date]
            if len(current_data) == 0:
                continue

            row = current_data.iloc[0]
            event = MarketEvent(
                type=EventType.MARKET,
                timestamp=self.current_date,
                symbol=symbol,
                price=row['close'],
                volume=int(row['volume']),
                data={
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                }
            )
            events.append(event)

            # Update latest bars cache
            self.latest_bars[symbol] = current_data

        return events

    def _get_next_trading_date(self) -> Optional[datetime]:
        """Get next trading date across all symbols."""
        next_dates = []

        for symbol, df in self.data.items():
            # Find next date after current_date
            future_dates = df[df.index > self.current_date]
            if len(future_dates) > 0:
                next_dates.append(future_dates.index[0])

        if not next_dates:
            return None

        return min(next_dates)

    @property
    def symbols(self) -> List[str]:
        """List of symbols being tracked."""
        return self.symbols_list.copy()

    def get_historical_data(self, symbol: str, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Get historical data for symbol within date range."""
        if symbol not in self.data:
            return pd.DataFrame()

        df = self.data[symbol]
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        return df.copy()

    def get_date_range(self) -> tuple[datetime, datetime]:
        """Get the date range of available data."""
        return self.start_date, self.end_date