import math


def tradability(bar):
    if bar is None:
        return "missing execution bar"
    price = float(bar["open"])
    if not math.isfinite(price) or price <= 0:
        return "invalid execution price"
    volume = float(bar["volume"])
    if not math.isfinite(volume) or volume <= 0:
        return "non-positive execution volume"
    return ""


def affordable_quantity(requested, cash, price, commission):
    lo, hi = 0, requested
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid * price + commission.calculate(mid, price) <= cash:
            lo = mid
        else:
            hi = mid - 1
    return lo
