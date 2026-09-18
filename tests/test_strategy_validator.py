from pathlib import Path
import pytest
from quantlab.strategy.validator import validate_weights, validate_strategy
from quantlab.strategy.loader import lint_strategy
from quantlab.types import InvalidStrategyOutputError

ROOT = Path(__file__).resolve().parents[1]


def test_official_strategy():
    assert (
        validate_strategy(ROOT / "strategies/fixed_weight_buy_and_hold.py")["version"]
        == "1.0.0"
    )


@pytest.mark.parametrize(
    "weights",
    [
        {"AAPL": -0.1},
        {"AAPL": float("nan")},
        {"AAPL": float("inf")},
        {"AAPL": True},
        {"X": 0.1},
        {"AAPL": 0.7, "TSLA": 0.4},
        [0.5],
    ],
)
def test_bad_weights(weights):
    with pytest.raises(InvalidStrategyOutputError):
        validate_weights(weights, ["AAPL", "TSLA"])


def test_limits():
    with pytest.raises(InvalidStrategyOutputError):
        validate_weights({"AAPL": 0.6}, ["AAPL"], 0.5)
    with pytest.raises(InvalidStrategyOutputError):
        validate_weights({"AAPL": 0.6}, ["AAPL"], 1, 0.5)
    assert validate_weights(None, ["AAPL"]) is None


@pytest.mark.parametrize(
    "source",
    [
        "import requests",
        "import yfinance",
        "from quantlab.engine import portfolio",
        "import os",
        "from pandas import read_csv",
        'import pandas as pd\npd.read_csv("x")',
        "ctx.cash = 0",
        "data._history",
        'getattr(data,"x")',
    ],
)
def test_lint(tmp_path, source):
    p = tmp_path / "bad.py"
    p.write_text(source)
    with pytest.raises(InvalidStrategyOutputError):
        lint_strategy(p)
