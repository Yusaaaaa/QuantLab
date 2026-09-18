import pandas as pd
from quantlab.metrics.drawdown import drawdown_details


def series(values):
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))


def test_known_drawdown():
    result = drawdown_details(series([100, 120, 90, 110, 130]))
    assert result == {
        "max_drawdown": -0.25,
        "max_dd_duration_days": 3,
        "peak_date": "2024-01-02",
        "trough_date": "2024-01-03",
        "recovery_date": "2024-01-05",
        "duration_days": 3,
    }


def test_unrecovered_and_flat():
    result = drawdown_details(series([100, 120, 90, 110]))
    assert result["recovery_date"] is None and result["max_dd_duration_days"] == 2
    assert drawdown_details(series([100, 100, 100]))["max_drawdown"] == 0


def test_longest_not_deepest():
    result = drawdown_details(series([100, 50, 100, 99, 98, 99, 100]))
    assert result["duration_days"] == 2 and result["max_dd_duration_days"] == 4
