import pytest
from quantlab.costs.commission import ZeroCommission, PerShareCommission, BpsCommission


def test_commissions():
    assert ZeroCommission().calculate(100, 100) == 0
    c = PerShareCommission(0.005, 1)
    assert c.calculate(100, 100) == 1
    assert c.calculate(-400, 100) == 2
    assert c.calculate(0, 100) == 0
    assert BpsCommission(10).calculate(-100, 100) == pytest.approx(10)
