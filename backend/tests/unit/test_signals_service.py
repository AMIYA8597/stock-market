"""Unit tests for app.services.signals_service and the algorithm registry."""

from decimal import Decimal

import pytest

from app.services import algorithm_provider, signals_service


class FakeSignal:
    def __init__(self, symbol_id=1, direction="BUY", confidence=0.73, signal=0.42):
        self.symbol_id = symbol_id
        self.direction = direction
        self.confidence = Decimal(str(confidence))
        self.signal = Decimal(str(signal))


class FakeDB:
    """Minimal AsyncSession stand-in recording the statements it receives."""

    def __init__(self, rows=None, entity=None):
        self._rows = rows or []
        self._entity = entity
        self.executed = []
        self.got = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        rows = self._rows

        class Scalars:
            def all(self):
                return rows

        class Result:
            def scalars(self):
                return Scalars()

        return Result()

    async def get(self, model, pk):
        self.got.append((model, pk))
        return self._entity


async def test_list_signals_returns_rows_ordered_by_time_desc():
    rows = [FakeSignal(symbol_id=2), FakeSignal(symbol_id=3)]
    db = FakeDB(rows=rows)

    result = await signals_service.list_signals(db)

    assert result == rows
    assert "ORDER BY" in str(db.executed[0]).upper()


async def test_list_signals_handles_empty_table():
    assert await signals_service.list_signals(FakeDB(rows=[])) == []


async def test_run_signal_delegates_to_signal_engine(monkeypatch):
    created = FakeSignal()
    calls = {}

    async def fake_process(db, symbol, payload):
        calls["args"] = (db, symbol, payload)
        return created

    monkeypatch.setattr(
        signals_service.SignalEngine, "process_new_prediction", staticmethod(fake_process)
    )
    db = FakeDB()
    payload = {"ensemble": {"raw_ensemble": 0.4}}

    result = await signals_service.run_signal(db, "RELIANCE", payload)

    assert result is created
    assert calls["args"] == (db, "RELIANCE", payload)


async def test_run_signal_propagates_engine_rejection(monkeypatch):
    async def fake_process(db, symbol, payload):
        return None

    monkeypatch.setattr(
        signals_service.SignalEngine, "process_new_prediction", staticmethod(fake_process)
    )

    assert await signals_service.run_signal(FakeDB(), "TCS", {}) is None


async def test_explain_signal_returns_none_for_unknown_signal():
    db = FakeDB(entity=None)

    assert await signals_service.explain_signal(db, 404) is None
    assert db.got == [(signals_service.EnsembleSignal, 404)]


async def test_explain_signal_builds_prompt_and_returns_explanation(monkeypatch):
    captured = {}

    async def fake_predict(db, payload):
        captured["payload"] = payload
        return {"explanation": "Momentum and regime both favour longs."}

    monkeypatch.setattr("app.services.ai_service.predict", fake_predict)
    db = FakeDB(entity=FakeSignal(symbol_id=7, direction="BUY", confidence=0.73, signal=0.42))

    explanation = await signals_service.explain_signal(db, 1)

    assert explanation == "Momentum and regime both favour longs."
    assert captured["payload"]["symbol"] == "7"
    prompt = captured["payload"]["prompt"]
    assert "ticker 7" in prompt
    assert "direction BUY" in prompt
    assert "73.00%" in prompt
    assert "0.4200" in prompt


async def test_explain_signal_returns_none_for_non_dict_ai_response(monkeypatch):
    async def fake_predict(db, payload):
        return "not-a-dict"

    monkeypatch.setattr("app.services.ai_service.predict", fake_predict)

    assert await signals_service.explain_signal(FakeDB(entity=FakeSignal()), 1) is None


async def test_explain_signal_swallows_ai_service_failure(monkeypatch):
    async def fake_predict(db, payload):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("app.services.ai_service.predict", fake_predict)

    assert await signals_service.explain_signal(FakeDB(entity=FakeSignal()), 1) is None


def test_get_algorithm_path_returns_registered_import_path():
    assert algorithm_provider.get_algorithm_path("ensemble") == "app.services.intelligence_service"


def test_get_algorithm_path_raises_for_unknown_algorithm():
    with pytest.raises(KeyError, match="is not registered"):
        algorithm_provider.get_algorithm_path("does-not-exist")


def test_list_algorithms_matches_registry_keys():
    assert algorithm_provider.list_algorithms() == list(algorithm_provider.ALGORITHM_MAP)
    assert "xgboost" in algorithm_provider.list_algorithms()
