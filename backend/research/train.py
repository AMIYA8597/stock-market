"""CLI for walk-forward ML training pipeline.

Usage:
    cd backend && uv run python research/train.py --symbols RELIANCE.NS TCS.NS --model xgboost lstm_attention
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("research.train")

ARTIFACT_DIR = Path(__file__).parent.parent / "data" / "artifacts"
DIRECTION_THRESHOLD = 0.001


@dataclass
class WalkForwardFold:
    fold: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    sharpe: float
    max_drawdown: float
    n_train: int
    n_test: int


@dataclass
class TrainingReport:
    symbol: str
    model_name: str
    training_date: str
    data_source: str
    n_total_bars: int
    feature_count: int
    folds: list[WalkForwardFold] = field(default_factory=list)
    mean_accuracy: float = 0.0
    std_accuracy: float = 0.0
    mean_precision: float = 0.0
    mean_recall: float = 0.0
    mean_f1: float = 0.0
    mean_sharpe: float = 0.0
    mean_max_drawdown: float = 0.0
    ci_accuracy_lower: float = 0.0
    ci_accuracy_upper: float = 0.0
    governance_status: str = "UNASSESSED"
    artifact_path: str = ""


def fetch_ohlcv(symbol: str, period: str = "3y") -> pd.DataFrame:
    """Fetch OHLCV data from yfinance."""
    import yfinance as yf

    logger.info("Fetching %s of daily data for %s from yfinance", period, symbol)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval="1d")

    if df.empty:
        msg = f"No data returned for {symbol}"
        raise ValueError(msg)

    df.index = pd.DatetimeIndex(df.index).tz_localize(None)
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    df["time"] = df.index
    df = df[["time", "open", "high", "low", "close", "volume"]].copy()
    df = df.dropna()

    logger.info("Fetched %d bars for %s: %s to %s", len(df), symbol, df.index[0].date(), df.index[-1].date())
    return df


def build_target(df: pd.DataFrame) -> pd.Series:
    """Next-bar direction with noise threshold."""
    next_ret = df["close"].pct_change().shift(-1)
    target = pd.Series(np.nan, index=df.index)
    target[next_ret > DIRECTION_THRESHOLD] = 1
    target[next_ret < -DIRECTION_THRESHOLD] = 0
    return target


def compute_signal_sharpe(predictions: pd.Series, returns: pd.Series) -> float:
    signal = predictions.map({1: 1.0, 0: -1.0})
    strat_ret = signal * returns
    mean_r = strat_ret.mean()
    std_r = strat_ret.std()
    if std_r == 0 or np.isnan(std_r):
        return 0.0
    return float(np.sqrt(252) * mean_r / std_r)


def compute_max_drawdown(predictions: pd.Series, returns: pd.Series) -> float:
    signal = predictions.map({1: 1.0, 0: -1.0})
    strat_ret = signal * returns
    cum = (1 + strat_ret).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    return float(dd.min()) if len(dd) > 0 else 0.0


def walk_forward_splits(
    n: int,
    train_months: int = 18,
    val_months: int = 3,
    test_months: int = 3,
    step_months: int = 3,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    days_per_month = 21
    train_days = train_months * days_per_month
    val_days = val_months * days_per_month
    test_days = test_months * days_per_month
    step_days = step_months * days_per_month
    window = train_days + val_days + test_days

    splits: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    start = 0
    while start + window <= n:
        train_idx = np.arange(start, start + train_days)
        val_idx = np.arange(start + train_days, start + train_days + val_days)
        test_idx = np.arange(start + train_days + val_days, start + window)
        splits.append((train_idx, val_idx, test_idx))
        start += step_days

    if not splits:
        msg = f"Insufficient data for walk-forward: need {window} bars, have {n}"
        raise ValueError(msg)
    return splits


def train_xgboost_fold(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    features: list[str],
) -> pd.Series:
    from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier

    clf = XGBoostDirectionalClassifier(n_estimators=200, max_depth=4, learning_rate=0.05)
    clf.features = features
    clf.fit(x_train, y_train)
    probs = clf.predict_proba_batch(x_test)
    return (probs > 0.5).astype(int)


def train_lstm_fold(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    features: list[str],
) -> pd.Series:
    from research.models.lstm_attention.classifier import LSTMAttentionClassifier

    clf = LSTMAttentionClassifier(seq_len=10, epochs=20, lr=0.001)
    clf.features = features
    clf.fit(x_train, y_train)
    probs = clf.predict_proba_batch(x_test)
    return (probs > 0.5).astype(int)


TRAIN_FN = {
    "xgboost": train_xgboost_fold,
    "lstm_attention": train_lstm_fold,
}


def run_walk_forward(
    symbol: str,
    model_name: str,
    df: pd.DataFrame,
    features: list[str],
    x: pd.DataFrame,
    y: pd.Series,
    returns: pd.Series,
) -> TrainingReport:
    train_fn = TRAIN_FN[model_name]
    splits = walk_forward_splits(len(x))
    report = TrainingReport(
        symbol=symbol,
        model_name=model_name,
        training_date=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        data_source="yfinance",
        n_total_bars=len(df),
        feature_count=len(features),
    )

    logger.info("Running %d-fold walk-forward for %s on %s", len(splits), model_name, symbol)

    for i, (train_idx, _val_idx, test_idx) in enumerate(splits):
        combined_train = np.concatenate([train_idx, _val_idx])
        x_tr = x.iloc[combined_train]
        y_tr = y.iloc[combined_train]
        x_te = x.iloc[test_idx]
        y_te = y.iloc[test_idx]
        ret_test = returns.iloc[test_idx]

        preds = train_fn(x_tr, y_tr, x_te, features)

        acc = accuracy_score(y_te, preds)
        prec = precision_score(y_te, preds, zero_division=0)
        rec = recall_score(y_te, preds, zero_division=0)
        f1_val = f1_score(y_te, preds, zero_division=0)
        sharpe = compute_signal_sharpe(preds, ret_test)
        mdd = compute_max_drawdown(preds, ret_test)

        fold_result = WalkForwardFold(
            fold=i + 1,
            train_start=str(df.index[train_idx[0]].date()),
            train_end=str(df.index[combined_train[-1]].date()),
            test_start=str(df.index[test_idx[0]].date()),
            test_end=str(df.index[test_idx[-1]].date()),
            accuracy=acc,
            precision=prec,
            recall=rec,
            f1=f1_val,
            sharpe=sharpe,
            max_drawdown=mdd,
            n_train=len(combined_train),
            n_test=len(test_idx),
        )
        report.folds.append(fold_result)
        logger.info(
            "  Fold %d: acc=%.4f prec=%.4f rec=%.4f f1=%.4f sharpe=%.3f mdd=%.3f",
            i + 1, acc, prec, rec, f1_val, sharpe, mdd,
        )

    accs = [f.accuracy for f in report.folds]
    report.mean_accuracy = float(np.mean(accs))
    report.std_accuracy = float(np.std(accs))
    report.mean_precision = float(np.mean([f.precision for f in report.folds]))
    report.mean_recall = float(np.mean([f.recall for f in report.folds]))
    report.mean_f1 = float(np.mean([f.f1 for f in report.folds]))
    report.mean_sharpe = float(np.mean([f.sharpe for f in report.folds]))
    report.mean_max_drawdown = float(np.mean([f.max_drawdown for f in report.folds]))

    n_folds = len(accs)
    if n_folds > 1:
        se = report.std_accuracy / np.sqrt(n_folds)
        t_val = 2.0
        report.ci_accuracy_lower = report.mean_accuracy - t_val * se
        report.ci_accuracy_upper = report.mean_accuracy + t_val * se
    else:
        report.ci_accuracy_lower = report.mean_accuracy
        report.ci_accuracy_upper = report.mean_accuracy

    if report.mean_accuracy > 0.75:
        report.governance_status = "HALT_SUSPECTED_LEAKAGE"
        logger.warning(
            "HONESTY LAW TRIGGERED: %s on %s achieved walk-forward accuracy %.4f > 0.75. "
            "Suspected data leakage. Artifacts NOT saved.",
            model_name, symbol, report.mean_accuracy,
        )
    else:
        report.governance_status = "PASSED"

    return report


def save_artifact(
    symbol: str,
    model_name: str,
    x: pd.DataFrame,
    y: pd.Series,
    features: list[str],
) -> str:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_sym = symbol.replace(".", "_")
    filename = f"{model_name}_{safe_sym}_{timestamp}.pkl"
    path = ARTIFACT_DIR / filename

    if model_name == "xgboost":
        from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier

        clf = XGBoostDirectionalClassifier(n_estimators=200, max_depth=4, learning_rate=0.05)
        clf.features = features
        clf.fit(x, y)
        clf.save(path)
    elif model_name == "lstm_attention":
        from research.models.lstm_attention.classifier import LSTMAttentionClassifier

        clf = LSTMAttentionClassifier(seq_len=10, epochs=20, lr=0.001)
        clf.features = features
        clf.fit(x, y)
        clf.save(path)

    logger.info("Saved artifact: %s", path)
    return str(path)


def print_report(report: TrainingReport) -> None:
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"WALK-FORWARD RESULTS: {report.model_name} on {report.symbol}")
    print(sep)
    print(f"Data source: {report.data_source}")
    print(f"Training date: {report.training_date}")
    print(f"Total bars: {report.n_total_bars} | Features: {report.feature_count}")
    print(f"Direction threshold: {DIRECTION_THRESHOLD * 100:.1f}%")
    print()

    for f in report.folds:
        print(
            f"  Fold {f.fold}: {f.train_start}->{f.train_end} | "
            f"{f.test_start}->{f.test_end} | "
            f"acc={f.accuracy:.4f} prec={f.precision:.4f} rec={f.recall:.4f} "
            f"f1={f.f1:.4f} sharpe={f.sharpe:.3f} mdd={f.max_drawdown:.3f}"
        )

    print()
    print(f"Mean accuracy:     {report.mean_accuracy:.4f} +/- {report.std_accuracy:.4f}")
    print(f"95% CI accuracy:   [{report.ci_accuracy_lower:.4f}, {report.ci_accuracy_upper:.4f}]")
    print(f"Mean precision:    {report.mean_precision:.4f}")
    print(f"Mean recall:       {report.mean_recall:.4f}")
    print(f"Mean F1:           {report.mean_f1:.4f}")
    print(f"Mean Sharpe:       {report.mean_sharpe:.3f}")
    print(f"Mean max drawdown: {report.mean_max_drawdown:.3f}")
    print(f"Governance:        {report.governance_status}")
    if report.artifact_path:
        print(f"Artifact:          {report.artifact_path}")
    print(f"{sep}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="NeuroQuant ML Training CLI")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "SBIN.NS"],
    )
    parser.add_argument(
        "--model",
        nargs="+",
        default=["xgboost", "lstm_attention"],
        choices=["xgboost", "lstm_attention"],
    )
    parser.add_argument("--walk-forward", action="store_true", default=True)
    parser.add_argument("--period", default="3y")
    parser.add_argument("--save-artifacts", action="store_true", default=True)
    parser.add_argument("--output-json", type=str, default=None)
    args = parser.parse_args()

    all_reports: list[TrainingReport] = []
    start_time = time.time()

    for symbol in args.symbols:
        try:
            df = fetch_ohlcv(symbol, period=args.period)
        except Exception:
            logger.exception("Failed to fetch data for %s", symbol)
            continue

        if len(df) < 504:
            logger.error("Insufficient data for %s: %d bars (need 504+)", symbol, len(df))
            continue

        from research.feature_engineering.api import build_features

        featured_df = build_features(df, mode="backtest")
        target = build_target(featured_df)

        valid_mask = target.notna()
        featured_df = featured_df[valid_mask]
        target = target[valid_mask].astype(int)

        exclude_cols = {
            "time", "symbol", "open", "high", "low", "close", "volume",
            "target_direction_1d", "target_return", "target_direction",
        }
        features = [
            c for c in featured_df.select_dtypes(include=[np.number]).columns
            if c not in exclude_cols
        ]

        x_all = featured_df[features].copy()
        # Drop columns that are >30% NaN (e.g. regime_label before HMM is trained)
        nan_frac = x_all.isna().mean()
        usable = nan_frac[nan_frac <= 0.3].index.tolist()
        dropped = set(features) - set(usable)
        if dropped:
            logger.info("Dropping %d high-NaN columns: %s", len(dropped), sorted(dropped)[:10])
        features = usable
        x_all = x_all[features]

        y_all = target.copy()
        rets = featured_df["close"].pct_change().shift(-1).loc[x_all.index]

        valid = x_all.notna().all(axis=1) & y_all.notna() & rets.notna()
        x_all = x_all[valid]
        y_all = y_all[valid]
        rets = rets[valid]

        logger.info("%s: %d clean samples, %d features", symbol, len(x_all), len(features))

        for model_name in args.model:
            try:
                report = run_walk_forward(symbol, model_name, df, features, x_all, y_all, rets)

                if report.governance_status == "PASSED" and args.save_artifacts:
                    report.artifact_path = save_artifact(symbol, model_name, x_all, y_all, features)
                elif report.governance_status == "HALT_SUSPECTED_LEAKAGE":
                    logger.warning("Skipping artifact save for %s/%s", model_name, symbol)

                print_report(report)
                all_reports.append(report)

            except Exception:
                logger.exception("Training failed for %s/%s", model_name, symbol)

    elapsed = time.time() - start_time
    logger.info("Training complete in %.1fs for %d model/symbol combinations", elapsed, len(all_reports))

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f_out:
            json.dump([asdict(r) for r in all_reports], f_out, indent=2)
        logger.info("Report saved to %s", output_path)

    if any(r.governance_status == "HALT_SUSPECTED_LEAKAGE" for r in all_reports):
        logger.error("One or more models triggered the honesty law.")
        sys.exit(1)


if __name__ == "__main__":
    main()
