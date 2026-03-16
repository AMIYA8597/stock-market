"""Event-driven backtesting framework for NeuroQuant.

Implements event-driven architecture with DataHandler, Portfolio, Execution, and Performance classes.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional, Protocol
import pandas as pd
import numpy as np
from enum import Enum


class EventType(Enum):
    """Types of events in the backtesting system."""
    MARKET = "market"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    timestamp: datetime
    data: Dict[str, Any]


@dataclass
class MarketEvent(Event):
    """Market data event."""
    symbol: str
    price: float
    volume: int
    type: EventType = EventType.MARKET


@dataclass
class SignalEvent(Event):
    """Trading signal event."""
    symbol: str
    direction: int  # +1 long, -1 short, 0 close
    strength: float  # Signal strength/confidence
    strategy_name: str
    type: EventType = EventType.SIGNAL


@dataclass
class OrderEvent(Event):
    """Order event."""
    symbol: str
    order_type: str  # 'MKT' market, 'LMT' limit
    quantity: int
    direction: int  # +1 buy, -1 sell
    price: Optional[float] = None  # For limit orders
    type: EventType = EventType.ORDER


@dataclass
class FillEvent(Event):
    """Order fill event."""
    symbol: str
    exchange: str
    quantity: int
    direction: int
    fill_price: float
    commission: float
    type: EventType = EventType.FILL


class DataHandler(abc.ABC):
    """Abstract base class for data handling."""

    @abc.abstractmethod
    def get_latest_bars(self, symbol: str, n: int = 1) -> pd.DataFrame:
        """Get latest n bars for symbol."""
        pass

    @abc.abstractmethod
    def update_bars(self) -> List[MarketEvent]:
        """Update bars and return market events."""
        pass

    @property
    @abc.abstractmethod
    def symbols(self) -> List[str]:
        """List of symbols being tracked."""
        pass

    @property
    @abc.abstractmethod
    def current_date(self) -> datetime:
        """Current date in backtest."""
        pass


class Portfolio:
    """Portfolio management class."""

    def __init__(self, initial_capital: float, data_handler: DataHandler):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_handler = data_handler

        # Holdings: symbol -> {'quantity': int, 'avg_price': float, 'current_price': float}
        self.holdings: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, int] = {}  # symbol -> quantity

        # Performance tracking
        self.portfolio_value_history: List[float] = [initial_capital]
        self.returns_history: List[float] = []
        self.dates: List[datetime] = []

        # Transaction costs
        self.commission_rate = 0.001  # 0.1%
        self.slippage_model = 'fixed'  # 'fixed' or 'proportional'
        self.slippage_rate = 0.0005  # 0.05%

    def update_holdings(self, symbol: str) -> None:
        """Update current prices for holdings."""
        if symbol in self.holdings:
            latest_bar = self.data_handler.get_latest_bars(symbol, 1)
            if not latest_bar.empty:
                current_price = latest_bar.iloc[-1]['close']
                self.holdings[symbol]['current_price'] = current_price

    def calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        total_value = self.current_capital

        for symbol, holding in self.holdings.items():
            self.update_holdings(symbol)
            total_value += holding['quantity'] * holding['current_price']

        return total_value

    def update_portfolio_value(self) -> None:
        """Update portfolio value history."""
        current_value = self.calculate_portfolio_value()
        self.portfolio_value_history.append(current_value)

        if len(self.portfolio_value_history) > 1:
            prev_value = self.portfolio_value_history[-2]
            ret = (current_value - prev_value) / prev_value
            self.returns_history.append(ret)

        self.dates.append(self.data_handler.current_date)

    def execute_order(self, order_event: OrderEvent) -> FillEvent:
        """Execute an order and return fill event."""
        symbol = order_event.symbol
        quantity = order_event.quantity
        direction = order_event.direction

        # Get current price
        latest_bar = self.data_handler.get_latest_bars(symbol, 1)
        if latest_bar.empty:
            raise ValueError(f"No data available for {symbol}")

        current_price = latest_bar.iloc[-1]['close']

        # Apply slippage
        if self.slippage_model == 'fixed':
            slippage = self.slippage_rate * current_price * direction
        else:  # proportional
            slippage = self.slippage_rate * current_price

        fill_price = current_price + slippage

        # Calculate commission
        commission = abs(quantity) * fill_price * self.commission_rate

        # Check if we have enough capital for buy orders
        if direction > 0:  # Buy
            cost = quantity * fill_price + commission
            if cost > self.current_capital:
                # Scale down order
                max_quantity = int(self.current_capital / (fill_price + commission))
                quantity = min(quantity, max_quantity)
                if quantity == 0:
                    raise ValueError("Insufficient capital for order")

        # Update holdings
        if symbol not in self.holdings:
            self.holdings[symbol] = {
                'quantity': 0,
                'avg_price': 0.0,
                'current_price': fill_price
            }

        holding = self.holdings[symbol]

        if direction > 0:  # Buy
            # Update average price
            total_cost = (holding['quantity'] * holding['avg_price']) + (quantity * fill_price)
            total_quantity = holding['quantity'] + quantity
            holding['avg_price'] = total_cost / total_quantity if total_quantity > 0 else 0
            holding['quantity'] = total_quantity
            self.current_capital -= (quantity * fill_price + commission)

        else:  # Sell
            # Check if we have enough shares
            if abs(quantity) > holding['quantity']:
                quantity = -holding['quantity']  # Sell all available

            # Calculate P&L
            pnl = (fill_price - holding['avg_price']) * abs(quantity)

            holding['quantity'] += quantity  # quantity is negative for sell
            self.current_capital += (abs(quantity) * fill_price - commission)

            if holding['quantity'] == 0:
                holding['avg_price'] = 0.0

        # Update positions
        self.positions[symbol] = holding['quantity']

        return FillEvent(
            type=EventType.FILL,
            timestamp=self.data_handler.current_date,
            symbol=symbol,
            exchange="BACKTEST",
            quantity=abs(quantity),
            direction=direction,
            fill_price=fill_price,
            commission=commission,
            data={}
        )

    def get_positions(self) -> Dict[str, int]:
        """Get current positions."""
        return self.positions.copy()

    def get_holdings_value(self) -> float:
        """Get value of current holdings."""
        return sum(holding['quantity'] * holding['current_price']
                  for holding in self.holdings.values())


class ExecutionHandler(abc.ABC):
    """Abstract base class for order execution."""

    @abc.abstractmethod
    def execute_order(self, order_event: OrderEvent) -> FillEvent:
        """Execute an order."""
        pass


class SimulatedExecutionHandler(ExecutionHandler):
    """Simulated order execution for backtesting."""

    def __init__(self, data_handler: DataHandler, portfolio: Portfolio):
        self.data_handler = data_handler
        self.portfolio = portfolio

    def execute_order(self, order_event: OrderEvent) -> FillEvent:
        """Execute order through portfolio."""
        return self.portfolio.execute_order(order_event)


class PerformanceCalculator:
    """Calculate performance metrics."""

    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if excess_returns.std() == 0:
            return 0.0
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio."""
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        return np.sqrt(252) * excess_returns.mean() / downside_returns.std()

    @staticmethod
    def calculate_max_drawdown(portfolio_values: pd.Series) -> float:
        """Calculate maximum drawdown."""
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        return drawdown.min()

    @staticmethod
    def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
        """Calculate Calmar ratio."""
        if max_drawdown == 0:
            return 0.0
        annual_return = (1 + returns.mean()) ** 252 - 1
        return annual_return / abs(max_drawdown)

    @staticmethod
    def calculate_win_rate(trade_returns: pd.Series) -> float:
        """Calculate win rate."""
        if len(trade_returns) == 0:
            return 0.0
        return (trade_returns > 0).sum() / len(trade_returns)

    @staticmethod
    def calculate_profit_factor(trade_returns: pd.Series) -> float:
        """Calculate profit factor."""
        winning_trades = trade_returns[trade_returns > 0]
        losing_trades = trade_returns[trade_returns < 0]

        if len(winning_trades) == 0:
            return 0.0
        if len(losing_trades) == 0:
            return float('inf')

        return winning_trades.sum() / abs(losing_trades.sum())