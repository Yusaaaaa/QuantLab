from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    average_cost: float = 0.0
    last_price: float = 0.0

    @property
    def market_value(self):
        return self.quantity * self.last_price

    @property
    def unrealized_pnl(self):
        return self.quantity * (self.last_price - self.average_cost)
