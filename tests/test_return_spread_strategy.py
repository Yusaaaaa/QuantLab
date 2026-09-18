from datetime import date
from pathlib import Path
import hashlib
import json
import runpy

import pandas as pd
import pytest

from quantlab.archive import archive_run
from quantlab.config import Config, load_config
from quantlab.data.calendar import schedule
from quantlab.data.market_view import MarketDataView
from quantlab.engine.backtest import run_backtest
from quantlab.engine.broker import Broker
from quantlab.engine.portfolio import Portfolio
from quantlab.engine.fill import Fill
from quantlab.engine.relative_sizing import freeze_relative_allocation
from quantlab.costs.commission import PerShareCommission, ZeroCommission
from quantlab.costs.slippage import FixedBpsSlippage, ZeroSlippage
from quantlab.strategy.loader import load_strategy
from quantlab.types import InvalidStrategyOutputError

ROOT = Path(__file__).resolve().parents[1]
FACTOR = ROOT / "factors/return_spread.py"
STRATEGY = ROOT / "strategies/aapl_weekly_relative_reversal.py"


def config():
    c = Config.model_validate(
        {
            "backtest": {"start_date": "2020-01-03", "end_date": "2020-01-31"},
            "universe": {"symbols": ["AAPL"]},
            "strategy": {
                "path": STRATEGY,
                "params": {"start_date": "2020-01-06", "end_date": "2020-01-31"},
                "factor_paths": {"factors.return_spread": FACTOR},
            },
            "execution": {"sizing": "decision_relative"},
            "commission": {"model": "zero"},
            "slippage": {"model": "zero"},
            "report": {"enabled": False},
        }
    )
    return c


def panel():
    rows = []
    special = {
        "2020-01-10": 90.0,
        "2020-01-13": 180.0,
        "2020-01-14": 90.0,
        "2020-01-15": 90.0,
        "2020-01-16": 90.0,
        "2020-01-21": 50.0,
    }
    for day in schedule("2020-01-03", "2020-01-31").index:
        apple = special.get(
            str(day.date()), 99.0 if day >= pd.Timestamp("2020-01-17") else 100.0
        )
        for symbol, price in [("AAPL", apple), ("SPY", 100.0)]:
            rows.append(
                dict(
                    date=day,
                    symbol=symbol,
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    adj_close=price,
                    volume=10000,
                )
            )
    return pd.DataFrame(rows)


def test_daily_and_weekly_are_distinct():
    functions = runpy.run_path(str(FACTOR))
    data = panel()
    # Thursday 90 -> Friday 99 is +10%; preceding Friday was also 90 here.
    data.loc[
        (data.symbol == "AAPL") & (data.date == "2020-01-16"),
        ["open", "close", "adj_close"],
    ] = 95.0
    view = MarketDataView(data, "2020-01-17", ["AAPL", "SPY"])
    daily = functions["daily_return_spread"](view, "AAPL", "SPY")
    weekly = functions["weekly_return_spread"](view, "AAPL", "SPY")
    assert daily["spread"] == pytest.approx(99 / 95 - 1)
    assert weekly["spread"] == pytest.approx(0.1)
    assert weekly["start_date"] == "2020-01-10" and weekly["end_date"] == "2020-01-17"


def test_exact_half_cash_and_shares_despite_open_gap():
    r = run_backtest(config(), panel())
    assert list(r.fills.side) == ["buy", "buy", "sell"]
    assert list(r.fills.quantity) == [500, 138, 319]
    assert list(r.fills.fill_price) == [100.0, 180.0, 50.0]
    assert pd.to_datetime(r.fills.timestamp).dt.date.tolist() == [
        date(2020, 1, 6),
        date(2020, 1, 13),
        date(2020, 1, 21),
    ]
    equity = r.equity_curve.set_index("date")
    assert equity.loc["2020-01-13", "cash"] == 25160
    assert equity.loc["2020-01-21", "cash"] == 41110
    assert equity.loc["2020-01-31", "equity"] == 41110 + 319 * 99
    audit = [json.loads(d) for d in r.decisions.details if d != "{}"]
    assert [d["action"] for d in audit] == [
        "initial",
        "buy_half_cash",
        "sell_half_shares",
        "hold",
    ]
    assert audit[1]["factor"]["spread"] == pytest.approx(-0.1)


@pytest.mark.parametrize("end_price", [99.0, 101.0])
def test_threshold_equality_does_not_trade(end_price):
    c = config()
    c.backtest.end_date = date(2020, 1, 13)
    prices = panel()
    prices = prices.loc[prices.date <= "2020-01-13"].copy()
    mask = (prices.symbol == "AAPL") & (prices.date == "2020-01-10")
    prices.loc[mask, ["open", "high", "low", "close", "adj_close"]] = end_price
    result = run_backtest(c, prices)
    assert len(result.fills) == 1
    assert (
        json.loads(
            result.decisions.loc[result.decisions.date == "2020-01-10", "details"].iloc[
                0
            ]
        )["action"]
        == "hold"
    )


