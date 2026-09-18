import pytest
from pydantic import ValidationError
from quantlab.config import Config, load_config


@pytest.mark.parametrize(
    "value",
    [
        {"typo": 1},
        {"execution": {"timimg": "next_open"}},
        {"execution": {"timing": "same_close"}},
        {"portfolio": {"allow_short": True}},
        {"backtest": {"initial_cash": -1}},
        {"slippage": {"bps": float("nan")}},
        {"universe": {"symbols": ["AAPL", "AAPL"]}},
        {"backtest": {"start_date": "2024-01-02", "end_date": "2020-01-01"}},
    ],
)
def test_invalid(value):
    with pytest.raises(ValidationError):
        Config.model_validate(value)


def test_paths_and_override(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("data: {path: prices.csv}")
    config = load_config(path, tmp_path / "s.py")
    assert config.data.path == tmp_path / "prices.csv"
    assert config.strategy.path == tmp_path / "s.py"
