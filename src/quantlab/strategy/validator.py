import math
from numbers import Real
from quantlab.types import InvalidStrategyOutputError
from .loader import load_strategy


def validate_weights(weights, symbols, max_position_weight=1.0, max_gross_exposure=1.0):
    if weights is None:
        return None
    if not isinstance(weights, dict):
        raise InvalidStrategyOutputError("Target weights must be dict or None")
    for symbol, value in weights.items():
        if symbol not in symbols:
            raise InvalidStrategyOutputError(f"Unknown target symbol: {symbol}")
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            or not 0 <= value <= max_position_weight
        ):
            raise InvalidStrategyOutputError(f"Invalid target weight {symbol}={value}")
    if sum(weights.values()) > min(1.0, max_gross_exposure) + 1e-12:
        raise InvalidStrategyOutputError("Target gross exposure exceeds maximum")
    return {s: float(w) for s, w in sorted(weights.items())}


def validate_strategy(
    path,
    params=None,
    symbols=None,
    factor_paths=None,
    benchmark="SPY",
    execution_sizing="target_weights",
):
    import pandas as pd
    from quantlab.data.market_view import MarketDataView
    from quantlab.data.calendar import schedule, next_session_date
    from .context import StrategyContext

    params = params if params is not None else {"weights": {"AAPL": 0.5, "TSLA": 0.5}}
    symbols = symbols or list(params.get("weights", {"AAPL": 0.5, "TSLA": 0.5}))
    observable_symbols = list(dict.fromkeys(symbols + [benchmark]))
    strategy, meta, _ = load_strategy(path, params, factor_paths)
    n = max(3, strategy.warmup_bars() + 1)
    if n > 10000:
        raise InvalidStrategyOutputError("Validator warmup limit is 10000 bars")
    start = pd.Timestamp(params.get("start_date", "2000-01-03")) - pd.Timedelta(days=7)
    dates = schedule(start, start + pd.Timedelta(days=n * 3 + 30)).index[:n]
    frame = pd.DataFrame(
        [
            dict(
                date=d,
                symbol=s,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1000.0,
            )
            for d in dates
            for s in observable_symbols
        ]
    )
    for dt in dates[-3:]:
        ctx = StrategyContext(
            100000.0,
            100000.0,
            {},
            tuple(symbols),
            42,
            next_session_date(dt),
            execution_sizing,
        )
        view = MarketDataView(frame, dt, observable_symbols)
        if all(len(view.history(s)) >= strategy.warmup_bars() for s in symbols):
            validate_weights(strategy.generate_target_weights(dt, view, ctx), symbols)
    return meta
