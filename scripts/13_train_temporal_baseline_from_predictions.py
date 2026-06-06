from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.classification_eval import classification_by_regime, classification_from_parquet, classification_summary
from models.deeplob import DeepLOB
from models.lob_transformer import LOBTransformerLite
from models.temporal_cnn import TemporalCNN
from models.torch_datasets import (
    ID_TO_LABEL,
    TemporalFeatureScaler,
    fit_lob_feature_scaler,
    iter_temporal_window_batches,
)
from utils.artifacts import stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import write_json, write_run_metadata
from utils.logging import configure_logging
from utils.seed import set_global_seed


MODEL_LABELS = {
    "tcn": "tcn_gpu_stage3_pilot",
    "deeplob": "deeplob_stage3_pilot",
    "deeplob_faithful_lite": "deeplob_faithful_lite_stage3_pilot",
    "lob_transformer": "lob_transformer_stage3_pilot",
}
PREDICTION_OUTPUTS = {
    "tcn": "data/predictions/predictions_stage3_tcn_gpu_pilot.parquet",
    "deeplob": "data/predictions/predictions_stage3_deeplob_pilot.parquet",
    "deeplob_faithful_lite": "data/predictions/predictions_stage3_deeplob_faithful_lite_pilot.parquet",
    "lob_transformer": "data/predictions/predictions_stage3_lob_transformer_pilot.parquet",
}
SUPPORTED_TEMPORAL_MODELS = sorted(MODEL_LABELS)


