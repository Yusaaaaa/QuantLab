import pytest
from quantlab.engine.portfolio import Portfolio
from quantlab.engine.fill import Fill
from quantlab.types import InsufficientCashError, ExecutionError


def fill(side, q, p, fee):
    return Fill("f", "o", "2024-01-03", "AAPL", side, q, p, fee, 0)


def test_round_trip_accounting():
    p = Portfolio(1000)
    p.apply_fill(fill("buy", 5, 100, 1))
    p.mark({"AAPL": 110})
    assert p.cash == 499
    assert p.positions["AAPL"].average_cost == pytest.approx(100.2)
    assert p.equity == 1049
    p.apply_fill(fill("sell", 2, 120, 1))
    assert p.cash == 738
    assert p.realized_pnl == pytest.approx(38.6)
    assert p.equity == pytest.approx(1000 + p.realized_pnl + p.unrealized_pnl)
    p.apply_fill(fill("sell", 3, 90, 1))
    assert p.equity == 1007
    assert p.realized_pnl == pytest.approx(7)


def test_invalid_fill_atomic():
    p = Portfolio(100)
    with pytest.raises(InsufficientCashError):
        p.apply_fill(fill("buy", 2, 100, 0))
    assert p.cash == 100 and p.positions == {}
    with pytest.raises(ExecutionError):
        p.apply_fill(fill("sell", 1, 100, 0))
