from dataclasses import replace
from datetime import date
from pathlib import Path
import json
import pandas as pd
import pytest
from quantlab.config import Config
from quantlab.data.calendar import schedule, next_session_date
from quantlab.data.market_view import MarketDataView
from quantlab.engine.backtest import run_backtest
from quantlab.strategy.context import StrategyContext
from quantlab.strategy.loader import load_strategy
from quantlab.strategy.validator import validate_strategy

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / "strategies/weekly_equal_weight_aapl_tsla.py"


def data_panel(start="2020-01-03", end="2020-01-31"):
    rows = []
    for index, day in enumerate(schedule(start, end).index):
        for symbol, price in [
            ("AAPL", 100 + index),
            ("TSLA", 200 - index),
            ("SPY", 300 + index),
        ]:
            rows.append(
                dict(
                    date=day,
                    symbol=symbol,
                    open=float(price),
                    high=float(price + 1),
                    low=float(price - 1),
                    close=float(price),
                    adj_close=float(price),
                    volume=10000,
                )
            )
    return pd.DataFrame(rows)


def configuration(end="2020-01-31"):
    c = Config.model_validate(
        {
            "backtest": {"start_date": "2020-01-03", "end_date": end},
            "commission": {"model": "zero"},
            "slippage": {"model": "zero"},
        }
    )
    c.strategy.path = STRATEGY
    c.strategy.params = {"start_date": "2020-01-06", "end_date": end}
    return c


def test_validator():
    assert (
        validate_strategy(
            STRATEGY, {"start_date": "2020-01-06", "end_date": "2025-12-31"}
        )["name"]
        == "weekly_equal_weight_aapl_tsla"
    )


def test_monday_open_and_holiday_rollforward():
    r = run_backtest(configuration(), data_panel())
    days = pd.to_datetime(r.fills.timestamp).dt.tz_convert("America/New_York").dt.date
    assert sorted(set(days)) == [
        date(2020, 1, 6),
        date(2020, 1, 13),
        date(2020, 1, 21),
        date(2020, 1, 27),
    ]
    assert (r.equity_curve.iloc[0][["cash", "equity"]] == 100000).all()
    assert r.positions.loc[r.positions.date == "2020-01-03", "quantity"].sum() == 0
    assert all(
        pd.Timestamp(a) < pd.Timestamp(b)
        for a, b in zip(r.orders.created_at, r.orders.execution_date)
    )
    nonnull = r.decisions[r.decisions.target_weights != "null"]
    assert list(nonnull.date.dt.strftime("%Y-%m-%d")) == [
        "2020-01-03",
        "2020-01-10",
        "2020-01-17",
        "2020-01-24",
    ]
    assert all(
        json.loads(value) == {"AAPL": 0.5, "TSLA": 0.5}
        for value in nonnull.target_weights
    )
    first = r.fills.loc[days == date(2020, 1, 6)]
    # First execution opens 101 and 199, not Friday's 100 and 200.
    assert first.quantity.tolist() == [495, 251]
    assert first.fill_price.tolist() == [101.0, 199.0]
    assert r.equity_curve.iloc[1]["cash"] == 100000 - 495 * 101 - 251 * 199


def test_full_calendar_has_exactly_one_instruction_per_week():
    c = configuration("2025-12-31")
    prices = data_panel(end="2025-12-31")
    prices[["open", "high", "low", "close", "adj_close"]] = 100.0
    r = run_backtest(c, prices)
    # Use calendar-only assertions for each decision. Price series must stay positive;
    # this particular test supplies fixed prices below.
    observed = [
        next_session_date(d)
        for d in r.decisions.loc[r.decisions.target_weights != "null", "date"]
    ]
    trading = schedule("2020-01-06", "2025-12-31").index
    expected = list(
        pd.Series(trading, index=trading)
        .groupby([trading.isocalendar().year, trading.isocalendar().week])
        .first()
        .dt.date
    )
    assert observed == expected
    assert len(observed) == 313
    assert observed[0] == date(2020, 1, 6) and observed[-1] == date(2025, 12, 29)


def test_future_prices_do_not_change_schedule_or_past_fills():
    c = configuration()
    prices = data_panel()
    a = run_backtest(c, prices)
    prices.loc[
        prices.date > "2020-01-14", ["open", "high", "low", "close", "adj_close"]
    ] *= 100
    b = run_backtest(c, prices)
    pd.testing.assert_frame_equal(a.decisions, b.decisions)
    pd.testing.assert_frame_equal(
        a.fills.loc[a.fills.timestamp < "2020-01-15"],
        b.fills.loc[b.fills.timestamp < "2020-01-15"],
    )


def test_context_exposes_calendar_not_future_prices():
    prices = data_panel()
    view = MarketDataView(prices, "2020-01-17", ["AAPL", "TSLA"])
    ctx = StrategyContext(
        100000, 100000, {}, ("AAPL", "TSLA"), 42, next_session_date("2020-01-17")
    )
    strategy, _, _ = load_strategy(STRATEGY, {})
    assert ctx.next_session_date == date(2020, 1, 21)
    assert strategy.generate_target_weights(pd.Timestamp("2020-01-17"), view, ctx) == {
        "AAPL": 0.5,
        "TSLA": 0.5,
    }
    assert view.history("AAPL").date.max() == pd.Timestamp("2020-01-17")
    with pytest.raises(ValueError):
        view.history("AAPL", end="2020-01-21")
    with pytest.raises(ValueError, match="next_session_date"):
        strategy.generate_target_weights(
            None, view, replace(ctx, next_session_date=None)
        )
