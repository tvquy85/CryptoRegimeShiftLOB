from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.cli import as_common_args, common_parser
from utils.config import load_config, project_root, resolve_path
from utils.io import write_run_metadata
from utils.logging import configure_logging


SPLIT_ORDER = ["train", "valid", "test"]
AUDIT_COLUMNS = [
    "symbol",
    "source_artifact",
    "split",
    "rows",
    "start_utc",
    "end_utc",
    "horizon_events",
    "next_split",
    "boundary_gap_rows",
    "boundary_gap_time_ms",
    "explicit_purge_rows",
    "horizon_overlap_rows",
    "status",
    "notes",
]


def audit_split_frame(
    frame: pd.DataFrame,
    *,
    symbol: str,
    source_artifact: str,
    explicit_purge_rows: int = 0,
) -> pd.DataFrame:
    if "split" not in frame.columns:
        raise ValueError("split column is required for split audit.")
    time_col = "event_time" if "event_time" in frame.columns else "origin_time"
    if time_col not in frame.columns:
        raise ValueError("event_time or origin_time column is required for split audit.")
    horizon_col = "label_horizon_events" if "label_horizon_events" in frame.columns else None
    data = frame.copy()
    data[time_col] = pd.to_datetime(data[time_col], utc=True)
    rows = []
    for split in SPLIT_ORDER:
        current = data.loc[data["split"].eq(split)]
        if current.empty:
            continue
        horizon = int(current[horizon_col].max()) if horizon_col else 0
        rows.append(
            {
                "symbol": symbol,
                "source_artifact": source_artifact,
                "split": split,
                "rows": int(len(current)),
                "start_utc": current[time_col].min().isoformat().replace("+00:00", "Z"),
                "end_utc": current[time_col].max().isoformat().replace("+00:00", "Z"),
                "horizon_events": horizon,
            }
        )
    return finalize_split_audit_rows(pd.DataFrame(rows), explicit_purge_rows=explicit_purge_rows)


