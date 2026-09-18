import pytest
from typer.testing import CliRunner

from quantlab import __version__
from quantlab.cli import app

runner = CliRunner()


def test_package_version():
    assert __version__ == "0.1.0"


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["backtest", "--help"],
        ["backtest", "run", "--help"],
        ["strategies", "validate", "--help"],
        ["report", "open", "--help"],
    ],
)
def test_help(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_missing_input_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["backtest", "run", "--strategy", "missing.py", "--config", "missing.yaml"]
    )
    assert result.exit_code == 1 and "Error:" in result.output
    assert list(tmp_path.iterdir()) == []


def test_missing_report():
    result = runner.invoke(app, ["report", "open", "missing"])
    assert result.exit_code == 1 and "Report not found" in result.output


def test_required_options():
    assert runner.invoke(app, ["backtest", "run"]).exit_code == 2


def test_unknown_command():
    assert runner.invoke(app, ["unknown"]).exit_code == 2
