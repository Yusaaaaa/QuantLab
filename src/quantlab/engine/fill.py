from dataclasses import dataclass


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    timestamp: str
    symbol: str
    side: str
    quantity: int
    fill_price: float
    commission: float
    slippage_cost: float
