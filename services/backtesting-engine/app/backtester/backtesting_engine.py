"""Main backtesting engine that orchestrates the event-driven system."""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio

from .event_driven_backtester import (
    Event, MarketEvent, SignalEvent, OrderEvent, FillEvent,
    Portfolio, SimulatedExecutionHandler, PerformanceCalculator
)
from .data_handler import HistoricalDataHandler
from .strategies.strategies import (
    BaseStrategy, KalmanFilterPairsTrading, AdaptiveMomentumStrategy,
    MLAlphaStrategy, StatisticalArbitrageStrategy, VolatilityRegimeStrategy,
    DeepRLAgentStrategy
)

logger = logging.getLogger(__name__)


class BacktestingEngine:
    """Main backtesting engine."""

    def __init__(self,
                 initial_capital: float = 1000000.0,
                 commission_rate: float = 0.001,
                 slippage_rate: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        # Components
        self.data_handler: Optional[HistoricalDataHandler] = None
        self.portfolio: Optional[Portfolio] = None
        self.execution_handler: Optional[SimulatedExecutionHandler] = None
        self.strategies: List[BaseStrategy] = []

        # Event queues
        self.market_events: List[MarketEvent] = []
        self.signal_events: List[SignalEvent] = []
        self.order_events: List[OrderEvent] = []
        self.fill_events: List[FillEvent] = []

        # Results
        self.results: Optional[Dict[str, Any]] = None

    def add_strategy(self, strategy: BaseStrategy) -> None:
        """Add a strategy to the backtest."""
        self.strategies.append(strategy)

    def load_data(self, data: Dict[str, pd.DataFrame], start_date: datetime, end_date: datetime) -> None:
        """Load historical data."""
        self.data_handler = HistoricalDataHandler(data, start_date, end_date)
        self.portfolio = Portfolio(self.initial_capital, self.data_handler)
        self.execution_handler = SimulatedExecutionHandler(self.data_handler, self.portfolio)

    def run_backtest(self) -> Dict[str, Any]:
        """Run the complete backtest."""
        if not self.data_handler or not self.portfolio or not self.execution_handler:
            raise ValueError("Data handler, portfolio, and execution handler must be initialized")

        logger.info(f"Starting backtest from {self.data_handler.start_date} to {self.data_handler.end_date}")

        # Reset event queues
        self._reset_events()

        # Main event loop
        while True:
            # Update market data
            market_events = self.data_handler.update_bars()
            if not market_events:
                break  # No more data

            self.market_events.extend(market_events)

            # Generate signals from all strategies
            for strategy in self.strategies:
                signals = strategy.generate_signals(self.data_handler, self.portfolio)
                self.signal_events.extend(signals)

            # Convert signals to orders
            orders = self._signals_to_orders()
            self.order_events.extend(orders)

            # Execute orders
            for order in orders:
                try:
                    fill = self.execution_handler.execute_order(order)
                    self.fill_events.append(fill)
                except ValueError as e:
                    logger.warning(f"Order execution failed: {e}")

            # Update portfolio value
            self.portfolio.update_portfolio_value()

        # Calculate performance metrics
        self.results = self._calculate_results()
        return self.results

    def _signals_to_orders(self) -> List[OrderEvent]:
        """Convert signals to orders."""
        orders = []

        # Group signals by symbol
        symbol_signals: Dict[str, List[SignalEvent]] = {}
        for signal in self.signal_events:
            if signal.timestamp == self.data_handler.current_date:
                if signal.symbol not in symbol_signals:
                    symbol_signals[signal.symbol] = []
                symbol_signals[signal.symbol].append(signal)

        # Process signals for each symbol
        for symbol, signals in symbol_signals.items():
            if not signals:
                continue

            # Aggregate signals (simple average for now)
            total_strength = sum(s.strength for s in signals)
            avg_direction = np.mean([s.direction for s in signals])

            # Determine target position
            current_position = self.portfolio.positions.get(symbol, 0)

            if avg_direction == 0:
                # Close position
                if current_position != 0:
                    orders.append(OrderEvent(
                        type=EventType.ORDER,
                        timestamp=self.data_handler.current_date,
                        symbol=symbol,
                        order_type='MKT',
                        quantity=abs(current_position),
                        direction=-1 if current_position > 0 else 1
                    ))
            else:
                # Calculate position size based on signal strength and capital
                portfolio_value = self.portfolio.calculate_portfolio_value()
                max_position_value = portfolio_value * 0.1  # Max 10% of portfolio

                latest_bar = self.data_handler.get_latest_bars(symbol, 1)
                if not latest_bar.empty:
                    price = latest_bar.iloc[-1]['close']
                    max_quantity = int(max_position_value / price)

                    # Target quantity based on signal
                    target_quantity = int(max_quantity * total_strength / len(signals))
                    target_quantity = int(target_quantity * avg_direction)

                    # Calculate order quantity
                    order_quantity = target_quantity - current_position

                    if abs(order_quantity) > 0:
                        orders.append(OrderEvent(
                            type=EventType.ORDER,
                            timestamp=self.data_handler.current_date,
                            symbol=symbol,
                            order_type='MKT',
                            quantity=abs(order_quantity),
                            direction=1 if order_quantity > 0 else -1
                        ))

        return orders

    def _reset_events(self) -> None:
        """Reset all event queues."""
        self.market_events = []
        self.signal_events = []
        self.order_events = []
        self.fill_events = []

    def _calculate_results(self) -> Dict[str, Any]:
        """Calculate comprehensive backtest results."""
        if not self.portfolio:
            return {}

        # Portfolio returns
        portfolio_values = pd.Series(
            self.portfolio.portfolio_value_history,
            index=self.portfolio.dates
        )

        returns = portfolio_values.pct_change().dropna()

        # Trade analysis
        trades = self._analyze_trades()

        # Performance metrics
        metrics = self._calculate_metrics(portfolio_values, returns, trades)

        return {
            'portfolio_values': portfolio_values,
            'returns': returns,
            'trades': trades,
            'metrics': metrics,
            'initial_capital': self.initial_capital,
            'final_capital': portfolio_values.iloc[-1] if len(portfolio_values) > 0 else self.initial_capital
        }

    def _analyze_trades(self) -> pd.DataFrame:
        """Analyze individual trades."""
        trades = []

        current_trade = None

        for fill in self.fill_events:
            if current_trade is None:
                # Start new trade
                current_trade = {
                    'symbol': fill.symbol,
                    'entry_date': fill.timestamp,
                    'entry_price': fill.fill_price,
                    'quantity': fill.quantity if fill.direction > 0 else -fill.quantity,
                    'entry_commission': fill.commission,
                    'direction': fill.direction
                }
            else:
                # Close existing trade
                if fill.symbol == current_trade['symbol'] and fill.direction != current_trade['direction']:
                    exit_price = fill.fill_price
                    exit_commission = fill.commission
                    exit_date = fill.timestamp

                    # Calculate P&L
                    if current_trade['direction'] > 0:  # Long trade
                        pnl = (exit_price - current_trade['entry_price']) * abs(current_trade['quantity'])
                    else:  # Short trade
                        pnl = (current_trade['entry_price'] - exit_price) * abs(current_trade['quantity'])

                    pnl -= (current_trade['entry_commission'] + exit_commission)

                    trade = {
                        'symbol': current_trade['symbol'],
                        'entry_date': current_trade['entry_date'],
                        'exit_date': exit_date,
                        'entry_price': current_trade['entry_price'],
                        'exit_price': exit_price,
                        'quantity': current_trade['quantity'],
                        'pnl': pnl,
                        'return_pct': pnl / (current_trade['entry_price'] * abs(current_trade['quantity'])),
                        'holding_period': (exit_date - current_trade['entry_date']).days,
                        'direction': 'long' if current_trade['direction'] > 0 else 'short'
                    }

                    trades.append(trade)
                    current_trade = None

        return pd.DataFrame(trades)

    def _calculate_metrics(self, portfolio_values: pd.Series, returns: pd.Series,
                          trades: pd.DataFrame) -> Dict[str, Any]:
        """Calculate performance metrics."""
        # Basic metrics
        total_return = (portfolio_values.iloc[-1] - portfolio_values.iloc[0]) / portfolio_values.iloc[0]
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1

        # Risk metrics
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = PerformanceCalculator.calculate_sharpe_ratio(returns)
        sortino_ratio = PerformanceCalculator.calculate_sortino_ratio(returns)
        max_drawdown = PerformanceCalculator.calculate_max_drawdown(portfolio_values)
        calmar_ratio = PerformanceCalculator.calculate_calmar_ratio(returns, max_drawdown)

        # Trade metrics
        if len(trades) > 0:
            win_rate = PerformanceCalculator.calculate_win_rate(trades['pnl'])
            profit_factor = PerformanceCalculator.calculate_profit_factor(trades['pnl'])
            avg_trade = trades['pnl'].mean()
            avg_win = trades[trades['pnl'] > 0]['pnl'].mean() if len(trades[trades['pnl'] > 0]) > 0 else 0
            avg_loss = trades[trades['pnl'] < 0]['pnl'].mean() if len(trades[trades['pnl'] < 0]) > 0 else 0
            largest_win = trades['pnl'].max()
            largest_loss = trades['pnl'].min()
            avg_holding_period = trades['holding_period'].mean()
        else:
            win_rate = profit_factor = avg_trade = avg_win = avg_loss = 0
            largest_win = largest_loss = avg_holding_period = 0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': len(trades),
            'avg_trade': avg_trade,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_holding_period': avg_holding_period
        }

    def walk_forward_optimization(self, data: Dict[str, pd.DataFrame],
                                strategy_class: type, param_ranges: Dict[str, List[Any]],
                                n_windows: int = 5, metric: str = 'sharpe') -> Dict[str, Any]:
        """Perform walk-forward optimization."""
        # This would implement walk-forward analysis
        # For now, return placeholder
        return {
            'optimal_params': {},
            'out_of_sample_performance': {},
            'windows': []
        }

    def monte_carlo_significance_test(self, n_simulations: int = 1000) -> Dict[str, Any]:
        """Perform Monte Carlo significance testing."""
        if not self.results:
            raise ValueError("Run backtest first")

        actual_sharpe = self.results['metrics']['sharpe_ratio']
        returns = self.results['returns']

        # Generate random returns with same statistics
        simulated_sharpes = []

        for _ in range(n_simulations):
            # Shuffle returns to destroy any signal
            shuffled_returns = returns.sample(frac=1, replace=True).values
            sim_sharpe = PerformanceCalculator.calculate_sharpe_ratio(pd.Series(shuffled_returns))
            simulated_sharpes.append(sim_sharpe)

        # Calculate p-value
        p_value = sum(1 for s in simulated_sharpes if s >= actual_sharpe) / n_simulations

        return {
            'actual_sharpe': actual_sharpe,
            'simulated_sharpes': simulated_sharpes,
            'p_value': p_value,
            'significant': p_value < 0.05
        }


def create_strategy(name: str, params: Optional[Dict[str, Any]] = None) -> BaseStrategy:
    """Factory function to create strategies."""
    strategies = {
        'kalman_pairs': KalmanFilterPairsTrading,
        'adaptive_momentum': AdaptiveMomentumStrategy,
        'ml_alpha': MLAlphaStrategy,
        'stat_arb': StatisticalArbitrageStrategy,
        'vol_regime': VolatilityRegimeStrategy,
        'rl_agent': DeepRLAgentStrategy
    }

    if name not in strategies:
        raise ValueError(f"Unknown strategy: {name}")

    return strategies[name](params)