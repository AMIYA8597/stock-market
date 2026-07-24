# Limitations & Disclaimer

## Data Delay
All real-time market data ingested into the system is **~15 minutes delayed** by default as it relies on free, public yfinance endpoints without a broker API key.

## Probabilistic Predictions & Honest Accuracy
Predictions provided by the ML pipeline (LightGBM, XGBoost, LSTM) are **strictly probabilistic**. 
A realistic, walk-forward tested daily directional accuracy for this dataset sits strictly between **52–62%**. 
Any claim of >90% accuracy in daily financial forecasting is either completely fabricated or the result of "lookahead bias" (leaking future data into the training set). We enforce strict walk-forward cross-validation to maintain honest accuracy. 

## Educational Use Only
This software is an **educational paper-trading system** designed for learning and research purposes. It is **not investment advice**. Do not use these models to trade real capital.
