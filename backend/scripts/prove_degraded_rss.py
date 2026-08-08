import os
import sys
import logging
import urllib.request
import urllib.error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("app.services.sentiment_analyzer")
logger.setLevel(logging.WARNING)

from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer

original_urlopen = urllib.request.urlopen

def mock_urlopen(req, timeout=10):
    raise urllib.error.URLError("Connection timed out")

urllib.request.urlopen = mock_urlopen

print("--- PROVING DEGRADED RSS FETCH ---")
analyzer = FinBERTSentimentAnalyzer()
print("Scraping market news with forced timeout...")
market_hls = analyzer.scrape_market_news()
print(f"Returned {len(market_hls)} headlines from market feeds.")

print("Scraping google news with forced timeout...")
google_hls = analyzer.scrape_google_news("RELIANCE stock")
print(f"Returned {len(google_hls)} headlines from google news.")

print("Done.")
