from dataclasses import dataclass
from typing import Protocol


class SlippageModel(Protocol):
    def execution_price(self, side, reference_price, quantity, market_data): ...


@dataclass(frozen=True)
class ZeroSlippage:
    def execution_price(self, side, reference_price, quantity=0, market_data=None):
        if side not in ("buy", "sell"):
            raise ValueError("Invalid side")
        return float(reference_price)


@dataclass(frozen=True)
class FixedBpsSlippage:
    bps: float = 0.0

    def execution_price(self, side, reference_price, quantity=0, market_data=None):
        if side not in ("buy", "sell"):
            raise ValueError("Invalid side")
        return reference_price * (1 + (1 if side == "buy" else -1) * self.bps / 10000)


def from_config(c):
    return ZeroSlippage() if c.model == "zero" else FixedBpsSlippage(c.bps)
