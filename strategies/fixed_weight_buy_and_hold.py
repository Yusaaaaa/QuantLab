"""Buy once at the next open; no subsequent rebalance or automatic retry."""

from quantlab.strategy.base import BaseStrategy

STRATEGY_META = {
    "name": "fixed_weight_buy_and_hold",
    "version": "1.0.0",
    "description": "Fixed target weights once, then hold; default AAPL/TSLA 50/50.",
}


class Strategy(BaseStrategy):
    def __init__(self, params):
        super().__init__(params)
        self.sent = False
        self.weights = dict(params.get("weights", {"AAPL": 0.5, "TSLA": 0.5}))

    def generate_target_weights(self, dt, data, ctx):
        if self.sent:
            return None
        for symbol, weight in self.weights.items():
            if weight > 0:
                bar = data.current(symbol)
                if bar is None or bar["volume"] <= 0:
                    return None
        self.sent = True
        return dict(self.weights)


def build_strategy(params):
    return Strategy(params)
