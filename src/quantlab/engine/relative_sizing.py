"""Preserve a single-asset cash/share trade fraction across an overnight price gap.

The strategy still returns target weights at the decision close. This explicit
execution policy freezes the requested change as a fraction of available cash
(for increases) or held shares (for reductions). The broker sizes it at the next
open. It does not inspect prices after the decision timestamp to choose direction.
"""

from dataclasses import dataclass
import math
from quantlab.types import InvalidStrategyOutputError


@dataclass(frozen=True)
class RelativeAllocation:
    symbol: str
    side: str
    fraction: float


def freeze_relative_allocation(target, portfolio, symbol):
    current_weight = portfolio.weights.get(symbol, 0.0)
    difference = target.get(symbol, 0.0) - current_weight
    if abs(difference) <= 1e-12:
        return None
    if difference > 0:
        cash_weight = portfolio.cash / portfolio.equity
        if cash_weight <= 0:
            raise InvalidStrategyOutputError("Cannot increase exposure without cash")
        fraction = difference / cash_weight
        side = "buy"
    else:
        fraction = -difference / current_weight
        side = "sell"
    if not math.isfinite(fraction) or not 0 < fraction <= 1 + 1e-10:
        raise InvalidStrategyOutputError("Relative trade fraction must be in (0, 1]")
    return RelativeAllocation(symbol, side, min(1.0, fraction))
