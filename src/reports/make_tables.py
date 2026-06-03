from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_dataset_stats(audit_path: Path, output_path: Path) -> Path:
    audit = pd.read_parquet(audit_path) if audit_path.exists() else pd.DataFrame()
    if audit.empty:
        table = pd.DataFrame()
    else:
        table = pd.DataFrame(
            [
                {
                    "rows": int(audit["n_rows"].sum()),
                    "days": int(audit["trade_date"].nunique()),
                    "median_snapshot_interval_ms": float(audit["p50_snapshot_interval_ms"].median()),
                    "mean_spread": float(audit["spread_mean"].mean()),
                    "mean_depth_top10": float(audit["depth_top10_mean"].mean()),
                }
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)
    return output_path


def copy_or_empty_csv(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        pd.read_csv(source).to_csv(target, index=False)
    else:
        pd.DataFrame().to_csv(target, index=False)
    return target

