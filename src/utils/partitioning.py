from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data.calendar import MONTHS
from utils.io import stage_range


@dataclass(frozen=True)
class StagePartition:
    token: str
    start: pd.Timestamp
    end: pd.Timestamp


def partitioned_stage_enabled(
    config: dict[str, object],
    stage: str,
    *,
    start: str | None = None,
    end: str | None = None,
) -> bool:
    if start or end:
        return False
    stage_months = config.get("stage_partition_months", {})
    stage_windows = config.get("stage_partition_windows", {})
    stage_day_windows = config.get("stage_partition_day_windows", {})
    return bool(
        config.get("partitioned_stage_feature_build", False)
        and (stage in stage_months or stage in stage_windows or stage in stage_day_windows)
    )


def stage_partitions(config: dict[str, object], stage: str) -> list[StagePartition]:
    partition_tokens = list(config.get("stage_partition_months", {}).get(stage, []))
    explicit_windows = list(config.get("stage_partition_windows", {}).get(stage, []))
    day_window_size = config.get("stage_partition_day_windows", {}).get(stage)
    stage_start, stage_end = stage_range(config, stage)
    if (not partition_tokens and not explicit_windows and not day_window_size) or stage_start is None or stage_end is None:
        return []
    partitions: list[StagePartition] = []
    for token in partition_tokens:
        month = MONTHS[str(token).upper()]
        month_start = pd.Timestamp(year=stage_start.year, month=month, day=1, tz="UTC")
        month_end = month_start + pd.offsets.MonthBegin(1) - pd.Timedelta(seconds=1)
        partitions.append(
            StagePartition(
                token=str(token).upper(),
                start=max(month_start, stage_start),
                end=min(month_end, stage_end),
            )
        )
    for window in explicit_windows:
        token = str(window["token"]).upper()
        window_start = pd.Timestamp(window["start"])
        window_end = pd.Timestamp(window["end"])
        if window_start.tzinfo is None:
            window_start = window_start.tz_localize("UTC")
        else:
            window_start = window_start.tz_convert("UTC")
        if window_end.tzinfo is None:
            window_end = window_end.tz_localize("UTC")
        else:
            window_end = window_end.tz_convert("UTC")
        partitions.append(
            StagePartition(
                token=token,
                start=max(window_start, stage_start),
                end=min(window_end, stage_end),
            )
        )
    if day_window_size:
        days = int(day_window_size)
        if days <= 0:
            raise ValueError("stage_partition_day_windows phải là số ngày dương.")
        current = stage_start
        index = 1
        while current <= stage_end:
            window_end = min(current + pd.Timedelta(days=days) - pd.Timedelta(seconds=1), stage_end)
            token = f"D{index:03d}_{current.strftime('%Y%m%d')}_{window_end.strftime('%Y%m%d')}"
            partitions.append(StagePartition(token=token, start=current, end=window_end))
            current = window_end + pd.Timedelta(seconds=1)
            index += 1
    return sorted(partitions, key=lambda partition: partition.start)
