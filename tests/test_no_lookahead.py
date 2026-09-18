from pathlib import Path
from quantlab.data.market_view import MarketDataView
from quantlab.data.sample import make_sample_data
from quantlab.strategy.loader import load_strategy
from quantlab.strategy.context import StrategyContext


def test_future_change_cannot_change_observation_or_output():
    frame = make_sample_data(start="2024-01-02", end="2024-01-10")
    changed = frame.copy()
    changed.loc[changed.date > "2024-01-03", ["open", "high", "low", "close"]] *= (
        1000000
    )
    path = (
        Path(__file__).resolve().parents[1] / "strategies/fixed_weight_buy_and_hold.py"
    )
    outputs = []
    observations = []
    for data in [frame, changed]:
        strategy, _, _ = load_strategy(path, {"weights": {"AAPL": 0.5, "TSLA": 0.5}})
        view = MarketDataView(data, "2024-01-03", ["AAPL", "TSLA"])
        observations.append(view.history("AAPL").close.tolist())
        outputs.append(
            strategy.generate_target_weights(
                view.as_of,
                view,
                StrategyContext(100000, 100000, {}, ("AAPL", "TSLA"), 42),
            )
        )
    assert observations[0] == observations[1]
    assert outputs[0] == outputs[1] == {"AAPL": 0.5, "TSLA": 0.5}
