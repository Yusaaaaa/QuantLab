"""XNYS session dates plus timezone-aware open/close timestamps."""

from functools import lru_cache
import pandas as pd
import exchange_calendars as xcals


@lru_cache(maxsize=32)
def _calendar(first_year, last_year):
    return xcals.get_calendar(
        "XNYS", start=f"{first_year - 1}-01-01", end=f"{last_year + 1}-12-31"
    )


def schedule(start, end) -> pd.DataFrame:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start > end:
        raise ValueError("Calendar start must not follow end")
    cal = _calendar(start.year, end.year)
    return cal.schedule.loc[start:end, ["open", "close"]].copy()


def next_session_date(day):
    """Known exchange schedule only; this does not expose future market prices."""
    day = pd.Timestamp(day)
    return _calendar(day.year, day.year).next_session(day).date()
