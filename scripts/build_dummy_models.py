import os
models_dir = os.path.join("backend", "app", "models")

dummies = {
    "feature_vectors": "FeatureVector",
    "journal": "TradeJournal",
    "model_artifact": "ModelArtifact",
    "model_metric": "ModelMetric",
    "prediction": "MLPrediction",
    "regime_states": "RegimeState",
    "sentiment": "NewsSentiment",
    "signal": "EnsembleSignal",
    "transactions": "Transaction",
    "watchlist": "UserWatchlist",
    "alert": "Alert",
    "auth_token": ["PasswordResetToken", "RefreshSession"],
    "backtest": "BacktestJob",
    "blog": "BlogPost",
    "csrf_token": "CSRFToken",
    "email_job": "EmailJob",
    "notification": "Notification",
    "portfolio": "PortfolioHolding",
    "paper_trading": ["PaperOrder", "PaperPosition", "PaperWallet"],
    "payment": "PaymentTransaction",
}

for module, classes in dummies.items():
    with open(os.path.join(models_dir, f"{module}.py"), "w") as f:
        f.write("from sqlalchemy.orm import declarative_base\n")
        f.write("Base = declarative_base()\n")
        if isinstance(classes, list):
            for cls in classes:
                f.write(f"class {cls}(Base):\n    __tablename__ = 'dummy_{cls.lower()}'\n    id = 1\n")
        else:
            f.write(f"class {classes}(Base):\n    __tablename__ = 'dummy_{classes.lower()}'\n    id = 1\n")
