"""
ML engine service.

Orchestrates predictions from all 5 models:
1. Temporal Fusion Transformer (TFT)
2. Hybrid CNN-BiLSTM
3. Ensemble XGBoost + LightGBM
4. Hidden Markov Model (Regime Detection)
5. Sentiment-Augmented FinBERT

Fully implemented in Phase 3.
"""
