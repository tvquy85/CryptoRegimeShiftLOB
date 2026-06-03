from __future__ import annotations

import json
from typing import Iterable

import numpy as np
import pandas as pd


META_COLUMNS = ["origin_time", "received_time", "sequence_number", "symbol", "exchange"]


def price_columns(side: str, levels: int = 20) -> list[str]:
    return [f"{side}_{level}_price" for level in range(levels)]


def size_columns(side: str, levels: int = 20) -> list[str]:
    return [f"{side}_{level}_size" for level in range(levels)]


def book_columns(levels: int = 20) -> list[str]:
    return META_COLUMNS + price_columns("bid", levels) + size_columns("bid", levels) + price_columns("ask", levels) + size_columns("ask", levels)


def validate_schema(columns: Iterable[str], levels: int = 20) -> dict[str, object]:
    column_set = set(columns)
    expected = set(book_columns(levels))
    missing = sorted(expected - column_set)
    extra = sorted(column_set - expected)
    return {"ok": not missing, "missing": missing, "extra": extra}


def event_time(frame: pd.DataFrame) -> pd.Series:
    origin = pd.to_datetime(frame.get("origin_time"), utc=True, errors="coerce")
    received = pd.to_datetime(frame.get("received_time"), utc=True, errors="coerce")
    return origin.where(origin.notna(), received)


def clean_book_frame(frame: pd.DataFrame, drop_crossed: bool = True) -> pd.DataFrame:
    if frame.empty:
        cleaned = frame.copy()
        cleaned["event_time"] = pd.Series(dtype="datetime64[ns, UTC]")
        return cleaned

    cleaned = frame.copy()
    cleaned["event_time"] = event_time(cleaned)
    for column in cleaned.columns:
        if column.endswith("_price") or column.endswith("_size"):
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype("float32")

    valid = (
        cleaned["event_time"].notna()
        & cleaned["bid_0_price"].gt(0)
        & cleaned["ask_0_price"].gt(0)
        & cleaned["bid_0_size"].gt(0)
        & cleaned["ask_0_size"].gt(0)
    )
    if drop_crossed:
        valid &= cleaned["bid_0_price"].le(cleaned["ask_0_price"])

    cleaned = cleaned.loc[valid].copy()
    cleaned["sequence_number"] = pd.to_numeric(cleaned["sequence_number"], errors="coerce").fillna(-1).astype("int64")
    cleaned = cleaned.sort_values(["event_time", "sequence_number"], kind="mergesort").reset_index(drop=True)
    return cleaned


def audit_daily(frame: pd.DataFrame, file_size_mb: float | None = None) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    raw = frame.copy()
    raw["event_time"] = event_time(raw)
    raw["trade_date"] = raw["event_time"].dt.date.astype(str)
    raw["spread"] = pd.to_numeric(raw["ask_0_price"], errors="coerce") - pd.to_numeric(raw["bid_0_price"], errors="coerce")
    raw["depth_top10"] = sum(pd.to_numeric(raw[f"bid_{i}_size"], errors="coerce").fillna(0) for i in range(10))
    raw["depth_top10"] += sum(pd.to_numeric(raw[f"ask_{i}_size"], errors="coerce").fillna(0) for i in range(10))

    records: list[dict[str, object]] = []
    for trade_date, group in raw.groupby("trade_date", dropna=False):
        ordered = group.sort_values(["event_time", "sequence_number"], kind="mergesort")
        interval_ms = ordered["event_time"].diff().dt.total_seconds().mul(1000)
        seq_diff = ordered["sequence_number"].diff()
        missing = {column: int(group[column].isna().sum()) for column in group.columns if group[column].isna().any()}
        record = {
            "trade_date": trade_date,
            "exchange": _first_text(group, "exchange"),
            "symbol": _first_text(group, "symbol"),
            "n_rows": int(len(group)),
            "first_timestamp": ordered["event_time"].min(),
            "last_timestamp": ordered["event_time"].max(),
            "duration_seconds": float((ordered["event_time"].max() - ordered["event_time"].min()).total_seconds()),
            "mean_snapshot_interval_ms": float(interval_ms.mean(skipna=True) or 0.0),
            "p50_snapshot_interval_ms": float(interval_ms.quantile(0.50) or 0.0),
            "p95_snapshot_interval_ms": float(interval_ms.quantile(0.95) or 0.0),
            "p99_snapshot_interval_ms": float(interval_ms.quantile(0.99) or 0.0),
            "n_duplicate_timestamps": int(group["event_time"].duplicated().sum()),
            "n_duplicate_sequence_numbers": int(group["sequence_number"].duplicated().sum()),
            "n_non_monotonic_sequence": int((seq_diff < 0).sum()),
            "n_missing_values_by_column": json.dumps(missing, ensure_ascii=False, sort_keys=True),
            "n_crossed_book_rows": int((pd.to_numeric(group["bid_0_price"], errors="coerce") > pd.to_numeric(group["ask_0_price"], errors="coerce")).sum()),
            "n_zero_or_negative_price_rows": int(_any_non_positive(group, "_price").sum()),
            "n_zero_or_negative_size_rows": int(_any_non_positive(group, "_size").sum()),
            "spread_mean": float(group["spread"].mean(skipna=True) or 0.0),
            "spread_p50": float(group["spread"].quantile(0.50) or 0.0),
            "spread_p95": float(group["spread"].quantile(0.95) or 0.0),
            "depth_top10_mean": float(group["depth_top10"].mean(skipna=True) or 0.0),
            "depth_top10_p50": float(group["depth_top10"].quantile(0.50) or 0.0),
            "depth_top10_p95": float(group["depth_top10"].quantile(0.95) or 0.0),
            "file_size_mb": float(file_size_mb or 0.0),
        }
        records.append(record)
    return pd.DataFrame.from_records(records)


def _first_text(group: pd.DataFrame, column: str) -> str | None:
    if column not in group.columns or group[column].dropna().empty:
        return None
    return str(group[column].dropna().iloc[0])


def _any_non_positive(group: pd.DataFrame, suffix: str) -> pd.Series:
    cols = [column for column in group.columns if column.endswith(suffix)]
    if not cols:
        return pd.Series(False, index=group.index)
    numeric = group[cols].apply(pd.to_numeric, errors="coerce")
    return numeric.le(0).any(axis=1)

