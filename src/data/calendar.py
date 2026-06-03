from __future__ import annotations

from pathlib import Path

import pandas as pd


MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def parse_month_token(path: str | Path) -> pd.Period | None:
    name = Path(path).name.upper()
    for token, month in MONTHS.items():
        if f"_{token}-" in name:
            year = int(name.split(f"_{token}-", maxsplit=1)[1].split(".", maxsplit=1)[0])
            return pd.Period(year=year, month=month, freq="M")
    return None


def overlaps(period: pd.Period | None, start: pd.Timestamp | None, end: pd.Timestamp | None) -> bool:
    if period is None:
        return True
    period_start = period.start_time.tz_localize("UTC")
    period_end = period.end_time.tz_localize("UTC")
    if start is not None and period_end < start:
        return False
    if end is not None and period_start > end:
        return False
    return True

