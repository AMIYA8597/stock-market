"""Sentiment Analyzer — Fetches headlines and analyzes sentiment with FinBERT."""

from __future__ import annotations

import logging
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger(__name__)


class FinBERTSentimentAnalyzer:
    """Singleton sentiment analyzer using ProsusAI/finbert on CPU."""

    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> FinBERTSentimentAnalyzer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        self.vader = None
        self._initialized = getattr(self, "_initialized", False)

    def get_stock_sentiment(self, symbol: str, headlines: list[dict]) -> float:
        """Calculate average sentiment score for a list of headlines."""
        if not headlines:
            return 0.0

        texts = [h["text"] for h in headlines]
        results = self.analyze_sentiment_batch(texts)

        scores = []
        for res in results:
            # Positive contributes +1, Negative contributes -1
            score = res.get("positive", 0.0) - res.get("negative", 0.0)
            scores.append(score)

        return sum(scores) / len(scores)

    def initialize(self) -> None:
        if self._initialized:
            return

        use_fast_fallback = os.getenv("USE_FAST_FALLBACK", "true").lower() == "true"

        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self.vader = SentimentIntensityAnalyzer()
            logger.info("VADER Sentiment Analyzer initialized.")
        except Exception as e:
            logger.error(f"Failed to load VADER: {e}")
            self.vader = None

        if use_fast_fallback:
            logger.info(
                "Using fast lexicon-based sentiment analyzer fallback (USE_FAST_FALLBACK=true)."
            )
            self._initialized = True
            self.fast_mode = True
            return

        self.fast_mode = False
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info("Initializing FinBERT model...")
            self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            self.model.eval()
            self._initialized = True
            logger.info("FinBERT model initialized successfully.")
        except Exception as e:
            logger.error(
                f"Failed to load FinBERT model: {e}. Sentiment analyzer will fall back to lexicon."
            )
            self._initialized = True
            self.fast_mode = True

    def _vader_fallback(self, text: str) -> dict[str, float]:
        if not self.vader:
            return {"positive": 0.05, "negative": 0.05, "neutral": 0.90}

        scores = self.vader.polarity_scores(text)
        # Vader provides pos, neg, neu, compound
        return {"positive": scores["pos"], "negative": scores["neg"], "neutral": scores["neu"]}

    def analyze_sentiment_batch(self, texts: list[str]) -> list[dict[str, float]]:
        """Analyze sentiment of multiple pieces of text in batches.

        Returns:
            List of Dicts with probabilities for positive, negative, and neutral.
        """
        if not texts:
            return []

        if not self._initialized:
            self.initialize()

        if getattr(self, "fast_mode", False) or not hasattr(self, "model"):
            return [self._vader_fallback(t) for t in texts]

        try:
            import torch

            # Process in batches of 32 to avoid OOM even on CPU
            batch_size = 32
            results = []

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                inputs = self.tokenizer(
                    batch_texts, return_tensors="pt", truncation=True, padding=True, max_length=512
                )
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1).tolist()

                for p in probs:
                    # FinBERT labels: 0: positive, 1: negative, 2: neutral
                    results.append(
                        {
                            "positive": float(p[0]),
                            "negative": float(p[1]),
                            "neutral": float(p[2]),
                        }
                    )
            return results
        except Exception as e:
            logger.error(f"Sentiment inference failed: {e}. Falling back to VADER.")
            return [self._vader_fallback(t) for t in texts]

    def analyze_sentiment(self, text: str) -> dict[str, float]:
        return self.analyze_sentiment_batch([text])[0]

    def _resolve_google_news_url(self, url: str) -> str:
        """Resolve Google News redirect URLs."""
        if not url.startswith("https://news.google.com"):
            return url

        try:
            import httpx

            with httpx.Client(follow_redirects=True, timeout=3.0) as client:
                response = client.get(url)
                return str(response.url)
        except Exception as e:
            logger.warning(f"Failed to resolve URL {url}: {e}")
            return url

    def scrape_market_news(self) -> list[dict[str, Any]]:
        """Scrape market-wide headlines from public RSS feeds."""
        feeds = [
            (
                "Economic Times",
                "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            ),
            ("Moneycontrol", "https://www.moneycontrol.com/rss/MCmarkets.xml"),
        ]

        headlines = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        for source_name, url in feeds:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()

                root = ET.fromstring(xml_data)  # nosec B314
                for item in root.findall(".//item"):
                    title = item.find("title")
                    pub_date = item.find("pubDate")
                    link = item.find("link")

                    if title is not None and title.text:
                        text = title.text.strip()
                        date_str = pub_date.text if pub_date is not None else ""
                        link_str = link.text if link is not None else ""
                        headlines.append(
                            {"text": text, "date": date_str, "url": link_str, "source": source_name}
                        )
            except Exception as e:
                logger.warning(
                    f"No sentiment tilt this cycle: Failed to parse XML/scrape headlines from {url}: {e}"
                )

        # Dedupe by text
        seen = set()
        unique_headlines = []
        for h in headlines:
            if h["text"] not in seen:
                seen.add(h["text"])
                unique_headlines.append(h)

        return unique_headlines

    def scrape_google_news(self, query: str) -> list[dict[str, Any]]:
        """Scrape headlines from Google News RSS for a specific query."""
        from urllib.parse import quote

        encoded_query = quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

        headlines = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)  # nosec B314
            for item in root.findall(".//item"):
                title = item.find("title")
                pub_date = item.find("pubDate")
                link = item.find("link")

                if title is not None and title.text:
                    text = title.text.strip()
                    # Clean up " - SourceName" suffix often added by Google News
                    text = re.sub(r"\s+-\s+[^-\n]+$", "", text)

                    date_str = pub_date.text if pub_date is not None else ""
                    link_str = link.text if link is not None else ""
                    resolved_url = self._resolve_google_news_url(link_str)
                    headlines.append(
                        {
                            "text": text,
                            "date": date_str,
                            "url": resolved_url,
                            "source": "Google News",
                        }
                    )
        except Exception as e:
            logger.warning(
                f"No sentiment tilt this cycle: Failed to scrape Google News for {query}: {e}"
            )

        return headlines
