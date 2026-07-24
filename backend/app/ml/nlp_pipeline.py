import logging
import os

from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)


class FinBERTPipeline:
    """Local, offline NLP inference pipeline using HuggingFace FinBERT."""

    _instance = None

    @classmethod
    def get_instance(cls, model_name="yiyanghkust/finbert-tone"):
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def __init__(self, model_name="yiyanghkust/finbert-tone"):
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        import torch

        torch.set_num_threads(1)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        try:
            logger.info(
                f"Loading FinBERT model '{model_name}' on {self.device}... (this may take a while to download initially)"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(
                self.device
            )
            self.model.eval()

            # Map labels to indices
            self.pos_idx = -1
            self.neg_idx = -1
            self.neu_idx = -1
            for idx, label in self.model.config.id2label.items():
                lbl = label.lower()
                if "pos" in lbl:
                    self.pos_idx = idx
                elif "neg" in lbl:
                    self.neg_idx = idx
                else:
                    self.neu_idx = idx

            if self.pos_idx == -1:
                self.pos_idx = 1
            if self.neg_idx == -1:
                self.neg_idx = 2
            if self.neu_idx == -1:
                self.neu_idx = 0

            logger.info("FinBERT model loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading FinBERT model: {e}")
            self.model = None

    async def analyze_headline(self, headline: str) -> dict:
        """Evaluate raw headline to compute sentiment polarization and bullish share."""
        if self.model is None or not headline:
            return {"P_pos": 0.333, "P_neg": 0.333, "P_neu": 0.333, "S_p": 0.0, "S_b": 0.5}

        import torch
        import torch.nn.functional as F

        inputs = self.tokenizer(headline, return_tensors="pt", truncation=True, max_length=512).to(
            self.device
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = F.softmax(logits, dim=-1).squeeze().cpu().numpy()

        if probs.ndim == 0:
            probs = [probs]

        P_pos = float(probs[self.pos_idx])
        P_neg = float(probs[self.neg_idx])
        P_neu = float(probs[self.neu_idx])

        # Qualitative Quantitative Features
        # Sentiment Polarisation: S_p = P_pos - P_neg
        S_p = P_pos - P_neg

        # Bullish Share: S_b = P_pos / (P_pos + P_neg)
        S_b = P_pos / (P_pos + P_neg) if (P_pos + P_neg) > 0 else 0.5

        return {"P_pos": P_pos, "P_neg": P_neg, "P_neu": P_neu, "S_p": S_p, "S_b": S_b}
