from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.dataset as ds

from data.audit_schema import book_columns, event_time
from data.calendar import overlaps, parse_month_token
from data.parquet_index import build_parquet_index, filter_index
from utils.io import stage_range


def discover_files(
    config: dict[str, object],
    stage: str,
    symbol: str | None = None,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    index = filter_index(
        build_parquet_index(config),
        exchange=str(config.get("exchange", "")) or None,
        symbol=symbol or _default_symbol(config),
    )
    stage_start, stage_end = stage_range(config, stage)
    start_ts = pd.Timestamp(start) if start else stage_start
    end_ts = pd.Timestamp(end) if end else stage_end
    keep = []
    for path in index["file_path"]:
        keep.append(overlaps(parse_month_token(path), start_ts, end_ts))
    return index.loc[keep].reset_index(drop=True)


def load_snapshots(
    config: dict[str, object],
    stage: str,
    symbol: str | None = None,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    columns: Iterable[str] | None = None,
    include_source_file: bool = False,
) -> pd.DataFrame:
    files = discover_files(config, stage, symbol=symbol, start=start, end=end)
    if files.empty:
        return pd.DataFrame(columns=list(columns or book_columns(int(config.get("levels", 20)))))

    stage_start, stage_end = stage_range(config, stage)
    start_ts = pd.Timestamp(start) if start else stage_start
    end_ts = pd.Timestamp(end) if end else stage_end
    requested_columns = list(columns or book_columns(int(config.get("levels", 20))))
    frames: list[pd.DataFrame] = []

    for row in files.itertuples(index=False):
        path = Path(row.file_path)
        dataset = ds.dataset(str(path), format="parquet")
        read_columns = [column for column in requested_columns if column in dataset.schema.names]
        filter_expr = None
        if "origin_time" in dataset.schema.names and (start_ts is not None or end_ts is not None):
            if start_ts is not None:
                filter_expr = ds.field("origin_time") >= start_ts.to_pydatetime()
            if end_ts is not None:
                upper = ds.field("origin_time") <= end_ts.to_pydatetime()
                filter_expr = upper if filter_expr is None else filter_expr & upper
        table = dataset.to_table(columns=read_columns, filter=filter_expr)
        frame = table.to_pandas()
        frame["event_time"] = event_time(frame)
        if start_ts is not None:
            frame = frame[frame["event_time"] >= start_ts]
        if end_ts is not None:
            frame = frame[frame["event_time"] <= end_ts]
        if include_source_file:
            frame["source_file"] = path.name
            frame["source_file_size_mb"] = float(row.file_size_mb)
        frames.append(frame.drop(columns=["event_time"], errors="ignore"))

    if not frames:
        return pd.DataFrame(columns=requested_columns)
    return pd.concat(frames, ignore_index=True)


def _default_symbol(config: dict[str, object]) -> str | None:
    symbols = config.get("symbols") or []
    return str(symbols[0]) if symbols else None
