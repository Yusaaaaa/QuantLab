"""Reject corrupt values; preserve unavailable bars explicitly for execution."""

import numpy as np
import pandas as pd
from .schema import REQUIRED_COLUMNS, PRICE_COLUMNS
from .calendar import schedule
from quantlab.types import DataUnavailableError


def validate_prices(
    frame, symbols, start, end, price_mode="adjusted", extreme_threshold=0.5
):
    frame = frame.copy()
    warnings = []

    def fail(message):
        raise DataUnavailableError(message)

    missing = set(REQUIRED_COLUMNS) - set(frame)
    if missing:
        fail(f"Missing columns: {sorted(missing)}")
    try:
        dates = pd.to_datetime(frame.date, errors="raise", format="ISO8601")
        if (
            dates.isna().any()
            or dates.dt.tz is not None
            or not dates.eq(dates.dt.normalize()).all()
        ):
            fail("date must be a timezone-naive NYSE session label")
        frame["date"] = dates
    except (ValueError, AttributeError) as exc:
        fail(f"Invalid dates: {exc}")
    if frame.symbol.isna().any() or frame.symbol.astype(str).str.strip().eq("").any():
        fail("Missing symbol")
    if frame.duplicated(["date", "symbol"]).any():
        fail("Duplicate date-symbol")
    if set(symbols) - set(frame.symbol):
        fail(f"Missing symbols: {sorted(set(symbols) - set(frame.symbol))}")
    sessions = schedule(start, end).index
    if not frame.date.isin(sessions).all():
        fail("Non-NYSE session or out-of-range date")
    for col in PRICE_COLUMNS + ["volume"]:
        try:
            frame[col] = pd.to_numeric(frame[col], errors="raise").astype(float)
        except (ValueError, TypeError) as exc:
            fail(f"Non-numeric {col}: {exc}")
        if col == "volume":
            if (~np.isfinite(frame[col]) | (frame[col] < 0)).any():
                fail("Invalid volume")
        else:
            if np.isinf(frame[col]).any() or (frame[col] <= 0).any():
                fail(f"Invalid non-positive/infinite {col}")
            if frame[col].isna().any():
                if col != "open":
                    fail(f"NaN {col}: cannot value daily portfolio")
                warnings.append(
                    f"{int(frame[col].isna().sum())} NaN open prices: orders will be cancelled"
                )
    if (
        (frame.high < frame[["open", "close", "low"]].max(axis=1))
        | (frame.low > frame[["open", "close", "high"]].min(axis=1))
    ).any():
        fail("Inconsistent OHLC range")
    if (frame.volume == 0).any():
        warnings.append(
            f"{int((frame.volume == 0).sum())} zero-volume bars: orders will be cancelled"
        )
    for symbol in symbols:
        missing_dates = sessions.difference(frame.loc[frame.symbol == symbol, "date"])
        if len(missing_dates):
            warnings.append(
                f"{symbol}: {len(missing_dates)} missing bars; cancel orders, carry last known valuation with daily warning"
            )
    if price_mode == "adjusted":
        if "adj_close" not in frame:
            fail(
                "adjusted mode requires adj_close; cannot silently treat raw OHLC as adjusted"
            )
        frame["adj_close"] = pd.to_numeric(frame.adj_close, errors="raise")
        if (~np.isfinite(frame.adj_close) | (frame.adj_close <= 0)).any():
            fail("Invalid adj_close")
        ratio = frame.adj_close / frame.close
        frame[PRICE_COLUMNS] = frame[PRICE_COLUMNS].mul(ratio, axis=0)
        warnings.append(
            "Adjusted research units: all OHLC scaled by adj_close/raw_close; dividends/splits are not posted separately; volume remains provider volume"
        )
    elif price_mode == "raw":
        if ("dividend" in frame and frame.dividend.fillna(0).ne(0).any()) or (
            "split_factor" in frame
            and (~frame.split_factor.fillna(1).isin([0, 1])).any()
        ):
            fail("Raw corporate actions are unsupported; supply adjusted research data")
        warnings.append(
            "Raw price-only research: corporate actions are not modeled; unreported dividends/splits may bias results"
        )
    else:
        fail("Unknown price_mode")
    frame = frame.sort_values(["date", "symbol"]).reset_index(drop=True)
    changes = frame.groupby("symbol").close.pct_change(fill_method=None)
    if changes.abs().gt(extreme_threshold).any():
        warnings.append(
            f"Suspicious absolute close returns > {extreme_threshold:.0%}; review data"
        )
    return frame, warnings
