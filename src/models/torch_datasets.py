from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


LABEL_ORDER = ["DOWN", "FLAT", "UP"]
LABEL_TO_ID = {label: idx for idx, label in enumerate(LABEL_ORDER)}
ID_TO_LABEL = {idx: label for label, idx in LABEL_TO_ID.items()}


@dataclass
class WindowedTensorBatch:
    x: np.ndarray
    y: np.ndarray


@dataclass(frozen=True)
class TemporalFeatureScaler:
    mean: np.ndarray
    std: np.ndarray


@dataclass
class TemporalWindowBatch:
    x: np.ndarray
    y: np.ndarray
    metadata: pd.DataFrame


DEFAULT_TEMPORAL_METADATA_COLUMNS = [
    "origin_time",
    "received_time",
    "sequence_number",
    "symbol",
    "exchange",
    "event_time",
    "mid_price",
    "spread",
    "rel_spread",
    "future_ret_h",
    "cost_threshold_t",
    "label_horizon_events",
    "label_fee_bps",
    "label",
    "regime",
    "split",
]


def build_windowed_tensor(frame: pd.DataFrame, feature_columns: list[str], label_column: str = "label_id", window: int = 100) -> WindowedTensorBatch:
    if len(frame) < window:
        return WindowedTensorBatch(
            x=np.empty((0, window, len(feature_columns)), dtype=np.float32),
            y=np.empty((0,), dtype=np.int64),
        )
    values = frame[feature_columns].to_numpy(dtype=np.float32)
    labels = frame[label_column].to_numpy(dtype=np.int64)
    xs = []
    ys = []
    for end in range(window - 1, len(frame)):
        xs.append(values[end - window + 1 : end + 1])
        ys.append(labels[end])
    return WindowedTensorBatch(x=np.stack(xs), y=np.asarray(ys, dtype=np.int64))


def lob_required_columns(levels: int = 10) -> list[str]:
    columns = ["mid_price", "label", "split", "symbol", "origin_time"]
    for level in range(levels):
        columns.extend([f"ask_{level}_price", f"ask_{level}_size", f"bid_{level}_price", f"bid_{level}_size"])
    return columns


def lob_feature_names(levels: int = 10) -> list[str]:
    names = []
    for level in range(levels):
        names.extend(
            [
                f"ask_{level}_price_rel",
                f"ask_{level}_size_log",
                f"bid_{level}_price_rel",
                f"bid_{level}_size_log",
            ]
        )
    return names


def transform_lob_frame(frame: pd.DataFrame, *, levels: int = 10, scaler: TemporalFeatureScaler | None = None) -> np.ndarray:
    _require_columns(frame, lob_required_columns(levels))
    mid = frame["mid_price"].to_numpy(dtype=np.float32, copy=False)
    mid = np.where(np.abs(mid) > 1e-12, mid, np.nan).astype(np.float32)
    features = []
    for level in range(levels):
        ask_price = frame[f"ask_{level}_price"].to_numpy(dtype=np.float32, copy=False)
        ask_size = frame[f"ask_{level}_size"].to_numpy(dtype=np.float32, copy=False)
        bid_price = frame[f"bid_{level}_price"].to_numpy(dtype=np.float32, copy=False)
        bid_size = frame[f"bid_{level}_size"].to_numpy(dtype=np.float32, copy=False)
        features.extend(
            [
                (ask_price - mid) / mid,
                np.log1p(np.maximum(ask_size, 0.0)),
                (bid_price - mid) / mid,
                np.log1p(np.maximum(bid_size, 0.0)),
            ]
        )
    values = np.column_stack(features).astype(np.float32)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    if scaler is not None:
        values = ((values - scaler.mean) / scaler.std).astype(np.float32)
        values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    return values


