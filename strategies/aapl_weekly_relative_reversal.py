"""Strategy Name: AAPL weekly relative reversal
Idea: User-defined relative-underperformance buying and outperformance selling.
Exact Mathematical Rule: f = prior completed week's AAPL return minus SPY return.
Universe: AAPL (tradable), SPY (benchmark observation only).
Selection Rule: No stock selection; hold AAPL and cash.
Portfolio Construction: Initially 50% AAPL; f < -0.01 spends half remaining cash
including commission; f > +0.01 sells floor(held shares / 2); otherwise no trade.
Decision Time: Previous week's final NYSE session close.
Execution Time: Monday open; holiday rolls to first session of the week.
Required Data: Adjusted daily closes for synchronized weekly endpoints, daily OHLCV.
Parameters: start_date, end_date, threshold (fixed 0.01 in this experiment).
Look-ahead Protection: Historical MarketDataView plus known next session calendar.
Known Limitations: Integer adjusted units; cash earns zero; no parameter fitting;
initialization takes precedence over the first week's signal; no automatic retries.
Required Execution Sizing: decision_relative (freezes cash/share fractions at close).
"""

from datetime import date
import math
from quantlab.strategy.base import BaseStrategy
from factors.return_spread import weekly_return_spread

STRATEGY_META = {
    "name": "aapl_weekly_relative_reversal",
    "version": "1.0.0",
    "description": "Initially 50% AAPL / 50% cash on 2020-01-06; weekly AAPL minus SPY return < -1pp buys with half remaining cash, > +1pp sells half shares, otherwise hold. Monday open, holidays roll forward. decision_relative sizing; 2020-01-03 is the cash preparation baseline.",
}


class Strategy(BaseStrategy):
    def __init__(self, params):
        super().__init__(params)
        self.start_date = date.fromisoformat(params.get("start_date", "2020-01-06"))
        self.end_date = date.fromisoformat(params.get("end_date", "2025-12-31"))
        self.threshold = float(params.get("threshold", 0.01))
        if self.start_date.weekday() != 0 or self.end_date < self.start_date:
            raise ValueError("Require a Monday start and a nondecreasing date range")
        if not math.isfinite(self.threshold) or self.threshold <= 0:
            raise ValueError("threshold must be positive and finite")
        self.initialized = False
        self.details = {}

    def generate_target_weights(self, dt, data, ctx):
        self.details = {}
        if ctx.execution_sizing != "decision_relative":
            raise ValueError(
                "This strategy requires execution.sizing: decision_relative"
            )
        upcoming = ctx.next_session_date
        if upcoming is None:
            raise ValueError("next_session_date is required")
        if not self.start_date <= upcoming <= self.end_date:
            return None
        if data.as_of.date().isocalendar()[:2] == upcoming.isocalendar()[:2]:
            return None
        if not self.initialized:
            self.initialized = True
            self.details = {"action": "initial", "execution_date": str(upcoming)}
            return {"AAPL": 0.5}
        factor = weekly_return_spread(data, "AAPL", "SPY")
        self.details = {
            "action": "insufficient_history",
            "execution_date": str(upcoming),
            "factor": factor,
        }
        if factor is None:
            return None
        quantity = ctx.positions.get("AAPL", 0)
        weight = quantity * float(data.current("AAPL")["close"]) / ctx.equity
        spread = factor["spread"]
        self.details["action"] = "hold"
        if math.isclose(abs(spread), self.threshold, rel_tol=0.0, abs_tol=1e-12):
            return None
        if spread < -self.threshold:
            self.details["action"] = "buy_half_cash"
            return {"AAPL": min(1.0, weight + 0.5 * ctx.cash / ctx.equity)}
        if spread > self.threshold:
            self.details["action"] = "sell_half_shares"
            return {"AAPL": weight * 0.5}
        return None

    def decision_metadata(self):
        return dict(self.details)


def build_strategy(params):
    return Strategy(params)
