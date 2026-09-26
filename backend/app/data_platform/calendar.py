from datetime import date, datetime, timedelta
from typing import Any

import pytz


class MarketCalendarService:
    def __init__(self):
        self.ist = pytz.timezone('Asia/Kolkata')
        # We will mock the database read for now, returning dummy but structurally correct data.
        # In a real environment, this queries the market_calendar table.
        self._hardcoded_holidays = {
            "2026-01-26": "Republic Day",
            "2026-08-15": "Independence Day",
        }

    def is_trading_day(self, exchange: str, check_date: date) -> bool:
        if exchange not in ["XNSE", "XBOM"]:
            return True # Fallback for unknown

        if check_date.weekday() >= 5: # Saturday=5, Sunday=6
            return False

        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in self._hardcoded_holidays:
            return False

        return True

    def session_bounds(self, exchange: str, check_date: date) -> tuple[datetime, datetime, datetime] | None:
        """Returns (pre_open, open, close) as timezone-aware datetimes."""
        if not self.is_trading_day(exchange, check_date):
            return None

        # Standard NSE times (IST)
        pre_open = self.ist.localize(datetime.combine(check_date, datetime.strptime("09:00", "%H:%M").time()))
        market_open = self.ist.localize(datetime.combine(check_date, datetime.strptime("09:15", "%H:%M").time()))
        market_close = self.ist.localize(datetime.combine(check_date, datetime.strptime("15:30", "%H:%M").time()))

        return pre_open, market_open, market_close

    def market_status(self, now: datetime, exchange: str) -> dict[str, Any]:
        """Returns the current state of the market."""
        # Convert now to IST
        now_ist = now.astimezone(self.ist)
        today = now_ist.date()

        if not self.is_trading_day(exchange, today):
            # Calculate next open
            next_day = today + timedelta(days=1)
            while not self.is_trading_day(exchange, next_day):
                next_day += timedelta(days=1)

            next_open = self.ist.localize(datetime.combine(next_day, datetime.strptime("09:15", "%H:%M").time()))

            if today.weekday() >= 5:
                state = "weekend"
            else:
                state = "holiday"

            return {
                "state": state,
                "next_open": next_open.isoformat(),
                "next_close": None,
                "source": "db_mock"
            }

        bounds = self.session_bounds(exchange, today)
        if not bounds:
            return {"state": "unknown", "next_open": None, "next_close": None, "source": "db_mock"}

        pre_open, market_open, market_close = bounds

        if now_ist < pre_open:
            return {"state": "closed", "next_open": market_open.isoformat(), "next_close": market_close.isoformat(), "source": "db_mock"}
        elif pre_open <= now_ist < market_open:
            return {"state": "pre_open", "next_open": market_open.isoformat(), "next_close": market_close.isoformat(), "source": "db_mock"}
        elif market_open <= now_ist < market_close:
            return {"state": "open", "next_open": None, "next_close": market_close.isoformat(), "source": "db_mock"}
        else:
            # Post-close, find next day
            next_day = today + timedelta(days=1)
            while not self.is_trading_day(exchange, next_day):
                next_day += timedelta(days=1)
            next_open = self.ist.localize(datetime.combine(next_day, datetime.strptime("09:15", "%H:%M").time()))

            return {"state": "closed", "next_open": next_open.isoformat(), "next_close": None, "source": "db_mock"}
