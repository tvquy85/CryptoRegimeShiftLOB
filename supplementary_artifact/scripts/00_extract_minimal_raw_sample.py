from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from artifact_lib import ROOT, path_in_root, validate_l2_schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a legally permitted minimal raw-format sample.")
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--output-dir", default="data/raw_sample/cryptolake_minimal")
    parser.add_argument("--source-type", choices=["provider_public_sample", "license_permitted_excerpt", "user_supplied_not_packaged"], required=True)
    parser.add_argument("--license-confirmed", action="store_true")
    parser.add_argument("--max-rows", type=int, default=20000)
    args = parser.parse_args()

    if not args.license_confirmed:
        raise SystemExit("[ERROR] Refusing to copy raw-format sample without --license-confirmed.")
    files = sorted(Path().glob(args.input_glob))
    if not files:
        raise SystemExit(f"[ERROR] No input files match {args.input_glob}")
    frames = []
    remaining = args.max_rows
    for p in files:
        df = pd.read_parquet(p)
        take = min(remaining, len(df))
        frames.append(df.head(take))
        remaining -= take
        if remaining <= 0:
            break
    out_df = pd.concat(frames, ignore_index=True)
    config = {"levels_per_side": 20, "paths": {"artifact_dir": "artifacts/raw_sample"}}
    validate_l2_schema(out_df, config, mode="raw-sample")
    out_dir = path_in_root(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "BOOK_BINANCE_MINIMAL_SAMPLE.parquet"
    out_df.to_parquet(out_path, index=False)
    meta = out_dir / "SOURCE.txt"
    meta.write_text(f"source_type={args.source_type}\nrows={len(out_df)}\nredistribution_confirmed_by_user=true\n", encoding="utf-8")
    print(f"[OK] raw-format minimal sample written: {out_path.relative_to(ROOT)} rows={len(out_df)}")

