"""Optional convenience adapter. Only explicit provider selection uses a network."""

import pandas as pd
from .base import select_prices
from quantlab.types import DataUnavailableError


class YahooDataProvider:
    def load_prices(self, symbols, start_date, end_date):
        try:
            import yfinance as yf
        except ImportError as exc:
            raise DataUnavailableError(
                "Install the optional dependency: pip install -e '.[online]'"
            ) from exc
        frames = []
        for symbol in symbols:
            raw = yf.Ticker(symbol).history(
                start=str(start_date),
                end=str(pd.Timestamp(end_date).date() + pd.Timedelta(days=1)),
                auto_adjust=False,
                actions=True,
            )
            if raw.empty:
                raise DataUnavailableError(f"Yahoo returned no data for {symbol}")
            raw = raw.reset_index().rename(
                columns={
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                    "Adj Close": "adj_close",
                    "Dividends": "dividend",
                    "Stock Splits": "split_factor",
                }
            )
            raw["date"] = pd.to_datetime(raw.date).dt.tz_localize(None).dt.normalize()
            raw["symbol"] = symbol
            frames.append(raw)
        return select_prices(
            pd.concat(frames, ignore_index=True), symbols, start_date, end_date
        )
