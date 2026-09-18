"""Freeze target equity at open; sell first, then buy in sorted symbol order."""

import math
from .order import Order
from .fill import Fill
from .execution import tradability, affordable_quantity
from quantlab.strategy.validator import validate_weights
from quantlab.types import InsufficientCashError


class Broker:
    def __init__(
        self, commission, slippage, max_position_weight=1.0, max_gross_exposure=1.0
    ):
        self.commission = commission
        self.slippage = slippage
        self.max_position_weight = max_position_weight
        self.max_gross_exposure = max_gross_exposure
        self.orders = []
        self.fills = []

    def execute(
        self,
        target,
        portfolio,
        bars,
        decision_at,
        execution_at,
        relative_allocation=None,
        relative_mode=False,
    ):
        if relative_mode:
            return self.execute_relative(
                relative_allocation, portfolio, bars, decision_at, execution_at
            )
        validate_weights(
            target,
            set(target) | set(portfolio.positions),
            self.max_position_weight,
            self.max_gross_exposure,
        )
        # Open valuation never reads today's close; unavailable marks retain last close.
        marks = {
            s: float(b["open"])
            for s, b in bars.items()
            if b is not None and math.isfinite(float(b["open"])) and b["open"] > 0
        }
        portfolio.mark(marks)
        equity = portfolio.equity
        pending = []
        for symbol in sorted(set(target) | set(portfolio.positions)):
            weight = target.get(symbol, 0.0)
            current = (
                portfolio.positions[symbol].quantity
                if symbol in portfolio.positions
                else 0
            )
            if weight == 0 and current == 0:
                continue
            bar = bars.get(symbol)
            reason = tradability(bar)
            reference = None if bar is None else float(bar["open"])
            if reference is not None and not math.isfinite(reference):
                reference = None
            if reason:
                last = (
                    portfolio.positions[symbol].last_price
                    if symbol in portfolio.positions
                    else None
                )
                quantity = (
                    abs(math.floor(weight * equity / last) - current) if last else 0
                )
                order = Order(
                    f"O{len(self.orders) + 1:06d}",
                    str(decision_at),
                    str(execution_at),
                    symbol,
                    "buy" if weight > 0 else "sell",
                    quantity,
                    reference,
                    status="cancelled",
                    reject_reason=reason,
                )
                self.orders.append(order)
                continue
            reference_target = math.floor(weight * equity / reference)
            if reference_target == current:
                continue
            side = "buy" if reference_target > current else "sell"
            price = self.slippage.execution_price(side, reference, 0, bar)
            target_qty = math.floor(weight * equity / price)
            delta = target_qty - current
            if (side == "buy" and delta <= 0) or (side == "sell" and delta >= 0):
                continue
            side = "buy" if delta > 0 else "sell"
            price = self.slippage.execution_price(side, reference, abs(delta), bar)
            order = Order(
                f"O{len(self.orders) + 1:06d}",
                str(decision_at),
                str(execution_at),
                symbol,
                side,
                abs(delta),
                reference,
            )
            self.orders.append(order)
            pending.append((order, price))
        for order, price in sorted(
            pending, key=lambda item: (item[0].side != "sell", item[0].symbol)
        ):
            q = order.quantity
            if order.side == "buy":
                q = affordable_quantity(q, portfolio.cash, price, self.commission)
            if q == 0:
                order.status = "rejected"
                order.reject_reason = "insufficient cash including commission"
                continue
            fee = self.commission.calculate(q, price)
            fill = Fill(
                f"F{len(self.fills) + 1:06d}",
                order.order_id,
                str(execution_at),
                order.symbol,
                order.side,
                q,
                price,
                fee,
                q * abs(price - order.reference_price),
            )
            try:
                portfolio.apply_fill(fill)
            except InsufficientCashError as exc:
                order.status = "rejected"
                order.reject_reason = str(exc)
                continue
            self.fills.append(fill)
            order.status = "filled"
            order.filled_quantity = q
            if q < order.quantity:
                order.reject_reason = f"cash constrained: resized {order.quantity} to {q}; remainder cancelled"
        # Restore open marks so intra-day unrealized P&L includes execution costs.
        portfolio.mark(marks)

    def execute_relative(self, allocation, portfolio, bars, decision_at, execution_at):
        if allocation is None:
            return
        symbol = allocation.symbol
        bar = bars.get(symbol)
        reason = tradability(bar)
        reference = float(bar["open"]) if bar is not None else None
        if reference is not None and not math.isfinite(reference):
            reference = None
        order = Order(
            f"O{len(self.orders) + 1:06d}",
            str(decision_at),
            str(execution_at),
            symbol,
            allocation.side,
            0,
            reference,
        )
        self.orders.append(order)
        if reason:
            order.status = "cancelled"
            order.reject_reason = reason
            return
        portfolio.mark({symbol: reference})
        price = self.slippage.execution_price(allocation.side, reference, 0, bar)
        if allocation.side == "buy":
            budget = portfolio.cash * allocation.fraction
            requested = math.floor(budget / price)
            quantity = affordable_quantity(requested, budget, price, self.commission)
        else:
            held = portfolio.positions[symbol].quantity
            requested = math.floor(held * allocation.fraction + 1e-9)
            quantity = min(held, requested)
        order.quantity = requested
        if quantity <= 0:
            order.status = "rejected"
            order.reject_reason = (
                "fractional allocation below one affordable integer share"
            )
            return
        fee = self.commission.calculate(quantity, price)
        fill = Fill(
            f"F{len(self.fills) + 1:06d}",
            order.order_id,
            str(execution_at),
            symbol,
            allocation.side,
            quantity,
            price,
            fee,
            quantity * abs(price - reference),
        )
        try:
            portfolio.apply_fill(fill)
        except InsufficientCashError as exc:
            order.status = "rejected"
            order.reject_reason = str(exc)
            return
        self.fills.append(fill)
        order.status = "filled"
        order.filled_quantity = quantity
        if quantity < requested:
            order.reject_reason = (
                f"cash budget includes commission: resized {requested} to {quantity}"
            )
        portfolio.mark({symbol: reference})
