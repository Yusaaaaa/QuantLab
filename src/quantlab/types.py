"""Domain errors and the stable result contract."""

from dataclasses import dataclass, field
import pandas as pd


class QuantLabError(ValueError):
    pass


class InvalidConfigError(QuantLabError):
    pass


class DataUnavailableError(QuantLabError):
    pass


class InvalidStrategyOutputError(QuantLabError):
    pass


class InsufficientHistoryError(QuantLabError):
    pass


class InsufficientCashError(QuantLabError):
    pass


class ExecutionError(QuantLabError):
    pass


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    returns: pd.DataFrame
    positions: pd.DataFrame
    orders: pd.DataFrame
    fills: pd.DataFrame
    benchmark: pd.DataFrame
    metrics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    decisions: pd.DataFrame = field(default_factory=pd.DataFrame)
