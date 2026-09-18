import numpy as np
import pandas as pd

class RiskEngine:
    @staticmethod
    def calculate_risk(df: pd.DataFrame) -> dict:
        if df.empty or len(df) < 21:
            return {"risk": "HIGH", "score": 85}

        # Calculate Volatility (21-day std)
        returns = df["close"].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)

        # Calculate Max Drawdown
        cum_returns = (1 + returns).cumprod()
        peak = cum_returns.expanding(min_periods=1).max()
        drawdown = (cum_returns / peak) - 1
        max_dd = drawdown.min()

        # Calculate VaR (95% Historical)
        var_95 = np.percentile(returns, 5)

        # Normalize score 0-100 (higher score = higher risk)
        score = min(100, max(0, (volatility * 100) + (abs(max_dd) * 100) + (abs(var_95) * 1000)))
        
        if score > 75:
            risk_level = "HIGH"
        elif score > 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk": risk_level,
            "score": int(score)
        }

