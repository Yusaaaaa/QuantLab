import numpy as np
import pandas as pd


def benchmark_metrics(returns, benchmark, trading_days=252, risk_free_rate=0.0):
    aligned = pd.concat(
        [returns.rename("strategy"), benchmark.rename("benchmark")], axis=1
    )
    if aligned.isna().any().any():
        raise ValueError("Benchmark and strategy returns must be exactly aligned")
    n = len(aligned)
    empty = dict(beta=None, alpha_ann=None, tracking_error=None, information_ratio=None)
    if n < 2:
        return empty
    r, b = aligned.strategy, aligned.benchmark
    rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    variance = b.var(ddof=1)
    beta = float(r.cov(b) / variance) if variance > 1e-24 else None
    active = r - b
    te = float(active.std(ddof=1) * np.sqrt(trading_days))
    return dict(
        beta=beta,
        alpha_ann=float(((r - rf).mean() - beta * (b - rf).mean()) * trading_days)
        if beta is not None
        else None,
        tracking_error=te,
        information_ratio=float(active.mean() * trading_days / te)
        if te > 1e-12
        else None,
    )