def main() -> None:
    parser = common_parser("Huấn luyện temporal LOB baseline từ predictions.parquet.")
    parser.add_argument("--model", choices=SUPPORTED_TEMPORAL_MODELS, default=None)
    parser.add_argument("--max-train-windows", type=int, default=None)
    parser.add_argument("--max-valid-windows", type=int, default=None)
    parser.add_argument("--max-test-windows", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    set_global_seed(int(config.get("random_seed", 7)))
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/temporal_train.log"))

    temporal_cfg = dict(config.get("temporal", {}))
    model_key = namespace.model or str(temporal_cfg.get("model_name", "tcn"))
    if model_key not in MODEL_LABELS:
        raise ValueError(f"Temporal model không được hỗ trợ: {model_key}")
    model_label = str(temporal_cfg.get("model_labels", {}).get(model_key, MODEL_LABELS[model_key]))
    source_path = resolve_path(config, str(temporal_cfg.get("prediction_source", config.get("prediction_output", "data/predictions/predictions.parquet"))))
    output_path = temporal_prediction_output_path(config, model_key)
    checkpoint_path = resolve_path(config, f"outputs/checkpoints/{args.run_id}_{model_label}.pt")

    levels = int(temporal_cfg.get("levels", 10))
    window = int(temporal_cfg.get("window", 100))
    source_batch_rows = int(temporal_cfg.get("source_batch_rows", 250_000))
    train_batch_windows = int(temporal_cfg.get("train_batch_windows", 1024))
    eval_batch_windows = int(temporal_cfg.get("eval_batch_windows", 2048))
    strides = temporal_cfg.get("strides", {})
    max_windows_cfg = temporal_cfg.get("max_windows", {})
    train_max = _override(namespace.max_train_windows, max_windows_cfg.get("train"))
    valid_max = _override(namespace.max_valid_windows, max_windows_cfg.get("valid"))
    test_max = _override(namespace.max_test_windows, max_windows_cfg.get("test"))
    epochs = int(namespace.epochs or temporal_cfg.get("epochs", 5))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = bool(temporal_cfg.get("mixed_precision", True)) and device.type == "cuda"
    logger.info("Temporal baseline model=%s label=%s device=%s amp=%s source=%s", model_key, model_label, device, use_amp, source_path)

    scaler = None
    if bool(temporal_cfg.get("normalize_features", True)):
        scaler_max_rows_cfg = temporal_cfg.get("scaler_max_rows", 1_000_000)
        scaler = fit_lob_feature_scaler(
            source_path,
            split="train",
            levels=levels,
            max_rows=None if scaler_max_rows_cfg is None else int(scaler_max_rows_cfg),
            source_batch_rows=source_batch_rows,
        )
        scaler_path = resolve_path(config, f"outputs/checkpoints/{args.run_id}_{model_label}_scaler.json")
        write_json({"mean": scaler.mean.tolist(), "std": scaler.std.tolist()}, scaler_path)
    else:
        scaler_path = None

    model = build_temporal_model(model_key, temporal_cfg, input_dim=levels * 4).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(temporal_cfg.get("learning_rate", 1e-3)), weight_decay=float(temporal_cfg.get("weight_decay", 1e-4)))
    loss_fn = nn.CrossEntropyLoss()
    grad_scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_state = None
    best_macro_f1 = -np.inf
    best_epoch = -1
    patience = int(temporal_cfg.get("early_stopping_patience", 2))
    stale = 0
    history = []

    for epoch in range(1, epochs + 1):
        train_loss, train_rows = train_one_epoch(
            model,
            optimizer,
            loss_fn,
            grad_scaler,
            source_path,
            scaler=scaler,
            device=device,
            use_amp=use_amp,
            levels=levels,
            window=window,
            stride=int(strides.get("train", 5)),
            source_batch_rows=source_batch_rows,
            batch_windows=train_batch_windows,
            max_windows=train_max,
        )
        valid_frame = predict_split_to_frame(
            model,
            source_path,
            scaler=scaler,
            device=device,
            levels=levels,
            window=window,
            stride=int(strides.get("valid", 10)),
            source_batch_rows=source_batch_rows,
            batch_windows=eval_batch_windows,
            max_windows=valid_max,
            split="valid",
        )
        valid_metrics = classification_summary(valid_frame) if not valid_frame.empty else _empty_metrics()
        history.append({"epoch": epoch, "train_loss": train_loss, "train_windows": train_rows, **{f"valid_{key}": value for key, value in valid_metrics.items()}})
        logger.info("epoch=%s train_loss=%.6f train_windows=%s valid_macro_f1=%.6f", epoch, train_loss, train_rows, valid_metrics["macro_f1"])
        if valid_metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = valid_metrics["macro_f1"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_key": model_key,
            "model_label": model_label,
            "state_dict": model.state_dict(),
            "levels": levels,
            "window": window,
            "model_config": temporal_model_config(model_key, temporal_cfg, input_dim=levels * 4),
            "best_epoch": best_epoch,
            "best_valid_macro_f1": best_macro_f1,
            "history": history,
            "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist()} if scaler else None,
        },
        checkpoint_path,
    )

    prediction_rows = write_temporal_predictions(
        model,
        source_path,
        output_path,
        scaler=scaler,
        device=device,
        model_label=model_label,
        levels=levels,
        window=window,
        strides={"train": int(strides.get("train", 5)), "valid": int(strides.get("valid", 10)), "test": int(strides.get("test", 10))},
        source_batch_rows=source_batch_rows,
        batch_windows=eval_batch_windows,
        max_windows={"train": int(temporal_cfg.get("prediction_train_windows", 0)), "valid": valid_max, "test": test_max},
    )
    overall, by_regime = classification_from_parquet(output_path)
    test_rows = int(by_regime["n_rows"].sum()) if not by_regime.empty else 0
    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    overall_row = {
        "model": model_label,
        "model_type": model_key,
        **overall,
        "n_rows": test_rows,
        "evaluation_scope": str(temporal_cfg.get("evaluation_scope", "temporal_pilot_sample")),
    }
    overall_path = tables / f"table_forecasting_overall_stage3_{model_label}.csv"
    by_regime_path = tables / f"table_forecasting_by_regime_stage3_{model_label}.csv"
    pd.DataFrame([overall_row]).to_csv(overall_path, index=False)
    by_regime.insert(0, "model", model_label)
    by_regime.insert(1, "model_type", model_key)
    by_regime.to_csv(by_regime_path, index=False)
    temporal_pilot_overall = stage_table_path(tables, "table_forecasting_overall_stage3_temporal_pilot", args.stage)
    temporal_pilot_by_regime = stage_table_path(tables, "table_forecasting_by_regime_stage3_temporal_pilot", args.stage)
    upsert_model_row(temporal_pilot_overall, pd.DataFrame([overall_row]))
    upsert_model_rows(temporal_pilot_by_regime, by_regime, key_columns=["model", "regime"])
    comparison_path = tables / "table_temporal_vs_tabular_comparison_stage3.csv"
    write_temporal_comparison(tables, comparison_path, overall_row)
    audit_path = write_temporal_audit(
        resolve_path(config, str(temporal_cfg.get("audit_output", "audits/audit_stage3_8_temporal_gpu_pilot.md"))),
        model_label=model_label,
        model_key=model_key,
        device=str(device),
        checkpoint_path=checkpoint_path,
        output_path=output_path,
        overall=overall_row,
        best_epoch=best_epoch,
        best_valid_macro_f1=best_macro_f1,
        prediction_rows=prediction_rows,
    )
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "13_train_temporal_baseline_from_predictions.py",
        artifacts={
            "predictions": output_path,
            "checkpoint": checkpoint_path,
            "scaler": scaler_path or "",
            "forecasting_overall": overall_path,
            "forecasting_by_regime": by_regime_path,
            "temporal_comparison": comparison_path,
            "audit": audit_path,
        },
        extra={
            "model_key": model_key,
            "model_label": model_label,
            "device": str(device),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "best_epoch": best_epoch,
            "best_valid_macro_f1": best_macro_f1,
            "prediction_rows": prediction_rows,
        },
    )
    logger.info("Temporal baseline xong: model=%s test_rows=%s output=%s", model_label, test_rows, output_path)


