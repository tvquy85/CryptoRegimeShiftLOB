from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.classification_eval import classification_from_parquet
from models.tabular_baselines import predict_probabilities, train_tabular_model
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import write_run_metadata
from utils.logging import configure_logging
from utils.seed import set_global_seed


PROBABILITY_COLUMNS = ["prob_down", "prob_flat", "prob_up", "pred_label"]


def main() -> None:
    parser = common_parser("Train XGBoost GPU Stage 3 từ predictions parquet đã có.")
    parser.add_argument("--model-label", default=None)
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    set_global_seed(int(config.get("random_seed", 7)))
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/train_xgboost_gpu.log"))

    source_path = resolve_path(config, str(config.get("prediction_source", config["prediction_output"])))
    output_path = resolve_path(config, str(config["prediction_output"]))
    if source_path.resolve() == output_path.resolve():
        raise RuntimeError("prediction_source và prediction_output phải khác nhau để không overwrite baseline hiện có.")
    if not source_path.exists():
        raise FileNotFoundError(f"Không tìm thấy prediction source: {source_path}")

    model_label = namespace.model_label or str(config.get("model_label", "xgboost_gpu_stage3"))
    requested_features = [str(column) for column in config.get("tabular_features", [])]
    available_columns = set(pq.ParquetFile(source_path).schema_arrow.names)
    features = [column for column in requested_features if column in available_columns]
    if not features:
        raise RuntimeError("Không tìm thấy feature tabular nào trong prediction source.")

    stage_cfg = config.get("xgboost_stage3", {})
    train_sample_rows = int(stage_cfg.get("train_sample_rows", 5_000_000))
    valid_sample_rows = int(stage_cfg.get("valid_sample_rows", 1_000_000))
    prediction_batch_size = int(stage_cfg.get("prediction_batch_size", 250_000))
    sample_columns = [*features, "label", "split"]
    train, train_total_rows = read_split_sample(source_path, "train", sample_columns, max_rows=train_sample_rows)
    valid, valid_total_rows = read_split_sample(source_path, "valid", sample_columns, max_rows=valid_sample_rows)
    if train.empty or valid.empty:
        raise RuntimeError("Train/valid sample rỗng, không thể train XGBoost.")

    logger.info(
        "Train XGBoost source=%s train_sample=%s/%s valid_sample=%s/%s.",
        source_path,
        len(train),
        train_total_rows,
        len(valid),
        valid_total_rows,
    )
    bundle = train_tabular_model(train, valid, features, "xgboost", config)
    checkpoint = resolve_path(config, f"{config['model_dir']}/{args.run_id}_{bundle.model_name}.joblib")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    bundle.save(str(checkpoint))

    n_prediction_rows = stream_predictions_from_source(
        source_path,
        output_path,
        bundle,
        batch_size=prediction_batch_size,
        logger=logger,
    )
    overall, by_regime = classification_from_parquet(output_path)
    test_rows = int(by_regime["n_rows"].sum()) if not by_regime.empty else 0
    overall_row = {"model": model_label, "model_backend": bundle.model_name, **overall, "n_rows": test_rows}
    by_regime.insert(0, "model", model_label)
    by_regime.insert(1, "model_backend", bundle.model_name)

    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([overall_row]).to_csv(tables / "table_forecasting_overall_stage3_xgboost_gpu.csv", index=False)
    by_regime.to_csv(tables / "table_forecasting_by_regime_stage3_xgboost_gpu.csv", index=False)

    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "11_train_xgboost_gpu_from_predictions.py",
        artifacts={
            "source_predictions": source_path,
            "xgboost_predictions": output_path,
            "checkpoint": checkpoint,
            "forecasting_overall": tables / "table_forecasting_overall_stage3_xgboost_gpu.csv",
            "forecasting_by_regime": tables / "table_forecasting_by_regime_stage3_xgboost_gpu.csv",
        },
        extra={
            "model_label": model_label,
            "model_backend": bundle.model_name,
            "features": features,
            "train_sample_rows": int(len(train)),
            "train_total_rows": train_total_rows,
            "valid_sample_rows": int(len(valid)),
            "valid_total_rows": valid_total_rows,
            "n_prediction_rows": n_prediction_rows,
            "test_rows": test_rows,
            "overall_test": overall,
        },
    )
    logger.info("XGBoost Stage 3.6 xong; backend=%s test_rows=%s.", bundle.model_name, test_rows)


def read_split_sample(path: Path, split: str, columns: list[str], *, max_rows: int) -> tuple[pd.DataFrame, int]:
    lazy = pl.scan_parquet(str(path)).filter(pl.col("split") == split).select(columns)
    n_rows = int(lazy.select(pl.len()).collect(engine="streaming").item())
    if max_rows > 0 and n_rows > max_rows:
        step = int(math.ceil(n_rows / max_rows))
        lazy = lazy.with_row_index("__sample_index").filter((pl.col("__sample_index") % step) == 0).drop("__sample_index")
    return lazy.collect(engine="streaming").to_pandas(), n_rows


def stream_predictions_from_source(source_path: Path, output_path: Path, bundle, *, batch_size: int, logger: Any | None = None) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    _set_xgboost_prediction_device_cpu(bundle)
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    parquet = pq.ParquetFile(source_path)
    try:
        for batch_idx, batch in enumerate(parquet.iter_batches(batch_size=batch_size), start=1):
            frame = batch.to_pandas()
            base = frame.drop(columns=[column for column in PROBABILITY_COLUMNS if column in frame.columns])
            probs = predict_probabilities(bundle, frame)
            predicted = base.reset_index(drop=True).join(probs.reset_index(drop=True))
            table = pa.Table.from_pandas(predicted, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temp_path, table.schema, compression="snappy")
            elif table.schema != writer.schema:
                table = table.cast(writer.schema)
            writer.write_table(table)
            total_rows += int(len(predicted))
            if logger is not None and (batch_idx == 1 or batch_idx % 25 == 0):
                logger.info("Stream XGBoost predictions batch=%s rows=%s.", batch_idx, total_rows)
    finally:
        if writer is not None:
            writer.close()
    if not temp_path.exists():
        raise RuntimeError("Streaming XGBoost predictions không sinh được parquet.")
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)
    return total_rows


def _set_xgboost_prediction_device_cpu(bundle) -> None:
    model = getattr(getattr(bundle, "pipeline", None), "named_steps", {}).get("model")
    if model is not None and hasattr(model, "set_params"):
        try:
            model.set_params(device="cpu")
        except (TypeError, ValueError):
            return


if __name__ == "__main__":
    main()
