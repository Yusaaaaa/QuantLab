from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    created_at: str
    execution_date: str
    symbol: str
    side: str
    quantity: int
    reference_price: float | None
    order_type: str = "market"
    status: str = "pending"
    reject_reason: str = ""
    filled_quantity: int = 0
