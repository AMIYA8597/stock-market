import pytest
from datetime import datetime, date
import pytz
from app.data_platform.calendar import MarketCalendarService

def test_calendar_weekend():
    svc = MarketCalendarService()
    # 2026-01-24 is a Saturday
    check_date = date(2026, 1, 24)
    assert svc.is_trading_day("XNSE", check_date) is False
    
def test_calendar_holiday():
    svc = MarketCalendarService()
    # 2026-01-26 is Republic Day
    check_date = date(2026, 1, 26)
    assert svc.is_trading_day("XNSE", check_date) is False
    
def test_calendar_trading_day():
    svc = MarketCalendarService()
    # 2026-01-27 is a Tuesday
    check_date = date(2026, 1, 27)
    assert svc.is_trading_day("XNSE", check_date) is True
    
def test_market_status_open():
    svc = MarketCalendarService()
    ist = pytz.timezone('Asia/Kolkata')
    
    # Tuesday 2026-01-27 10:00 AM IST
    now = ist.localize(datetime(2026, 1, 27, 10, 0, 0))
    status = svc.market_status(now, "XNSE")
    assert status["state"] == "open"
    assert status["next_close"] is not None

def test_market_status_pre_open():
    svc = MarketCalendarService()
    ist = pytz.timezone('Asia/Kolkata')
    
    # Tuesday 2026-01-27 09:10 AM IST
    now = ist.localize(datetime(2026, 1, 27, 9, 10, 0))
    status = svc.market_status(now, "XNSE")
    assert status["state"] == "pre_open"

def test_market_status_closed():
    svc = MarketCalendarService()
    ist = pytz.timezone('Asia/Kolkata')
    
    # Tuesday 2026-01-27 16:00 PM IST
    now = ist.localize(datetime(2026, 1, 27, 16, 0, 0))
    status = svc.market_status(now, "XNSE")
    assert status["state"] == "closed"
