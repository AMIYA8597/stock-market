"""Test Backtesting Engine functionality."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.backtester.backtesting_engine import BacktestingEngine, create_strategy


def test_backtesting_engine():
    """Test the complete backtesting engine."""
    print("Testing Backtesting Engine...")

    # Create sample data
    symbols = ['RELIANCE.NS', 'TCS.NS']
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 1, 1)

    np.random.seed(42)

    data = {}
    dates = pd.date_range(start_date, end_date, freq='B')

    for symbol in symbols:
        # Generate synthetic OHLCV data
        n_days = len(dates)
        returns = np.random.normal(0.0005, 0.02, n_days)
        prices = 1000 * np.exp(np.cumsum(returns))

        ohlcv_data = []
        for price in prices:
            open_price = price * (1 + np.random.normal(0, 0.005))
            high_price = price * (1 + np.random.uniform(0, 0.02))
            low_price = price * (1 - np.random.uniform(0, 0.02))
            close_price = price
            volume = int(np.random.uniform(100000, 1000000))

            ohlcv_data.append({
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })

        df = pd.DataFrame(ohlcv_data, index=dates)
        data[symbol] = df

    # Initialize backtest engine
    engine = BacktestingEngine(
        initial_capital=1000000.0,
        commission_rate=0.001,
        slippage_rate=0.0005
    )

    # Load data
    engine.load_data(data, start_date, end_date)

    # Add momentum strategy
    strategy = create_strategy('adaptive_momentum', {
        'momentum_period': 60,
        'vol_lookback': 20,
        'regime_filter': True
    })
    engine.add_strategy(strategy)

    # Run backtest
    results = engine.run_backtest()

    # Print results
    metrics = results['metrics']
    print("
Backtest Results:")
    print(f"Total Return: {metrics['total_return']:.2%}")
    print(f"Annual Return: {metrics['annual_return']:.2%}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"Win Rate: {metrics['win_rate']:.1%}")
    print(f"Total Trades: {metrics['total_trades']}")

    # Test Monte Carlo significance
    print("
Running Monte Carlo significance test...")
    mc_results = engine.monte_carlo_significance_test(n_simulations=100)
    print(f"Actual Sharpe: {mc_results['actual_sharpe']:.2f}")
    print(f"P-value: {mc_results['p_value']:.3f}")
    print(f"Significant: {mc_results['significant']}")

    print("\nBacktesting engine test completed successfully!")


def test_strategies():
    """Test individual strategies."""
    print("\nTesting individual strategies...")

    # Test strategy creation
    strategies = ['kalman_pairs', 'adaptive_momentum', 'ml_alpha', 'stat_arb', 'vol_regime', 'rl_agent']

    for strategy_name in strategies:
        try:
            strategy = create_strategy(strategy_name)
            params = strategy.get_params()
            print(f"✓ {strategy_name}: {params}")
        except Exception as e:
            print(f"✗ {strategy_name}: {e}")

    print("Strategy creation test completed!")


if __name__ == "__main__":
    test_strategies()
    test_backtesting_engine()