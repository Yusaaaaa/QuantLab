PERCENT_METRICS = {
    "total_return",
    "cagr",
    "ann_vol",
    "max_drawdown",
    "avg_gross_exposure",
    "avg_cash_weight",
    "alpha_ann",
    "tracking_error",
}


def format_metric(name, value):
    if value is None:
        return "N/A"
    if name in PERCENT_METRICS:
        return f"{value:.2%}"
    if name in {"n_orders", "n_fills", "max_dd_duration_days"}:
        return str(int(value))
    if name.startswith("total_") and name != "total_return":
        return f"${value:,.2f}"
    return f"{value:,.4f}"
