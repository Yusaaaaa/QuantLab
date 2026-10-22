"""Strategy Name: user-defined
Idea: must be explicitly specified by the user
Exact Mathematical Rule: required before implementation
Universe: configured symbols
Selection Rule: user-defined
Portfolio Construction: target weights only
Decision Time: session close
Execution Time: next session open
Required Data: through decision timestamp only
Parameters: user-defined
Look-ahead Protection: MarketDataView, immutable context
Known Limitations: V1 long-only integer adjusted research units
"""

from quantlab.strategy.base import BaseStrategy

STRATEGY_META = {
    "name": "template",
    "version": "0.0.0",
    "description": "Inert strategy template, not a research example",
}


class Strategy(BaseStrategy):
    def generate_target_weights(self, dt, data, ctx):
        return None


def build_strategy(params):
    return Strategy(params)
