from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from .config import project_root, resolve_path
from .gpu import gpu_summary


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_frame(frame: pd.DataFrame, path: Path) -> Path:
    ensure_parent(path)
    frame.to_parquet(path, index=False)
    return path


def read_frame(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def read_filtered_frame(
    path: Path,
    *,
    filters: list[tuple[str, str, object]] | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    lazy = pl.scan_parquet(str(path))
    if columns:
        lazy = lazy.select(columns)
    for column, operator, value in filters or []:
        if operator == "==":
            lazy = lazy.filter(pl.col(column) == value)
        elif operator == "!=":
            lazy = lazy.filter(pl.col(column) != value)
        elif operator == "<":
            lazy = lazy.filter(pl.col(column) < value)
        elif operator == "<=":
            lazy = lazy.filter(pl.col(column) <= value)
        elif operator == ">":
            lazy = lazy.filter(pl.col(column) > value)
        elif operator == ">=":
            lazy = lazy.filter(pl.col(column) >= value)
        elif operator == "in":
            lazy = lazy.filter(pl.col(column).is_in(value))
        else:
            raise ValueError(f"Unsupported parquet filter operator: {operator}")
    return lazy.collect(engine="streaming").to_pandas()


def parquet_num_rows(path: Path) -> int:
    return int(pq.ParquetFile(path).metadata.num_rows)


def merge_parquet_parts(part_paths: list[Path], output_path: Path, batch_size: int = 250_000) -> tuple[Path, int]:
    if not part_paths:
        raise ValueError("Không có parquet part nào để merge.")
    ensure_parent(output_path)
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    try:
        for part_path in part_paths:
            parquet = pq.ParquetFile(part_path)
            for batch in parquet.iter_batches(batch_size=batch_size):
                table = pa.Table.from_batches([batch])
                if writer is None:
                    writer = pq.ParquetWriter(temp_path, table.schema, compression="snappy")
                elif table.schema != writer.schema:
                    table = table.cast(writer.schema)
                writer.write_table(table)
                total_rows += int(table.num_rows)
    finally:
        if writer is not None:
            writer.close()
    if not temp_path.exists():
        raise RuntimeError("Merge parquet không sinh được file tạm.")
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)
    return output_path, total_rows


def write_json(payload: dict[str, Any], path: Path) -> Path:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
    return path


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def git_commit(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip() or None if completed.returncode == 0 else None
    except OSError:
        return None


def stage_range(config: dict[str, Any], stage: str) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    ranges = config.get("stage_ranges", {})
    current = ranges.get(stage, {})
    start = pd.Timestamp(current["start"]) if current.get("start") else None
    end = pd.Timestamp(current["end"]) if current.get("end") else None
    return start, end


def run_dir(config: dict[str, Any], run_id: str) -> Path:
    root = project_root(config)
    path = root / "outputs" / "logs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_run_metadata(
    config: dict[str, Any],
    run_id: str,
    stage: str,
    script_name: str,
    artifacts: dict[str, str | Path] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    root = project_root(config)
    output = run_dir(config, run_id) / "metadata.json"
    start, end = stage_range(config, stage)
    payload = {
        "run_id": run_id,
        "stage": stage,
        "script_name": script_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(root),
        "config_path": config.get("_config_path"),
        "data_date_range": {"start": start, "end": end},
        "gpu": gpu_summary(),
        "artifacts": {key: str(value) for key, value in (artifacts or {}).items()},
    }
    if extra:
        payload["extra"] = extra
    return write_json(payload, output)


def artifact_path(config: dict[str, Any], key: str) -> Path:
    value = config[key]
    return resolve_path(config, value)
