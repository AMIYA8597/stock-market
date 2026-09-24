with open('app/services/intelligence_service.py', 'r') as f:
    text = f.read()

import re

# Fix get_signal
text = re.sub(r'''        try:\n            loop = asyncio\.get_running_loop\(\)\n        except RuntimeError:\n            loop = None\n\n        try:\n            if loop and loop\.is_running\(\):\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n            else:\n                result = asyncio\.run\(get_full_prediction\(symbol\)\)\n        except Exception as e:\n            result = \{"is_computed": False, "message": str\(e\), "symbol": symbol\}''', '''        try:\n            result = await get_full_prediction(symbol)\n        except Exception as e:\n            result = {"is_computed": False, "message": str(e), "symbol": symbol}''', text)

# Fix get_signal_history
text = re.sub(r'''        try:\n            loop = asyncio\.get_running_loop\(\)\n        except RuntimeError:\n            loop = None\n\n        try:\n            hist_days = days \+ 10\n            if loop and loop\.is_running\(\):\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n            else:\n                bars = asyncio\.run\(MarketDataService\.get_history\(symbol, "1d", f"\{hist_days\}d"\)\)\n        except Exception:\n            bars = \[\]''', '''        try:\n            hist_days = days + 10\n            bars = await MarketDataService.get_history(symbol, "1d", f"{hist_days}d")\n        except Exception:\n            bars = []''', text)

with open('app/services/intelligence_service.py', 'w') as f:
    f.write(text)