def fit_lob_feature_scaler(
    parquet_path: str | Path,
    *,
    split: str = "train",
    levels: int = 10,
    max_rows: int | None = 1_000_000,
    source_batch_rows: int = 250_000,
) -> TemporalFeatureScaler:
    columns = _available_columns(parquet_path, lob_required_columns(levels))
    count = 0
    running_sum = np.zeros(levels * 4, dtype=np.float64)
    running_sumsq = np.zeros(levels * 4, dtype=np.float64)
    parquet = pq.ParquetFile(parquet_path)
    row_groups = _row_groups_matching_split(parquet, split)
    for batch in parquet.iter_batches(batch_size=source_batch_rows, columns=columns, row_groups=row_groups):
        frame = batch.to_pandas()
        frame = frame[frame["split"] == split]
        if frame.empty:
            continue
        if max_rows is not None:
            remaining = max_rows - count
            if remaining <= 0:
                break
            frame = frame.head(remaining)
        values = transform_lob_frame(frame, levels=levels)
        running_sum += values.sum(axis=0, dtype=np.float64)
        running_sumsq += np.square(values, dtype=np.float64).sum(axis=0)
        count += int(len(values))
        if max_rows is not None and count >= max_rows:
            break
    if count == 0:
        raise RuntimeError(f"Không fit được temporal scaler vì split={split} rỗng.")
    mean = running_sum / count
    variance = np.maximum(running_sumsq / count - mean * mean, 1e-12)
    std = np.sqrt(variance)
    return TemporalFeatureScaler(mean=mean.astype(np.float32), std=std.astype(np.float32))


def build_temporal_windows_from_frame(
    frame: pd.DataFrame,
    *,
    levels: int = 10,
    window: int = 100,
    stride: int = 1,
    scaler: TemporalFeatureScaler | None = None,
    metadata_columns: Iterable[str] | None = DEFAULT_TEMPORAL_METADATA_COLUMNS,
) -> TemporalWindowBatch:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    metadata_rows: list[dict[str, object]] = []
    for _, group in _iter_temporal_groups(frame):
        _append_group_windows(
            group,
            xs,
            ys,
            metadata_rows,
            levels=levels,
            window=window,
            stride=stride,
            scaler=scaler,
            metadata_columns=metadata_columns,
            require_new_targets=False,
        )
    return _make_temporal_batch(xs, ys, metadata_rows, window=window, n_features=levels * 4)


def iter_temporal_window_batches(
    parquet_path: str | Path,
    *,
    split: str,
    levels: int = 10,
    window: int = 100,
    stride: int = 1,
    scaler: TemporalFeatureScaler | None = None,
    source_batch_rows: int = 250_000,
    output_batch_windows: int = 1024,
    max_windows: int | None = None,
    metadata_columns: Iterable[str] | None = DEFAULT_TEMPORAL_METADATA_COLUMNS,
) -> Iterable[TemporalWindowBatch]:
    required = lob_required_columns(levels)
    requested_columns = list(dict.fromkeys([*required, *(metadata_columns or [])]))
    columns = _available_columns(parquet_path, requested_columns)
    parquet = pq.ParquetFile(parquet_path)
    carry = pd.DataFrame()
    xs: list[np.ndarray] = []
    ys: list[int] = []
    metadata_rows: list[dict[str, object]] = []
    emitted = 0

    row_groups = _row_groups_matching_split(parquet, split)
    for batch in parquet.iter_batches(batch_size=source_batch_rows, columns=columns, row_groups=row_groups):
        frame = batch.to_pandas()
        frame = frame[frame["split"] == split].copy()
        if frame.empty and carry.empty:
            continue
        frame["__is_new_target"] = True
        if carry.empty:
            combined = frame
        else:
            carry = carry.copy()
            carry["__is_new_target"] = False
            combined = pd.concat([carry, frame], ignore_index=True)
        if combined.empty:
            continue

        last_group = pd.DataFrame()
        for _, group in _iter_temporal_groups(combined):
            last_group = group
            before = len(xs)
            _append_group_windows(
                group,
                xs,
                ys,
                metadata_rows,
                levels=levels,
                window=window,
                stride=stride,
                scaler=scaler,
                metadata_columns=metadata_columns,
                require_new_targets=True,
            )
            while len(xs) >= output_batch_windows:
                take = min(output_batch_windows, len(xs))
                if max_windows is not None:
                    remaining = max_windows - emitted
                    if remaining <= 0:
                        return
                    take = min(take, remaining)
                batch_out = _make_temporal_batch(xs[:take], ys[:take], metadata_rows[:take], window=window, n_features=levels * 4)
                xs = xs[take:]
                ys = ys[take:]
                metadata_rows = metadata_rows[take:]
                emitted += int(len(batch_out.y))
                yield batch_out
                if max_windows is not None and emitted >= max_windows:
                    return
            if max_windows is not None and emitted + len(xs) >= max_windows:
                remaining = max_windows - emitted
                if remaining > 0:
                    yield _make_temporal_batch(xs[:remaining], ys[:remaining], metadata_rows[:remaining], window=window, n_features=levels * 4)
                return
            if len(xs) == before:
                continue

        carry = last_group.tail(max(window - 1, 0)).drop(columns=["__group_date"], errors="ignore").copy()

    if xs:
        if max_windows is not None:
            remaining = max_windows - emitted
            if remaining <= 0:
                return
            xs = xs[:remaining]
            ys = ys[:remaining]
            metadata_rows = metadata_rows[:remaining]
        yield _make_temporal_batch(xs, ys, metadata_rows, window=window, n_features=levels * 4)