def temporal_prediction_output_path(config: dict[str, Any], model_key: str) -> Path:
    temporal_cfg = config.get("temporal", {})
    outputs = temporal_cfg.get("prediction_outputs", {})
    return resolve_path(config, str(outputs.get(model_key, PREDICTION_OUTPUTS[model_key])))


def build_temporal_model(model_key: str, config: dict[str, Any], *, input_dim: int) -> nn.Module:
    model_config = temporal_model_config(model_key, config, input_dim=input_dim)
    if model_key == "tcn":
        return TemporalCNN(**model_config)
    if model_key in {"deeplob", "deeplob_faithful_lite"}:
        return DeepLOB(**model_config)
    if model_key == "lob_transformer":
        return LOBTransformerLite(**model_config)
    raise ValueError(f"Temporal model không được hỗ trợ: {model_key}")


def temporal_model_config(model_key: str, config: dict[str, Any], *, input_dim: int) -> dict[str, Any]:
    hidden_dim = int(config.get("hidden_dim", 64))
    if model_key == "tcn":
        return {"input_dim": input_dim, "hidden_dim": hidden_dim}
    if model_key in {"deeplob", "deeplob_faithful_lite"}:
        if input_dim != 40:
            raise ValueError("DeepLOB-faithful-lite yêu cầu đúng 40 LOB features từ 10 levels.")
        return {
            "input_dim": input_dim,
            "conv_channels": int(config.get("deeplob_conv_channels", 16)),
            "inception_channels": int(config.get("deeplob_inception_channels", 32)),
            "hidden_dim": hidden_dim,
        }
    if model_key == "lob_transformer":
        if input_dim != 40:
            raise ValueError("LOB-Transformer requires exactly 40 LOB features from 10 levels.")
        return {
            "input_dim": input_dim,
            "conv_channels": int(config.get("transformer_conv_channels", config.get("deeplob_conv_channels", 16))),
            "inception_channels": int(config.get("transformer_inception_channels", 32)),
            "n_heads": int(config.get("transformer_heads", 4)),
            "n_layers": int(config.get("transformer_layers", 1)),
            "dropout": float(config.get("transformer_dropout", 0.1)),
        }
    raise ValueError(f"Temporal model không được hỗ trợ: {model_key}")


