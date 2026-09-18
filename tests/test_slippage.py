import pytest
from quantlab.costs.slippage import ZeroSlippage, FixedBpsSlippage


def test_slippage():
    c = FixedBpsSlippage(10)
    assert c.execution_price("buy", 100) == pytest.approx(100.10)
    assert c.execution_price("sell", 100) == pytest.approx(99.90)
    assert ZeroSlippage().execution_price("buy", 100) == 100
