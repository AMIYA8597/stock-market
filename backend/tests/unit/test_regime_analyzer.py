"""Unit tests for app.services.regime_analyzer (GARCH + HMM wrappers).

The heavy `arch` / `hmmlearn` dependencies are stubbed so the wrapper logic
(guard rails, scaling, fallbacks, state labelling) is tested in isolation.
"""

import sys
import types

import numpy as np
import pandas as pd
import pytest

from app.services.regime_analyzer import GARCHVolatilityModel, HMMRegimeModel


@pytest.fixture
def returns() -> pd.Series:
    rng = np.random.default_rng(17)
    return pd.Series(rng.normal(0.0005, 0.011, 300))


@pytest.fixture
def hmm_features() -> pd.DataFrame:
    rng = np.random.default_rng(19)
    return pd.DataFrame(
        {
            "returns": rng.normal(0.0, 0.01, 250),
            "volatility": rng.gamma(2.0, 0.005, 250),
        }
    )


def _install_module(monkeypatch, name: str, module: object) -> None:
    monkeypatch.setitem(sys.modules, name, module)


# ── GARCH ──────────────────────────────────────────────────────────────────


def test_garch_forecast_without_fit_returns_zeros():
    model = GARCHVolatilityModel()

    assert model.forecast(horizon=4) == [0.0, 0.0, 0.0, 0.0]


