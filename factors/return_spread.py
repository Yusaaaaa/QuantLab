"""User-approved return-spread factor; pure historical arithmetic, no trading.

Daily = asset daily close-to-close return minus benchmark daily return.
Weekly = latest completed week's last close / preceding week's last close - 1,
computed separately for asset and benchmark and then subtracted.
All input is obtained from the caller's truncated MarketDataView. The weekly
function is called only at the final session close of a calendar week; exchange
calendar metadata in the strategy establishes this condition. No beta adjustment,
normalization, thresholds, position sizing, data download, or portfolio mutation.
"""


def daily_return_spread(data, symbol, benchmark):
    asset = data.history(symbol, bars=2)
    market = data.history(benchmark, bars=2)
    return calculate_spread(asset, market, data.as_of)


def weekly_return_spread(data, symbol, benchmark):
    asset = data.history(symbol)
    market = data.history(benchmark)
    # ISO calendar weeks respect holiday-shortened trading weeks and year boundaries.
    asset = (
        asset.assign(week=asset.date.dt.strftime("%G-%V"))
        .groupby("week", sort=False)
        .tail(1)
        .tail(2)
    )
    market = (
        market.assign(week=market.date.dt.strftime("%G-%V"))
        .groupby("week", sort=False)
        .tail(1)
        .tail(2)
    )
    if len(asset) == 2:
        # Do not silently compare across a completely absent week.
        if (asset.date.iloc[-1] - asset.date.iloc[-2]).days > 10:
            raise ValueError("Missing weekly endpoint")
    return calculate_spread(asset, market, data.as_of)


def calculate_spread(asset, market, as_of):
    if len(asset) < 2 or len(market) < 2:
        return None
    if asset.date.tolist() != market.date.tolist() or asset.date.iloc[-1] != as_of:
        raise ValueError("Factor requires synchronized, current close endpoints")
    if (asset.close <= 0).any() or (market.close <= 0).any():
        raise ValueError("Non-positive factor price")
    a = float(asset.close.iloc[-1] / asset.close.iloc[-2] - 1)
    b = float(market.close.iloc[-1] / market.close.iloc[-2] - 1)
    return {
        "start_date": str(asset.date.iloc[-2].date()),
        "end_date": str(asset.date.iloc[-1].date()),
        "asset_return": a,
        "benchmark_return": b,
        "spread": a - b,
    }
