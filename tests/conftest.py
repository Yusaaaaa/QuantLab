from pathlib import Path
import pandas as pd
import pytest
from quantlab.config import Config


@pytest.fixture
def config():
    c = Config.model_validate(
        {
            "backtest": {"start_date": "2024-01-02", "end_date": "2024-01-04"},
            "commission": {"model": "zero"},
            "slippage": {"model": "zero"},
        }
    )
    c.strategy.path = (
        Path(__file__).resolve().parents[1] / "strategies/fixed_weight_buy_and_hold.py"
    )
    return c


@pytest.fixture
def manual_prices():
    rows = []
    for day, a, t, s in [
        ("2024-01-02", 90, 180, 400),
        ("2024-01-03", 110, 210, 404),
        ("2024-01-04", 120, 190, 408),
    ]:
        for symbol, close in [("AAPL", a), ("TSLA", t), ("SPY", s)]:
            op = 100 if symbol == "AAPL" else 200 if symbol == "TSLA" else 400
            rows.append(
                dict(
                    date=pd.Timestamp(day),
                    symbol=symbol,
                    open=op,
                    high=max(op, close) + 1,
                    low=min(op, close) - 1,
                    close=close,
                    adj_close=close,
                    volume=1000,
                )
            )
    return pd.DataFrame(rows)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
