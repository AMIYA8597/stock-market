class BuySellEngine:
    @staticmethod
    def generate_signal(up_probability: int, confidence: int, risk_score: int) -> str:
        """
        Generate a Buy/Sell signal based on Ensemble Models, Risk, and Confidence.
        """
        if up_probability > 75 and confidence > 80 and risk_score < 50:
            return "Strong Buy"
        elif up_probability > 60 and confidence > 60:
            return "Buy"
        elif up_probability < 25 and confidence > 80 and risk_score < 50:
            return "Strong Sell"
        elif up_probability < 40 and confidence > 60:
            return "Sell"
        else:
            return "Hold"

