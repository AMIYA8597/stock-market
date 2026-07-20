import backtrader as bt
from datetime import datetime
from .data_service import get_historical

class SignalStrategy(bt.Strategy):
    params = (('ma_period', 20),)

    def __init__(self):
        self.sma = bt.ind.SMA(self.datas[0].close, period=self.p.ma_period)
        self.crossover = bt.ind.CrossOver(self.datas[0].close, self.sma)

    def next(self):
        if not self.position:
            if self.crossover > 0:  # price crosses above SMA -> buy
                self.buy()
        else:
            if self.crossover < 0:  # price crosses below SMA -> sell
                self.sell()

def run_backtest(ticker: str, start_date: str, end_date: str):
    """Run a simple SMA crossover backtest for the given ticker and date range.
    Returns a dict with performance metrics.
    """
    # Load historical daily data
    hist = get_historical(ticker, days=365)  # get up to a year, filter later
    # Convert to pandas DataFrame
    import pandas as pd
    df = pd.DataFrame(hist)
    df['datetime'] = pd.to_datetime(df['time'])
    df.set_index('datetime', inplace=True)
    # Filter by date range
    mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
    df = df.loc[mask]
    if df.empty:
        raise ValueError('No data in the specified date range')

    data = bt.feeds.PandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(SignalStrategy)
    cerebro.broker.setcash(100000.0)
    cerebro.addobserver(bt.observers.TimeReturn)
    result = cerebro.run()
    # Extract performance
    portfolio_value = cerebro.broker.getvalue()
    returns = cerebro.observers[0].get_analysis()
    # Simple metrics
    total_return = (portfolio_value - 100000.0) / 100000.0
    return {
        'ticker': ticker,
        'start': start_date,
        'end': end_date,
        'final_portfolio_value': round(portfolio_value, 2),
        'total_return_pct': round(total_return * 100, 2),
        'returns_series': returns  # can be plotted on front‑end
    }
