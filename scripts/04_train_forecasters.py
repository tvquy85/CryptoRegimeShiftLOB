from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from evaluation.classification_eval import classification_by_regime, classification_from_parquet, classification_summary
from models.tabular_baselines import predict_probabilities, train_streaming_sgd, train_tabular_model
from utils.artifacts import artifact_namespace, model_stage_table_path, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import read_filtered_frame, read_frame, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.partitioning import partitioned_stage_enabled
from utils.seed import set_global_seed


def main() -> None:
    parser = common_parser("Huan luyen forecasting baseline tabular.")
    parser.add_argument("--model", choices=["sgd", "xgboost"], default=None)
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    set_global_seed(int(config.get("random_seed", 7)))
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/train.log"))
    split_path = resolve_path(config, str(config["split_output"]))
    requested_features = [str(column) for column in config.get("tabular_features", [])]
    available_columns = set(pq.ParquetFile(split_path).schema_arrow.names)
    features = [column for column in requested_features if column in available_columns]
    if not features:
        raise RuntimeError("Khong tim thay feature tabular nao trong split manifest.")

    partition_mode = partitioned_stage_enabled(config, args.stage, start=args.start, end=args.end)
    model_name = namespace.model or str(config.get("model_name", "sgd"))
    training_mode = "in_memory"

    if partition_mode and model_name == "sgd":
        bundle = train_streaming_sgd(split_path, features, config)
        training_mode = "streaming_sgd"
    else:
        if partition_mode:
            train = read_filtered_frame(
                split_path,
                filters=[("split", "==", "train")],
                columns=[*features, "label", "split"],
            )
            valid = read_filtered_frame(
                split_path,
                filters=[("split", "==", "valid")],
                columns=[*features, "label", "split"],
            )
        else:
            split = read_frame(split_path)
            train = split[split["split"] == "train"].copy()
            valid = split[split["split"] == "valid"].copy()
        if train.empty or valid.empty:
            raise RuntimeError("Train/valid split rong.")
        bundle = train_tabular_model(train, valid, features, model_name, config)

    pred_path = resolve_path(config, str(config["prediction_output"]))
    if partition_mode:
        n_prediction_rows = _stream_predictions(split_path, pred_path, bundle)
        overall, by_regime = classification_from_parquet(pred_path)
        test_rows = int(sum(row["n_rows"] for row in by_regime.to_dict("records")))
    else:
        probs = predict_probabilities(bundle, split)
        predictions = split.reset_index(drop=True).join(probs.reset_index(drop=True))
        write_frame(predictions, pred_path)
        test_eval = predictions[predictions["split"] == "test"][["label", "pred_label", "regime"]].copy()
        n_prediction_rows = int(len(predictions))
        overall = classification_summary(test_eval)
        by_regime = classification_by_regime(test_eval)
        test_rows = int(len(test_eval))
    checkpoint = resolve_path(config, f"{config['model_dir']}/{args.run_id}_{bundle.model_name}.joblib")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    bundle.save(str(checkpoint))

    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    namespace = artifact_namespace(config)
    model_label = str(config.get("model_label", bundle.model_name))
    overall_table = pd.DataFrame([{"model": model_label, **overall, "n_rows": test_rows}])
    by_regime.insert(0, "model", model_label)
    if not namespace:
        overall_table.to_csv(tables / "table_forecasting_overall.csv", index=False)
        by_regime.to_csv(tables / "table_forecasting_by_regime.csv", index=False)
    if args.stage == "stage_2_medium_scale":
        by_regime.to_csv(tables / "table_forecasting_by_regime_stage2.csv", index=False)
        if bundle.model_name.startswith("xgboost"):
            pd.DataFrame([{"model": model_label, **overall, "n_rows": test_rows}]).to_csv(
                tables / "table_forecasting_overall_xgboost_stage2.csv",
                index=False,
            )
            by_regime.to_csv(tables / "table_forecasting_by_regime_xgboost_stage2.csv", index=False)
    if namespace or args.stage == "stage_3_full_scale":
        overall_table.to_csv(stage_table_path(tables, "table_forecasting_overall", args.stage, namespace=namespace), index=False)
        by_regime.to_csv(stage_table_path(tables, "table_forecasting_by_regime", args.stage, namespace=namespace), index=False)
        overall_table.to_csv(model_stage_table_path(tables, "table_forecasting_overall", args.stage, model_label, namespace=namespace), index=False)
        by_regime.to_csv(model_stage_table_path(tables, "table_forecasting_by_regime", args.stage, model_label, namespace=namespace), index=False)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "04_train_forecasters.py",
        artifacts={"predictions": pred_path, "checkpoint": checkpoint},
        extra={
            "model": bundle.model_name,
            "model_label": model_label,
            "features": features,
            "overall_test": overall,
            "partition_mode": partition_mode,
            "training_mode": training_mode,
            "n_prediction_rows": n_prediction_rows,
        },
    )
    logger.info("Huan luyen %s xong; test rows=%s.", bundle.model_name, test_rows)


def _stream_predictions(
    split_path: Path,
    pred_path: Path,
    bundle,
    *,
    batch_size: int = 250_000,
) -> int:
    pred_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = pred_path.with_suffix(pred_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    parquet = pq.ParquetFile(split_path)
    try:
        for batch in parquet.iter_batches(batch_size=batch_size):
            frame = batch.to_pandas()
            probs = predict_probabilities(bundle, frame)
            predicted = frame.reset_index(drop=True).join(probs.reset_index(drop=True))
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
    if not temp_path.exists():
        raise RuntimeError("Streaming predictions khong sinh duoc parquet.")
    if pred_path.exists():
        pred_path.unlink()
    temp_path.replace(pred_path)
    return total_rows


if __name__ == "__main__":
    main()