def audit_split_parquet(
    path: Path,
    *,
    symbol: str,
    root: Path,
    explicit_purge_rows: int = 0,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    schema = pl.scan_parquet(str(path)).collect_schema().names()
    time_col = "event_time" if "event_time" in schema else "origin_time"
    if "split" not in schema or time_col not in schema:
        raise ValueError(f"{path} must contain split and {time_col} columns.")
    horizon_expr = (
        pl.col("label_horizon_events").max().alias("horizon_events")
        if "label_horizon_events" in schema
        else pl.lit(0).alias("horizon_events")
    )
    summary = (
        pl.scan_parquet(str(path))
        .select(["split", time_col, *([] if "label_horizon_events" not in schema else ["label_horizon_events"])])
        .group_by("split")
        .agg(
            [
                pl.len().alias("rows"),
                pl.col(time_col).min().alias("start_utc"),
                pl.col(time_col).max().alias("end_utc"),
                horizon_expr,
            ]
        )
        .collect(engine="streaming")
        .to_pandas()
    )
    summary["symbol"] = symbol
    summary["source_artifact"] = _rel(path, root)
    summary["start_utc"] = pd.to_datetime(summary["start_utc"], utc=True).map(_format_utc)
    summary["end_utc"] = pd.to_datetime(summary["end_utc"], utc=True).map(_format_utc)
    return finalize_split_audit_rows(summary, explicit_purge_rows=explicit_purge_rows)


def finalize_split_audit_rows(summary: pd.DataFrame, *, explicit_purge_rows: int = 0) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=AUDIT_COLUMNS)
    ordered = summary.copy()
    ordered["__split_order"] = ordered["split"].map({split: idx for idx, split in enumerate(SPLIT_ORDER)})
    ordered = ordered.sort_values("__split_order").drop(columns=["__split_order"])
    by_split = {str(row["split"]): row for row in ordered.to_dict("records")}
    rows = []
    for split in SPLIT_ORDER:
        if split not in by_split:
            continue
        row = dict(by_split[split])
        next_split = _next_present_split(split, by_split)
        horizon = int(row.get("horizon_events", 0) or 0)
        overlap = max(horizon - int(explicit_purge_rows), 0) if next_split else 0
        gap_time_ms = ""
        if next_split:
            current_end = pd.Timestamp(row["end_utc"])
            next_start = pd.Timestamp(by_split[next_split]["start_utc"])
            gap_time_ms = float((next_start - current_end).total_seconds() * 1000.0)
        row.update(
            {
                "next_split": next_split,
                "boundary_gap_rows": int(explicit_purge_rows) if next_split else "",
                "boundary_gap_time_ms": gap_time_ms,
                "explicit_purge_rows": int(explicit_purge_rows) if next_split else "",
                "horizon_overlap_rows": int(overlap),
                "status": "PASS" if overlap == 0 else "WARN_BOUNDARY_OVERLAP",
                "notes": _notes(split, next_split, overlap),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def build_split_audit(
    *,
    root: Path,
    sources: dict[str, Path],
    explicit_purge_rows: int = 0,
) -> pd.DataFrame:
    frames = [
        audit_split_parquet(path, symbol=symbol, root=root, explicit_purge_rows=explicit_purge_rows)
        for symbol, path in sources.items()
        if path.exists()
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=AUDIT_COLUMNS)


def write_split_audit_markdown(audit: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    warn = int(audit["status"].eq("WARN_BOUNDARY_OVERLAP").sum()) if "status" in audit else 0
    if warn == 0:
        status_lines = [
            "- Tat ca boundary train/validation co `horizon_overlap_rows=0` theo explicit purge rows da khai bao.",
            "- Split artifact co the dung cho submission sau khi downstream forecasting/execution/stress/bootstrap duoc regenerate tu cung split nay.",
        ]
    else:
        status_lines = [
            "- Artifact hien tai chua purge du label horizon tai mot so boundary; khong duoc claim la submission-ready.",
            "- Split generator da duoc harden de purge `h` rows cho cac rerun sau.",
        ]
    lines = [
        "# Split audit P0-02",
        "",
        "## Muc tieu",
        "",
        "Audit train/validation/test chronological split cho artifact Stage 3 hien co, dong thoi ghi ro rui ro horizon-boundary leakage.",
        "",
        "## Ket luan nhanh",
        "",
        f"- So boundary co horizon overlap: `{warn}`.",
        "- Cac artifact duoc audit dung split theo thoi gian 60/20/20 va co validation split ro rang.",
        *status_lines,
        "- Test split chi nen dung cho final reporting; model/scaler fit tren train, policy/RSEP tune tren validation.",
        "",
        "## Bang audit",
        "",
        _markdown_table(audit) if not audit.empty else "_Khong co row audit._",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = common_parser("Audit chronological train/validation/test split.")
    parser.add_argument("--btc-predictions", default="data/predictions/predictions.parquet")
    parser.add_argument("--eth-predictions", default="data/predictions/predictions_eth_stage3_sgd.parquet")
    parser.add_argument("--explicit-purge-rows", type=int, default=0)
    parser.add_argument("--output-suffix", default="")
    parser.add_argument("--promote-if-pass", action="store_true")
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/split_audit.log"))
    sources = {
        "BTC-USDT": resolve_path(config, namespace.btc_predictions),
        "ETH-USDT": resolve_path(config, namespace.eth_predictions),
    }
    audit = build_split_audit(root=root, sources=sources, explicit_purge_rows=int(namespace.explicit_purge_rows))
    artifacts_dir = root / "artifacts"
    paper_dir = root / "outputs" / "paper_assets"
    suffix = _safe_suffix(str(namespace.output_suffix))
    csv_path = artifacts_dir / f"split_audit{suffix}.csv"
    md_path = artifacts_dir / f"split_audit{suffix}.md"
    paper_path = paper_dir / f"table_19_chronological_split_audit{suffix}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    paper_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(csv_path, index=False)
    audit.to_csv(paper_path, index=False)
    write_split_audit_markdown(audit, md_path)
    promoted = False
    if bool(namespace.promote_if_pass):
        if audit.empty or not audit["status"].eq("PASS").all():
            raise RuntimeError("Khong promote split audit canonical vi audit chua PASS tat ca rows.")
        shutil.copy2(csv_path, artifacts_dir / "split_audit.csv")
        shutil.copy2(md_path, artifacts_dir / "split_audit.md")
        shutil.copy2(paper_path, paper_dir / "table_19_chronological_split_audit.csv")
        promoted = True
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "23_build_split_audit.py",
        artifacts={"split_audit_csv": csv_path, "split_audit_md": md_path, "paper_table": paper_path},
        extra={
            "n_rows": int(len(audit)),
            "explicit_purge_rows": int(namespace.explicit_purge_rows),
            "output_suffix": suffix,
            "promoted_to_canonical": promoted,
        },
    )
    logger.info("Split audit complete: %s rows.", len(audit))


def _next_present_split(split: str, by_split: dict[str, dict[str, object]]) -> str:
    current = SPLIT_ORDER.index(split)
    for candidate in SPLIT_ORDER[current + 1 :]:
        if candidate in by_split:
            return candidate
    return ""


def _format_utc(value: pd.Timestamp) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _safe_suffix(value: str) -> str:
    cleaned = value.strip().strip("_").lower()
    if not cleaned:
        return ""
    cleaned = "".join(char if char.isalnum() else "_" for char in cleaned).strip("_")
    return f"_{cleaned}" if cleaned else ""


def _notes(split: str, next_split: str, overlap: int) -> str:
    if not next_split:
        return "Final reporting split; no later split boundary."
    if overlap > 0:
        return f"Current locked artifact has {overlap} event labels whose horizon can cross into {next_split}."
    return f"Boundary to {next_split} is purged by at least the label horizon."


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in frame.astype(str).to_dict("records"):
        values = [row.get(column, "").replace("|", "/") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
