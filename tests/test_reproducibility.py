import json
import pandas as pd
from quantlab.engine.backtest import run_backtest
from quantlab.metrics.performance import performance_metrics
from quantlab.archive import archive_run
from quantlab.config import load_config


def test_identical_inputs(config, manual_prices):
    a = run_backtest(config, manual_prices)
    b = run_backtest(config, manual_prices)
    for field in ["equity_curve", "positions", "orders", "fills", "decisions"]:
        pd.testing.assert_frame_equal(getattr(a, field), getattr(b, field))
    assert performance_metrics(a, config.analytics) == performance_metrics(
        b, config.analytics
    )


def test_archive_and_frozen_reproduction(config, manual_prices, tmp_path):
    source = tmp_path / "original.csv"
    manual_prices.to_csv(source, index=False)
    config.data.path = source
    config.report.runs_dir = tmp_path / "runs"
    run, a = archive_run(config)
    required = [
        "config.snapshot.yaml",
        "strategy.snapshot.py",
        "summary.json",
        "metrics.json",
        "equity.csv",
        "returns.csv",
        "positions.parquet",
        "orders.csv",
        "fills.csv",
        "benchmark.csv",
        "warnings.json",
        "report.html",
        "logs.txt",
        "metadata.json",
        "manifest.json",
        "data.snapshot.parquet",
    ]
    assert all((run / p).is_file() for p in required)
    html = (run / "report.html").read_text()
    assert html.count("data:image/png;base64,") == 10
    assert "Audit assumptions" in html and "quantlab backtest run" in html
    assert all(key in html for key in a.metrics)
    metadata = json.loads((run / "metadata.json").read_text())
    assert metadata["status"] == "complete" and metadata["data_fingerprint"]
    # Original data is no longer available; reproduction must consume frozen input.
    source.unlink()
    frozen = load_config(run / "config.snapshot.yaml")
    frozen.report.enabled = False
    second, b = archive_run(frozen)
    assert run != second and (run / "report.html").exists()
    assert a.metrics == b.metrics
    assert a.metadata["data_fingerprint"] == b.metadata["data_fingerprint"]
    for field in ["equity_curve", "orders", "fills", "positions"]:
        pd.testing.assert_frame_equal(getattr(a, field), getattr(b, field))
