"""Strategy Name: Weekly equal-weight AAPL / TSLA
Idea: User-defined weekly 1:1 holding-value rebalance, without stock selection.
Exact Mathematical Rule: On each scheduled execution date, w_AAPL = w_TSLA = 0.5.
Universe: AAPL and TSLA, fixed throughout; selection/survivorship bias possible.
Selection Rule: None; both securities always belong to the portfolio.
Portfolio Construction: Long-only 50/50 target weights; integer research shares.
Decision Time: Previous NYSE session close, using only the known trading calendar.
Execution Time: Monday open; Monday holiday shifts to the week's first session.
Required Data: Adjusted daily OHLCV; historical view and known next session date.
Parameters: start_date=2020-01-06, end_date=2025-12-31, both inclusive.
Look-ahead Protection: next_session_date is calendar metadata, not a future bar.
Known Limitations: Fees, slippage and integer rounding prevent exact equality;
weights drift between weekly executions. No extra retry after cancelled orders.
The engine baseline is 2020-01-03 close, an all-cash preparation session.
"""

from datetime import date
from quantlab.strategy.base import BaseStrategy

STRATEGY_META = {
    "name": "weekly_equal_weight_aapl_tsla",
    "version": "1.0.0",
    "description": "AAPL/TSLA 50/50 at Monday open (holiday: first session of week), 2020-01-06 through 2025-12-31. Prior-session close decisions; 2020-01-03 is a cash-only preparation baseline. Integer adjusted research units, no forced final liquidation.",
}


class Strategy(BaseStrategy):
    def __init__(self, params):
        super().__init__(params)
        self.start_date = date.fromisoformat(params.get("start_date", "2020-01-06"))
        self.end_date = date.fromisoformat(params.get("end_date", "2025-12-31"))
        if self.start_date.weekday() != 0:
            raise ValueError("start_date must be the intended Monday")
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")

    def generate_target_weights(self, dt, data, ctx):
        execution_date = ctx.next_session_date
        if execution_date is None:
            raise ValueError("Known next_session_date calendar metadata is required")
        if not self.start_date <= execution_date <= self.end_date:
            return None
        current_date = data.as_of.date()
        if current_date.isocalendar()[:2] != execution_date.isocalendar()[:2]:
            return {"AAPL": 0.5, "TSLA": 0.5}
        return None


def build_strategy(params):
    return Strategy(params)
