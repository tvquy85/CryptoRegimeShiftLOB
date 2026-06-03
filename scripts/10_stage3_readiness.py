from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data.crypto_lake_loader import discover_files
from utils.cli import as_common_args, common_parser
from utils.config import load_config, project_root, resolve_path
from utils.io import parquet_num_rows, stage_range, write_json, write_run_metadata
from utils.logging import configure_logging
from utils.partitioning import stage_partitions


STAGE2_ARTIFACTS = {
    "predictions": "data/predictions/predictions.parquet",
    "regimes": "data/regimes/regimes.parquet",
    "splits": "data/splits/splits.parquet",
}


def main() -> None:
    parser = common_parser("Kiem tra san sang Stage 3 full-year.")
    args = as_common_args(parser.parse_args())
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/stage3_readiness.log"))
    symbol = args.symbol or str((config.get("symbols") or ["BTC-USDT"])[0])

    stage2_files = discover_files(config, "stage_2_medium_scale", symbol=symbol)
    stage3_files = discover_files(config, "stage_3_full_scale", symbol=symbol)
    stage2_raw_bytes = int(stage2_files["file_size_mb"].sum() * 1024 * 1024) if not stage2_files.empty else 0
    stage3_raw_bytes = int(stage3_files["file_size_mb"].sum() * 1024 * 1024) if not stage3_files.empty else 0
    raw_ratio = stage3_raw_bytes / max(stage2_raw_bytes, 1)

    split_path = root / STAGE2_ARTIFACTS["splits"]
    stage2_rows = parquet_num_rows(split_path) if split_path.exists() else 0
    stage3_audit_table = root / "outputs" / "tables" / "table_data_audit_stage_3_full_scale.csv"
    actual_stage3_audit_rows = _audit_row_count(stage3_audit_table)
    estimated_stage3_rows = actual_stage3_audit_rows or (int(stage2_rows * raw_ratio) if stage2_rows else 0)
    row_ratio = estimated_stage3_rows / max(stage2_rows, 1)

    artifact_rows = []
    current_stage2_bytes = 0
    estimated_stage3_bytes = 0
    for name, relative in STAGE2_ARTIFACTS.items():
        path = root / relative
        size = int(path.stat().st_size) if path.exists() else 0
        estimated = int(size * row_ratio) if size else 0
        current_stage2_bytes += size
        estimated_stage3_bytes += estimated
        artifact_rows.append(
            {
                "artifact": name,
                "stage2_path": relative,
                "stage2_bytes": size,
                "estimated_stage3_bytes": estimated,
            }
        )

    free_bytes = int(shutil.disk_usage(root).free)
    # Lower bound because feature/label intermediates and temp parquet merges are not present after Stage 2 cleanup.
    lower_bound_required = int(estimated_stage3_bytes * 1.25)
    ready = free_bytes > lower_bound_required and len(stage_partitions(config, "stage_3_full_scale")) > 0
    partitions = stage_partitions(config, "stage_3_full_scale")
    start, end = stage_range(config, "stage_3_full_scale")

    summary = {
        "symbol": symbol,
        "stage3_start": str(start),
        "stage3_end": str(end),
        "stage3_raw_files": int(len(stage3_files)),
        "stage2_raw_bytes": stage2_raw_bytes,
        "stage3_raw_bytes": stage3_raw_bytes,
        "raw_size_ratio_stage3_over_stage2": raw_ratio,
        "stage2_rows": int(stage2_rows),
        "estimated_stage3_rows": estimated_stage3_rows,
        "actual_stage3_audit_rows": int(actual_stage3_audit_rows),
        "current_stage2_artifact_bytes": current_stage2_bytes,
        "estimated_stage3_core_artifact_bytes": estimated_stage3_bytes,
        "lower_bound_required_free_bytes": lower_bound_required,
        "current_free_bytes": free_bytes,
        "stage3_partition_count": int(len(partitions)),
        "stage3_partition_days": config.get("stage_partition_day_windows", {}).get("stage_3_full_scale"),
        "ready_for_stage3_feature_build": bool(ready),
    }

    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(tables / "table_stage3_readiness.csv", index=False)
    pd.DataFrame(artifact_rows).to_csv(tables / "table_stage3_artifact_size_estimates.csv", index=False)
    write_json(summary, resolve_path(config, "data/reports/stage3_readiness_summary.json"))
    audit_path = resolve_path(config, "audits/audit_stage3_readiness_v001.md")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(_audit_markdown(summary, artifact_rows), encoding="utf-8")
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "10_stage3_readiness.py",
        artifacts={
            "readiness_table": tables / "table_stage3_readiness.csv",
            "artifact_size_estimates": tables / "table_stage3_artifact_size_estimates.csv",
            "readiness_summary": resolve_path(config, "data/reports/stage3_readiness_summary.json"),
            "audit": audit_path,
        },
        extra=summary,
    )
    logger.info("Stage 3 readiness: ready=%s, free_gb=%.2f, lower_bound_gb=%.2f.", ready, free_bytes / 1e9, lower_bound_required / 1e9)


