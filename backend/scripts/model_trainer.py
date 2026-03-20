"""Model training orchestration script.

Trains available research models against OHLCV data and persists checkpoints.

Examples:
    python scripts/model_trainer.py --model hmm --symbol RELIANCE
    python scripts/model_trainer.py --model tft --symbol TCS
    python scripts/model_trainer.py --model gnn --universe NSE
    python scripts/model_trainer.py --model all --universe NSE
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.core.database import async_session_factory
from research.models.hmm_garch.trainer import HMMGarchTrainer


async def _load_symbol_ohlcv(symbol: str, interval: str = "1d") -> pd.DataFrame:
    query = text(
        """
        SELECT o.time, o.close
        FROM ohlcv o
        JOIN symbols s ON s.id = o.symbol_id
        WHERE UPPER(s.ticker) = :symbol
          AND o.interval = :interval
        ORDER BY o.time ASC
        """
    )
    async with async_session_factory() as session:
        rows = (await session.execute(query, {"symbol": symbol.upper(), "interval": interval})).mappings().all()

    if not rows:
        return pd.DataFrame(columns=["time", "close"])

    frame = pd.DataFrame([dict(r) for r in rows])
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame["close"] = frame["close"].astype(float)
    return frame


async def _load_universe_returns(exchange: str = "NSE", interval: str = "1d", max_symbols: int = 30) -> pd.DataFrame:
    query = text(
        """
        SELECT s.ticker, o.time, o.close
        FROM ohlcv o
        JOIN symbols s ON s.id = o.symbol_id
        WHERE o.interval = :interval
          AND UPPER(s.exchange) = :exchange
        ORDER BY s.ticker, o.time ASC
        """
    )
    async with async_session_factory() as session:
        rows = (await session.execute(query, {"interval": interval, "exchange": exchange.upper()})).mappings().all()

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame([dict(r) for r in rows])
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame["close"] = frame["close"].astype(float)

    closes = frame.pivot(index="time", columns="ticker", values="close").sort_index()
    returns = np.log(closes / closes.shift(1)).dropna(how="all")

    valid_cols = [col for col in returns.columns if returns[col].notna().sum() >= 200]
    returns = returns[valid_cols]
    if returns.shape[1] > max_symbols:
        returns = returns.iloc[:, :max_symbols]

    return returns.dropna(axis=0, how="any")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


async def _train_hmm(symbol: str, interval: str) -> dict[str, Any]:
    frame = await _load_symbol_ohlcv(symbol, interval)
    if len(frame) < 300:
        raise RuntimeError(f"Not enough rows for HMM training for {symbol}. Need >=300, found {len(frame)}")

    returns = np.log(frame["close"] / frame["close"].shift(1)).dropna().to_numpy(dtype=float)
    trainer = HMMGarchTrainer(checkpoint_dir="data/models/hmm_garch")
    train_result, regime_result = trainer.train(returns=returns, symbol=symbol.upper())

    return {
        "model": "hmm",
        "symbol": symbol.upper(),
        "samples": int(train_result.n_samples),
        "final_state": int(train_result.final_state),
        "mean_conditional_vol": float(train_result.mean_conditional_vol),
        "checkpoint": train_result.checkpoint_path,
        "forecast_5d_last": float(regime_result.forecast_5d[-1]),
        "forecast_21d_last": float(regime_result.forecast_21d[-1]),
    }


async def _train_tft(symbol: str, interval: str, epochs: int) -> dict[str, Any]:
    try:
        import torch

        from research.models.tft.architecture import TemporalFusionTransformer
        from research.models.tft.dataset import TimeSeriesDatasetConfig, build_tft_training_tensors
        from research.models.tft.trainer import TFTTrainConfig, train_tft
    except Exception as exc:
        raise RuntimeError(f"TFT dependencies unavailable: {exc}")

    frame = await _load_symbol_ohlcv(symbol, interval)
    if len(frame) < 260:
        raise RuntimeError(f"Not enough rows for TFT training for {symbol}. Need >=260, found {len(frame)}")

    frame = frame.copy()
    frame["ret_1d"] = np.log(frame["close"] / frame["close"].shift(1))
    frame["ret_5d"] = np.log(frame["close"] / frame["close"].shift(5))
    frame["vol_21d"] = frame["ret_1d"].rolling(21).std()
    frame["mom_21d"] = frame["close"] / frame["close"].shift(21) - 1.0
    frame = frame.dropna().reset_index(drop=True)

    if len(frame) < 220:
        raise RuntimeError(f"Insufficient post-feature rows for TFT for {symbol}: {len(frame)}")

    feature_cols = ["ret_1d", "ret_5d", "vol_21d", "mom_21d"]
    features = frame[feature_cols].to_numpy(dtype=np.float32)
    # Shape to (T, n_features, feature_dim=1) expected by TFT VSN.
    features_3d = features[:, :, None]
    targets = frame["ret_1d"].to_numpy(dtype=np.float32)

    ds_cfg = TimeSeriesDatasetConfig(seq_len=60, horizon=21)
    x_hist, x_fut, y = build_tft_training_tensors(features_3d, targets, ds_cfg)

    model = TemporalFusionTransformer(n_features=features_3d.shape[1], feature_dim=1, horizon=21)
    train_cfg = TFTTrainConfig(epochs=max(1, epochs), batch_size=64)
    losses = train_tft(model=model, x_hist=x_hist, x_fut=x_fut, y=y, cfg=train_cfg, device="cpu")

    out_dir = Path("data/models/tft")
    _ensure_dir(out_dir)
    ckpt_path = out_dir / f"{symbol.lower()}_tft.pt"
    torch.save(
        {
            "symbol": symbol.upper(),
            "state_dict": model.state_dict(),
            "feature_cols": feature_cols,
            "seq_len": ds_cfg.seq_len,
            "horizon": ds_cfg.horizon,
            "losses": losses,
        },
        ckpt_path,
    )

    return {
        "model": "tft",
        "symbol": symbol.upper(),
        "samples": int(x_hist.shape[0]),
        "epochs": int(epochs),
        "final_loss": float(losses[-1]),
        "checkpoint": str(ckpt_path),
    }


async def _train_gnn(exchange: str, interval: str, epochs: int) -> dict[str, Any]:
    try:
        import torch

        from research.models.gnn.trainer import GNNTrainConfig, train_gnn
    except Exception as exc:
        raise RuntimeError(f"GNN dependencies unavailable: {exc}")

    returns = await _load_universe_returns(exchange=exchange, interval=interval)
    if returns.empty or returns.shape[1] < 5:
        raise RuntimeError("Not enough cross-asset data for GNN training (need >=5 symbols with history).")

    # Use last 252 days for graph, simple node features from rolling statistics.
    ret_window = returns.tail(252)
    symbols = list(ret_window.columns)

    mean_20 = ret_window.tail(20).mean().to_numpy(dtype=np.float32)
    vol_20 = ret_window.tail(20).std().to_numpy(dtype=np.float32)
    mom_60 = (1.0 + ret_window.tail(60)).prod(axis=0).to_numpy(dtype=np.float32) - 1.0
    node_features = np.column_stack([mean_20, vol_20, mom_60]).astype(np.float32)

    # Predict next-day proxy using last observed return.
    targets = ret_window.iloc[-1].to_numpy(dtype=np.float32)

    cfg = GNNTrainConfig(epochs=max(1, epochs), corr_threshold=0.2, top_k=8)
    model, losses = train_gnn(
        returns_window=ret_window.to_numpy(dtype=np.float32),
        node_features=node_features,
        targets=targets,
        symbols=symbols,
        cfg=cfg,
        device="cpu",
    )

    out_dir = Path("data/models/gnn")
    _ensure_dir(out_dir)
    ckpt_path = out_dir / f"{exchange.lower()}_gnn.pt"
    torch.save(
        {
            "exchange": exchange.upper(),
            "symbols": symbols,
            "state_dict": model.state_dict(),
            "losses": losses,
        },
        ckpt_path,
    )

    return {
        "model": "gnn",
        "exchange": exchange.upper(),
        "n_symbols": len(symbols),
        "epochs": int(epochs),
        "final_loss": float(losses[-1]),
        "checkpoint": str(ckpt_path),
    }


async def run_training(model: str, symbol: str | None, universe: str | None, interval: str, epochs: int) -> int:
    selected = model.lower()
    symbol_value = (symbol or "NIFTY").upper()
    exchange_value = (universe or "NSE").upper()

    reports: list[dict[str, Any]] = []

    if selected in {"hmm", "all"}:
        reports.append(await _train_hmm(symbol=symbol_value, interval=interval))

    if selected in {"tft", "all"}:
        reports.append(await _train_tft(symbol=symbol_value, interval=interval, epochs=epochs))

    if selected in {"gnn", "all"}:
        reports.append(await _train_gnn(exchange=exchange_value, interval=interval, epochs=epochs))

    if selected in {"xgboost_lgbm", "cnn_bilstm", "finbert"}:
        raise RuntimeError(
            f"Model '{selected}' is not wired in backend/research yet. Supported now: hmm, tft, gnn, all."
        )

    print(json.dumps({"status": "ok", "reports": reports}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="QuantEdge model trainer")
    parser.add_argument(
        "--model",
        type=str,
        default="all",
        choices=["all", "hmm", "tft", "gnn", "cnn_bilstm", "xgboost_lgbm", "finbert"],
    )
    parser.add_argument("--symbol", type=str, help="Single symbol ticker (for hmm/tft)")
    parser.add_argument("--universe", type=str, help="Exchange/universe key (for gnn), e.g. NSE")
    parser.add_argument("--interval", type=str, default="1d", help="OHLCV interval")
    parser.add_argument("--epochs", type=int, default=20, help="Epochs for trainable deep models")
    args = parser.parse_args()

    try:
        return asyncio.run(
            run_training(
                model=args.model,
                symbol=args.symbol,
                universe=args.universe,
                interval=args.interval,
                epochs=args.epochs,
            )
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
