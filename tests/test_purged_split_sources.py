from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def _load_purged_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "28_build_purged_split_sources.py"
    spec = importlib.util.spec_from_file_location("purged_split_sources", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_split_audit_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "23_build_split_audit.py"
    spec = importlib.util.spec_from_file_location("split_audit_module", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_purged_split_source_drops_boundary_rows_and_stale_predictions(tmp_path: Path) -> None:
    module = _load_purged_module()
    frame = pd.DataFrame(
        {
            "row_id": np.arange(20),
            "event_time": pd.date_range("2024-01-01", periods=20, freq="s", tz="UTC"),
            "label_horizon_events": np.full(20, 2, dtype=np.int16),
            "label": ["FLAT"] * 20,
            "regime": ["BALANCED_TRANSITION"] * 20,
            "prob_down": np.full(20, 0.1),
            "prob_flat": np.full(20, 0.8),
            "prob_up": np.full(20, 0.1),
            "pred_label": ["FLAT"] * 20,
        }
    )
    source = tmp_path / "source.parquet"
    output = tmp_path / "purged.parquet"
    frame.to_parquet(source, index=False)

    summary = module.build_purged_split_source(
        source,
        output,
        train_fraction=0.6,
        valid_fraction=0.2,
        purge_gap_events=2,
    )
    result = pd.read_parquet(output)

    assert summary["output_rows"] == 16
    assert result.loc[result["split"].eq("train"), "row_id"].tolist() == list(range(10))
    assert result.loc[result["split"].eq("valid"), "row_id"].tolist() == [12, 13]
    assert result.loc[result["split"].eq("test"), "row_id"].tolist() == [16, 17, 18, 19]
    assert {"prob_down", "prob_flat", "prob_up", "pred_label"}.isdisjoint(result.columns)
    assert pq.ParquetFile(output).metadata.num_rows == 16


def test_split_audit_purged_boundaries_pass() -> None:
    module = _load_split_audit_module()
    frame = pd.DataFrame(
        {
            "event_time": pd.date_range("2024-01-01", periods=16, freq="s", tz="UTC"),
            "split": ["train"] * 10 + ["valid"] * 2 + ["test"] * 4,
            "label_horizon_events": np.full(16, 2, dtype=np.int16),
        }
    )

    audit = module.audit_split_frame(
        frame,
        symbol="BTC-USDT",
        source_artifact="purged.parquet",
        explicit_purge_rows=2,
    )
    boundary = audit.loc[audit["split"].isin(["train", "valid"])]

    assert set(boundary["horizon_overlap_rows"]) == {0}
    assert set(boundary["status"]) == {"PASS"}


def test_safe_suffix_for_purged_output() -> None:
    module = _load_split_audit_module()

    assert module._safe_suffix("purged") == "_purged"
    assert module._safe_suffix("_P0-02B Purged_") == "_p0_02b_purged"
    assert module._safe_suffix("") == ""
