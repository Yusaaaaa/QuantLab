"""Strict, resolved configuration; paths are relative to the YAML file."""

from datetime import date
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from quantlab.types import InvalidConfigError


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, validate_assignment=True
    )


class BacktestConfig(StrictModel):
    start_date: date = date(2020, 1, 1)
    end_date: date = date(2024, 12, 31)
    initial_cash: float = Field(default=100000, gt=0)
    base_currency: Literal["USD"] = "USD"

    @model_validator(mode="after")
    def dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class DataConfig(StrictModel):
    provider: Literal["csv_local", "parquet_local", "yahoo"] = "csv_local"
    path: Path = Path("../data/raw/sample.csv")
    frequency: Literal["1d"] = "1d"
    price_mode: Literal["adjusted", "raw"] = "adjusted"
    benchmark: str = "SPY"
    source: str = "user supplied data; provenance unverified"
    extreme_return_threshold: float = Field(default=0.5, gt=0)
    missing_data_policy: Literal["cancel_orders_stale_valuation"] = (
        "cancel_orders_stale_valuation"
    )


class UniverseConfig(StrictModel):
    symbols: list[str] = Field(default_factory=lambda: ["AAPL", "TSLA"], min_length=1)
    source: Literal["fixed_list", "current_constituents"] = "fixed_list"

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.symbols)) != len(self.symbols) or any(
            not s.strip() for s in self.symbols
        ):
            raise ValueError("symbols must be nonempty and unique")
        return self


class StrategyConfig(StrictModel):
    path: Path = Path("../strategies/fixed_weight_buy_and_hold.py")
    params: dict = Field(
        default_factory=lambda: {"weights": {"AAPL": 0.5, "TSLA": 0.5}}
    )
    rebalance_schedule: Literal["daily", "weekly", "monthly"] = "daily"
    factor_paths: dict[str, Path] = Field(default_factory=dict)


class ExecutionConfig(StrictModel):
    decision_time: Literal["close"] = "close"
    timing: Literal["next_open"] = "next_open"
    sizing: Literal["target_weights", "decision_relative"] = "target_weights"
    allow_fractional_shares: Literal[False] = False


class CommissionConfig(StrictModel):
    model: Literal["zero", "per_share", "bps"] = "per_share"
    per_share: float = Field(default=0.005, ge=0)
    minimum: float = Field(default=1.0, ge=0)
    bps: float = Field(default=0.0, ge=0)


class SlippageConfig(StrictModel):
    model: Literal["zero", "bps"] = "bps"
    bps: float = Field(default=5.0, ge=0, lt=10000)


class PortfolioConfig(StrictModel):
    allow_short: Literal[False] = False
    allow_negative_cash: Literal[False] = False
    max_position_weight: float = Field(default=1.0, gt=0, le=1)
    max_gross_exposure: float = Field(default=1.0, gt=0, le=1)


class AnalyticsConfig(StrictModel):
    trading_days: int = Field(default=252, gt=0)
    risk_free_rate: float = Field(default=0.0, gt=-1)
    rolling_window: int = Field(default=63, ge=2)


class ReportConfig(StrictModel):
    enabled: bool = True
    open_after_run: bool = False
    runs_dir: Path = Path("../runs")


class ReproducibilityConfig(StrictModel):
    random_seed: int = Field(default=42, ge=0, le=4294967295)


class Config(StrictModel):
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    commission: CommissionConfig = Field(default_factory=CommissionConfig)
    slippage: SlippageConfig = Field(default_factory=SlippageConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    reproducibility: ReproducibilityConfig = Field(
        default_factory=ReproducibilityConfig
    )


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently keeping the last value."""


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            if key in result:
                raise InvalidConfigError(f"Duplicate YAML key: {key}")
            result[key] = loader.construct_object(value_node, deep=deep)
        except TypeError as exc:
            raise InvalidConfigError("YAML mapping keys must be scalar") from exc
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def load_config(path: str | Path, strategy_override: Path | None = None) -> Config:
    path = Path(path).resolve()
    try:
        content = yaml.load(path.read_text(), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise InvalidConfigError(f"Invalid YAML in {path}: {exc}") from exc
    config = Config.model_validate({} if content is None else content)
    for section, field in [
        (config.data, "path"),
        (config.strategy, "path"),
        (config.report, "runs_dir"),
    ]:
        value = getattr(section, field)
        setattr(section, field, (path.parent / value).resolve())
    config.strategy.factor_paths = {
        name: (path.parent / value).resolve()
        for name, value in config.strategy.factor_paths.items()
    }
    if strategy_override is not None:
        config.strategy.path = strategy_override.resolve()
    return config
