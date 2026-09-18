"""Calendar-day drawdown durations; unrecovered episodes end at last observation."""


def drawdown_series(equity):
    return equity / equity.cummax() - 1


def drawdown_details(equity):
    if equity.empty:
        return {
            "max_drawdown": 0.0,
            "max_dd_duration_days": 0,
            "peak_date": None,
            "trough_date": None,
            "recovery_date": None,
            "duration_days": 0,
        }
    peak_date = equity.index[0]
    peak = float(equity.iloc[0])
    trough_date = peak_date
    depth = 0.0
    episodes = []
    active = False
    for dt, value in equity.items():
        if value >= peak:
            if active:
                episodes.append(
                    (depth, peak_date, trough_date, dt, (dt - peak_date).days)
                )
            peak = float(value)
            peak_date = dt
            trough_date = dt
            depth = 0.0
            active = False
        else:
            active = True
            dd = value / peak - 1
            if dd < depth:
                depth = dd
                trough_date = dt
    if active:
        episodes.append(
            (depth, peak_date, trough_date, None, (equity.index[-1] - peak_date).days)
        )
    if not episodes:
        return {
            "max_drawdown": 0.0,
            "max_dd_duration_days": 0,
            "peak_date": None,
            "trough_date": None,
            "recovery_date": None,
            "duration_days": 0,
        }
    deepest = min(episodes, key=lambda x: x[0])
    return {
        "max_drawdown": float(deepest[0]),
        "max_dd_duration_days": max(x[4] for x in episodes),
        "peak_date": deepest[1].date().isoformat(),
        "trough_date": deepest[2].date().isoformat(),
        "recovery_date": deepest[3].date().isoformat()
        if deepest[3] is not None
        else None,
        "duration_days": deepest[4],
    }