def _append_group_windows(
    group: pd.DataFrame,
    xs: list[np.ndarray],
    ys: list[int],
    metadata_rows: list[dict[str, object]],
    *,
    levels: int,
    window: int,
    stride: int,
    scaler: TemporalFeatureScaler | None,
    metadata_columns: Iterable[str] | None,
    require_new_targets: bool,
) -> None:
    if len(group) < window:
        return
    values = transform_lob_frame(group, levels=levels, scaler=scaler)
    labels = group["label"].map(LABEL_TO_ID).to_numpy()
    is_new = group["__is_new_target"].to_numpy(dtype=bool) if "__is_new_target" in group.columns else np.ones(len(group), dtype=bool)
    existing_metadata = [column for column in (metadata_columns or []) if column in group.columns]
    for end in range(window - 1, len(group), max(stride, 1)):
        if require_new_targets and not bool(is_new[end]):
            continue
        label_id = labels[end]
        if pd.isna(label_id):
            continue
        xs.append(values[end - window + 1 : end + 1].copy())
        ys.append(int(label_id))
        row = group.iloc[end]
        metadata = {column: row[column] for column in existing_metadata}
        metadata["window_end_index"] = int(row.name) if isinstance(row.name, (int, np.integer)) else int(end)
        metadata_rows.append(metadata)


def _iter_temporal_groups(frame: pd.DataFrame):
    if frame.empty:
        return
    grouped = frame.copy()
    time_col = "origin_time" if "origin_time" in grouped.columns else "event_time"
    grouped["__group_date"] = pd.to_datetime(grouped[time_col], errors="coerce").dt.date.astype("string").fillna("unknown")
    group_columns = [column for column in ["split", "symbol", "__group_date"] if column in grouped.columns]
    yield from grouped.groupby(group_columns, sort=False, dropna=False, observed=False)


def _make_temporal_batch(
    xs: list[np.ndarray],
    ys: list[int],
    metadata_rows: list[dict[str, object]],
    *,
    window: int,
    n_features: int,
) -> TemporalWindowBatch:
    if not xs:
        return TemporalWindowBatch(
            x=np.empty((0, window, n_features), dtype=np.float32),
            y=np.empty((0,), dtype=np.int64),
            metadata=pd.DataFrame(metadata_rows),
        )
    return TemporalWindowBatch(
        x=np.stack(xs).astype(np.float32),
        y=np.asarray(ys, dtype=np.int64),
        metadata=pd.DataFrame(metadata_rows),
    )


def _available_columns(parquet_path: str | Path, requested: list[str]) -> list[str]:
    schema_columns = set(pq.ParquetFile(parquet_path).schema_arrow.names)
    missing = [column for column in lob_required_columns(10) if column in requested and column not in schema_columns]
    if missing:
        raise KeyError(f"Thiếu cột bắt buộc cho temporal LOB: {missing}")
    return [column for column in requested if column in schema_columns]


def _row_groups_matching_split(parquet: pq.ParquetFile, split: str) -> list[int] | None:
    try:
        split_idx = parquet.schema_arrow.names.index("split")
    except ValueError:
        return None
    selected: list[int] = []
    for row_group_idx in range(parquet.metadata.num_row_groups):
        column = parquet.metadata.row_group(row_group_idx).column(split_idx)
        stats = column.statistics
        if stats is None or not stats.has_min_max:
            return None
        min_value = _decode_stat_value(stats.min)
        max_value = _decode_stat_value(stats.max)
        if min_value == max_value:
            if min_value == split:
                selected.append(row_group_idx)
        else:
            selected.append(row_group_idx)
    return selected


def _decode_stat_value(value: object) -> object:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Thiếu cột bắt buộc cho temporal LOB: {missing}")
