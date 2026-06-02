"""Deterministic service layer for advanced intelligence endpoints.

This module provides consistent, typed API payloads while model training and
live market integrations are built out incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from random import Random

from app.schemas.intelligence import (
    CorrelationEdge,
    CorrelationGraphResponse,
    CorrelationNode,
    CounterfactualFeatureChange,
    CounterfactualRequest,
    CounterfactualResponse,
    DriftItem,
    EconomicCalendarEvent,
    EnsembleSignal,
    EnsembleWeightPoint,
    ExplainAttentionResponse,
    ExplainShapResponse,
    FactorExposureItem,
    FactorExposureResponse,
    GNNSignal,
    HMMGarchSignal,
    LSTMAttnSignal,
    ModelAccuracyItem,
    RegimeCurrentResponse,
    RegimeDetails,
    RegimeHistoryPoint,
    RegimeStatisticsItem,
    SHAPContribution,
    SignalHistoryPoint,
    SignalResponse,
    TFTSignal,
    XGBoostSignal,
)

REGIME_STATES = ["BULL", "BEAR", "SIDEWAYS", "CRISIS"]
MODELS = ["tft", "hmm_garch", "gnn", "lstm_attn", "xgboost", "ensemble"]


@dataclass(frozen=True)
class IntelligenceService:
    """Generates deterministic data contracts for intelligence APIs."""

    def _seed(self, key: str) -> int:
        digest = sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def _direction(self, score: float) -> str:
        if score > 0.6:
            return "STRONG_BUY"
        if score > 0.2:
            return "BUY"
        if score < -0.6:
            return "STRONG_SELL"
        if score < -0.2:
            return "SELL"
        return "NEUTRAL"

    def _normalize_weights(self, raw: dict[str, float]) -> dict[str, float]:
        total = sum(raw.values())
        return {k: round(v / total, 4) for k, v in raw.items()}

    def get_signal(self, symbol: str) -> SignalResponse:
        rng = Random(self._seed(symbol.upper()))
        model_weights = self._normalize_weights(
            {
                "tft": 0.24 + rng.random() * 0.08,
                "hmm_garch": 0.18 + rng.random() * 0.08,
                "gnn": 0.14 + rng.random() * 0.07,
                "lstm_attn": 0.17 + rng.random() * 0.07,
                "xgboost": 0.16 + rng.random() * 0.07,
            }
        )
        raw_scores = {
            "tft": rng.uniform(-1, 1),
            "hmm_garch": rng.uniform(-1, 1),
            "gnn": rng.uniform(-1, 1),
            "lstm_attn": rng.uniform(-1, 1),
            "xgboost": rng.uniform(-1, 1),
        }
        ensemble_score = sum(raw_scores[k] * model_weights[k] for k in raw_scores)
        disagreement = max(raw_scores.values()) - min(raw_scores.values())
        confidence = max(0.05, min(0.99, 1.0 - disagreement / 2.0))

        regime_probs = self._normalize_weights({state: rng.random() for state in REGIME_STATES})
        current_state = max(regime_probs, key=regime_probs.get)

        return SignalResponse(
            symbol=symbol.upper(),
            timestamp=datetime.now(UTC),
            ensemble=EnsembleSignal(
                signal=self._direction(ensemble_score),
                confidence=round(confidence, 4),
                direction=self._direction(ensemble_score),
                kelly_fraction=round(min(0.25, max(0.0, ensemble_score * confidence / 2 + 0.125)), 4),
            ),
            models={
                "tft": TFTSignal(
                    p10=round(-0.018 + rng.random() * 0.01, 5),
                    p50=round(raw_scores["tft"] * 0.012, 5),
                    p90=round(0.016 + rng.random() * 0.01, 5),
                    raw_signal=round(raw_scores["tft"], 4),
                    horizon_days=1,
                ),
                "hmm_garch": HMMGarchSignal(
                    regime_signal=current_state,
                    vol_forecast_1d=round(0.009 + rng.random() * 0.02, 5),
                    vol_forecast_21d=round(0.02 + rng.random() * 0.05, 5),
                ),
                "gnn": GNNSignal(
                    spillover_risk=round(rng.random(), 4),
                    embedding_norm=round(0.6 + rng.random() * 1.8, 4),
                    top_correlated_assets=["NIFTY50", "BANKNIFTY", "FINNIFTY"],
                ),
                "lstm_attn": LSTMAttnSignal(
                    raw_signal=round(raw_scores["lstm_attn"], 4),
                    attention_peaks=[
                        {"timestep": 7.0, "weight": round(0.15 + rng.random() * 0.1, 4)},
                        {"timestep": 21.0, "weight": round(0.2 + rng.random() * 0.1, 4)},
                    ],
                ),
                "xgboost": XGBoostSignal(
                    raw_signal=round(raw_scores["xgboost"], 4),
                    top_features=[
                        {"name": "rsi_14", "shap_value": round(rng.uniform(-0.2, 0.2), 4)},
                        {"name": "volatility_21d", "shap_value": round(rng.uniform(-0.2, 0.2), 4)},
                        {"name": "momentum_63d", "shap_value": round(rng.uniform(-0.2, 0.2), 4)},
                    ],
                ),
            },
            model_weights=model_weights,
            regime=RegimeDetails(
                state=current_state,
                probs=regime_probs,
                transition_probs=self._normalize_weights({state: rng.random() for state in REGIME_STATES}),
            ),
        )

    def get_bulk_signals(self, symbols: list[str]) -> list[SignalResponse]:
        return [self.get_signal(symbol) for symbol in symbols]

    def get_signal_history(self, symbol: str, model: str, days: int) -> list[SignalHistoryPoint]:
        rng = Random(self._seed(f"history:{symbol}:{model}:{days}"))
        now = datetime.now(UTC)
        points: list[SignalHistoryPoint] = []
        for i in range(days):
            signal = rng.uniform(-1, 1)
            realized = signal * 0.004 + rng.uniform(-0.01, 0.01)
            points.append(
                SignalHistoryPoint(
                    timestamp=now - timedelta(days=days - i),
                    signal=round(signal, 4),
                    actual_return=round(realized, 5),
                    model=model,
                )
            )
        return points

    def get_regime_current(self) -> RegimeCurrentResponse:
        rng = Random(self._seed("regime_current"))
        probs = self._normalize_weights({state: rng.random() for state in REGIME_STATES})
        rows = []
        for _ in REGIME_STATES:
            row = self._normalize_weights({state: rng.random() for state in REGIME_STATES})
            rows.append([row[state] for state in REGIME_STATES])

        return RegimeCurrentResponse(
            state=max(probs, key=probs.get),
            probs=probs,
            transition_matrix=rows,
            cond_vol_1d=0.013,
            cond_vol_5d=0.022,
            cond_vol_21d=0.041,
            days_in_state=17,
            last_transition_date=date.today() - timedelta(days=17),
        )

    def get_regime_history(self, days: int) -> list[RegimeHistoryPoint]:
        rng = Random(self._seed(f"regime_history:{days}"))
        rows: list[RegimeHistoryPoint] = []
        for i in range(days):
            d = date.today() - timedelta(days=days - i)
            probs = self._normalize_weights({state: rng.random() for state in REGIME_STATES})
            rows.append(
                RegimeHistoryPoint(
                    time=d,
                    state=max(probs, key=probs.get),
                    probs=probs,
                    cond_vol=round(0.008 + rng.random() * 0.03, 5),
                )
            )
        return rows

    def get_regime_statistics(self) -> list[RegimeStatisticsItem]:
        return [
            RegimeStatisticsItem(state="BULL", avg_duration=48.2, avg_return=0.0012, avg_vol=0.011, freq=0.36),
            RegimeStatisticsItem(state="BEAR", avg_duration=29.7, avg_return=-0.0016, avg_vol=0.022, freq=0.23),
            RegimeStatisticsItem(state="SIDEWAYS", avg_duration=38.5, avg_return=0.0002, avg_vol=0.009, freq=0.31),
            RegimeStatisticsItem(state="CRISIS", avg_duration=11.3, avg_return=-0.0034, avg_vol=0.038, freq=0.10),
        ]

    def get_shap(self, symbol: str) -> ExplainShapResponse:
        rng = Random(self._seed(f"shap:{symbol}"))
        features = [
            "rsi_14",
            "macd_hist",
            "realized_vol_21d",
            "momentum_63d",
            "order_flow_imbalance",
            "earnings_surprise",
        ]
        contribs = [
            SHAPContribution(
                name=name,
                shap_val=round(rng.uniform(-0.4, 0.4), 4),
                feature_val=round(rng.uniform(-3, 3), 4),
                pct_rank=round(rng.uniform(0.1, 0.99), 4),
            )
            for name in features
        ]
        output = sum(item.shap_val for item in contribs)
        return ExplainShapResponse(
            model="xgboost",
            feature_contributions=contribs,
            base_value=0.0,
            output_value=round(output, 4),
            waterfall_ready=True,
        )

    def get_attention(self, symbol: str, model: str) -> ExplainAttentionResponse:
        model_name = "tft" if model not in {"tft", "lstm_attn"} else model
        rng = Random(self._seed(f"attn:{symbol}:{model_name}"))
        weights: list[list[float]] = []
        for _ in range(8):
            row_raw = [rng.random() for _ in range(60)]
            total = sum(row_raw)
            weights.append([round(v / total, 6) for v in row_raw])

        mean_weights = []
        for idx in range(60):
            mean_weights.append(round(sum(row[idx] for row in weights) / len(weights), 6))

        top_indices = sorted(range(60), key=lambda i: mean_weights[i], reverse=True)[:5]
        top = [
            {"date": date.today() - timedelta(days=(60 - idx)), "weight": mean_weights[idx]}
            for idx in top_indices
        ]

        return ExplainAttentionResponse(
            model=model_name,
            weights=weights,
            mean_weights=mean_weights,
            top_timesteps=top,
        )

    def get_counterfactuals(self, symbol: str, payload: CounterfactualRequest) -> list[CounterfactualResponse]:
        rng = Random(self._seed(f"cf:{symbol}:{payload.target_direction}:{payload.num_cfs}"))
        rows: list[CounterfactualResponse] = []
        for idx in range(payload.num_cfs):
            rows.append(
                CounterfactualResponse(
                    cf_id=f"CF-{idx + 1}",
                    changed_features=[
                        CounterfactualFeatureChange(
                            name="rsi_14",
                            original=round(32 + rng.random() * 10, 2),
                            counterfactual=round(48 + rng.random() * 8, 2),
                        ),
                        CounterfactualFeatureChange(
                            name="momentum_21d",
                            original=round(-0.03 + rng.random() * 0.02, 4),
                            counterfactual=round(0.01 + rng.random() * 0.02, 4),
                        ),
                    ],
                    resulting_signal="BUY" if payload.target_direction == "BUY" else "SELL",
                    proximity_score=round(0.7 + rng.random() * 0.25, 4),
                )
            )
        return rows

    def get_model_accuracy(self) -> list[ModelAccuracyItem]:
        rows: list[ModelAccuracyItem] = []
        for model in MODELS:
            base = 0.53 if model != "ensemble" else 0.61
            rows.append(
                ModelAccuracyItem(
                    model=model,
                    precision=round(base, 4),
                    recall=round(base - 0.02, 4),
                    directional_accuracy=round(base + 0.03, 4),
                    p50_rmse=round(0.012 if model == "ensemble" else 0.016, 5),
                    winkler_coverage_score=round(0.82 if model == "ensemble" else 0.77, 4),
                )
            )
        return rows

    def get_drift(self) -> list[DriftItem]:
        rows: list[DriftItem] = []
        for model in MODELS:
            seeded = Random(self._seed(f"drift:{model}"))
            rows.append(
                DriftItem(
                    model=model,
                    adwin_p_value=round(seeded.random(), 4),
                    drift_detected=seeded.random() < 0.2,
                    residual_distribution=[round(seeded.uniform(-0.03, 0.03), 4) for _ in range(63)],
                    ks_stat=round(seeded.uniform(0.03, 0.21), 4),
                )
            )
        return rows

    def get_ensemble_weights_history(self, days: int) -> list[EnsembleWeightPoint]:
        rows: list[EnsembleWeightPoint] = []
        for i in range(days):
            d = date.today() - timedelta(days=days - i)
            base = Random(self._seed(f"weights:{d.isoformat()}"))
            weights = self._normalize_weights(
                {
                    "tft": 0.22 + base.random() * 0.08,
                    "hmm_garch": 0.16 + base.random() * 0.08,
                    "gnn": 0.14 + base.random() * 0.06,
                    "lstm_attn": 0.16 + base.random() * 0.07,
                    "xgboost": 0.17 + base.random() * 0.08,
                }
            )
            rows.append(
                EnsembleWeightPoint(
                    date=d,
                    tft=weights["tft"],
                    hmm_garch=weights["hmm_garch"],
                    gnn=weights["gnn"],
                    lstm_attn=weights["lstm_attn"],
                    xgboost=weights["xgboost"],
                )
            )
        return rows

    def get_economic_calendar(self) -> list[EconomicCalendarEvent]:
        today = date.today()
        return [
            EconomicCalendarEvent(
                date=today + timedelta(days=3),
                category="FOMC",
                title="FOMC Rate Decision",
                impact="HIGH",
            ),
            EconomicCalendarEvent(
                date=today + timedelta(days=7),
                category="EARNINGS",
                title="Large Cap Q4 Earnings Week",
                impact="MEDIUM",
            ),
            EconomicCalendarEvent(
                date=today + timedelta(days=11),
                category="EXPIRY",
                title="NSE Monthly Derivatives Expiry",
                impact="HIGH",
            ),
            EconomicCalendarEvent(
                date=today + timedelta(days=20),
                category="MACRO",
                title="US CPI Release",
                impact="MEDIUM",
            ),
        ]

    def get_correlation_graph(self, window_days: int = 60) -> CorrelationGraphResponse:
        symbols = [
            ("RELIANCE.NS", "Energy"),
            ("TCS.NS", "IT"),
            ("INFY.NS", "IT"),
            ("HDFCBANK.NS", "Banking"),
            ("ICICIBANK.NS", "Banking"),
            ("NIFTY", "Index"),
            ("BTC-USD", "Crypto"),
            ("ETH-USD", "Crypto"),
        ]
        rng = Random(self._seed(f"corr:{window_days}"))

        nodes: list[CorrelationNode] = []
        for index, (ticker, sector) in enumerate(symbols):
            base_x = 15 + (index % 4) * 20
            base_y = 20 + (index // 4) * 35
            nodes.append(
                CorrelationNode(
                    ticker=ticker,
                    sector=sector,
                    x=round(base_x + rng.uniform(-4, 4), 2),
                    y=round(base_y + rng.uniform(-6, 6), 2),
                    size=round(12 + rng.uniform(2, 9), 2),
                )
            )

        edges_seed = [
            ("NIFTY", "RELIANCE.NS"),
            ("NIFTY", "TCS.NS"),
            ("NIFTY", "HDFCBANK.NS"),
            ("TCS.NS", "INFY.NS"),
            ("HDFCBANK.NS", "ICICIBANK.NS"),
            ("BTC-USD", "ETH-USD"),
            ("NIFTY", "BTC-USD"),
        ]
        edges: list[CorrelationEdge] = []
        for source, target in edges_seed:
            corr = round(rng.uniform(0.22, 0.89), 3)
            edges.append(CorrelationEdge(source=source, target=target, correlation=corr))

        central = "NIFTY"
        top_correlates = [
            {"ticker": edge.target, "correlation": edge.correlation}
            for edge in sorted((e for e in edges if e.source == central), key=lambda item: item.correlation, reverse=True)
        ]

        return CorrelationGraphResponse(
            window_days=window_days,
            central_asset=central,
            nodes=nodes,
            edges=edges,
            top_correlates=top_correlates,
        )

    def get_factor_exposure(self, symbol: str, window_days: int = 126) -> FactorExposureResponse:
        ticker = symbol.upper()
        rng = Random(self._seed(f"factor:{ticker}:{window_days}"))

        factors = ["MKT", "SMB", "HML", "RMW", "CMA", "Momentum", "Volatility"]
        exposures = [
            FactorExposureItem(factor=factor, beta=round(rng.uniform(-0.45, 0.95), 3))
            for factor in factors
        ]

        metrics = {
            "alpha_annualized": round(rng.uniform(0.02, 0.09), 4),
            "tracking_error": round(rng.uniform(0.04, 0.11), 4),
            "information_ratio": round(rng.uniform(0.3, 1.4), 4),
            "factor_concentration": round(rng.uniform(0.22, 0.67), 4),
            "residual_volatility": round(rng.uniform(0.05, 0.14), 4),
            "active_share": round(rng.uniform(0.58, 0.89), 4),
        }

        return FactorExposureResponse(
            symbol=ticker,
            window_days=window_days,
            exposures=exposures,
            metrics=metrics,
        )


intelligence_service = IntelligenceService()
