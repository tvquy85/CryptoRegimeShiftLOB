from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.partitioning import partitioned_stage_enabled, stage_partitions


def test_day_window_partitions_cover_stage_range_without_overlap() -> None:
    config = {
        "partitioned_stage_feature_build": True,
        "stage_partition_day_windows": {"stage_3_full_scale": 10},
        "stage_ranges": {
            "stage_3_full_scale": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-31T23:59:59Z",
            }
        },
    }
    partitions = stage_partitions(config, "stage_3_full_scale")
    assert partitioned_stage_enabled(config, "stage_3_full_scale")
    assert [partition.token for partition in partitions] == [
        "D001_20240101_20240110",
        "D002_20240111_20240120",
        "D003_20240121_20240130",
        "D004_20240131_20240131",
    ]
    assert partitions[0].start.isoformat() == "2024-01-01T00:00:00+00:00"
    assert partitions[-1].end.isoformat() == "2024-01-31T23:59:59+00:00"
    for left, right in zip(partitions, partitions[1:]):
        assert left.end < right.start
