"""Each session is an open event followed by a close event."""

from dataclasses import dataclass
import pandas as pd
from quantlab.data.calendar import schedule


@dataclass(frozen=True)
class Session:
    date: pd.Timestamp
    open: pd.Timestamp
    close: pd.Timestamp


class Clock:
    def __init__(self, start, end):
        self.schedule = schedule(start, end)

    def __iter__(self):
        for dt, row in self.schedule.iterrows():
            yield Session(dt, row["open"], row["close"])


def decision_due(date, previous, frequency):
    if frequency == "daily" or previous is None:
        return True
    if frequency == "weekly":
        return date.isocalendar()[:2] != previous.isocalendar()[:2]
    if frequency == "monthly":
        return (date.year, date.month) != (previous.year, previous.month)
    raise ValueError(f"Unsupported schedule: {frequency}")
