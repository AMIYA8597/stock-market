"""Unit tests for the ensemble weighting, sizing and aggregation modules."""

import numpy as np
import pytest

from research.models.ensemble.aggregator import (
    EnsembleDecision,
    _direction_from_score,
    build_ensemble_decision,
)
from research.models.ensemble.kelly_sizer import half_kelly_capped, kelly_fraction
from research.models.ensemble.signal_combiner import (
    combine_weighted_signals,
    direction_from_score,
)
from research.models.ensemble.weight_manager import (
    aggregate_signal,
    compute_dynamic_weights,
    half_kelly_fraction,
    rolling_sharpe_from_signals,
    softmax,
)

# ── kelly_sizer ────────────────────────────────────────────────────────────


def test_kelly_fraction_matches_formula():
    assert kelly_fraction(
        score=0.5, confidence=0.8, regime_mean=0.02, regime_variance=0.04
    ) == pytest.approx(0.8 * 0.5 * (0.02 / 0.04))


def test_kelly_fraction_rejects_non_positive_variance():
    with pytest.raises(ValueError, match="regime_variance must be > 0"):
        kelly_fraction(score=0.5, confidence=0.8, regime_mean=0.02, regime_variance=0.0)


def test_half_kelly_capped_halves_full_kelly_inside_cap():
    full = kelly_fraction(score=0.2, confidence=0.5, regime_mean=0.01, regime_variance=0.05)

    assert half_kelly_capped(
        score=0.2, confidence=0.5, regime_mean=0.01, regime_variance=0.05
    ) == pytest.approx(full / 2.0)


def test_half_kelly_capped_applies_upper_cap():
    assert (
        half_kelly_capped(score=1.0, confidence=1.0, regime_mean=0.5, regime_variance=0.1) == 0.25
    )


def test_half_kelly_capped_floors_negative_edge_at_zero():
    assert (
        half_kelly_capped(score=-0.8, confidence=0.9, regime_mean=0.02, regime_variance=0.04) == 0.0
    )


def test_half_kelly_capped_honours_custom_cap():
    assert (
        half_kelly_capped(score=1.0, confidence=1.0, regime_mean=0.5, regime_variance=0.1, cap=0.05)
        == 0.05
    )


# ── weight_manager ─────────────────────────────────────────────────────────


def test_rolling_sharpe_annualizes_signed_returns():
    signals = np.array([1.0, 1.0, -1.0, 1.0])
    actual = np.array([0.01, 0.02, -0.01, 0.005])
    signed = np.sign(signals) * actual
    expected = np.mean(signed) / np.std(signed, ddof=1) * np.sqrt(252.0)

    assert rolling_sharpe_from_signals(signals, actual) == pytest.approx(expected)


def test_rolling_sharpe_rewards_correct_direction():
    actual = np.array([0.01, -0.02, 0.015, -0.01, 0.02])
    aligned = rolling_sharpe_from_signals(np.sign(actual), actual)
    inverted = rolling_sharpe_from_signals(-np.sign(actual), actual)

    assert aligned > 0 > inverted


def test_rolling_sharpe_is_zero_when_signed_returns_are_constant():
    signals = np.ones(5)
    actual = np.full(5, 0.01)

    assert rolling_sharpe_from_signals(signals, actual) == 0.0


def test_rolling_sharpe_requires_matching_shapes():
    with pytest.raises(ValueError, match="same shape"):
        rolling_sharpe_from_signals(np.ones(3), np.ones(4))


def test_softmax_is_normalized_and_shift_invariant():
    values = np.array([1.0, 2.0, 3.0])

    probs = softmax(values)

    assert probs.sum() == pytest.approx(1.0)
    assert np.all(probs > 0)
    assert np.allclose(probs, softmax(values + 100.0))


def test_compute_dynamic_weights_blends_sharpe_and_regime_priors():
    sharpes = {"tft": 2.0, "gnn": 0.5, "xgb": -1.0}
    regime = {"tft": 0.2, "gnn": 0.3, "xgb": 0.5}

    weights = compute_dynamic_weights(sharpes, regime)

    sr = softmax(np.array([2.0, 0.5, -1.0]))
    reg = np.array([0.2, 0.3, 0.5])
    expected = 0.6 * sr + 0.4 * reg

    assert sum(weights.values()) == pytest.approx(1.0)
    assert [weights[m] for m in ("tft", "gnn", "xgb")] == pytest.approx(expected)


def test_compute_dynamic_weights_falls_back_to_uniform_regime_prior():
    sharpes = {"a": 0.0, "b": 0.0}

    weights = compute_dynamic_weights(sharpes, {"a": 0.0, "b": 0.0})

    assert weights == {"a": pytest.approx(0.5), "b": pytest.approx(0.5)}


def test_compute_dynamic_weights_normalizes_unnormalized_regime_prior():
    weights = compute_dynamic_weights({"a": 1.0, "b": 1.0}, {"a": 6.0, "b": 2.0})

    assert weights["a"] == pytest.approx(0.6 * 0.5 + 0.4 * 0.75)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_compute_dynamic_weights_favours_the_better_model():
    weights = compute_dynamic_weights({"good": 3.0, "bad": -3.0}, {"good": 0.5, "bad": 0.5})

    assert weights["good"] > weights["bad"]


def test_aggregate_signal_computes_weighted_score_and_agreement_confidence():
    signals = {"a": 0.8, "b": 0.4}
    weights = {"a": 3.0, "b": 1.0}

    result = aggregate_signal(signals, weights)

    assert result.weights == {"a": pytest.approx(0.75), "b": pytest.approx(0.25)}
    assert result.score == pytest.approx(0.75 * 0.8 + 0.25 * 0.4)
    assert result.confidence == pytest.approx(1.0 - np.std([0.8, 0.4]) / 2.0)


