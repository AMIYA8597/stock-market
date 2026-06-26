"""Sentiment Analyzer — Fetches headlines and analyzes sentiment with FinBERT."""

from __future__ import annotations

import os
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
from typing import List, Dict, Any
import numpy as np

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
        pass

    def initialize(self) -> None:
        if self._initialized:
            return
        
        use_fast_fallback = os.getenv("USE_FAST_FALLBACK", "true").lower() == "true"
        if use_fast_fallback:
            logger.info("Using fast lexicon-based sentiment analyzer fallback (USE_FAST_FALLBACK=true).")
            self._initialized = True
            self.fast_mode = True
            return

        self.fast_mode = False
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            logger.info("Initializing FinBERT model...")
            self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            self.model.eval()
            self._initialized = True
            logger.info("FinBERT model initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}. Sentiment analyzer will fall back to lexicon.")
            self._initialized = True
            self.fast_mode = True

    def scrape_headlines(self) -> List[Dict[str, Any]]:
        """Scrape headlines from public RSS feeds."""
        feeds = [
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "https://www.moneycontrol.com/rss/MCmarkets.xml"
        ]
        
        headlines = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        for url in feeds:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()
                
                root = ET.fromstring(xml_data)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    pub_date = item.find("pubDate")
                    
                    if title is not None:
                        text = title.text or ""
                        date_str = pub_date.text if pub_date is not None else ""
                        headlines.append({
                            "text": text,
                            "date": date_str
                        })
            except Exception as e:
                logger.warning(f"Failed to scrape headlines from {url}: {e}")
                
        # Return unique headlines
        seen = set()
        unique_headlines = []
        for h in headlines:
            if h["text"] not in seen:
                seen.add(h["text"])
                unique_headlines.append(h)
                
        return unique_headlines

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of a single piece of text.
        
        Returns:
            Dict with probabilities for positive, negative, and neutral.
        """
        if not self._initialized:
            # Try to initialize
            self.initialize()
            
        if not self._initialized:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

        # Lexicon fallback
        if getattr(self, "fast_mode", False):
            text_lower = text.lower()
            pos_words = ["bullish", "profit", "growth", "high", "rise", "gain", "upbeat", "positive", "advance", "strong", "outperform", "buy", "beat", "dividend"]
            neg_words = ["bearish", "loss", "drop", "fall", "decline", "down", "negative", "weak", "underperform", "sell", "alert", "caution", "miss", "deficit"]
            
            pos_count = sum(1 for w in pos_words if w in text_lower)
            neg_count = sum(1 for w in neg_words if w in text_lower)
            
            total = pos_count + neg_count
            if total == 0:
                return {"positive": 0.05, "negative": 0.05, "neutral": 0.90}
                
            pos_prob = (pos_count / total) * 0.85
            neg_prob = (neg_count / total) * 0.85
            
            return {
                "positive": round(pos_prob, 3),
                "negative": round(neg_prob, 3),
                "neutral": round(1.0 - pos_prob - neg_prob, 3)
            }

        try:
            import torch
            
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1).squeeze().tolist()
            
            # FinBERT labels: 0: positive, 1: negative, 2: neutral
            return {
                "positive": float(probs[0]),
                "negative": float(probs[1]),
                "neutral": float(probs[2])
            }
        except Exception as e:
            logger.error(f"Sentiment inference failed: {e}. Falling back to lexicon analysis.")
            text_lower = text.lower()
            pos_words = ["bullish", "profit", "growth", "high", "rise", "gain", "upbeat", "positive", "advance", "strong", "outperform", "buy"]
            neg_words = ["bearish", "loss", "drop", "fall", "decline", "down", "negative", "weak", "underperform", "sell", "alert", "caution"]
            pos_count = sum(1 for w in pos_words if w in text_lower)
            neg_count = sum(1 for w in neg_words if w in text_lower)
            total = pos_count + neg_count
            if total == 0:
                return {"positive": 0.05, "negative": 0.05, "neutral": 0.90}
            pos_prob = (pos_count / total) * 0.85
            neg_prob = (neg_count / total) * 0.85
            return {
                "positive": round(pos_prob, 3),
                "negative": round(neg_prob, 3),
                "neutral": round(1.0 - pos_prob - neg_prob, 3)
            }

    def scrape_gdelt_headlines(self, symbol: str) -> List[Dict[str, Any]]:
        """Scrape GDELT API for articles related to the symbol."""
        clean_symbol = symbol.split(".")[0].upper()
        import json
        
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={clean_symbol}&mode=artlist&format=json"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        headlines = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            articles = data.get("articles", [])
            for art in articles:
                text = art.get("title", "")
                date_str = art.get("seendate", "")
                if text:
                    headlines.append({
                        "text": text,
                        "date": date_str
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch from GDELT for {clean_symbol}: {e}")
            
        return headlines

    def get_stock_sentiment(self, symbol: str, headlines: List[Dict[str, Any]] | None = None) -> float:
        """Compute the average sentiment score for a stock.
        
        Score is in [-1, +1] where +1 is bullish, -1 is bearish.
        """
        gdelt_headlines = self.scrape_gdelt_headlines(symbol)
        
        if headlines is None:
            headlines = self.scrape_headlines()
            
        all_headlines = headlines + gdelt_headlines
        if not all_headlines:
            return 0.0

        # Clean symbol name to search for (e.g. RELIANCE.NS -> RELIANCE)
        clean_symbol = symbol.split(".")[0].upper()
        
        relevant_scores = []
        
        # Look for headlines mentioning the symbol or name
        for h in all_headlines:
            text_upper = h["text"].upper()
            if clean_symbol in text_upper or ("NSE" in text_upper and "MARKET" in text_upper):
                sentiment = self.analyze_sentiment(h["text"])
                # Score = positive_prob - negative_prob
                score = sentiment["positive"] - sentiment["negative"]
                relevant_scores.append(score)
                
        if not relevant_scores:
            # Try parsing a wider net
            for h in all_headlines[:5]: # Default to top general market news
                sentiment = self.analyze_sentiment(h["text"])
                score = sentiment["positive"] - sentiment["negative"]
                relevant_scores.append(score)

        return float(np.mean(relevant_scores)) if relevant_scores else 0.0