def _audit_markdown(summary: dict[str, object], artifact_rows: list[dict[str, object]]) -> str:
    ready_text = "PASS" if summary["ready_for_stage3_feature_build"] else "FAIL"
    audit_done = int(summary.get("actual_stage3_audit_rows", 0)) > 0
    rows = "\n".join(
        f"- `{row['artifact']}`: stage2 `{_gb(row['stage2_bytes']):.2f} GB`, ước lượng stage3 `{_gb(row['estimated_stage3_bytes']):.2f} GB`"
        for row in artifact_rows
    )
    recommendation = (
        "Có thể mở Stage 3 feature build theo partition 10 ngày."
        if summary["ready_for_stage3_feature_build"]
        else "Chưa nên mở Stage 3 feature build. Cần giải phóng hoặc chuyển bớt artifact lớn trước khi build full-year."
    )
    post_disk_step = (
        "Sau khi đủ dung lượng: build features Stage 3 theo partition 10 ngày."
        if audit_done
        else "Sau khi đủ dung lượng: chạy `00_audit_data.py` full-year, rồi mới build features Stage 3 theo partition 10 ngày."
    )
    return f"""# Audit Stage 3 Readiness v001

## Tóm tắt

- Symbol: `{summary['symbol']}`
- Khoảng thời gian Stage 3: `{summary['stage3_start']}` đến `{summary['stage3_end']}`
- Số raw file Stage 3: `{summary['stage3_raw_files']}`
- Số partition Stage 3: `{summary['stage3_partition_count']}` partition, mỗi partition `{summary['stage3_partition_days']}` ngày
- Gate dung lượng: **{ready_text}**

## Ước lượng quy mô

- Stage 2 rows: `{summary['stage2_rows']:,}`
- Stage 3 rows ước lượng: `{summary['estimated_stage3_rows']:,}`
- Stage 3 audit rows thực tế: `{summary['actual_stage3_audit_rows']:,}`
- Raw size ratio Stage 3 / Stage 2: `{summary['raw_size_ratio_stage3_over_stage2']:.2f}`
- Free disk hiện tại: `{_gb(summary['current_free_bytes']):.2f} GB`
- Lower-bound dung lượng cần cho core artifacts: `{_gb(summary['lower_bound_required_free_bytes']):.2f} GB`

## Artifact size estimates

{rows}

## Kết luận

{recommendation}

Ghi chú: lower-bound trên chưa tính đủ feature/label intermediates và temp parquet merge. Vì vậy nếu gate FAIL ở lower-bound thì Stage 3 full-year chắc chắn rủi ro; nếu gate PASS thì vẫn cần theo dõi disk sau từng bước.

## Bước tiếp theo

- Nếu chưa đủ dung lượng: snapshot các bảng/audit quan trọng, sau đó xóa hoặc di chuyển `predictions.parquet`, `regimes.parquet`, `splits.parquet` và regime parts Stage 2 khi không còn cần rerun trực tiếp.
- {post_disk_step}
- Không mở XGBoost/TCN Stage 3 trước khi feature/regime/split full-year pass.
"""


def _gb(value: object) -> float:
    return float(value) / 1024**3


def _audit_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        table = pd.read_csv(path, usecols=["n_rows"])
    except Exception:
        return 0
    return int(table["n_rows"].sum())


if __name__ == "__main__":
    main()
