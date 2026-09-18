import math
from .position import Position
from quantlab.types import ExecutionError, InsufficientCashError


class Portfolio:
    def __init__(self, initial_cash):
        if not math.isfinite(initial_cash) or initial_cash <= 0:
            raise ValueError("Invalid initial cash")
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.positions = {}
        self.realized_pnl = 0.0

    @property
    def market_value(self):
        return sum(p.market_value for p in self.positions.values())

    @property
    def equity(self):
        return self.cash + self.market_value

    @property
    def unrealized_pnl(self):
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def weights(self):
        return (
            {s: p.market_value / self.equity for s, p in self.positions.items()}
            if self.equity
            else {}
        )

    def mark(self, prices):
        for symbol, price in prices.items():
            if not math.isfinite(price) or price <= 0:
                raise ExecutionError(f"Invalid mark: {symbol}")
            if symbol in self.positions:
                self.positions[symbol].last_price = float(price)
        self.check()

    def apply_fill(self, fill):
        q, p, fee = fill.quantity, fill.fill_price, fill.commission
        if (
            type(q) is not int
            or q <= 0
            or not math.isfinite(p)
            or p <= 0
            or not math.isfinite(fee)
            or fee < 0
        ):
            raise ExecutionError("Invalid fill")
        position = self.positions.get(fill.symbol, Position(fill.symbol))
        if fill.side == "buy":
            debit = q * p + fee
            if debit > self.cash:
                raise InsufficientCashError("Fill exceeds available cash")
            position.average_cost = (
                position.quantity * position.average_cost + debit
            ) / (position.quantity + q)
            self.cash -= debit
            position.quantity += q
        elif fill.side == "sell":
            if q > position.quantity:
                raise ExecutionError("Short selling forbidden")
            proceeds = q * p - fee
            if self.cash + proceeds < 0:
                raise InsufficientCashError(
                    "Sell commission exceeds cash plus proceeds"
                )
            self.cash += proceeds
            self.realized_pnl += proceeds - q * position.average_cost
            position.quantity -= q
            if not position.quantity:
                position.average_cost = 0.0
        else:
            raise ExecutionError("Unknown side")
        position.last_price = p
        self.positions[fill.symbol] = position
        self.check()

    def check(self):
        if self.cash < 0 or any(
            p.quantity < 0 or type(p.quantity) is not int
            for p in self.positions.values()
        ):
            raise ExecutionError("Portfolio constraint violated")
        if not math.isfinite(self.equity):
            raise ExecutionError("Non-finite equity")
        if not math.isclose(
            self.equity,
            self.initial_cash + self.realized_pnl + self.unrealized_pnl,
            abs_tol=1e-7,
            rel_tol=1e-10,
        ):
            raise ExecutionError("Ledger P&L identity violated")
