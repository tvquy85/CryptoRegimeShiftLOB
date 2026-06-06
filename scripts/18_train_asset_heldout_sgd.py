from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from evaluation.classification_eval import classification_from_parquet
from models.tabular_baselines import predict_probabilities, train_streaming_sgd
from utils.config import load_config, project_root, resolve_path
from utils.io import write_run_metadata
from utils.logging import configure_logging
from utils.seed import set_global_seed


PREDICTION_COLUMNS = {"prob_down", "prob_flat", "prob_up", "pred_label"}


def main() -> None:
    parser = argparse.ArgumentParser("Train SGD asset-held-out tu source asset va evaluate target test.")
    parser.add_argument("--source-config", required=True)
    parser.add_argument("--target-config", required=True)
    parser.add_argument("--source-symbol", required=True)
    parser.add_argument("--target-symbol", required=True)
    parser.add_argument("--direction", choices=["btc_to_eth", "eth_to_btc"], required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", default="stage_3_full_scale")
    parser.add_argument("--batch-size", type=int, default=250_000)
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--model-label", default=None)
    args = parser.parse_args()

    source_config = load_config(args.source_config)
    target_config = load_config(args.target_config)
    set_global_seed(int(source_config.get("random_seed", 7)))
    logger = configure_logging(resolve_path(source_config, f"outputs/logs/{args.run_id}/asset_heldout.log"))

    source_path = resolve_model_input_path(source_config)
    target_path = resolve_model_input_path(target_config)
    features = available_tabular_features(source_config, source_path)
    if not features:
        raise RuntimeError("Khong tim thay feature tabular hop le trong source input.")

    logger.info("Train source=%s target=%s direction=%s.", args.source_symbol, args.target_symbol, args.direction)
    logger.info("Source input=%s; target input=%s; n_features=%s.", source_path, target_path, len(features))
    bundle = train_streaming_sgd(source_path, features, source_config, batch_size=args.batch_size)

    model_label = args.model_label or f"asset_{args.direction}_sgd"
    output_path = resolve_path(
        source_config,
        args.output_path or f"data/predictions/predictions_asset_{args.direction}_sgd.parquet",
    )
    target_rows = stream_target_test_predictions(target_path, output_path, bundle, batch_size=args.batch_size)
    overall, by_regime = classification_from_parquet(output_path, split="test")
    overall_row = {
        "direction": args.direction,
        "model": model_label,
        "source_symbol": args.source_symbol,
        "target_symbol": args.target_symbol,
        **overall,
        "n_rows": target_rows,
    }
    by_regime.insert(0, "target_symbol", args.target_symbol)
    by_regime.insert(0, "source_symbol", args.source_symbol)
    by_regime.insert(0, "model", model_label)
    by_regime.insert(0, "direction", args.direction)

    tables_dir = project_root(source_config) / "outputs" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    upsert_csv(
        tables_dir / "table_asset_heldout_forecasting_stage3.csv",
        pd.DataFrame([overall_row]),
        key_columns=["direction", "model"],
    )
    upsert_csv(
        tables_dir / "table_asset_heldout_forecasting_by_regime_stage3.csv",
        by_regime,
        key_columns=["direction", "model", "regime"],
    )

    checkpoint = resolve_path(source_config, f"{source_config.get('model_dir', 'outputs/checkpoints')}/{args.run_id}_sgd.joblib")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    bundle.save(str(checkpoint))
    write_run_metadata(
        source_config,
        args.run_id,
        args.stage,
        "18_train_asset_heldout_sgd.py",
        artifacts={
            "source_input": source_path,
            "target_input": target_path,
            "predictions": output_path,
            "checkpoint": checkpoint,
        },
        extra={
            "direction": args.direction,
            "model_label": model_label,
            "source_symbol": args.source_symbol,
            "target_symbol": args.target_symbol,
            "features": features,
            "target_test_rows": target_rows,
            "overall_target_test": overall,
        },
    )
    logger.info("Asset-held-out %s xong; target test rows=%s.", args.direction, target_rows)


def resolve_model_input_path(config: dict[str, object]) -> Path:
    for key in ("split_output", "prediction_output"):
        value = config.get(key)
        if not value:
            continue
        path = resolve_path(config, str(value))
        if path.exists():
            return path
    raise FileNotFoundError("Khong tim thay split_output hoac prediction_output ton tai cho config.")


def available_tabular_features(config: dict[str, object], input_path: Path) -> list[str]:
    requested = [str(column) for column in config.get("tabular_features", [])]
    available = set(pq.ParquetFile(input_path).schema_arrow.names)
    return [column for column in requested if column in available]


def stream_target_test_predictions(
    target_path: Path,
    output_path: Path,
    bundle,
    *,
    batch_size: int,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    parquet = pq.ParquetFile(target_path)
    try:
        for batch in parquet.iter_batches(batch_size=batch_size):
            frame = batch.to_pandas()
            if "split" not in frame.columns:
                raise RuntimeError("Target input thieu cot split.")
            test = frame[frame["split"] == "test"].copy()
            if test.empty:
                continue
            test = test.drop(columns=[column for column in PREDICTION_COLUMNS if column in test.columns], errors="ignore")
            probs = predict_probabilities(bundle, test)
            predicted = test.reset_index(drop=True).join(probs.reset_index(drop=True))
            table = pa.Table.from_pandas(predicted, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temp_path, table.schema, compression="snappy")
            elif table.schema != writer.schema:
                table = table.cast(writer.schema)
            writer.write_table(table)
            total_rows += int(len(predicted))
    finally:
        if writer is not None:
            writer.close()
    if total_rows == 0 or not temp_path.exists():
        raise RuntimeError("Khong sinh duoc target test prediction cho asset-held-out.")
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)
    return total_rows


def upsert_csv(path: Path, rows: pd.DataFrame, *, key_columns: list[str]) -> None:
    if path.exists():
        current = pd.read_csv(path)
        new_keys = set(map(tuple, rows[key_columns].astype(str).to_numpy()))
        keep_mask = ~current[key_columns].astype(str).apply(tuple, axis=1).isin(new_keys)
        current = current[keep_mask]
        output = pd.concat([current, rows], ignore_index=True)
    else:
        output = rows
    output.to_csv(path, index=False)


if __name__ == "__main__":
    main()
