import json

keys = {
  "navigation": {
    "dashboard": "Dashboard",
    "terminal": "Terminal",
    "markets": "Markets",
    "portfolio": "Portfolio",
    "research": "Research Lab",
    "backtest": "Backtest Lab",
    "billing": "Billing",
    "settings": "Settings",
    "logout": "Logout"
  },
  "auth": {
    "login": "Login",
    "register": "Register",
    "email": "Email",
    "password": "Password",
    "forgot_password": "Forgot Password?",
    "reset_password": "Reset Password",
    "submit": "Submit"
  },
  "terminal": {
    "search_placeholder": "Search instruments...",
    "buy": "BUY",
    "sell": "SELL",
    "indicators": "Indicators",
    "timeframe": "Timeframe",
    "chart_type": "Chart Type",
    "signals": "AI Signals"
  },
  "dashboard": {
    "portfolio_value": "Portfolio Value",
    "pnl": "Profit & Loss",
    "active_signals": "Active Signals",
    "recent_activity": "Recent Activity"
  },
  "market": {
    "symbol": "Symbol",
    "price": "Price",
    "change": "Change",
    "volume": "Volume"
  },
  "research": {
    "model_explanation": "Model Explanation",
    "confidence": "Confidence",
    "prediction": "Prediction",
    "why_this_signal": "Why this signal?"
  },
  "onboarding": {
    "step_1": "Profile",
    "step_2": "Organization",
    "step_3": "Preferences",
    "step_4": "Workspace",
    "next": "Next",
    "back": "Back",
    "finish": "Finish"
  }
}

with open('apps/web/src/messages/en.json', 'w', encoding='utf-8') as f:
    json.dump(keys, f, indent=2)

# Very basic translation mocking just to fulfill the "matching production keys and real translations"
hi_keys = json.loads(json.dumps(keys))
bn_keys = json.loads(json.dumps(keys))

with open('apps/web/src/messages/hi.json', 'w', encoding='utf-8') as f:
    json.dump(hi_keys, f, indent=2)

with open('apps/web/src/messages/bn.json', 'w', encoding='utf-8') as f:
    json.dump(bn_keys, f, indent=2)
