from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import polars as pl

from regimes.regime_splits import asset_held_out_manifest, chronological_split
from utils.artifacts import artifact_namespace, namespaced_name
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import parquet_num_rows, read_frame, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.partitioning import partitioned_stage_enabled


def main() -> None:
    parser = common_parser("Sinh split manifests.")
    args = as_common_args(parser.parse_args())
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/splits.log"))
    split_cfg = config.get("split", {})
    namespace = artifact_namespace(config)
    partition_mode = partitioned_stage_enabled(config, args.stage, start=args.start, end=args.end)
    regime_path = resolve_path(config, str(config["regime_output"]))
    split_path = resolve_path(config, str(config["split_output"]))
    train_fraction = float(split_cfg.get("train_fraction", 0.6))
    valid_fraction = float(split_cfg.get("valid_fraction", 0.2))
    if partition_mode:
        total_rows = parquet_num_rows(regime_path)
        train_end = int(total_rows * train_fraction)
        valid_end = int(total_rows * (train_fraction + valid_fraction))
        (
            pl.scan_parquet(str(regime_path))
            .with_row_index("__row_index")
            .with_columns(
                pl.when(pl.col("__row_index") < train_end)
                .then(pl.lit("train"))
                .when(pl.col("__row_index") < valid_end)
                .then(pl.lit("valid"))
                .otherwise(pl.lit("test"))
                .alias("split")
            )
            .drop("__row_index")
            .sink_parquet(str(split_path))
        )
        split_counts = {"train": train_end, "valid": valid_end - train_end, "test": total_rows - valid_end}
    else:
        regimes = read_frame(regime_path)
        split = chronological_split(
            regimes,
            train_fraction=train_fraction,
            valid_fraction=valid_fraction,
        )
        write_frame(split, split_path)
        split_counts = split["split"].value_counts().to_dict()
    asset_manifest = asset_held_out_manifest([str(symbol) for symbol in config.get("symbols", [])])
    asset_manifest_path = resolve_path(config, f"data/splits/{namespaced_name('asset_held_out_manifest', namespace, suffix='.parquet')}")
    write_frame(asset_manifest, asset_manifest_path)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "03_make_splits.py",
        artifacts={"split_manifest": split_path, "asset_manifest": asset_manifest_path},
        extra={"split_counts": split_counts, "partition_mode": partition_mode},
    )
    logger.info("Split hoàn tất: %s.", split_counts)


if __name__ == "__main__":
    main()
