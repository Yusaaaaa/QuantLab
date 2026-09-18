from dataclasses import dataclass
from typing import Protocol


class CommissionModel(Protocol):
    def calculate(self, quantity, price) -> float: ...


@dataclass(frozen=True)
class ZeroCommission:
    def calculate(self, quantity, price):
        return 0.0


@dataclass(frozen=True)
class PerShareCommission:
    per_share_fee: float = 0.005
    minimum_fee: float = 1.0

    def calculate(self, quantity, price):
        return (
            max(self.minimum_fee, abs(quantity) * self.per_share_fee)
            if quantity
            else 0.0
        )


@dataclass(frozen=True)
class BpsCommission:
    bps: float = 0.0

    def calculate(self, quantity, price):
        return abs(quantity * price) * self.bps / 10000


def from_config(c):
    return {
        "zero": lambda: ZeroCommission(),
        "per_share": lambda: PerShareCommission(c.per_share, c.minimum),
        "bps": lambda: BpsCommission(c.bps),
    }[c.model]()