def train_one_epoch(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    loss_fn: nn.Module,
    grad_scaler: torch.amp.GradScaler,
    source_path: Path,
    *,
    scaler: TemporalFeatureScaler | None,
    device: torch.device,
    use_amp: bool,
    levels: int,
    window: int,
    stride: int,
    source_batch_rows: int,
    batch_windows: int,
    max_windows: int | None,
) -> tuple[float, int]:
    model.train()
    total_loss = 0.0
    total_rows = 0
    for batch in iter_temporal_window_batches(
        source_path,
        split="train",
        levels=levels,
        window=window,
        stride=stride,
        scaler=scaler,
        source_batch_rows=source_batch_rows,
        output_batch_windows=batch_windows,
        max_windows=max_windows,
    ):
        x = torch.from_numpy(batch.x).to(device, non_blocking=True)
        y = torch.from_numpy(batch.y).to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=use_amp):
            logits = model(x)
            loss = loss_fn(logits, y)
        grad_scaler.scale(loss).backward()
        grad_scaler.step(optimizer)
        grad_scaler.update()
        total_loss += float(loss.detach().cpu()) * int(len(y))
        total_rows += int(len(y))
    if total_rows == 0:
        raise RuntimeError("Không tạo được train windows cho temporal baseline.")
    return total_loss / total_rows, total_rows


@torch.no_grad()
def predict_split_to_frame(
    model: nn.Module,
    source_path: Path,
    *,
    scaler: TemporalFeatureScaler | None,
    device: torch.device,
    levels: int,
    window: int,
    stride: int,
    source_batch_rows: int,
    batch_windows: int,
    max_windows: int | None,
    split: str,
) -> pd.DataFrame:
    model.eval()
    frames = []
    for batch in iter_temporal_window_batches(
        source_path,
        split=split,
        levels=levels,
        window=window,
        stride=stride,
        scaler=scaler,
        source_batch_rows=source_batch_rows,
        output_batch_windows=batch_windows,
        max_windows=max_windows,
    ):
        probs, pred_labels = predict_batch(model, batch.x, device=device)
        frame = batch.metadata.reset_index(drop=True).copy()
        frame["prob_down"] = probs[:, 0]
        frame["prob_flat"] = probs[:, 1]
        frame["prob_up"] = probs[:, 2]
        frame["pred_label"] = pred_labels
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


@torch.no_grad()
def predict_batch(model: nn.Module, x_values: np.ndarray, *, device: torch.device) -> tuple[np.ndarray, list[str]]:
    x = torch.from_numpy(x_values).to(device, non_blocking=True)
    logits = model(x)
    probs = torch.softmax(logits, dim=1).detach().cpu().numpy().astype(np.float32)
    pred_idx = probs.argmax(axis=1)
    pred_labels = [ID_TO_LABEL[int(idx)] for idx in pred_idx]
    return probs, pred_labels


