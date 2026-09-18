import pandas as pd
import pytest
from quantlab.engine.backtest import run_backtest
from quantlab.types import DataUnavailableError


@pytest.mark.parametrize(
    "cm,sm,qa,qt,cash,fee,slip",
    [
        ("zero", "zero", 500, 250, 0, 0, 0),
        ("per_share", "zero", 500, 249, 196.255, 3.745, 0),
        ("zero", "bps", 499, 249, 200.3, 0, 99.7),
        ("per_share", "bps", 499, 249, 196.56, 3.74, 99.7),
    ],
)
def test_manual_end_to_end(config, manual_prices, cm, sm, qa, qt, cash, fee, slip):
    config.commission.model = cm
    config.slippage.model = sm
    config.slippage.bps = 10
    r = run_backtest(config, manual_prices)
    assert list(r.fills.quantity) == [qa, qt]
    assert r.fills.commission.sum() == pytest.approx(fee)
    assert r.fills.slippage_cost.sum() == pytest.approx(slip)
    assert r.equity_curve.iloc[0].equity == 100000
    assert r.equity_curve.iloc[1].cash == pytest.approx(cash)
    assert r.equity_curve.iloc[1].equity == pytest.approx(cash + qa * 110 + qt * 210)
    assert r.equity_curve.iloc[-1].equity == pytest.approx(cash + qa * 120 + qt * 190)
    assert all(
        pd.Timestamp(x).date().isoformat() == "2024-01-03" for x in r.fills.timestamp
    )
    assert all(
        pd.Timestamp(a) < pd.Timestamp(b)
        for a, b in zip(r.orders.created_at, r.orders.execution_date)
    )
    assert (r.equity_curve.cash >= 0).all()
    assert r.equity_curve.equity.equals(
        r.equity_curve.cash + r.equity_curve.market_value
    )
    assert r.benchmark.iloc[-1].equity == pytest.approx(102000)


def test_missing_execution_and_stale_valuation(config, manual_prices):
    # AAPL cannot fill on Jan 3. TSLA fills then has no Jan 4 close.
    f = manual_prices.loc[
        ~(
            (
                (manual_prices.symbol == "AAPL")
                & (manual_prices.date == pd.Timestamp("2024-01-03"))
            )
            | (
                (manual_prices.symbol == "TSLA")
                & (manual_prices.date == pd.Timestamp("2024-01-04"))
            )
        )
    ]
    r = run_backtest(config, f)
    assert len(r.fills) == 1 and r.fills.iloc[0].symbol == "TSLA"
    assert r.orders.iloc[0].status == "cancelled"
    assert any("stale valuation" in x for x in r.warnings)


def test_missing_benchmark_fails(config, manual_prices):
    f = manual_prices.loc[
        ~(
            (manual_prices.symbol == "SPY")
            & (manual_prices.date == pd.Timestamp("2024-01-03"))
        )
    ]
    with pytest.raises(DataUnavailableError, match="Benchmark"):
        run_backtest(config, f)


def test_last_day_no_same_day_fill(config, manual_prices):
    config.backtest.end_date = config.backtest.start_date
    r = run_backtest(config, manual_prices.loc[manual_prices.date == "2024-01-02"])
    assert r.fills.empty and r.orders.iloc[0].status == "cancelled"


def test_future_change_does_not_change_past_fills(config, manual_prices):
    a = run_backtest(config, manual_prices)
    changed = manual_prices.copy()
    changed.loc[
        changed.date == "2024-01-04", ["open", "high", "low", "close", "adj_close"]
    ] *= 1000
    b = run_backtest(config, changed)
    pd.testing.assert_frame_equal(a.fills, b.fills)
    pd.testing.assert_frame_equal(a.decisions, b.decisions)
    pd.testing.assert_frame_equal(a.equity_curve.iloc[:2], b.equity_curve.iloc[:2])
