import numpy as np
import pandas as pd
import pytest
from quantlab.metrics.performance import performance_metrics, METRIC_DEFINITIONS
from quantlab.metrics.benchmark import benchmark_metrics
from quantlab.metrics.rolling import period_returns, rolling_statistics
from quantlab.engine.backtest import run_backtest


def test_manual_metrics(config, manual_prices):
    result = run_backtest(config, manual_prices)
    metrics = performance_metrics(result, config.analytics)
    # Equity: 100000, 107500, 107500 => returns 0.075, 0.
    assert metrics["total_return"] == pytest.approx(0.075)
    assert metrics["cagr"] == pytest.approx(1.075 ** (365.25 / 2) - 1)
    assert metrics["ann_vol"] == pytest.approx(np.sqrt(0.075**2 / 2) * np.sqrt(252))
    assert metrics["sharpe"] == pytest.approx(np.sqrt(126))
    assert metrics["sortino"] is None
    assert metrics["calmar"] is None
    assert metrics["turnover_ann"] == pytest.approx(126)
    assert metrics["avg_gross_exposure"] == pytest.approx(2 / 3)
    assert metrics["avg_cash_weight"] == pytest.approx(1 / 3)
    assert metrics["n_orders"] == metrics["n_fills"] == 2
    assert metrics["total_transaction_cost"] == 0
    assert set(metrics) == set(METRIC_DEFINITIONS)


def test_risk_metrics(config, manual_prices):
    result = run_backtest(config, manual_prices)
    r = np.array([0.1, -0.1])
    result.equity_curve["equity"] = [100000, 110000, 99000]
    result.returns["return"] = [0, *r]
    m = performance_metrics(result, config.analytics)
    assert m["total_return"] == pytest.approx(-0.01)
    assert m["max_drawdown"] == pytest.approx(-0.1)
    assert m["sortino"] == pytest.approx(0)
    assert m["calmar"] == pytest.approx(m["cagr"] / 0.1)


def test_beta_alpha_tracking_error():
    b = pd.Series([-0.01, 0, 0.01])
    r = 2 * b + 0.001
    m = benchmark_metrics(r, b)
    assert m["beta"] == pytest.approx(2)
    assert m["alpha_ann"] == pytest.approx(0.252)
    assert m["tracking_error"] == pytest.approx(0.01 * np.sqrt(252))
    assert m["information_ratio"] == pytest.approx(0.001 / 0.01 * np.sqrt(252))
    assert benchmark_metrics(b, b)["information_ratio"] is None
    assert benchmark_metrics(b, pd.Series([0.0, 0.0, 0.0]))["beta"] is None


def test_monthly_compounding_and_rolling():
    r = pd.Series(
        [0.1, -0.1, 0.05],
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01"]),
    )
    assert period_returns(r, "ME").iloc[0] == pytest.approx(-0.01)
    vol, sharpe = rolling_statistics(r, 2)
    assert pd.isna(vol.iloc[0])
    assert vol.iloc[1] == pytest.approx(np.std([0.1, -0.1], ddof=1) * np.sqrt(252))
    assert sharpe.iloc[1] == pytest.approx(0)


def test_single_session_undefined(config, manual_prices):
    config.backtest.end_date = config.backtest.start_date
    result = run_backtest(config, manual_prices.loc[manual_prices.date == "2024-01-02"])
    m = performance_metrics(result, config.analytics)
    assert m["cagr"] is None and m["sharpe"] is None and m["beta"] is None
