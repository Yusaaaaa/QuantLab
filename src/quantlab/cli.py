"""Public CLI; all business logic resides in domain modules."""

from pathlib import Path
import webbrowser
import typer

app = typer.Typer(
    help="US Equity Quant Lab — daily equity research.", no_args_is_help=True
)
backtest_app = typer.Typer(help="Run backtests.", no_args_is_help=True)
strategies_app = typer.Typer(help="Validate strategy contracts.", no_args_is_help=True)
report_app = typer.Typer(help="Open archived reports.", no_args_is_help=True)
app.add_typer(backtest_app, name="backtest")
app.add_typer(strategies_app, name="strategies")
app.add_typer(report_app, name="report")


def fail(exc):
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=1)


@backtest_app.command("run")
def backtest_run(
    strategy: Path = typer.Option(
        None, "--strategy", help="Override strategy path in config."
    ),
    config: Path = typer.Option(..., "--config", help="YAML configuration path."),
):
    """Run a backtest and archive inputs, results and report."""
    from quantlab.config import load_config
    from quantlab.archive import archive_run

    try:
        run, result = archive_run(load_config(config, strategy))
    except (
        ValueError,
        OSError,
        ImportError,
        TypeError,
        RuntimeError,
        SyntaxError,
    ) as exc:
        fail(exc)
    typer.echo(f"Run saved: {run}")
    typer.echo(f"Final equity: ${result.equity_curve.equity.iloc[-1]:,.2f}")
    if (run / "report.html").exists():
        typer.echo(f"Report: {run / 'report.html'}")


@strategies_app.command("validate")
def strategies_validate(
    path: Path = typer.Argument(...),
    config: Path = typer.Option(
        None, "--config", help="Optional config supplies strategy params and universe."
    ),
):
    """Lint, load and smoke-test a strategy contract (trusted Python only)."""
    from quantlab.strategy.validator import validate_strategy
    from quantlab.config import load_config

    try:
        c = load_config(config) if config else None
        meta = validate_strategy(
            path,
            c.strategy.params if c else None,
            c.universe.symbols if c else None,
            c.strategy.factor_paths if c else None,
            c.data.benchmark if c else "SPY",
            c.execution.sizing if c else "target_weights",
        )
    except (
        ValueError,
        OSError,
        ImportError,
        TypeError,
        RuntimeError,
        SyntaxError,
    ) as exc:
        fail(exc)
    typer.echo(f"Validated {meta['name']} {meta['version']}")


@report_app.command("open")
def report_open(
    run_id: str = typer.Argument(...),
    runs_dir: Path = typer.Option(Path("runs"), "--runs-dir"),
):
    """Open an archived HTML report using the system browser."""
    root = runs_dir.resolve()
    path = (root / run_id / "report.html").resolve()
    if not path.is_relative_to(root) or not path.is_file():
        fail(ValueError(f"Report not found under {root}: {run_id}"))
    if not webbrowser.open(path.as_uri()):
        fail(
            RuntimeError(
                f"Browser could not open report; open this file manually: {path}"
            )
        )
    typer.echo(str(path))


if __name__ == "__main__":
    app()
