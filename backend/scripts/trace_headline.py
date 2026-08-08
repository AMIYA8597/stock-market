import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(message)s")

from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer

analyzer = FinBERTSentimentAnalyzer()
analyzer.initialize()

print("--- TRACING A SINGLE HEADLINE THROUGH FINBERT ---")
symbol = "RELIANCE.NS"
headline_text = "Reliance Industries Q3 profits surge 25% despite weak margins, driving immense market optimism."
headlines = [{"text": headline_text, "date": "", "url": "", "source": "FakeNews"}]

print(f"Symbol: {symbol}")
print(f"Headline: {headline_text}")

# First let's get the raw positive/negative/neutral probs
probs = analyzer.analyze_sentiment_batch([headline_text])[0]
print(f"Raw FinBERT Probs: Positive={probs['positive']:.4f}, Negative={probs['negative']:.4f}, Neutral={probs['neutral']:.4f}")

# Next get the stock sentiment
sentiment_score = analyzer.get_stock_sentiment(symbol, headlines)
print(f"Attributed Sentiment Score for {symbol}: {sentiment_score:.4f}")

# Finally, sentiment_tilt computation as per fusion rule
sentiment_tilt = sentiment_score * 0.15
print(f"Final Sentiment Tilt applied to {symbol} ensemble: {sentiment_tilt:.4f}")
print("Done.")
