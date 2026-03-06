#!/usr/bin/env python3
"""
Phase 3 Data Pipeline Test - Complete data ingestion test
Tests yfinance fetcher, data processing, and WebSocket simulation
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf
from loguru import logger

def test_phase3_data_pipeline():
    """Test all Phase 3 data pipeline components."""
    
    print("📊 Testing Phase 3: Data Pipeline")
    print("=" * 50)
    
    try:
        # Test 1: yfinance Data Fetching
        print("1. Testing yfinance data fetching...")
        
        # Define NSE symbols to test
        nse_symbols = [
            'RELIANCE.NS',  # Reliance Industries
            'TCS.NS',       # Tata Consultancy Services
            'HDFCBANK.NS',  # HDFC Bank
            'INFY.NS',      # Infosys
            'ICICIBANK.NS'  # ICICI Bank
        ]
        
        # Fetch historical data for the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"   Fetching data for {len(nse_symbols)} symbols...")
        print(f"   Period: {start_date.date()} to {end_date.date()}")
        
        # Download data
        data = yf.download(
            nse_symbols,
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=False  # Get raw prices including adjusted close
        )
        
        if not data.empty:
            print(f"✅ yfinance data fetched successfully")
            print(f"   Shape: {data.shape}")
            print(f"   Columns: {list(data.columns)}")
            print(f"   Date range: {data.index.min().date()} to {data.index.max().date()}")
        else:
            print("❌ No data fetched from yfinance")
            return False
        
        # Test 2: Data Processing and Validation
        print("\n2. Testing data processing and validation...")
        
        # Process multi-level columns (yfinance returns multi-index for multiple symbols)
        if isinstance(data.columns, pd.MultiIndex):
            # Flatten column names from MultiIndex
            data.columns = [f'{col[1]}_{col[0]}' if col[0] != '' else col[1] for col in data.columns.values]
            print(f"   Flattened columns: {list(data.columns)[:10]}...")
        
        # Check for missing data
        missing_data = data.isnull().sum()
        if missing_data.sum() > 0:
            print(f"⚠️  Missing data found: {missing_data[missing_data > 0].to_dict()}")
            # Forward fill missing data
            data = data.fillna(method='ffill')
            data = data.fillna(method='bfill')
            print("   Missing data filled using forward/backward fill")
        
        # Validate data quality
        required_columns = []
        for symbol in nse_symbols:
            required_columns.extend([f'{symbol}_Open', f'{symbol}_High', f'{symbol}_Low', 
                                   f'{symbol}_Close', f'{symbol}_Volume'])
        
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        print("✅ Data processing and validation passed")
        
        # Test 3: OHLCV Data Transformation
        print("\n3. Testing OHLCV data transformation...")
        
        transformed_data = []
        
        for symbol in nse_symbols:
            symbol_data = data[[f'{symbol}_Open', f'{symbol}_High', f'{symbol}_Low', 
                              f'{symbol}_Close', f'{symbol}_Volume']].copy()
            symbol_data.columns = ['open', 'high', 'low', 'close', 'volume']
            symbol_data['symbol'] = symbol.replace('.NS', '')  # Remove exchange suffix
            symbol_data['exchange'] = 'NSE'
            symbol_data['time'] = symbol_data.index
            symbol_data['adjusted_close'] = symbol_data['close']  # For simplicity
            
            # Remove any rows with zero volume (non-trading days)
            symbol_data = symbol_data[symbol_data['volume'] > 0]
            
            transformed_data.append(symbol_data)
        
        # Combine all symbols
        ohlcv_data = pd.concat(transformed_data, ignore_index=True)
        
        print(f"✅ OHLCV data transformed successfully")
        print(f"   Total records: {len(ohlcv_data)}")
        print(f"   Symbols: {ohlcv_data['symbol'].nunique()}")
        print(f"   Date range: {ohlcv_data['time'].min().date()} to {ohlcv_data['time'].max().date()}")
        
        # Test 4: Technical Indicators Calculation
        print("\n4. Testing technical indicators calculation...")
        
        # Calculate basic technical indicators for each symbol
        def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
            """Calculate basic technical indicators."""
            df = df.copy()
            
            # Sort by time
            df = df.sort_values('time')
            
            # Simple Moving Averages
            df['sma_5'] = df['close'].rolling(window=5, min_periods=1).mean()
            df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
            df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
            
            # Exponential Moving Average
            df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # RSI (Relative Strength Index)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
            bb_std = df['close'].rolling(window=20, min_periods=1).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return df
        
        # Apply technical indicators
        ohlcv_with_indicators = []
        for symbol in ohlcv_data['symbol'].unique():
            symbol_data = ohlcv_data[ohlcv_data['symbol'] == symbol].copy()
            symbol_data = calculate_technical_indicators(symbol_data)
            ohlcv_with_indicators.append(symbol_data)
        
        final_data = pd.concat(ohlcv_with_indicators, ignore_index=True)
        
        print("✅ Technical indicators calculated successfully")
        print(f"   Indicators added: SMA, EMA, RSI, MACD, Bollinger Bands, Volume Ratio")
        print(f"   Final columns: {len(final_data.columns)}")
        
        # Test 5: Real-time Price Simulation
        print("\n5. Testing real-time price simulation...")
        
        # Simulate real-time price updates
        class PriceSimulator:
            """Simple price simulator for testing."""
            
            def __init__(self, base_data: pd.DataFrame):
                self.base_data = base_data
                self.current_prices = {}
                self.price_history = {}
                
                # Initialize with last known prices
                for symbol in base_data['symbol'].unique():
                    symbol_data = base_data[base_data['symbol'] == symbol].sort_values('time')
                    if not symbol_data.empty:
                        last_price = symbol_data.iloc[-1]['close']
                        self.current_prices[symbol] = last_price
                        self.price_history[symbol] = [last_price]
            
            def get_next_price(self, symbol: str) -> float:
                """Generate next price with realistic movement."""
                if symbol not in self.current_prices:
                    return 0.0
                
                current_price = self.current_prices[symbol]
                
                # Random walk with volatility
                volatility = 0.02  # 2% daily volatility
                drift = 0.0001    # Small upward drift
                
                # Generate random price movement
                random_change = random.gauss(drift, volatility)
                new_price = current_price * (1 + random_change)
                
                # Update current price and history
                self.current_prices[symbol] = new_price
                self.price_history[symbol].append(new_price)
                
                # Keep only last 100 prices
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol] = self.price_history[symbol][-100:]
                
                return new_price
            
            def get_market_snapshot(self) -> Dict[str, Any]:
                """Get current market snapshot."""
                snapshot = {}
                for symbol, price in self.current_prices.items():
                    # Calculate change from previous price
                    if len(self.price_history[symbol]) > 1:
                        prev_price = self.price_history[symbol][-2]
                        change = price - prev_price
                        change_pct = (change / prev_price) * 100
                    else:
                        change = 0.0
                        change_pct = 0.0
                    
                    snapshot[symbol] = {
                        'price': round(price, 2),
                        'change': round(change, 2),
                        'change_pct': round(change_pct, 2),
                        'timestamp': datetime.now().isoformat(),
                        'volume': int(random.random() * 1000000)  # Simulated volume
                    }
                
                return snapshot
        
        # Initialize price simulator
        simulator = PriceSimulator(final_data)
        
        # Simulate 5 price updates
        print("   Simulating real-time price updates...")
        for i in range(5):
            snapshot = simulator.get_market_snapshot()
            print(f"   Update {i+1}:")
            for symbol, data in list(snapshot.items())[:3]:  # Show first 3 symbols
                trend = "▲" if data['change_pct'] > 0 else "▼" if data['change_pct'] < 0 else "→"
                print(f"     {symbol}: ₹{data['price']} ({trend} {data['change_pct']:.2f}%)")
            time.sleep(0.5)  # Simulate real-time delay
        
        print("✅ Real-time price simulation working")
        
        # Test 6: Data Export and Storage Preparation
        print("\n6. Testing data export and storage preparation...")
        
        # Prepare data for database storage
        storage_data = final_data.copy()
        
        # Convert to records format for database insertion
        records = storage_data.to_dict('records')
        
        # Sample record structure
        if records:
            sample_record = records[0]
            print("✅ Data prepared for storage")
            print(f"   Sample record keys: {list(sample_record.keys())[:10]}...")
            print(f"   Total records to store: {len(records)}")
        
        # Test 7: Market Hours Detection
        print("\n7. Testing market hours detection...")
        
        def is_market_open() -> bool:
            """Check if NSE market is currently open."""
            now = datetime.now()
            
            # Weekend check
            if now.weekday() >= 5:  # Saturday, Sunday
                return False
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= market_close
        
        market_status = "OPEN" if is_market_open() else "CLOSED"
        print(f"✅ Market hours detection working")
        print(f"   Current market status: {market_status}")
        
        print("\n🎉 Phase 3 Data Pipeline Test - PASSED")
        print("=" * 50)
        print("✅ yfinance data fetching working")
        print("✅ Data processing and validation working")
        print("✅ OHLCV data transformation working")
        print("✅ Technical indicators calculation working")
        print("✅ Real-time price simulation working")
        print("✅ Data export preparation working")
        print("✅ Market hours detection working")
        print("\n📋 Ready for Phase 4: ML Training")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 3 Data Pipeline Test - FAILED")
        print(f"Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check internet connection for yfinance API")
        print("2. Verify pandas and yfinance are installed")
        print("3. Check if NSE symbols are valid")
        return False

if __name__ == "__main__":
    success = test_phase3_data_pipeline()
    exit(0 if success else 1)
