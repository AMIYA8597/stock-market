import asyncio
import logging
import os
import uuid

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sqlalchemy.future import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.model_artifact import ModelArtifact
from app.models.model_metric import ModelMetric
from research.feature_engineering.pipeline import FeaturePipeline
from research.models.baselines.arima import ARIMADirectionalClassifier
from research.models.baselines.naive import NaiveDirectionalClassifier
from research.models.lightgbm_model.classifier import LightGBMDirectionalClassifier
from research.models.lstm_attention.classifier import LSTMAttentionClassifier
from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier

logger = logging.getLogger(__name__)

TRADE_COST_BPS = 0.0010  # 10 bps


class TrainingPipeline:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.instrument = None
        self.feature_pipeline = FeaturePipeline(symbol)

    async def run(self, frame: pd.DataFrame | None = None) -> dict:
        logger.info(f"Starting A4/A5 Training Pipeline for {self.symbol}")

        if frame is None:
            raise ValueError(
                "CANONICAL_DATASET_REQUIRED: training requires a point-in-time dataset "
                "frame supplied by the canonical data platform"
            )

        required_columns = {"time", "open", "high", "low", "close", "volume"}
        missing_columns = sorted(required_columns - set(frame.columns))
        if missing_columns:
            raise ValueError(
                "CANONICAL_DATASET_INVALID: missing required columns: "
                + ", ".join(missing_columns)
            )

        async with async_session_factory() as session:
            res = await session.execute(select(Instrument).where(Instrument.symbol == self.symbol))
            self.instrument = res.scalars().first()
            if not self.instrument:
                raise ValueError(
                    f"Instrument {self.symbol} not found in DB. Add it to the symbols table "
                    "before training — refusing to persist model artifacts against a fake instrument id."
                )

        df = frame.copy()
        if df.empty or len(df) < 252:
            logger.error("Insufficient data for training. Need at least 252 days.")
            return {}

        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)

        # Add targets
        df["target_return"] = df["close"].pct_change().shift(-1)
        df["target_direction"] = (df["target_return"] > 0).astype(int)

        # Add ret_1d for Naive model
        df["ret_1d"] = df["close"].pct_change()

        df = FeaturePipeline().run(df)

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        train_size = 252
        test_size = 63

        logger.info(f"Shape before dropna: {df.shape}")

        # Keep a copy of regime_label before it gets potentially dropped
        regimes = df["regime_label"].copy()
        regimes = regimes.fillna("unknown")

        # Drop columns with > 10% NaNs
        cols_to_drop = df.columns[df.isna().mean() > 0.1]
        logger.info(f"Dropping high-NaN columns: {list(cols_to_drop)}")
        df.drop(columns=cols_to_drop, inplace=True)

        df.dropna(inplace=True)
        logger.info(f"Shape after dropna: {df.shape}")

        if len(df) < train_size + test_size:
            logger.error("Insufficient data after dropna.")
            return {}

        features = [
            c
            for c in df.columns
            if c
            not in [
                "time",
                "symbol",
                "close",
                "target_return",
                "target_direction",
                "target_direction_1d",
            ]
        ]
        X = df[features]
        y = df["target_direction"]

        models_to_evaluate = {
            "Naive": NaiveDirectionalClassifier(),
            "ARIMA": ARIMADirectionalClassifier(order=(1, 0, 1)),
            "XGBoost": XGBoostDirectionalClassifier(
                n_estimators=50, max_depth=3
            ),  # lower estimators for speed
            "LightGBM": LightGBMDirectionalClassifier(n_estimators=50, max_depth=3),
        }

        try:
            lstm_model = LSTMAttentionClassifier(seq_len=10, epochs=20, lr=0.005)
            models_to_evaluate["LSTM"] = lstm_model
        except Exception as e:
            logger.warning(f"Could not load LSTM: {e}")

        results = {}
        best_model_name = None
        best_cost_adj_sharpe = -999.0

        for name, model in models_to_evaluate.items():
            logger.info(f"Evaluating model: {name}")
            all_preds = pd.Series(dtype=int)
            all_probs = pd.Series(dtype=float)

            for start_idx in range(0, len(df) - train_size - test_size + 1, test_size):
                end_train = start_idx + train_size
                end_test = end_train + test_size

                # Expanding window walk-forward CV
                X_train = X.iloc[0:end_train]
                y_train = y.iloc[0:end_train]

                X_test = X.iloc[end_train:end_test]

                try:
                    if name in ["XGBoost", "LightGBM"]:
                        import optuna
                        from sklearn.model_selection import TimeSeriesSplit

                        def objective(trial, name=name, X_train=X_train, y_train=y_train):
                            max_depth = trial.suggest_int("max_depth", 2, 6)
                            learning_rate = trial.suggest_float(
                                "learning_rate", 1e-3, 0.1, log=True
                            )

                            if name == "XGBoost":
                                temp_model = XGBoostDirectionalClassifier(
                                    n_estimators=50,
                                    max_depth=max_depth,
                                    learning_rate=learning_rate,
                                )
                            else:
                                temp_model = LightGBMDirectionalClassifier(
                                    n_estimators=50,
                                    max_depth=max_depth,
                                    learning_rate=learning_rate,
                                )

                            tscv = TimeSeriesSplit(n_splits=3)
                            scores = []
                            for train_i, val_i in tscv.split(X_train):
                                X_t, y_t = X_train.iloc[train_i], y_train.iloc[train_i]
                                X_v, y_v = X_train.iloc[val_i], y_train.iloc[val_i]

                                temp_model.fit(X_t, y_t)

                                if hasattr(temp_model, "predict_proba_batch"):
                                    p = temp_model.predict_proba_batch(X_v)
                                else:
                                    p = temp_model.predict_proba(X_v)

                                if isinstance(p, float) or isinstance(p, int):
                                    p = pd.Series(p, index=X_v.index)
                                elif isinstance(p, pd.Series):
                                    pass
                                else:
                                    if len(p.shape) > 1 and p.shape[1] == 2:
                                        p = p[:, 1]
                                    elif len(p.shape) > 1:
                                        p = p.squeeze()
                                    p = pd.Series(p, index=X_v.index)

                                pr = (p > 0.5).astype(int)
                                scores.append(accuracy_score(y_v, pr))

                            return np.mean(scores)

                        optuna.logging.set_verbosity(optuna.logging.WARNING)
                        study = optuna.create_study(direction="maximize")
                        study.optimize(objective, n_trials=3)

                        best_params = study.best_params
                        if name == "XGBoost":
                            model = XGBoostDirectionalClassifier(n_estimators=50, **best_params)
                        else:
                            model = LightGBMDirectionalClassifier(n_estimators=50, **best_params)

                        models_to_evaluate[name] = model

                    # fit
                    model.fit(X_train, y_train)

                    # predict
                    if hasattr(model, "predict_proba_batch"):
                        probs = model.predict_proba_batch(X_test)
                    else:
                        probs = model.predict_proba(X_test)

                    if isinstance(probs, float) or isinstance(probs, int):
                        probs = pd.Series(probs, index=X_test.index)
                    elif isinstance(probs, pd.Series):
                        pass
                    else:
                        if len(probs.shape) > 1 and probs.shape[1] == 2:
                            probs = probs[:, 1]
                        elif len(probs.shape) > 1:
                            probs = probs.squeeze()
                        probs = pd.Series(probs, index=X_test.index)
                    preds = (probs > 0.5).astype(int)

                    all_preds = pd.concat([all_preds, pd.Series(preds, index=X_test.index)])
                    all_probs = pd.concat([all_probs, pd.Series(probs, index=X_test.index)])
                except Exception as e:
                    logger.error(f"Error evaluating {name} at fold {start_idx}: {e}")
                    raise RuntimeError(
                        f"TRAINING_FOLD_FAILED: {name} at fold {start_idx}"
                    ) from e

            # Compute metrics for this model
            eval_idx = all_preds.index
            y_eval = y.loc[eval_idx]

            # Use target_return as the day return for cost-adjusted sharpe
            ret_eval = df.loc[eval_idx, "target_return"]

            acc = accuracy_score(y_eval, all_preds)
            prec = precision_score(y_eval, all_preds, zero_division=0)
            rec = recall_score(y_eval, all_preds, zero_division=0)
            try:
                auc = roc_auc_score(y_eval, all_probs)
            except ValueError:
                auc = 0.5

            strat_rets = all_preds * ret_eval
            mean_ret = strat_rets.mean()
            std_ret = strat_rets.std()
            sharpe = (np.sqrt(252) * mean_ret / std_ret) if std_ret > 0 else 0

            turnover = all_preds.diff().abs().fillna(1.0)
            cost = turnover * TRADE_COST_BPS
            cost_adj_rets = strat_rets - cost
            mean_adj_ret = cost_adj_rets.mean()
            std_adj_ret = cost_adj_rets.std()
            cost_adj_sharpe = (np.sqrt(252) * mean_adj_ret / std_adj_ret) if std_adj_ret > 0 else 0

            # Regime Breakdown
            regime_breakdown = {}
            eval_regimes = regimes.loc[eval_idx]
            for reg in eval_regimes.unique():
                reg_mask = eval_regimes == reg
                if reg_mask.sum() > 0:
                    y_reg = y_eval[reg_mask]
                    p_reg = all_preds[reg_mask]
                    regime_breakdown[str(reg)] = float(accuracy_score(y_reg, p_reg))

            logger.info(
                f"{name} Results - Acc: {acc:.4f}, AUC: {auc:.4f}, Sharpe: {sharpe:.4f}, AdjSharpe: {cost_adj_sharpe:.4f}"
            )

            governance_status = "HOLD_FOR_REVIEW" if acc > 0.75 else "UNASSESSED"
            if governance_status == "HOLD_FOR_REVIEW":
                logger.warning(
                    f"Governance review required for {name}: accuracy {acc:.2%} "
                    "exceeds the configured suspicious-performance threshold."
                )

            results[name] = {
                "accuracy": float(acc),
                "precision": float(prec),
                "recall": float(rec),
                "auc": float(auc),
                "sharpe": float(sharpe),
                "cost_adjusted_sharpe": float(cost_adj_sharpe),
                "regime_breakdown": regime_breakdown,
                "governance_status": governance_status,
            }

            # Keep track of winner among tradeable ML models (not Naive/ARIMA which are just baselines)
            if name in ["XGBoost", "LightGBM", "LSTM"]:
                if cost_adj_sharpe > best_cost_adj_sharpe:
                    best_cost_adj_sharpe = cost_adj_sharpe
                    best_model_name = name

        # Decision Gate (Honesty Law)
        # If LSTM didn't beat XGBoost/LightGBM, we flag it.
        # But wait, best_model_name handles whichever is highest.
        # If LSTM was highest, it's best_model_name.
        # But let's check specifically if it beats XGBoost.
        if "LSTM" in results and "XGBoost" in results:
            if (
                results["LSTM"]["cost_adjusted_sharpe"]
                <= results["XGBoost"]["cost_adjusted_sharpe"]
            ):
                logger.info(
                    "Decision Gate: LSTM did NOT beat XGBoost in walk-forward Sharpe. LSTM is NOT recommended for production."
                )
            else:
                logger.info("Decision Gate: LSTM strictly beat XGBoost! It has earned its place.")

        logger.info("\n### Final Walk-Forward Evaluation Metrics\n")
        logger.info("| Model | Accuracy | AUC | Sharpe | Cost-Adj Sharpe |")
        logger.info("|-------|----------|-----|--------|-----------------|")
        for m, res in results.items():
            logger.info(
                f"| {m} | {res['accuracy']:.4f} | {res['auc']:.4f} | {res['sharpe']:.4f} | {res['cost_adjusted_sharpe']:.4f} |"
            )

        logger.info(f"Best Model Selected: {best_model_name}")

        # Train final best model on all data
        final_model = models_to_evaluate[best_model_name]
        final_model.fit(X, y)

        artifact_dir = "data/artifacts"
        os.makedirs(artifact_dir, exist_ok=True)
        version_tag = f"{best_model_name.lower()}_{self.symbol}_{uuid.uuid4().hex[:8]}"
        artifact_path = os.path.join(artifact_dir, f"{version_tag}.pkl")

        # Some custom models have a save method, LSTM might save via torch
        if hasattr(final_model, "save"):
            final_model.save(artifact_path)
        else:
            import joblib

            joblib.dump(final_model, artifact_path)

        async with async_session_factory() as session:
            await session.execute(
                ModelArtifact.__table__.update()
                .where(ModelArtifact.symbol_id == self.instrument.id)
                .values(is_active=False)
            )

            import datetime

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            for m_name, metrics in results.items():
                is_active = m_name == best_model_name

                model_inst = models_to_evaluate[m_name]
                hyper_params = {}
                if hasattr(model_inst, "get_feature_importances"):
                    try:
                        hyper_params["feature_importances"] = model_inst.get_feature_importances()
                    except Exception as e:
                        logger.warning(f"Could not get feature importances for {m_name}: {e}")

                artifact = ModelArtifact(
                    symbol_id=self.instrument.id,
                    model_type=m_name,
                    version_tag=f"{m_name.lower()}_{self.symbol}_{timestamp_str}",
                    artifact_path=artifact_path if is_active else "",
                    hyperparameters=hyper_params,
                    is_active=is_active,
                )
                session.add(artifact)
                await session.flush()

                metric = ModelMetric(
                    artifact_id=artifact.id,
                    accuracy=metrics["accuracy"],
                    precision=metrics["precision"],
                    recall=metrics["recall"],
                    auc=metrics["auc"],
                    sharpe=metrics["sharpe"],
                    cost_adjusted_sharpe=metrics["cost_adjusted_sharpe"],
                    regime_breakdown=metrics["regime_breakdown"],
                )
                session.add(metric)

            await session.commit()

        return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    pipeline = TrainingPipeline("RELIANCE.NS")
    asyncio.run(pipeline.run())
