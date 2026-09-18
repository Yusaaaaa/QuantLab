import pandas as pd
import pytest
from dataclasses import FrozenInstanceError
from quantlab.data.market_view import MarketDataView
from quantlab.strategy.context import StrategyContext
from quantlab.data.sample import make_sample_data


def test_truncated_and_copied():
    frame = make_sample_data(start="2024-01-02", end="2024-01-10")
    view = MarketDataView(frame, "2024-01-03", ["AAPL"])
    assert view.history("AAPL").date.max() == pd.Timestamp("2024-01-03")
    copy = view.history("AAPL")
    copy.loc[:, "close"] = 0
    assert (view.history("AAPL").close > 0).all()
    with pytest.raises(ValueError):
        view.history("AAPL", end="2024-01-04")
    with pytest.raises(ValueError):
        view.history("SPY")


def test_context_immutable():
    positions = {"AAPL": 1}
    ctx = StrategyContext(1, 2, positions, ("AAPL",), 42)
    positions["AAPL"] = 5
    assert ctx.positions["AAPL"] == 1
    with pytest.raises(TypeError):
        ctx.positions["AAPL"] = 2
    with pytest.raises(FrozenInstanceError):
        ctx.cash = 2
