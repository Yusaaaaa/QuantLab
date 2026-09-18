import pytest
from quantlab.engine.portfolio import Portfolio
from quantlab.engine.broker import Broker
from quantlab.costs.commission import ZeroCommission, PerShareCommission
from quantlab.costs.slippage import ZeroSlippage, FixedBpsSlippage


def bars(a=100, b=200):
    return {"AAPL": {"open": a, "volume": 1000}, "TSLA": {"open": b, "volume": 1000}}


@pytest.mark.parametrize(
    "commission,slippage,qa,qt,cash",
    [
        (ZeroCommission(), ZeroSlippage(), 500, 250, 0),
        (PerShareCommission(0.005, 1), ZeroSlippage(), 500, 249, 196.255),
        (ZeroCommission(), FixedBpsSlippage(10), 499, 249, 200.3),
        (PerShareCommission(0.005, 1), FixedBpsSlippage(10), 499, 249, 196.56),
    ],
)
def test_hand_calculated(commission, slippage, qa, qt, cash):
    p = Portfolio(100000)
    b = Broker(commission, slippage)
    b.execute(
        {"AAPL": 0.5, "TSLA": 0.5}, p, bars(), "2024-01-02 21:00Z", "2024-01-03 14:30Z"
    )
    assert p.positions["AAPL"].quantity == qa and p.positions["TSLA"].quantity == qt
    assert p.cash == pytest.approx(cash)
    assert b.fills[0].fill_price == pytest.approx(slippage.execution_price("buy", 100))
    assert b.fills[0].commission == pytest.approx(
        commission.calculate(qa, b.fills[0].fill_price)
    )
    assert sum(f.slippage_cost for f in b.fills) == pytest.approx(
        qa * (b.fills[0].fill_price - 100) + qt * (b.fills[1].fill_price - 200)
    )
    p.mark({"AAPL": 110, "TSLA": 210})
    assert p.equity == pytest.approx(cash + qa * 110 + qt * 210)
    assert p.cash >= 0


@pytest.mark.parametrize(
    "bar,reason",
    [
        (None, "missing"),
        ({"open": 100, "volume": 0}, "volume"),
        ({"open": float("nan"), "volume": 1}, "price"),
        ({"open": float("inf"), "volume": 1}, "price"),
    ],
)
def test_untradable(bar, reason):
    p = Portfolio(1000)
    b = Broker(ZeroCommission(), ZeroSlippage())
    b.execute({"AAPL": 1}, p, {"AAPL": bar}, "t", "t+1")
    assert not b.fills and p.cash == 1000
    assert b.orders[0].status == "cancelled" and reason in b.orders[0].reject_reason


def test_sell_before_buy_and_liquidate_omitted():
    p = Portfolio(1000)
    b = Broker(ZeroCommission(), ZeroSlippage())
    b.execute({"TSLA": 1}, p, bars(), "t", "t+1")
    b.execute({"AAPL": 1}, p, bars(), "t+1", "t+2")
    assert [f.side for f in b.fills] == ["buy", "sell", "buy"]
    assert p.positions["TSLA"].quantity == 0 and p.positions["AAPL"].quantity == 10


def test_insufficient_cash_rejected():
    p = Portfolio(100)
    b = Broker(PerShareCommission(0, 1000), ZeroSlippage())
    b.execute({"AAPL": 1}, p, bars(), "t", "t+1")
    assert b.orders[0].status == "rejected" and p.cash == 100


def test_already_at_target_does_not_trade_only_because_of_slippage():
    from quantlab.engine.fill import Fill

    portfolio = Portfolio(1000)
    portfolio.apply_fill(Fill("f", "o", "t", "AAPL", "buy", 10, 100, 0, 0))
    broker = Broker(ZeroCommission(), FixedBpsSlippage(10))
    broker.execute({"AAPL": 1.0}, portfolio, bars(), "t", "t+1")
    assert not broker.orders and not broker.fills
    assert portfolio.positions["AAPL"].quantity == 10
