from typing import Protocol
import pandas as pd


class DataProvider(Protocol):
    def load_prices(self, symbols: list[str], start_date, end_date) -> pd.DataFrame: ...


def select_prices(frame, symbols, start_date, end_date):
    from quantlab.types import DataUnavailableError

    try:
        dates = pd.to_datetime(frame["date"], errors="raise", format="ISO8601")
        if dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
            raise ValueError(
                "daily dates must be timezone-naive session labels at midnight"
            )
        frame = frame.copy()
        frame["date"] = dates
        return frame.loc[
            frame.symbol.isin(symbols)
            & dates.between(pd.Timestamp(start_date), pd.Timestamp(end_date))
        ].copy()
    except (KeyError, ValueError, AttributeError) as exc:
        raise DataUnavailableError(f"Invalid price schema/dates: {exc}") from exc