def write_temporal_predictions(
    model: nn.Module,
    source_path: Path,
    output_path: Path,
    *,
    scaler: TemporalFeatureScaler | None,
    device: torch.device,
    model_label: str,
    levels: int,
    window: int,
    strides: dict[str, int],
    source_batch_rows: int,
    batch_windows: int,
    max_windows: dict[str, int | None],
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    try:
        for split in ["train", "valid", "test"]:
            limit = max_windows.get(split)
            if limit == 0:
                continue
            for batch in iter_temporal_window_batches(
                source_path,
                split=split,
                levels=levels,
                window=window,
                stride=int(strides[split]),
                scaler=scaler,
                source_batch_rows=source_batch_rows,
                output_batch_windows=batch_windows,
                max_windows=limit,
            ):
                probs, pred_labels = predict_batch(model, batch.x, device=device)
                frame = batch.metadata.reset_index(drop=True).copy()
                frame["model"] = model_label
                frame["prob_down"] = probs[:, 0]
                frame["prob_flat"] = probs[:, 1]
                frame["prob_up"] = probs[:, 2]
                frame["pred_label"] = pred_labels
                table = pa.Table.from_pandas(frame, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(temp_path, table.schema, compression="snappy")
                elif table.schema != writer.schema:
                    table = table.cast(writer.schema)
                writer.write_table(table)
                total_rows += int(len(frame))
    finally:
        if writer is not None:
            writer.close()
    if total_rows == 0 or not temp_path.exists():
        raise RuntimeError("Temporal prediction writer không sinh được parquet.")
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)
    return total_rows


def upsert_model_row(path: Path, row: pd.DataFrame) -> None:
    upsert_model_rows(path, row, key_columns=["model"])


def upsert_model_rows(path: Path, rows: pd.DataFrame, *, key_columns: list[str]) -> None:
    if path.exists():
        existing = pd.read_csv(path)
        combined = pd.concat([existing, rows], ignore_index=True)
    else:
        combined = rows.copy()
    combined = combined.drop_duplicates(subset=key_columns, keep="last")
    combined.to_csv(path, index=False)


def write_temporal_comparison(tables: Path, output_path: Path, temporal_row: dict[str, object]) -> None:
    rows = []
    baseline_path = tables / "table_model_forecasting_execution_comparison_stage3.csv"
    if baseline_path.exists():
        baseline = pd.read_csv(baseline_path)
        baseline["evaluation_scope"] = "full_year_test"
        rows.append(baseline)
    if output_path.exists():
        previous = pd.read_csv(output_path)
        baseline_models = set(rows[0]["model"]) if rows and "model" in rows[0].columns else set()
        previous = previous[(previous["model"] != temporal_row["model"]) & (~previous["model"].isin(baseline_models))]
        rows.append(previous)
    rows.append(pd.DataFrame([temporal_row]))
    comparison = pd.concat(rows, ignore_index=True, sort=False)
    if "model" in comparison.columns:
        comparison = comparison.drop_duplicates(subset=["model"], keep="last")
    comparison.to_csv(output_path, index=False)


def write_temporal_audit(
    path: Path,
    *,
    model_label: str,
    model_key: str,
    device: str,
    checkpoint_path: Path,
    output_path: Path,
    overall: dict[str, object],
    best_epoch: int,
    best_valid_macro_f1: float,
    prediction_rows: int,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Audit Stage 3.8: Temporal GPU Pilot

- `run_id`: xem metadata tương ứng trong `outputs/logs`
- Model: `{model_label}` (`{model_key}`)
- Device: `{device}`
- Mục tiêu: kiểm tra liệu temporal/deep baseline kiểu DeepLOB/TCN có cải thiện forecasting so với SGD/XGBoost full-year hay không, trước khi mở full inference/execution.

## Artifact

- Checkpoint: `{checkpoint_path}`
- Predictions: `{output_path}`
- Prediction rows: `{prediction_rows}`

## Kết quả forecasting test pilot

- accuracy: `{overall.get('accuracy')}`
- macro-F1: `{overall.get('macro_f1')}`
- weighted-F1: `{overall.get('weighted_f1')}`
- MCC: `{overall.get('mcc')}`
- balanced accuracy: `{overall.get('balanced_accuracy')}`
- test rows: `{overall.get('n_rows')}`
- best epoch: `{best_epoch}`
- best validation macro-F1: `{best_valid_macro_f1}`

## Đánh giá Principal ML Scientist

Temporal pilot này chỉ nên được so với SGD/XGBoost bằng macro-F1, MCC và by-regime stability. Nếu chỉ tăng accuracy nhưng macro-F1 thấp, không nên xem là baseline mạnh hơn.

## Đánh giá Reviewer ICDM

Baseline temporal giúp giảm rủi ro reviewer cho rằng paper thiếu deep LOB model. Tuy nhiên pilot sample không thay thế full-year inference; nếu kết quả hứa hẹn cần mở Stage 3.9 để chạy inference đầy đủ và execution/RSEP tương ứng.

## Quyết định

- Pass kỹ thuật nếu artifact đầy đủ, không OOM và metrics sinh được.
- Go Stage 3.9 nếu macro-F1/MCC hoặc by-regime stability cải thiện rõ so với tabular baselines.
- Nếu không cải thiện, giữ làm negative baseline và không claim deep model tốt hơn.
"""
    path.write_text(text, encoding="utf-8")
    return path


def _override(value: int | None, default: object) -> int | None:
    if value is not None:
        return value
    if default is None:
        return None
    return int(default)


def _empty_metrics() -> dict[str, float]:
    return {"accuracy": 0.0, "macro_f1": 0.0, "weighted_f1": 0.0, "mcc": 0.0, "balanced_accuracy": 0.0}


if __name__ == "__main__":
    main()
