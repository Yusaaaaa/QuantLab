"""Explicit daily-return definitions; undefined ratios are JSON null, never infinity."""

import numpy as np
import pandas as pd
from .drawdown import drawdown_details
from .benchmark import benchmark_metrics
from quantlab.utils.serialization import json_safe

METRIC_DEFINITIONS = {
    "total_return": "Final equity / initial cash - 1.",
    "cagr": "Compound return using elapsed calendar days / 365.25, first session close to last session close.",
    "ann_vol": "Sample standard deviation (ddof=1) of close-to-close returns × sqrt(trading_days).",
    "sharpe": "Mean daily excess return / sample excess-return std × sqrt(trading_days); geometric daily risk-free rate.",
    "sortino": "Mean daily excess return / sqrt(mean(min(excess,0)^2)) × sqrt(trading_days); all observations in denominator.",
    "max_drawdown": "Minimum equity / running maximum - 1; initial cash included at first close.",
    "max_dd_duration_days": "Longest peak-to-recovery calendar-day duration; active episode ends at final observation.",
    "calmar": "CAGR / abs(max_drawdown); undefined if no drawdown.",
    "turnover_ann": "Two-sided gross traded fill notional / previous close equity, summed × trading_days / return intervals. No division by two.",
    "avg_gross_exposure": "Arithmetic mean of end-of-session invested market value / equity, including initial cash-only session.",
    "avg_cash_weight": "Arithmetic mean of end-of-session cash / equity, including initial cash-only session.",
    "beta": "Sample covariance(strategy, benchmark) / sample variance(benchmark).",
    "alpha_ann": "Arithmetic Jensen alpha: (mean(strategy excess) - beta × mean(benchmark excess)) × trading_days.",
    "tracking_error": "Sample standard deviation of strategy - benchmark daily returns × sqrt(trading_days).",
    "information_ratio": "Mean active daily return × trading_days / tracking_error.",
    "n_orders": "All orders, including cancelled and rejected.",
    "n_fills": "Actual fill count.",
    "total_commission": "Sum of fees charged on fills.",
    "total_slippage_cost": "Sum quantity × abs(fill price - open reference).",
    "total_transaction_cost": "Commission + slippage attribution; slippage is already in fill price, not charged twice.",
}


def performance_metrics(result, analytics):
    equity = result.equity_curve.set_index("date").equity
    initial = result.metadata.get("initial_cash", float(equity.iloc[0]))
    total = float(equity.iloc[-1] / initial - 1)
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        cagr = float(np.expm1(np.log1p(total) / years)) if years > 0 else None
    if cagr is not None and not np.isfinite(cagr):
        result.warnings.append("CAGR undefined: annualization exceeds numeric range")
        cagr = None
    # First row is a baseline, not an observed daily return.
    returns = result.returns.set_index("date")["return"].iloc[1:]
    benchmark = result.benchmark.set_index("date")["return"].iloc[1:]
    n = len(returns)
    td = analytics.trading_days
    rf = (1 + analytics.risk_free_rate) ** (1 / td) - 1
    excess = returns - rf
    std = float(excess.std(ddof=1)) if n >= 2 else None
    downside = float(np.sqrt(np.mean(np.minimum(excess, 0) ** 2))) if n else None
    dd = drawdown_details(equity)
    notional = 0.0
    previous = equity.shift(1)
    for _, fill in result.fills.iterrows():
        day = (
            pd.Timestamp(fill.timestamp)
            .tz_convert("America/New_York")
            .tz_localize(None)
            .normalize()
        )
        denominator = previous.loc[day]
        if not np.isfinite(denominator) or denominator <= 0:
            raise ValueError("Invalid turnover equity denominator")
        notional += abs(fill.quantity * fill.fill_price) / denominator
    commission = float(result.fills.commission.sum())
    slippage = float(result.fills.slippage_cost.sum())
    metrics = dict(
        total_return=total,
        cagr=cagr,
        ann_vol=std * np.sqrt(td) if std is not None else None,
        sharpe=float(excess.mean() / std * np.sqrt(td))
        if std is not None and std > 1e-12
        else None,
        sortino=float(excess.mean() / downside * np.sqrt(td))
        if downside is not None and downside > 1e-12
        else None,
        max_drawdown=dd["max_drawdown"],
        max_dd_duration_days=dd["max_dd_duration_days"],
        calmar=cagr / abs(dd["max_drawdown"])
        if cagr is not None and dd["max_drawdown"] < 0
        else None,
        turnover_ann=notional * td / n if n else 0.0,
        avg_gross_exposure=float(result.equity_curve.gross_exposure.mean()),
        avg_cash_weight=float(result.equity_curve.cash_weight.mean()),
        n_orders=len(result.orders),
        n_fills=len(result.fills),
        total_commission=commission,
        total_slippage_cost=slippage,
        total_transaction_cost=commission + slippage,
    )
    metrics.update(benchmark_metrics(returns, benchmark, td, analytics.risk_free_rate))
    result.metadata["drawdown_details"] = dd
    result.metadata["metric_definitions"] = METRIC_DEFINITIONS
    result.metrics = json_safe(metrics)
    return result.metrics
