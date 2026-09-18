"""Self-contained static research charts; no external CDN or network resources."""

import base64
from io import BytesIO
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from quantlab.metrics.drawdown import drawdown_series
from quantlab.metrics.rolling import rolling_statistics, period_returns


def build_charts(result, analytics):
    equity = result.equity_curve.set_index("date")
    returns = result.returns.set_index("date")["return"].iloc[1:]
    benchmark = result.benchmark.set_index("date")
    charts = []

    def figure(title, draw):
        with plt.rc_context(
            {
                "font.family": "DejaVu Sans",
                "font.size": 9,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.titleweight": "bold",
                "axes.labelcolor": "#263c48",
                "axes.prop_cycle": plt.cycler(color=["#166c69", "#c66b37", "#445e81"]),
            }
        ):
            fig, ax = plt.subplots(figsize=(9, 3.6), layout="constrained")
            draw(ax)
            ax.set_title(title, loc="left", pad=14)
            ax.grid(alpha=0.15)
            stream = BytesIO()
            fig.savefig(stream, format="png", dpi=135, facecolor="white")
            plt.close(fig)
            charts.append(
                {
                    "title": title,
                    "src": "data:image/png;base64,"
                    + base64.b64encode(stream.getvalue()).decode(),
                }
            )

    figure(
        "Strategy equity",
        lambda ax: (ax.plot(equity.index, equity.equity), ax.set_ylabel("USD")),
    )
    figure(
        "Strategy vs benchmark",
        lambda ax: (
            ax.plot(
                equity.index, equity.equity / equity.equity.iloc[0], label="Strategy"
            ),
            ax.plot(
                benchmark.index,
                benchmark.equity / benchmark.equity.iloc[0],
                label="Benchmark",
            ),
            ax.legend(),
            ax.set_ylabel("Growth of 1"),
        ),
    )
    dd = drawdown_series(equity.equity) * 100
    figure(
        "Drawdown",
        lambda ax: (
            ax.plot(dd.index, dd, color="#b65d43"),
            ax.set_ylabel("% below peak"),
        ),
    )
    figure(
        "Underwater",
        lambda ax: (
            ax.fill_between(dd.index, dd, 0, color="#b65d43", alpha=0.5),
            ax.set_ylabel("% below peak"),
        ),
    )
    vol, sharpe = rolling_statistics(
        returns,
        analytics.rolling_window,
        analytics.trading_days,
        analytics.risk_free_rate,
    )

    def rolling(ax, values, ylabel):
        if values.notna().any():
            ax.plot(values.index, values)
        else:
            ax.text(
                0.5,
                0.5,
                f"Insufficient history for {analytics.rolling_window}-session window",
                ha="center",
                transform=ax.transAxes,
            )
        ax.set_ylabel(ylabel)

    figure("Rolling volatility", lambda ax: rolling(ax, vol * 100, "Annualized %"))
    figure("Rolling Sharpe", lambda ax: rolling(ax, sharpe, "Ratio"))

    def heatmap(ax):
        monthly = period_returns(returns, "ME")
        if monthly.empty:
            ax.text(
                0.5, 0.5, "No return intervals", ha="center", transform=ax.transAxes
            )
            return
        data = pd.DataFrame(
            {
                "year": monthly.index.year,
                "month": monthly.index.month,
                "return": monthly.to_numpy() * 100,
            }
        )
        grid = data.pivot(index="year", columns="month", values="return").reindex(
            columns=range(1, 13)
        )
        bound = max(1, float(np.nanmax(abs(grid.to_numpy()))))
        ax.imshow(
            grid.to_numpy(), aspect="auto", cmap="RdYlGn", vmin=-bound, vmax=bound
        )
        ax.set_xticks(
            range(12),
            [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
        )
        ax.set_yticks(range(len(grid)), grid.index)
        for i in range(len(grid)):
            for j in range(12):
                value = grid.iloc[i, j]
                if pd.notna(value):
                    ax.text(j, i, f"{value:.1f}%", ha="center", va="center", fontsize=8)
        ax.grid(False)

    figure("Monthly returns", heatmap)

    def yearly(ax):
        values = period_returns(returns, "YE") * 100
        ax.bar(
            values.index.year.astype(str),
            values,
            color=["#166c69" if v >= 0 else "#b65d43" for v in values],
        )
        ax.set_ylabel("Return % (partial years included)")

    figure("Yearly returns", yearly)
    figure(
        "Cash weight / invested exposure",
        lambda ax: (
            ax.plot(equity.index, equity.cash_weight * 100, label="Cash"),
            ax.plot(equity.index, equity.gross_exposure * 100, label="Invested"),
            ax.legend(),
            ax.set_ylabel("% equity"),
        ),
    )

    def costs(ax):
        daily = pd.DataFrame(
            0.0, index=equity.index, columns=["Commission", "Slippage"]
        )
        for _, fill in result.fills.iterrows():
            day = (
                pd.Timestamp(fill.timestamp)
                .tz_convert("America/New_York")
                .tz_localize(None)
                .normalize()
            )
            daily.loc[day] += [fill.commission, fill.slippage_cost]
        ax.plot(daily.index, daily.Commission.cumsum(), label="Commission")
        ax.plot(daily.index, daily.Slippage.cumsum(), label="Slippage")
        ax.legend()
        ax.set_ylabel("Cumulative USD")

    figure("Transaction costs over time", costs)
    return charts
