from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from data.calendar import parse_month_token
from utils.config import resolve_path


FILE_RE = re.compile(
    r"BOOK_(?P<exchange>[A-Z0-9]+)_(?P<symbol>[A-Z0-9\-]+)_(?P<month>[A-Z]{3})-(?P<year>\d{4})\.parquet$"
)


def build_parquet_index(config: dict[str, object]) -> pd.DataFrame:
    raw_root = resolve_path(config, str(config["raw_data_root"]))
    records: list[dict[str, object]] = []
    for path in sorted(raw_root.glob("BOOK_*_*.parquet")):
        match = FILE_RE.match(path.name)
        if not match:
            continue
        stat = path.stat()
        period = parse_month_token(path)
        records.append(
            {
                "file_path": str(path.resolve()),
                "file_name": path.name,
                "exchange": match.group("exchange"),
                "symbol": match.group("symbol"),
                "month": match.group("month"),
                "year": int(match.group("year")),
                "period": str(period) if period is not None else None,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 4),
            }
        )
    return pd.DataFrame.from_records(records)


def filter_index(
    index: pd.DataFrame,
    exchange: str | None = None,
    symbol: str | None = None,
) -> pd.DataFrame:
    current = index.copy()
    if exchange:
        current = current[current["exchange"] == exchange]
    if symbol:
        current = current[current["symbol"] == symbol]
    return current.reset_index(drop=True)

