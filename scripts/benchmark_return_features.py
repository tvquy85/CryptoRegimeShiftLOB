from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from data.audit_schema import clean_book_frame
from features.lob_features import add_lob_features, add_return_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark nhẹ cho add_return_features.")
    parser.add_argument("--rows", type=int, default=200_000)
    parser.add_argument("--parquet", type=Path, default=None)
    args = parser.parse_args()
    frame = _load_frame(args.parquet, args.rows) if args.parquet else _synthetic_frame(args.rows)
    start = time.perf_counter()
    output = add_return_features(frame, event_horizons=(10, 50, 100), event_windows=(20, 100, 500))
    elapsed = time.perf_counter() - start
    print(
        f"rows={len(output)} cols={len(output.columns)} add_return_features_seconds={elapsed:.6f} "
        f"rows_per_second={len(output) / max(elapsed, 1.0e-9):.2f}"
    )


def _load_frame(path: Path, rows: int) -> pd.DataFrame:
    parquet = pq.ParquetFile(path)
    raw = parquet.read_row_group(0).to_pandas().iloc[:rows].copy()
    cleaned = clean_book_frame(raw)
    return add_lob_features(cleaned, eps=1.0e-9, depth_levels=(1, 3, 5, 10, 20))


def _synthetic_frame(rows: int) -> pd.DataFrame:
    x = np.arange(rows, dtype="float64")
    mid_price = 100.0 + 0.01 * x + np.sin(x / 17.0)
    return pd.DataFrame({"mid_price": mid_price})


if __name__ == "__main__":
    main()