def test_aggregate_signal_full_agreement_gives_max_confidence():
    result = aggregate_signal({"a": 0.5, "b": 0.5, "c": 0.5}, {"a": 1.0, "b": 1.0, "c": 1.0})

    assert result.confidence == pytest.approx(1.0)
    assert result.score == pytest.approx(0.5)


def test_aggregate_signal_uses_uniform_weights_when_all_weights_are_zero():
    result = aggregate_signal({"a": 1.0, "b": -1.0}, {"a": 0.0, "b": 0.0})

    assert result.weights == {"a": pytest.approx(0.5), "b": pytest.approx(0.5)}
    assert result.score == pytest.approx(0.0)
    assert result.confidence == pytest.approx(0.5)


def test_half_kelly_fraction_is_clipped_to_unit_interval_cap():
    assert half_kelly_fraction(1.0, 1.0, 0.4, 0.1) == pytest.approx(0.25)
    assert half_kelly_fraction(-1.0, 1.0, 0.4, 0.1) == pytest.approx(0.0)
    assert half_kelly_fraction(0.2, 0.5, 0.02, 0.04) == pytest.approx(0.5 * 0.2 * 0.5 / 2.0)


def test_half_kelly_fraction_rejects_non_positive_variance():
    with pytest.raises(ValueError, match="regime_variance must be > 0"):
        half_kelly_fraction(0.5, 0.5, 0.01, -0.1)


# ── signal_combiner ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.9, "STRONG_BUY"),
        (0.61, "STRONG_BUY"),
        (0.6, "BUY"),
        (0.3, "BUY"),
        (0.2, "NEUTRAL"),
        (0.0, "NEUTRAL"),
        (-0.2, "NEUTRAL"),
        (-0.4, "SELL"),
        (-0.6, "SELL"),
        (-0.9, "STRONG_SELL"),
    ],
)
def test_direction_from_score_thresholds(score, expected):
    assert direction_from_score(score) == expected


def test_combine_weighted_signals_returns_consistent_bundle():
    signals = {"tft": 0.9, "gnn": 0.7}
    weights = {"tft": 0.5, "gnn": 0.5}

    combined = combine_weighted_signals(signals, weights, regime_mean=0.02, regime_variance=0.04)

    assert combined.score == pytest.approx(0.8)
    assert combined.confidence == pytest.approx(1.0 - np.std([0.9, 0.7]) / 2.0)
    assert combined.direction == "STRONG_BUY"
    assert combined.kelly_fraction == pytest.approx(
        half_kelly_capped(combined.score, combined.confidence, 0.02, 0.04)
    )


def test_combine_weighted_signals_uses_uniform_weights_when_missing():
    combined = combine_weighted_signals(
        {"a": 0.4, "b": 0.4}, {}, regime_mean=0.01, regime_variance=0.02
    )

    assert combined.score == pytest.approx(0.4)
    assert combined.direction == "BUY"


def test_combine_weighted_signals_disagreement_lowers_confidence():
    agreeing = combine_weighted_signals(
        {"a": 0.5, "b": 0.5}, {"a": 1.0, "b": 1.0}, regime_mean=0.02, regime_variance=0.04
    )
    conflicting = combine_weighted_signals(
        {"a": 1.0, "b": -1.0}, {"a": 1.0, "b": 1.0}, regime_mean=0.02, regime_variance=0.04
    )

    assert agreeing.confidence > conflicting.confidence
    assert conflicting.direction == "NEUTRAL"
    assert conflicting.kelly_fraction == 0.0


# ── aggregator ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.6, "STRONG_BUY"),
        (0.2, "BUY"),
        (0.0, "NEUTRAL"),
        (-0.2, "SELL"),
        (-0.6, "STRONG_SELL"),
    ],
)
def test_aggregator_direction_boundaries_are_inclusive(score, expected):
    assert _direction_from_score(score) == expected


def test_build_ensemble_decision_matches_component_pipeline():
    model_signals = {"tft": 0.8, "gnn": 0.4, "xgb": 0.6}
    rolling_sharpes = {"tft": 1.5, "gnn": 0.2, "xgb": 0.9}
    regime_weights = {"tft": 0.5, "gnn": 0.2, "xgb": 0.3}

    decision = build_ensemble_decision(
        model_signals=model_signals,
        rolling_sharpes=rolling_sharpes,
        regime_weights=regime_weights,
        regime_mean=0.03,
        regime_variance=0.05,
    )

    expected_weights = compute_dynamic_weights(rolling_sharpes, regime_weights)
    expected_agg = aggregate_signal(model_signals, expected_weights)

    assert isinstance(decision, EnsembleDecision)
    assert decision.score == pytest.approx(expected_agg.score)
    assert decision.confidence == pytest.approx(expected_agg.confidence)
    assert decision.direction == _direction_from_score(expected_agg.score)
    assert decision.kelly_fraction == pytest.approx(
        half_kelly_fraction(expected_agg.score, expected_agg.confidence, 0.03, 0.05)
    )
    assert sum(decision.weights.values()) == pytest.approx(1.0)


def test_build_ensemble_decision_bearish_signals_produce_sell_and_no_size():
    decision = build_ensemble_decision(
        model_signals={"tft": -0.7, "gnn": -0.8},
        rolling_sharpes={"tft": 1.0, "gnn": 0.5},
        regime_weights={"tft": 0.5, "gnn": 0.5},
        regime_mean=0.02,
        regime_variance=0.04,
    )

    assert decision.direction == "STRONG_SELL"
    assert decision.kelly_fraction == 0.0
