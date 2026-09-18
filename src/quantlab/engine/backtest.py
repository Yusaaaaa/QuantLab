"""Explicit open/close event engine. Analytics consume only BacktestResult."""

from dataclasses import asdict, fields
import json
import logging
import random
import numpy as np
import pandas as pd
from quantlab.config import Config
from quantlab.types import (
    BacktestResult,
    DataUnavailableError,
    InsufficientHistoryError,
)
from quantlab.data.providers import get_provider
from quantlab.data.calendar import next_session_date
from quantlab.data.validator import validate_prices
from quantlab.data.market_view import MarketDataView
from quantlab.strategy.loader import load_strategy
from quantlab.strategy.validator import validate_weights
from quantlab.strategy.context import StrategyContext
from quantlab.costs.commission import from_config as commission_model
from quantlab.costs.slippage import from_config as slippage_model
from quantlab.utils.serialization import data_fingerprint
from .clock import Clock, decision_due
from .portfolio import Portfolio
from .broker import Broker
from .order import Order
from .fill import Fill
from .relative_sizing import freeze_relative_allocation

log = logging.getLogger("quantlab")


def run_backtest(config: Config, prices=None) -> BacktestResult:
    # Preserve caller RNG state, including if user strategy raises.
    state = random.getstate()
    np_state = np.random.get_state()
    try:
        random.seed(config.reproducibility.random_seed)
        np.random.seed(config.reproducibility.random_seed)
        return _run(config, prices)
    finally:
        random.setstate(state)
        np.random.set_state(np_state)


