import hashlib
import json
import pandas as pd
import pytest
from pydantic import ValidationError
from quantlab.config import load_config
from quantlab.data.market_view import MarketDataView
from quantlab.data.validator import validate_prices
from quantlab.strategy.validator import validate_strategy
from quantlab.strategy.loader import load_strategy
from quantlab.strategy.context import StrategyContext
from quantlab.engine.backtest import run_backtest
from quantlab.engine.clock import decision_due
from quantlab.archive import archive_run
from quantlab.types import (
    InvalidStrategyOutputError,
    InsufficientHistoryError,
    DataUnavailableError,
)


def write_strategy(path, body, warmup=0):
    path.write_text(
        'from quantlab.strategy.base import BaseStrategy\nSTRATEGY_META = {"name":"test", "version":"1", "description":"test only"}\nclass Strategy(BaseStrategy):\n    def warmup_bars(self): return '
        + str(warmup)
        + "\n    def generate_target_weights(self, dt, data, ctx):\n        "
        + body
        + "\ndef build_strategy(params): return Strategy(params)\n"
    )
    return path


def test_intraday_daily_bar_denied(manual_prices):
    with pytest.raises(ValueError, match="session close"):
        MarketDataView(manual_prices, pd.Timestamp("2024-01-02 15:00Z"), ["AAPL"])
    view = MarketDataView(manual_prices, pd.Timestamp("2024-01-02 21:00Z"), ["AAPL"])
    assert len(view.history("AAPL")) == 1


def test_data_dependent_no_lookahead(manual_prices, tmp_path):
    path = write_strategy(
        tmp_path / "test.py",
        "return {'AAPL': 1.0 if data.history('AAPL')['close'].iloc[-1] > 100 else 0.0}",
    )
    future = manual_prices.copy()
    future.loc[future.date > "2024-01-02", "close"] = 1e12
    ctx = StrategyContext(100000, 100000, {}, ("AAPL",), 42)
    outputs = []
    for data in (manual_prices, future):
        strategy, _, _ = load_strategy(path, {})
        outputs.append(
            strategy.generate_target_weights(
                pd.Timestamp("2024-01-02"),
                MarketDataView(data, "2024-01-02", ["AAPL"]),
                ctx,
            )
        )
    assert outputs == [{"AAPL": 0.0}, {"AAPL": 0.0}]


def test_changed_source_never_uses_stale_bytecode(tmp_path):
    p = tmp_path / "s.py"
    write_strategy(p, "return {'AAPL': 0.1}")
    a, _, _ = load_strategy(p, {})
    write_strategy(p, "return {'AAPL': 0.2}")
    b, _, _ = load_strategy(p, {})
    assert a.generate_target_weights(None, None, None) == {"AAPL": 0.1}
    assert b.generate_target_weights(None, None, None) == {"AAPL": 0.2}


@pytest.mark.parametrize(
    "frequency,previous,current,expected",
    [
        ("weekly", "2024-01-04", "2024-01-05", False),
        ("weekly", "2024-01-05", "2024-01-08", True),
        ("monthly", "2024-01-30", "2024-01-31", False),
        ("monthly", "2024-01-31", "2024-02-01", True),
        ("weekly", "2023-12-29", "2024-01-02", True),
    ],
)
def test_schedule(frequency, previous, current, expected):
    assert (
        decision_due(pd.Timestamp(current), pd.Timestamp(previous), frequency)
        == expected
    )


def test_warmup_and_delay(config, manual_prices, tmp_path):
    config.strategy.path = write_strategy(
        tmp_path / "warmup.py", "return {'AAPL': 1.0}", warmup=2
    )
    r = run_backtest(config, manual_prices)
    assert len(r.fills) == 1 and "2024-01-04" in r.fills.iloc[0].timestamp
    write_strategy(config.strategy.path, "return {'AAPL': 1.0}", warmup=10)
    with pytest.raises(InsufficientHistoryError):
        run_backtest(config, manual_prices)


def test_strategy_limit_checked_by_engine(config, manual_prices):
    config.portfolio.max_position_weight = 0.4
    with pytest.raises(InvalidStrategyOutputError):
        run_backtest(config, manual_prices)


def test_zero_volume_cancellation_no_retry(config, manual_prices):
    manual_prices.loc[
        (manual_prices.symbol == "AAPL") & (manual_prices.date == "2024-01-03"),
        "volume",
    ] = 0
    result = run_backtest(config, manual_prices)
    assert len(result.fills) == 1 and result.fills.iloc[0].symbol == "TSLA"
    assert result.orders.loc[result.orders.symbol == "AAPL", "status"].tolist() == [
        "cancelled"
    ]


