import pandas as pd
import pytest
from quantlab.data.sample import make_sample_data, write_sample_data
from quantlab.data.csv_local import CSVLocalDataProvider
from quantlab.data.parquet_local import ParquetLocalDataProvider
from quantlab.data.validator import validate_prices
from quantlab.data.calendar import schedule
from quantlab.types import DataUnavailableError


@pytest.fixture
def bars():
    return make_sample_data(start="2024-01-02", end="2024-03-01")


def validate(bars):
    return validate_prices(bars, list(bars.symbol.unique()), "2024-01-02", "2024-03-01")


def test_deterministic_and_exceptions(bars):
    pd.testing.assert_frame_equal(
        bars, make_sample_data(start="2024-01-02", end="2024-03-01")
    )
    _, warnings = validate(bars)
    assert any("missing bars" in w for w in warnings)
    assert any("zero-volume" in w for w in warnings)
    assert any("NaN open" in w for w in warnings)


@pytest.mark.parametrize(
    "col,value",
    [
        ("close", 0),
        ("volume", -1),
        ("close", float("nan")),
        ("open", float("inf")),
        ("date", "bad"),
        ("symbol", None),
    ],
)
def test_invalid(bars, col, value):
    bars[col] = bars[col].astype(object)
    bars.loc[0, col] = value
    with pytest.raises((DataUnavailableError, ValueError)):
        validate(bars)


def test_duplicate(bars):
    with pytest.raises(DataUnavailableError):
        validate(pd.concat([bars, bars.iloc[:1]]))


def test_adjustment(bars):
    bars.adj_close *= 0.5
    out, _ = validate(bars)
    assert out.iloc[0].close == bars.iloc[0].close * 0.5
    assert out.iloc[0].open == bars.iloc[0].open * 0.5


def test_local_providers(tmp_path):
    write_sample_data(tmp_path)
    a = CSVLocalDataProvider(tmp_path / "sample.csv").load_prices(
        ["AAPL", "SPY"], "2024-01-02", "2024-01-10"
    )
    b = ParquetLocalDataProvider(tmp_path / "sample.parquet").load_prices(
        ["AAPL", "SPY"], "2024-01-02", "2024-01-10"
    )
    pd.testing.assert_frame_equal(a, b)


def test_calendar():
    s = schedule("2024-07-03", "2024-07-05")
    assert list(s.index.strftime("%Y-%m-%d")) == ["2024-07-03", "2024-07-05"]
    assert s.iloc[0]["close"].hour == 17  # early close, UTC (13:00 New York)
    assert len(schedule("2024-07-04", "2024-07-04")) == 0
