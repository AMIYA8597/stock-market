"""Market Status service for NSE market hours and holidays."""

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


class MarketStatusService:
    IST = ZoneInfo("Asia/Kolkata")

    # Static known NSE holidays for 2026 to ensure reliability
    HOLIDAYS = {
        date(2026, 1, 26), # Republic Day
        date(2026, 3, 3),  # Mahashivratri
        date(2026, 3, 20), # Holi
        date(2026, 4, 3),  # Good Friday
        date(2026, 4, 14), # Ambedkar Jayanti
        date(2026, 5, 1),  # Maharashtra Day
        date(2026, 8, 15), # Independence Day
        date(2026, 9, 15), # Ganesh Chaturthi
        date(2026, 10, 2), # Gandhi Jayanti
        date(2026, 10, 20),# Dussehra
        date(2026, 11, 8), # Diwali
        date(2026, 11, 23),# Gurunanak Jayanti
        date(2026, 12, 25) # Christmas
    }

    @classmethod
    def is_holiday(cls, dt: date) -> bool:
        return dt.weekday() >= 5 or dt in cls.HOLIDAYS

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        now = datetime.now(cls.IST)
        today = now.date()

        market_open_time = time(9, 15)
        market_close_time = time(15, 30)

        is_open = not cls.is_holiday(today) and (market_open_time <= now.time() <= market_close_time)

        # Calculate next open
        next_open = now
        if is_open:
            next_close = datetime.combine(today, market_close_time, tzinfo=cls.IST)
            # Find next open (next day)
            n_open = now + timedelta(days=1)
            while cls.is_holiday(n_open.date()):
                n_open += timedelta(days=1)
            next_open = datetime.combine(n_open.date(), market_open_time, tzinfo=cls.IST)
        else:
            next_close = None
            if now.time() > market_close_time or cls.is_holiday(today):
                next_open += timedelta(days=1)

            while cls.is_holiday(next_open.date()):
                next_open += timedelta(days=1)
            next_open = datetime.combine(next_open.date(), market_open_time, tzinfo=cls.IST)

        return {
            "market_open": is_open,
            "next_open": next_open.isoformat(),
            "next_close": next_close.isoformat() if next_close else None,
        }
