import numpy as np


def rolling_statistics(returns, window=63, trading_days=252, risk_free_rate=0.0):
    excess = returns - ((1 + risk_free_rate) ** (1 / trading_days) - 1)
    std = returns.rolling(window, min_periods=window).std(ddof=1)
    sharpe = (
        excess.rolling(window, min_periods=window).mean()
        / std.where(std > 1e-12)
        * np.sqrt(trading_days)
    )
    return std * np.sqrt(trading_days), sharpe


def period_returns(returns, frequency):
    return (1 + returns).resample(frequency).prod() - 1