def test_failed_archive_keeps_error(config, manual_prices, tmp_path):
    config.data.path = tmp_path / "bad.csv"
    manual_prices.assign(close=-1).to_csv(config.data.path, index=False)
    config.report.runs_dir = tmp_path / "runs"
    with pytest.raises(DataUnavailableError):
        archive_run(config)
    runs = list(config.report.runs_dir.iterdir())
    assert len(runs) == 1
    assert json.loads((runs[0] / "failure.json").read_text())["status"] == "failed"
    assert not (runs[0] / "metadata.json").exists()
    assert "Run failed" in (runs[0] / "logs.txt").read_text()


@pytest.mark.parametrize(
    "yaml_text",
    [
        "false",
        "[]",
        "data: {price_mode: bad}",
        "strategy: {rebalance_schedule: hourly}",
    ],
)
def test_invalid_config_documents(tmp_path, yaml_text):
    p = tmp_path / "bad.yaml"
    p.write_text(yaml_text)
    with pytest.raises(ValidationError):
        load_config(p)


@pytest.mark.parametrize(
    "change",
    [
        "timezone",
        "missing_symbol",
        "missing_column",
        "weekend",
        "no_adj_close",
        "raw_actions",
    ],
)
def test_strict_data_policy(manual_prices, change):
    f = manual_prices.copy()
    mode = "adjusted"
    if change == "timezone":
        f.date = f.date.dt.tz_localize("UTC")
    if change == "missing_symbol":
        f = f.loc[f.symbol != "TSLA"]
    if change == "missing_column":
        f = f.drop(columns="volume")
    if change == "weekend":
        f.loc[0, "date"] = pd.Timestamp("2024-01-06")
    if change == "no_adj_close":
        f = f.drop(columns="adj_close")
    if change == "raw_actions":
        f["dividend"] = 1.0
        mode = "raw"
    with pytest.raises(DataUnavailableError):
        validate_prices(f, ["AAPL", "TSLA", "SPY"], "2024-01-02", "2024-01-04", mode)


def test_context_mutation_fails_runtime(tmp_path):
    p = write_strategy(tmp_path / "bad.py", "ctx.positions['AAPL'] = 100; return None")
    with pytest.raises(TypeError):
        validate_strategy(p)


def test_report_open_cli(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from quantlab.cli import app

    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "report.html").write_text("<html></html>")
    opened = []
    monkeypatch.setattr(
        "quantlab.cli.webbrowser.open", lambda url: opened.append(url) or True
    )
    result = CliRunner().invoke(
        app, ["report", "open", "run", "--runs-dir", str(tmp_path)]
    )
    assert result.exit_code == 0 and opened == [(folder / "report.html").as_uri()]
    result = CliRunner().invoke(
        app, ["report", "open", "../escape", "--runs-dir", str(tmp_path)]
    )
    assert result.exit_code == 1


def test_minimal_cli_run(config, manual_prices, tmp_path):
    import yaml
    from typer.testing import CliRunner
    from quantlab.cli import app

    config.data.path = tmp_path / "p.csv"
    manual_prices.to_csv(config.data.path, index=False)
    config.report.runs_dir = tmp_path / "runs"
    config.report.enabled = False
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config.model_dump(mode="json")))
    result = CliRunner().invoke(app, ["backtest", "run", "--config", str(path)])
    assert result.exit_code == 0 and "Final equity: $107,500.00" in result.output
    run = next(config.report.runs_dir.iterdir())
    manifest = json.loads((run / "manifest.json").read_text())
    assert all(
        hashlib.sha256((run / name).read_bytes()).hexdigest() == digest
        for name, digest in manifest.items()
    )


@pytest.mark.parametrize(
    "text", ["data: [", "data: {provider: csv_local, provider: parquet_local}"]
)
def test_yaml_errors_are_actionable(tmp_path, text):
    from quantlab.types import InvalidConfigError

    p = tmp_path / "bad.yaml"
    p.write_text(text)
    with pytest.raises(InvalidConfigError):
        load_config(p)


def test_naive_intraday_denied(manual_prices):
    with pytest.raises(ValueError, match="timezone-aware"):
        MarketDataView(manual_prices, "2024-01-02 10:00", ["AAPL"])


def test_manifest_failure_never_marks_success(
    config, manual_prices, tmp_path, monkeypatch
):
    import quantlab.archive as archive

    config.data.path = tmp_path / "p.csv"
    manual_prices.to_csv(config.data.path, index=False)
    config.report.runs_dir = tmp_path / "runs"
    config.report.enabled = False
    original = archive.write_json

    def failure(path, value):
        if path.name == "manifest.json":
            raise OSError("injected write failure")
        return original(path, value)

    monkeypatch.setattr(archive, "write_json", failure)
    with pytest.raises(OSError, match="injected"):
        archive.archive_run(config)
    run = next(config.report.runs_dir.iterdir())
    assert not (run / "metadata.json").exists() and (run / "failure.json").exists()