def test_buy_budget_includes_fee_and_sell_odd_quantity_rounds_down():
    p = Portfolio(1000)
    p.apply_fill(Fill("old", "old", "t", "AAPL", "buy", 5, 100, 0, 0))
    allocation = freeze_relative_allocation({"AAPL": 0.75}, p, "AAPL")
    assert allocation.side == "buy" and allocation.fraction == pytest.approx(0.5)
    b = Broker(PerShareCommission(0, 1), FixedBpsSlippage(10))
    b.execute_relative(
        allocation, p, {"AAPL": {"open": 10.0, "volume": 100}}, "t", "t+1"
    )
    assert b.fills[0].quantity == 24
    assert p.cash == pytest.approx(500 - 24 * 10.01 - 1)
    assert 500 - p.cash <= 250  # exactly half the available cash budget, fees included
    p = Portfolio(1000)
    p.apply_fill(Fill("old", "old", "t", "AAPL", "buy", 5, 100, 0, 0))
    allocation = freeze_relative_allocation({"AAPL": 0.25}, p, "AAPL")
    b = Broker(ZeroCommission(), ZeroSlippage())
    b.execute_relative(
        allocation, p, {"AAPL": {"open": 50.0, "volume": 100}}, "t", "t+1"
    )
    assert b.fills[0].quantity == 2 and p.positions["AAPL"].quantity == 3


def test_factor_rejects_unsynchronized_endpoints():
    prices = panel()
    prices = prices.loc[~((prices.symbol == "SPY") & (prices.date == "2020-01-10"))]
    view = MarketDataView(prices, "2020-01-17", ["AAPL", "SPY"])
    with pytest.raises(ValueError, match="synchronized"):
        runpy.run_path(str(FACTOR))["weekly_return_spread"](view, "AAPL", "SPY")


def test_future_perturbation_cannot_change_past_factor_or_fills():
    prices = panel()
    a = run_backtest(config(), prices)
    prices.loc[
        prices.date > "2020-01-13", ["open", "high", "low", "close", "adj_close"]
    ] *= 100
    b = run_backtest(config(), prices)
    pd.testing.assert_frame_equal(
        a.decisions.loc[a.decisions.date <= "2020-01-13"],
        b.decisions.loc[b.decisions.date <= "2020-01-13"],
    )
    pd.testing.assert_frame_equal(a.fills.iloc[:2], b.fills.iloc[:2])


def test_factor_binding_and_recursive_lint(tmp_path):
    with pytest.raises(InvalidStrategyOutputError, match="import"):
        load_strategy(STRATEGY, {})
    unsafe = tmp_path / "unsafe.py"
    unsafe.write_text("import requests\n")
    with pytest.raises(InvalidStrategyOutputError, match="import"):
        load_strategy(STRATEGY, {}, {"factors.return_spread": unsafe})


def test_mode_is_explicit_and_single_asset():
    c = config()
    c.execution.sizing = "target_weights"
    with pytest.raises(ValueError, match="decision_relative"):
        run_backtest(c, panel())
    c = config()
    c.universe.symbols = ["AAPL", "SPY"]
    with pytest.raises(ValueError, match="one tradable"):
        run_backtest(c, panel())


def test_factor_snapshot_survives_original_change(tmp_path):
    c = config()
    path = tmp_path / "factor.py"
    path.write_bytes(FACTOR.read_bytes())
    c.strategy.factor_paths = {"factors.return_spread": path}
    c.data.path = tmp_path / "prices.parquet"
    panel().to_parquet(c.data.path, index=False)
    c.data.provider = "parquet_local"
    c.report.runs_dir = tmp_path / "runs"
    run, a = archive_run(c)
    path.write_text('raise RuntimeError("original factor changed")\n')
    frozen = load_config(run / "config.snapshot.yaml")
    second, b = archive_run(frozen)
    assert a.metrics == b.metrics
    for field in ["equity_curve", "fills", "orders", "decisions"]:
        pd.testing.assert_frame_equal(getattr(a, field), getattr(b, field))
    copied = next((run / "factors.snapshot").glob("*.py"))
    metadata = json.loads((run / "metadata.json").read_text())
    assert (
        metadata["factor_fingerprints"]["factors.return_spread"]
        == hashlib.sha256(copied.read_bytes()).hexdigest()
    )
    assert copied.read_bytes() == FACTOR.read_bytes() and run != second
