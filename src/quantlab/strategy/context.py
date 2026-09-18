from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class StrategyContext:
    cash: float
    equity: float
    positions: Mapping[str, int]
    universe: tuple[str, ...]
    seed: int
    next_session_date: date | None = None
    execution_sizing: str = "target_weights"

    def __post_init__(self):
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))
        object.__setattr__(self, "universe", tuple(self.universe))
