from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .plots import build_charts
from .tables import format_metric


def audit_assumptions(c):
    return {
        "Decision timing": "NYSE session close; daily OHLCV through the current close only.",
        "Execution timing": "Next NYSE session open. Open executions occur before that day’s close decision. No same-close fills.",
        "Price adjustment policy": f"{c.data.price_mode}: adjusted mode scales every OHLC by adj_close/raw_close; no separate dividend/split postings. Integer quantities are research units, not historical raw-share quantities. Raw mode rejects declared corporate actions.",
        "Commission assumption": str(c.commission.model_dump()),
        "Slippage assumption": str(c.slippage.model_dump())
        + "; slippage embedded in fill price, never debited twice.",
        "Fractional-share policy": "Integer shares only. Standard mode floors target notional / execution price; decision_relative mode floors the requested buy budget or sell share fraction.",
        "Sizing policy": c.execution.sizing
        + (
            ": at decision close freeze a single-asset cash or share fraction; buys use that fraction of execution-time cash INCLUDING commission; sells floor that fraction of held shares. Target weights are decision-close instructions, not open-time weight targets."
            if c.execution.sizing == "decision_relative"
            else ": convert target weights using execution-time equity and prices."
        ),
        "Factor source bindings": str(c.strategy.factor_paths),
        "Cash allocation": (
            "Single asset: preserve the requested fraction of available cash or held shares. Buy budget includes commission; sell quantities are rounded down. No automatic retry."
            if c.execution.sizing == "decision_relative"
            else "Target equity marked at open; sell before buy; alphabetical buy allocation; reduce quantity to afford fees. Unfilled remainder cancelled, no automatic retry."
        ),
        "Cash return": "Uninvested cash earns zero interest. No interest income or financing is modeled.",
        "Missing-data policy": "Missing bar, nonfinite open or volume <= 0: cancel. Held missing close: last known mark with warning. No future price fill. Missing benchmark sessions fail.",
        "Daily execution proxy": "Final daily volume is used only as a zero-volume tradability flag, as required by the V1 daily-bar model. It is not known at the open; this is not an intraday liquidity simulation. No volume-based sizing.",
        "Adjusted-data limitation": "Provider-adjusted series may be revised after corporate actions and are not point-in-time raw prices. Integer-share rounding on adjusted units is a research approximation.",
        "Universe source": c.universe.source
        + "; symbols: "
        + ", ".join(c.universe.symbols),
        "Survivorship warning": "Fixed/current selected symbols are not a point-in-time universe; selection and survivorship bias are possible.",
        "Look-ahead protection": "MarketDataView holds physically truncated copies; context is immutable. Import/AST lint is a contract check, not an adversarial Python sandbox. Only trusted reviewed strategy code may run.",
        "Rebalance schedule": c.strategy.rebalance_schedule
        + " decision eligibility; actual target frequency is defined by the loaded strategy. None means no instruction. See Strategy Description and frozen strategy source. Execution cancellation does not automatically retry.",
        "Exposure limits": "Limits validate requested target weights, not subsequent market drift; no forced end-of-day rebalance.",
        "Benchmark": "Frictionless fractional buy-and-hold normalized at first session close, same price policy and dates; first strategy close is the cash baseline.",
        "Warmup": "Observed bars inside the requested date range; insufficient warmup raises an error. Missing bars do not count.",
        "End of test": "Final-close targets are cancelled; existing holdings are marked, not forcibly liquidated.",
        "Reproducibility": "Frozen raw input panel, strategy, explicitly bound factor sources, resolved config, engine source copy, package versions and source/data fingerprints. Reinstall saved code/dependencies for exact environment reproduction.",
        "Data source": c.data.source,
    }


def build_report(result, config, path, reproduction_command):
    environment = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    environment.filters["metric"] = format_metric
    summary = {
        "Run ID": result.metadata["run_id"],
        "Strategy": result.metadata["strategy"]["name"],
        "Strategy Description": result.metadata["strategy"]["description"],
        "Start / End": f"{config.backtest.start_date} / {config.backtest.end_date}",
        "Initial Cash": f"${config.backtest.initial_cash:,.2f}",
        "Final Equity": f"${result.equity_curve.equity.iloc[-1]:,.2f}",
        "Benchmark": config.data.benchmark,
        "Data Provider": config.data.provider,
        "Price Policy": config.data.price_mode,
        "Decision Timing": config.execution.decision_time,
        "Execution Timing": config.execution.timing,
        "Commission": str(config.commission.model_dump()),
        "Slippage": str(config.slippage.model_dump()),
        "Universe": ", ".join(config.universe.symbols),
        "Git Commit": result.metadata.get("git_commit") or "Uncommitted repository",
    }
    html = environment.get_template("report.html.j2").render(
        result=result,
        summary=summary,
        charts=build_charts(result, config.analytics),
        metrics=[(k, format_metric(k, v)) for k, v in result.metrics.items()],
        audit=audit_assumptions(config),
        reproduction_command=reproduction_command,
        orders=result.orders.head(500).to_dict("records"),
        order_columns=list(result.orders.columns),
    )
    Path(path).write_text(html)
    return Path(path)