def _run(c, prices):
    if c.execution.sizing == "decision_relative" and len(c.universe.symbols) != 1:
        raise ValueError(
            "decision_relative sizing currently requires one tradable symbol"
        )
    symbols = list(dict.fromkeys(c.universe.symbols + [c.data.benchmark]))
    if prices is None:
        prices = get_provider(c.data).load_prices(
            symbols, c.backtest.start_date, c.backtest.end_date
        )
    frame, warnings = validate_prices(
        prices,
        symbols,
        c.backtest.start_date,
        c.backtest.end_date,
        c.data.price_mode,
        c.data.extreme_return_threshold,
    )
    fingerprint = data_fingerprint(prices)
    clock = Clock(c.backtest.start_date, c.backtest.end_date)
    dates = clock.schedule.index
    if not len(dates):
        raise DataUnavailableError("No NYSE sessions in requested date range")
    benchmark_prices = (
        frame.loc[frame.symbol == c.data.benchmark]
        .set_index("date")
        .close.reindex(dates)
    )
    if benchmark_prices.isna().any():
        raise DataUnavailableError(
            "Benchmark must cover every NYSE session; no silent forward fill"
        )
    strategy, meta, source = load_strategy(
        c.strategy.path, c.strategy.params, c.strategy.factor_paths
    )
    log.info("Strategy validated: %s %s", meta["name"], meta["version"])
    if c.universe.source == "current_constituents":
        warnings.append(
            "Potential survivorship bias: current constituent list is being used historically."
        )
    else:
        warnings.append(
            "Fixed-list universe; no point-in-time constituent database. Symbol selection may introduce survivorship/selection bias."
        )
    portfolio = Portfolio(c.backtest.initial_cash)
    broker = Broker(
        commission_model(c.commission),
        slippage_model(c.slippage),
        c.portfolio.max_position_weight,
        c.portfolio.max_gross_exposure,
    )
    pending = None
    previous = None
    eligible = False
    snapshots = []
    position_rows = []
    decisions = []
    # Lookup by date prevents accidental use of future execution/valuation bars.
    daily = {
        dt: {r.symbol: r for _, r in group.iterrows()}
        for dt, group in frame.groupby("date")
    }
    for session in clock:
        bars = daily.get(session.date, {})
        # OPEN: execute only the target created at a previous close.
        if pending is not None:
            target, created_at, allocation = pending
            before = len(broker.orders)
            broker.execute(
                target,
                portfolio,
                {s: bars.get(s) for s in c.universe.symbols},
                created_at,
                session.open,
                relative_allocation=allocation,
                relative_mode=c.execution.sizing == "decision_relative",
            )
            for order in broker.orders[before:]:
                log.info("Order %s", asdict(order))
                if order.reject_reason:
                    warnings.append(
                        f"{session.date.date()} {order.symbol}: {order.reject_reason}"
                    )
            pending = None
        # CLOSE: mark only currently observable prices; missing held bars carry last mark.
        close_marks = {
            s: float(bars[s]["close"]) for s in portfolio.positions if s in bars
        }
        for symbol, position in portfolio.positions.items():
            if position.quantity and symbol not in bars:
                warning = f"{session.date.date()} {symbol}: stale valuation at last known price {position.last_price}; no future fill"
                warnings.append(warning)
                log.warning(warning)
        portfolio.mark(close_marks)
        if decision_due(session.date, previous, c.strategy.rebalance_schedule):
            view = MarketDataView(frame, session.close, symbols)
            if all(
                len(view.history(s)) >= strategy.warmup_bars()
                for s in c.universe.symbols
            ):
                eligible = True
                ctx = StrategyContext(
                    portfolio.cash,
                    portfolio.equity,
                    {s: p.quantity for s, p in portfolio.positions.items()},
                    tuple(c.universe.symbols),
                    c.reproducibility.random_seed,
                    next_session_date=next_session_date(session.date),
                    execution_sizing=c.execution.sizing,
                )
                weights = validate_weights(
                    strategy.generate_target_weights(session.close, view, ctx),
                    c.universe.symbols,
                    c.portfolio.max_position_weight,
                    c.portfolio.max_gross_exposure,
                )
                decisions.append(
                    {
                        "decision_timestamp": session.close,
                        "date": session.date,
                        "target_weights": json.dumps(weights, sort_keys=True),
                        "details": json.dumps(
                            strategy.decision_metadata(),
                            sort_keys=True,
                            allow_nan=False,
                        ),
                    }
                )
                log.info("Decision %s target=%s", session.close, weights)
                if weights is not None:
                    allocation = (
                        freeze_relative_allocation(
                            weights, portfolio, c.universe.symbols[0]
                        )
                        if c.execution.sizing == "decision_relative"
                        else None
                    )
                    pending = (weights, session.close, allocation)
        portfolio.check()
        snapshots.append(
            dict(
                date=session.date,
                valuation_timestamp=session.close,
                cash=portfolio.cash,
                market_value=portfolio.market_value,
                equity=portfolio.equity,
                gross_exposure=portfolio.market_value / portfolio.equity
                if portfolio.equity
                else 0.0,
                cash_weight=portfolio.cash / portfolio.equity
                if portfolio.equity
                else 0.0,
                realized_pnl=portfolio.realized_pnl,
                unrealized_pnl=portfolio.unrealized_pnl,
            )
        )
        for symbol in c.universe.symbols:
            p = portfolio.positions.get(symbol)
            position_rows.append(
                dict(
                    date=session.date,
                    symbol=symbol,
                    quantity=p.quantity if p else 0,
                    average_cost=p.average_cost if p else 0.0,
                    last_price=p.last_price if p else None,
                    market_value=p.market_value if p else 0.0,
                    unrealized_pnl=p.unrealized_pnl if p else 0.0,
                    weight=portfolio.weights.get(symbol, 0.0),
                )
            )
        previous = session.date
    if not eligible:
        raise InsufficientHistoryError(
            f"No decision met warmup_bars={strategy.warmup_bars()}; warmup is counted inside backtest range"
        )
    if pending is not None:
        target, created, allocation = pending
        for symbol in sorted(set(target) | set(portfolio.positions)):
            if target.get(symbol, 0) == 0 and (
                symbol not in portfolio.positions
                or portfolio.positions[symbol].quantity == 0
            ):
                continue
            broker.orders.append(
                Order(
                    f"O{len(broker.orders) + 1:06d}",
                    str(created),
                    "",
                    symbol,
                    "buy" if target.get(symbol, 0) > 0 else "sell",
                    0,
                    None,
                    status="cancelled",
                    reject_reason="end of backtest: no next execution session",
                )
            )
        warnings.append(
            "Final-close target cancelled: no next execution session within backtest; no forced liquidation"
        )
    equity = pd.DataFrame(snapshots)
    returns = equity[["date"]].copy()
    returns["return"] = equity.equity.pct_change(fill_method=None).fillna(0.0)
    benchmark = pd.DataFrame({"date": dates, "close": benchmark_prices.to_numpy()})
    benchmark["return"] = benchmark.close.pct_change(fill_method=None).fillna(0.0)
    benchmark["equity"] = (
        c.backtest.initial_cash * benchmark.close / benchmark.close.iloc[0]
    )
    for warning in warnings:
        log.warning(warning)
    return BacktestResult(
        equity,
        returns,
        pd.DataFrame(position_rows),
        pd.DataFrame(
            [asdict(o) for o in broker.orders], columns=[f.name for f in fields(Order)]
        ),
        pd.DataFrame(
            [asdict(f) for f in broker.fills], columns=[f.name for f in fields(Fill)]
        ),
        benchmark,
        warnings=warnings,
        metadata={
            "strategy": meta,
            "data_fingerprint": fingerprint,
            "random_seed": c.reproducibility.random_seed,
            "strategy_source": source,
            "price_policy": c.data.price_mode,
            "initial_cash": c.backtest.initial_cash,
            "n_sessions": len(dates),
        },
        decisions=pd.DataFrame(decisions),
    )
