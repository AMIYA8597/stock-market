import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_section = """
---

## 📈 5. Trading Strategies & Backtesting Engines

NeuroQuant comes bundled with a powerful set of Python-based technical strategies that are translated directly from popular Pine Script algorithms. These run natively using `pandas_ta` and output explicit signals for the terminal UI and automated execution.

### **Integrated Strategies**
1. **EZ Algo EMA Suite (`ez_algo_service.py`)**
   - Implements multi-timeframe EMA crossovers and breakdown mapping.
   - Includes full dynamic filter support (ADX > 25, ATR Expansion, Bollinger Band Squeeze breakouts, and Volume Confirmation).
   - Outputs boolean signals for UI consumption.

2. **Optimized Retest Strategy (`optimized_retest_strategy.py`)**
   - **Highly Optimized Edge**: A sophisticated EMA trend-following strategy with pull-back mechanics.
   - **Candle Quality Filter**: strictly ignores wicks and dojis by measuring body-to-range ratios (`body% > 40%`).
   - **Smart Pyramiding**: Features a built-in state-machine backtester that limits entries to 2 per cycle, only adding the second entry if the first is running in profit.
   - **Explicit Signal Payload**: Generates detailed JSON configurations mimicking TradingView's Long/Short position tool, complete with dynamically scaled ATR Stop Losses and custom Risk/Reward Targets.

**To run backtests directly:**
```bash
# Evaluate the Optimized Retest Strategy on 5m data
python test_retest_5m.py 
```"""

# Insert before "5. Real-Time Terminal & WebSockets"
content = re.sub(r'(##.*5\.\s*Real-Time Terminal)', new_section + r'\n\n## 🔌 6. Real-Time Terminal', content)
content = re.sub(r'##.*6\.\s*Where to Change What', r'## 🗺️ 7. Where to Change What', content)
content = re.sub(r'##.*7\.\s*Local Setup & Execution Guide', r'## 🚀 8. Local Setup & Execution Guide', content)
content = re.sub(r'##.*8\.\s*Troubleshooting & Gotchas', r'## ⚠️ 9. Troubleshooting & Gotchas', content)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)