def test_garch_fit_skips_when_sample_too_small(monkeypatch):
    called = False

    def arch_model(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should not be called")

    _install_module(monkeypatch, "arch", types.SimpleNamespace(arch_model=arch_model))
    model = GARCHVolatilityModel()

    model.fit(pd.Series(np.zeros(49)))

    assert called is False
    assert model.result is None


def test_garch_fit_scales_returns_to_percent_and_stores_result(monkeypatch, returns):
    captured: dict = {}
    fitted = object()

    class FakeModel:
        def fit(self, disp=None, show_warning=None):
            captured["disp"] = disp
            return fitted

    def arch_model(data, vol=None, p=None, q=None, rescale=None):
        captured["data"] = data
        captured["vol"] = vol
        captured["pq"] = (p, q)
        captured["rescale"] = rescale
        return FakeModel()

    _install_module(monkeypatch, "arch", types.SimpleNamespace(arch_model=arch_model))
    model = GARCHVolatilityModel()

    model.fit(returns)

    assert model.result is fitted
    assert captured["vol"] == "Garch"
    assert captured["pq"] == (1, 1)
    assert captured["rescale"] is False
    assert captured["disp"] == "off"
    pd.testing.assert_series_equal(captured["data"], returns.dropna() * 100.0)


def test_garch_fit_survives_missing_arch_package(monkeypatch, returns):
    _install_module(monkeypatch, "arch", None)  # forces ImportError on import
    model = GARCHVolatilityModel()

    model.fit(returns)

    assert model.result is None


def test_garch_fit_swallows_optimizer_failure(monkeypatch, returns):
    def arch_model(*args, **kwargs):
        raise RuntimeError("optimizer diverged")

    _install_module(monkeypatch, "arch", types.SimpleNamespace(arch_model=arch_model))
    model = GARCHVolatilityModel()

    model.fit(returns)

    assert model.result is None


def test_garch_forecast_annualizes_variance_of_scaled_returns():
    model = GARCHVolatilityModel()
    variance = pd.DataFrame([[2.0, 4.5]])  # variance of percent returns

    class FakeResult:
        def forecast(self, horizon):
            assert horizon == 2
            return types.SimpleNamespace(variance=variance)

    model.result = FakeResult()

    forecast = model.forecast(horizon=2)

    expected = (np.sqrt(np.array([2.0, 4.5]) / 10000.0) * np.sqrt(252)).tolist()
    assert forecast == pytest.approx(expected)
    assert all(0.0 < v < 1.0 for v in forecast)


def test_garch_forecast_returns_zeros_when_forecasting_fails():
    model = GARCHVolatilityModel()

    class ExplodingResult:
        def forecast(self, horizon):
            raise RuntimeError("singular covariance")

    model.result = ExplodingResult()

    assert model.forecast(horizon=3) == [0.0, 0.0, 0.0]


# ── HMM ────────────────────────────────────────────────────────────────────


class FakeGaussianHMM:
    """Minimal stand-in for hmmlearn's GaussianHMM."""

    instances: list["FakeGaussianHMM"] = []

    def __init__(self, n_components=3, covariance_type=None, n_iter=None, random_state=None):
        self.n_components = n_components
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.random_state = random_state
        self.fitted_rows = 0
        self.means_ = np.array([[0.01, 0.01], [-0.02, 0.04], [0.0, 0.02]])
        FakeGaussianHMM.instances.append(self)

    def fit(self, values):
        self.fitted_rows = len(values)

    def predict(self, values):
        return np.array([0, 1, 2] * (len(values) // 3 + 1))[: len(values)]

    def predict_proba(self, values):
        rows = np.tile(np.array([0.2, 0.3, 0.5]), (len(values), 1))
        return rows


@pytest.fixture
def fake_hmmlearn(monkeypatch):
    FakeGaussianHMM.instances = []
    module = types.ModuleType("hmmlearn.hmm")
    module.GaussianHMM = FakeGaussianHMM
    _install_module(monkeypatch, "hmmlearn", types.ModuleType("hmmlearn"))
    _install_module(monkeypatch, "hmmlearn.hmm", module)
    return module


def test_hmm_default_state_count_is_three():
    assert HMMRegimeModel().n_states == 3
    assert HMMRegimeModel(n_states=4).n_states == 4


def test_hmm_predict_without_fit_returns_neutral_state():
    model = HMMRegimeModel()

    assert model.predict(pd.DataFrame({"a": [1.0]})) == (0, [0.0, 0.0, 0.0])


def test_hmm_predict_with_empty_features_returns_neutral_state(fake_hmmlearn, hmm_features):
    model = HMMRegimeModel()
    model.fit(hmm_features)

    assert model.predict(pd.DataFrame()) == (0, [0.0, 0.0, 0.0])


def test_hmm_fit_configures_gaussian_hmm(fake_hmmlearn, hmm_features):
    model = HMMRegimeModel(n_states=3)

    model.fit(hmm_features)

    assert isinstance(model.model, FakeGaussianHMM)
    assert model.model.n_components == 3
    assert model.model.covariance_type == "full"
    assert model.model.random_state == 42
    assert model.model.fitted_rows == len(hmm_features)


def test_hmm_fit_skips_when_sample_too_small(fake_hmmlearn):
    model = HMMRegimeModel()

    model.fit(pd.DataFrame({"returns": np.zeros(99), "volatility": np.zeros(99)}))

    assert model.model is None
    assert FakeGaussianHMM.instances == []


def test_hmm_fit_survives_missing_hmmlearn_package(monkeypatch, hmm_features):
    _install_module(monkeypatch, "hmmlearn.hmm", None)
    model = HMMRegimeModel()

    model.fit(hmm_features)

    assert model.model is None


def test_hmm_predict_returns_last_state_and_probabilities(fake_hmmlearn, hmm_features):
    model = HMMRegimeModel()
    model.fit(hmm_features)

    state, probs = model.predict(hmm_features)

    assert state in (0, 1, 2)
    assert probs == pytest.approx([0.2, 0.3, 0.5])
    assert sum(probs) == pytest.approx(1.0)


def test_hmm_predict_falls_back_when_model_raises(fake_hmmlearn, hmm_features):
    model = HMMRegimeModel()
    model.fit(hmm_features)

    def boom(values):
        raise RuntimeError("shape mismatch")

    model.model.predict = boom

    assert model.predict(hmm_features) == (0, [0.0, 0.0, 0.0])


def test_map_states_to_labels_defaults_without_a_fitted_model():
    assert HMMRegimeModel().map_states_to_labels(pd.DataFrame()) == {
        0: "bull",
        1: "bear",
        2: "sideways",
    }


def test_map_states_to_labels_ranks_by_return_minus_half_volatility(fake_hmmlearn, hmm_features):
    model = HMMRegimeModel()
    model.fit(hmm_features)
    # scores: state0 = 0.01 - 0.005 = 0.005, state1 = -0.02 - 0.02 = -0.04, state2 = -0.01
    mapping = model.map_states_to_labels(hmm_features)

    assert mapping == {0: "bull", 1: "bear", 2: "sideways"}


def test_map_states_to_labels_follows_the_fitted_means(fake_hmmlearn, hmm_features):
    model = HMMRegimeModel()
    model.fit(hmm_features)
    model.model.means_ = np.array([[-0.05, 0.06], [0.03, 0.01], [0.0, 0.02]])

    mapping = model.map_states_to_labels(hmm_features)

    assert mapping[1] == "bull"
    assert mapping[0] == "bear"
    assert mapping[2] == "sideways"
