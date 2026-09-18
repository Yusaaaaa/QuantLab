"""Deterministic artificial prices, never presented as historical market data."""

from pathlib import Path
import numpy as np
import pandas as pd
from .calendar import schedule


def make_sample_data(seed=42, start="2020-01-01", end="2024-12-31"):
    rng = np.random.default_rng(seed)
    dates = schedule(start, end).index
    frames = []
    for i, symbol in enumerate(
        ["AAPL", "TSLA", "SPY", "SYN1", "SYN2", "SYN3", "SYN4", "SYN5"]
    ):
        drift = np.where(np.arange(len(dates)) % 250 < 150, 0.0007, -0.0005)
        close = (80 + 20 * i) * np.exp(
            np.cumsum(rng.normal(drift, 0.012 + i * 0.001, len(dates)))
        )
        op = np.r_[close[0], close[:-1]] * np.exp(rng.normal(0, 0.003, len(dates)))
        frame = pd.DataFrame(
            dict(
                date=dates,
                symbol=symbol,
                open=op,
                high=np.maximum(op, close) * 1.01,
                low=np.minimum(op, close) * 0.99,
                close=close,
                volume=rng.integers(100000, 2000000, len(dates)),
                adj_close=close,
            )
        )
        if symbol == "SYN1" and len(dates) > 25:
            frame = frame.drop(index=[10, 25])
        if symbol == "SYN2" and len(dates) > 20:
            frame.loc[20, "volume"] = 0
        if symbol == "SYN3" and len(dates) > 30:
            frame.loc[30, "open"] = np.nan
        frames.append(frame)
    return pd.concat(frames).sort_values(["date", "symbol"]).reset_index(drop=True)


def write_sample_data(directory, seed=42):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    frame = make_sample_data(seed)
    frame.to_csv(directory / "sample.csv", index=False, float_format="%.10f")
    # Same numerical precision across both local provider examples.
    pd.read_csv(directory / "sample.csv").to_parquet(
        directory / "sample.parquet", index=False
    )
    (directory / "known_prices.csv").write_text(
        "date,symbol,open,high,low,close,volume,adj_close\n2024-01-02,AAPL,100,101,89,90,1000,90\n2024-01-02,TSLA,200,201,179,180,1000,180\n2024-01-02,SPY,400,401,399,400,1000,400\n2024-01-03,AAPL,100,111,99,110,1000,110\n2024-01-03,TSLA,200,211,199,210,1000,210\n2024-01-03,SPY,400,405,399,404,1000,404\n2024-01-04,AAPL,100,121,99,120,1000,120\n2024-01-04,TSLA,200,201,189,190,1000,190\n2024-01-04,SPY,400,409,399,408,1000,408\n"
    )
    return directory / "sample.csv"
