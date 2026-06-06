from __future__ import annotations

import shutil
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.cli import as_common_args, common_parser
from utils.config import load_config, project_root, resolve_path
from utils.io import parquet_num_rows, write_run_metadata
from utils.logging import configure_logging


PREDICTION_COLUMNS = ("prob_down", "prob_flat", "prob_up", "pred_label")
DEFAULT_SOURCES = {
    "BTC-USDT": ("data/predictions/predictions.parquet", "data/splits/splits_btc_stage3_purged.parquet"),
    "ETH-USDT": ("data/splits/splits_eth_stage3.parquet", "data/splits/splits_eth_stage3_purged.parquet"),
}


def main() -> None:
    parser = common_parser("Build h-row purged chronological split sources from locked Stage 3 artifacts.")
    parser.add_argument("--btc-input", default=DEFAULT_SOURCES["BTC-USDT"][0])
    parser.add_argument("--btc-output", default=DEFAULT_SOURCES["BTC-USDT"][1])
    parser.add_argument("--eth-input", default=DEFAULT_SOURCES["ETH-USDT"][0])
    parser.add_argument("--eth-output", default=DEFAULT_SOURCES["ETH-USDT"][1])
    parser.add_argument("--train-fraction", type=float, default=0.6)
    parser.add_argument("--valid-fraction", type=float, default=0.2)
    parser.add_argument("--purge-gap-events", type=int, default=50)
    parser.add_argument("--min-free-gb", type=float, default=120.0)
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/purged_split_sources.log"))

    free_gb = shutil.disk_usage(root.anchor).free / (1024**3)
    if free_gb < float(namespace.min_free_gb):
        raise RuntimeError(f"Free disk {free_gb:.2f} GB < required {namespace.min_free_gb:.2f} GB.")

    outputs = {}
    summaries = {}
    for symbol, input_value, output_value in [
        ("BTC-USDT", namespace.btc_input, namespace.btc_output),
        ("ETH-USDT", namespace.eth_input, namespace.eth_output),
    ]:
        input_path = resolve_path(config, str(input_value))
        output_path = resolve_path(config, str(output_value))
        summary = build_purged_split_source(
            input_path,
            output_path,
            train_fraction=float(namespace.train_fraction),
            valid_fraction=float(namespace.valid_fraction),
            purge_gap_events=int(namespace.purge_gap_events),
        )
        outputs[f"{symbol}_purged_split_source"] = output_path
        summaries[symbol] = summary
        logger.info("Built purged source %s: %s.", symbol, summary)

    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "28_build_purged_split_sources.py",
        artifacts=outputs,
        extra={
            "train_fraction": float(namespace.train_fraction),
            "valid_fraction": float(namespace.valid_fraction),
            "purge_gap_events": int(namespace.purge_gap_events),
            "summaries": summaries,
        },
    )


def build_purged_split_source(
    input_path: Path,
    output_path: Path,
    *,
    train_fraction: float,
    valid_fraction: float,
    purge_gap_events: int,
) -> dict[str, int | str | list[str]]:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if not (0.0 < train_fraction < 1.0) or not (0.0 <= valid_fraction < 1.0):
        raise ValueError("train_fraction/valid_fraction khong hop le.")
    if train_fraction + valid_fraction >= 1.0:
        raise ValueError("train_fraction + valid_fraction phai nho hon 1.")
    if purge_gap_events < 0:
        raise ValueError("purge_gap_events phai khong am.")

    total_rows = parquet_num_rows(input_path)
    train_end = int(total_rows * train_fraction)
    valid_end = int(total_rows * (train_fraction + valid_fraction))
    train_label_end = max(train_end - purge_gap_events, 0)
    valid_label_end = max(valid_end - purge_gap_events, train_end)

    schema_names = pl.scan_parquet(str(input_path)).collect_schema().names()
    stale_prediction_columns = [column for column in PREDICTION_COLUMNS if column in schema_names]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    (
        pl.scan_parquet(str(input_path))
        .with_row_index("__row_index")
        .with_columns(
            pl.when(pl.col("__row_index") < train_label_end)
            .then(pl.lit("train"))
            .when((pl.col("__row_index") >= train_end) & (pl.col("__row_index") < valid_label_end))
            .then(pl.lit("valid"))
            .when(pl.col("__row_index") >= valid_end)
            .then(pl.lit("test"))
            .otherwise(pl.lit("__purge__"))
            .alias("split")
        )
        .filter(pl.col("split") != "__purge__")
        .drop(["__row_index", *stale_prediction_columns])
        .sink_parquet(str(temp_path), compression="snappy")
    )
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)

    rows_after = parquet_num_rows(output_path)
    expected_rows = train_label_end + max(valid_label_end - train_end, 0) + max(total_rows - valid_end, 0)
    if rows_after != expected_rows:
        raise RuntimeError(f"Purged row count mismatch: {rows_after} != {expected_rows}")
    output_schema = set(pl.scan_parquet(str(output_path)).collect_schema().names())
    leaked = sorted(column for column in PREDICTION_COLUMNS if column in output_schema)
    if leaked:
        raise RuntimeError(f"Output con stale prediction columns: {leaked}")

    return {
        "input": str(input_path),
        "output": str(output_path),
        "input_rows": int(total_rows),
        "output_rows": int(rows_after),
        "train_rows": int(train_label_end),
        "valid_rows": int(max(valid_label_end - train_end, 0)),
        "test_rows": int(max(total_rows - valid_end, 0)),
        "dropped_train_boundary_rows": int(max(train_end - train_label_end, 0)),
        "dropped_valid_boundary_rows": int(max(valid_end - valid_label_end, 0)),
        "dropped_prediction_columns": stale_prediction_columns,
    }


if __name__ == "__main__":
    main()
