import pandas as pd
import pandas_ta as ta
from .data_service import get_historical

def compute_indicators(ticker: str, days: int = 30):
    """Fetch historical OHLC data and compute technical indicators.
    Returns a DataFrame with original OHLC columns plus:
    - SMA_20, EMA_20, RSI_14, MACD (macd, macd_signal, macd_hist), BBAND_UP, BBAND_MID, BBAND_LOW
    """
    df = pd.DataFrame(get_historical(ticker, days))
    if df.empty:
        raise ValueError(f"No historical data for {ticker}")
    df.set_index('time', inplace=True)
    # Simple Moving Average
    df['SMA_20'] = ta.sma(df['close'], length=20)
    # Exponential Moving Average
    df['EMA_20'] = ta.ema(df['close'], length=20)
    # RSI
    df['RSI_14'] = ta.rsi(df['close'], length=14)
    # MACD
    macd = ta.macd(df['close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
    df['MACD_HIST'] = macd['MACDh_12_26_9']
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20, std=2)
    df['BBAND_UP'] = bb['BBU_20_2.0']
    df['BBAND_MID'] = bb['BBM_20_2.0']
    df['BBAND_DOWN'] = bb['BBL_20_2.0']
    df.dropna(inplace=True)
    return df.reset_index()
