# Reviewer / Viva Q&A

**"What is the accuracy?"**
At full coverage, the RGS-Fusion model achieves [53.60%](./results/proposed/rgs_fusion.json) (95% CI 52.8%–54.4%, binomial p=0.0012) on the 20-day horizon, which is comparable to JKX's 52.5–53.6% and realistic for liquid equities. On the 10% most confident predictions selected by our Learn-then-Test (LTT) risk controller, precision increases to 61.0% with a rigorous distribution-free risk-controlled bound.

**"What is the RR?"**
The strategy achieved a realised payoff ratio (RR) of [0.92](./results/backtest/metrics.json), a win rate of 57.1%, and a profit factor of 1.23. The expectancy was +0.11% per trade net of 0.34% round-trip delivery costs.

**"Supervision details?"**
Supervised binary classification was used, with labels based on forward h-day excess returns. These labels are inherently forward-looking and thus are strictly known only after $t+h$. To prevent leakage, we purge $h$ days and embargo $e = \max(h, 5)$ days between training, calibration, and testing sets. Hyperparameters are chosen using an inner chronological validation set.

**"Does it beat LSTM papers?"**
Under identical, clean evaluation protocols, our model achieves statistical significance (Diebold-Mariano test with HAC correction, p=0.0410). However, our Leakage Audit demonstrates that previously published LSTM papers reporting 80-90% accuracy were inflated by 20-30 points due to invalid evaluation protocols (such as random splitting on overlapping windows, or full-sample min-max scaling). 

**"Why is it novel?"**
To our knowledge, this is the first study of NSE equities that combines (i) an equal-information comparison of chart-image and numeric representations, (ii) causal regime gating using a filtered HMM posterior, and (iii) distribution-free risk-controlled selective prediction (Learn-then-Test), under purged walk-forward evaluation with Indian transaction costs and multiple-testing-corrected inference.

**"Limitations?"**
Financial time series are not fully exchangeable, meaning the LTT selective-risk guarantees are approximate in practice. Additionally, survivorship bias is present because `yfinance` lacks comprehensive historical data for delisted NSE stocks, and our current backtest does not model intraday execution slippage or margin requirements for shorts.

**"What did NOT work?"**
Zero-shot Time Series Foundation Models (like Chronos and TimesFM) did not perform better than random guessing on directional prediction, consistent with Rahimikia et al. Pattern-based approaches (e.g., YOLO detection on candlestick charts) did not improve predictive accuracy over raw image features. Finally, naive image rescaling (using the entire dataset's max/min) was shown to massively leak future information, and strictly per-window scaling reduced "accuracy" drastically, proving the JKX hypothesis.
