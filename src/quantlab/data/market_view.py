"""A physically truncated copy: no reference to future rows is retained."""

import pandas as pd


class MarketDataView:
    __slots__ = ("_history", "_date", "_symbols")

    def __init__(self, frame, dt, symbols):
        timestamp = pd.Timestamp(dt)
        if not timestamp.tzinfo and timestamp != timestamp.normalize():
            raise ValueError(
                "Intraday timestamps must be timezone-aware; use a session date for a close view"
            )
        self._date = (
            timestamp.tz_convert("America/New_York").tz_localize(None).normalize()
            if timestamp.tzinfo
            else timestamp.normalize()
        )
        if timestamp.tzinfo:
            from .calendar import schedule

            session = schedule(self._date, self._date)
            if session.empty or timestamp < session.iloc[0]["close"]:
                raise ValueError(
                    "Daily OHLCV is only observable at or after session close"
                )
        self._symbols = tuple(symbols)
        self._history = frame.loc[
            (frame.date <= self._date) & frame.symbol.isin(symbols)
        ].copy(deep=True)

    @property
    def symbols(self):
        return self._symbols

    @property
    def as_of(self):
        return self._date

    def history(self, symbol, bars=None, end=None):
        if symbol not in self._symbols:
            raise ValueError(f"Unknown symbol: {symbol}")
        if end is not None:
            end = pd.Timestamp(end)
            if end.tzinfo:
                end = end.tz_convert("America/New_York").tz_localize(None).normalize()
            if end > self._date:
                raise ValueError("Future data request denied")
        result = self._history.loc[self._history.symbol == symbol]
        if end is not None:
            result = result.loc[result.date <= pd.Timestamp(end)]
        if bars is not None:
            if not isinstance(bars, int) or isinstance(bars, bool) or bars < 1:
                raise ValueError("bars must be a positive integer")
            result = result.tail(bars)
        return result.copy(deep=True)

    def current(self, symbol):
        result = self.history(symbol)
        result = result.loc[result.date == self._date]
        return None if result.empty else result.iloc[-1].copy(deep=True)
