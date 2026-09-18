"""Independent arithmetic audit of a frozen weekly reversal run, using its raw data.

No engine, strategy or factor implementation is imported. Recompute the weekly
signal, cash budget, integer shares, fees and closing equity from the saved panel.
"""

from pathlib import Path
import argparse
import json
import math
import numpy as np
import pandas as pd
import yaml


def audit(run):
    config = yaml.safe_load((run / "config.snapshot.yaml").read_text())
    data = pd.read_parquet(run / "data.snapshot.parquet")
    data["adjusted_open"] = data.open * data.adj_close / data.close
    close = data.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    opens = data.pivot(
        index="date", columns="symbol", values="adjusted_open"
    ).sort_index()
    # Calendar-week endpoints identified independently from ISO date tuples.
    dates = close.index
    keys = [(d.isocalendar().year, d.isocalendar().week) for d in dates]
    initial_cash = float(config["backtest"]["initial_cash"])
    threshold = float(config["strategy"]["params"]["threshold"])
    cash = initial_cash
    shares = 0
    pending = None
    prior_endpoint = None
    predicted = []
    fills = []
    actions = []
    for i, day in enumerate(dates):
        if pending is not None:
            side = "buy" if pending in ("initial", "buy_half_cash") else "sell"
            price = float(opens.loc[day, "AAPL"]) * (
                1.0005 if side == "buy" else 0.9995
            )
            if side == "buy":
                budget = cash / 2
                quantity = math.floor(budget / price)
                while (
                    quantity and quantity * price + max(1.0, quantity * 0.005) > budget
                ):
                    quantity -= 1
            else:
                quantity = shares // 2
            if quantity:
                fee = max(1.0, quantity * 0.005)
                if side == "buy":
                    cash -= quantity * price + fee
                    shares += quantity
                else:
                    cash += quantity * price - fee
                    shares -= quantity
                fills.append((day.date(), side, quantity, price, fee))
            pending = None
        predicted.append(cash + shares * float(close.loc[day, "AAPL"]))
        if i + 1 < len(dates) and keys[i] != keys[i + 1]:
            if prior_endpoint is None:
                pending = "initial"
                signal = None
            else:
                signal = (
                    close.loc[day, "AAPL"] / close.loc[prior_endpoint, "AAPL"] - 1
                ) - (close.loc[day, "SPY"] / close.loc[prior_endpoint, "SPY"] - 1)
                pending = (
                    "buy_half_cash"
                    if signal < -threshold
                    and not math.isclose(signal, -threshold, abs_tol=1e-12)
                    else "sell_half_shares"
                    if signal > threshold
                    and not math.isclose(signal, threshold, abs_tol=1e-12)
                    else None
                )
            actions.append((str(day.date()), pending or "hold", signal))
            prior_endpoint = day
    actual = pd.read_csv(run / "fills.csv")
    expected_dates = (
        pd.to_datetime(actual.timestamp)
        .dt.tz_convert("America/New_York")
        .dt.date.tolist()
    )
    assert [x[0] for x in fills] == expected_dates
    assert [x[1] for x in fills] == actual.side.tolist()
    assert [x[2] for x in fills] == actual.quantity.tolist()
    np.testing.assert_allclose(
        [x[3] for x in fills], actual.fill_price, rtol=1e-12, atol=1e-9
    )
    np.testing.assert_allclose(
        [x[4] for x in fills], actual.commission, rtol=1e-12, atol=1e-9
    )
    equity = pd.read_csv(run / "equity.csv")
    np.testing.assert_allclose(predicted, equity.equity, rtol=1e-12, atol=1e-7)
    decisions = pd.read_csv(run / "decisions.csv")
    details = [json.loads(value) for value in decisions.details if value != "{}"]
    assert [x[1] for x in actions] == [x["action"] for x in details]
    for (_, action, signal), detail in zip(actions, details):
        if action != "initial":
            assert math.isclose(
                signal, detail["factor"]["spread"], rel_tol=1e-12, abs_tol=1e-12
            )
    return {
        "status": "passed",
        "method": "independent weekly signal, share/cash arithmetic, and every fill/closing equity",
        "sessions": len(dates),
        "weekly_decisions": len(actions),
        "fills": len(fills),
        "final_equity": predicted[-1],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.run), indent=2))
