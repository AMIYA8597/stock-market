"""Unit tests for app.services.market_status.MarketStatusService."""

from datetime import date, datetime, time
from unittest.mock import patch

import pytest

from app.services.market_status import MarketStatusService

IST = MarketStatusService.IST


def _at(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=IST)


class _FrozenDatetime(datetime):
    """datetime subclass whose now() returns a fixed instant."""

    frozen: datetime

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return cls.frozen if tz is None else cls.frozen.astimezone(tz)


def freeze(moment: datetime):
    _FrozenDatetime.frozen = moment
    return patch("app.services.market_status.datetime", _FrozenDatetime)


def test_weekends_are_holidays():
    assert MarketStatusService.is_holiday(date(2026, 7, 25))  # Saturday
    assert MarketStatusService.is_holiday(date(2026, 7, 26))  # Sunday


def test_listed_nse_holidays_are_holidays():
    assert MarketStatusService.is_holiday(date(2026, 1, 26))  # Republic Day
    assert MarketStatusService.is_holiday(date(2026, 11, 8))  # Diwali


def test_regular_weekday_is_not_a_holiday():
    assert not MarketStatusService.is_holiday(date(2026, 7, 27))  # Monday


def test_status_open_during_trading_hours_on_a_business_day():
    with freeze(_at(2026, 7, 27, 11, 0)):
        status = MarketStatusService.get_status()

    assert status["market_open"] is True
    assert datetime.fromisoformat(status["next_close"]) == _at(2026, 7, 27, 15, 30)
    # Next session opens on the following business day.
    assert datetime.fromisoformat(status["next_open"]) == _at(2026, 7, 28, 9, 15)


@pytest.mark.parametrize(
    ("moment", "expected_open"),
    [
        (_at(2026, 7, 27, 9, 15), True),  # opening bell
        (_at(2026, 7, 27, 15, 30), True),  # closing bell
        (_at(2026, 7, 27, 9, 14), False),
        (_at(2026, 7, 27, 15, 31), False),
    ],
)
def test_market_open_boundaries_are_inclusive(moment, expected_open):
    with freeze(moment):
        assert MarketStatusService.get_status()["market_open"] is expected_open


def test_status_before_open_points_to_same_day_open():
    with freeze(_at(2026, 7, 27, 8, 0)):
        status = MarketStatusService.get_status()

    assert status["market_open"] is False
    assert status["next_close"] is None
    assert datetime.fromisoformat(status["next_open"]) == _at(2026, 7, 27, 9, 15)


def test_status_after_close_points_to_next_business_day():
    with freeze(_at(2026, 7, 27, 18, 0)):
        status = MarketStatusService.get_status()

    assert status["market_open"] is False
    assert datetime.fromisoformat(status["next_open"]) == _at(2026, 7, 28, 9, 15)


def test_status_on_friday_evening_skips_the_weekend():
    with freeze(_at(2026, 7, 31, 17, 0)):  # Friday after close
        status = MarketStatusService.get_status()

    assert datetime.fromisoformat(status["next_open"]) == _at(2026, 8, 3, 9, 15)  # Monday


def test_status_on_holiday_skips_to_next_open_session():
    with freeze(_at(2026, 1, 26, 10, 0)):  # Republic Day, a Monday
        status = MarketStatusService.get_status()

    assert status["market_open"] is False
    assert datetime.fromisoformat(status["next_open"]) == _at(2026, 1, 27, 9, 15)


def test_status_next_open_is_always_at_the_opening_bell():
    with freeze(_at(2026, 12, 25, 12, 0)):  # Christmas, a Friday
        status = MarketStatusService.get_status()

    next_open = datetime.fromisoformat(status["next_open"])
    assert next_open.time() == time(9, 15)
    assert not MarketStatusService.is_holiday(next_open.date())
