from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.classification_eval import classification_from_parquet
from models.deeplob import DeepLOB
from models.lob_transformer import LOBTransformerLite
from models.temporal_cnn import TemporalCNN
from models.torch_datasets import ID_TO_LABEL, TemporalFeatureScaler, iter_temporal_window_batches
from utils.artifacts import model_stage_table_path, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.execution_columns import execution_columns
from utils.io import write_run_metadata
from utils.logging import configure_logging
from utils.seed import set_global_seed


PROBABILITY_COLUMNS = {"prob_down", "prob_flat", "prob_up", "pred_label"}
DEFAULT_CHECKPOINT = "outputs/checkpoints/stage3_8_tcn_gpu_pilot_btc_full2024_v001_tcn_gpu_stage3_pilot.pt"
DEFAULT_OUTPUT = "data/predictions/predictions_stage3_tcn_gpu_execution_ready.parquet"


def main() -> None:
    parser = common_parser("Sinh temporal LOB predictions execution-ready tu checkpoint.")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-train-windows", type=int, default=None)
    parser.add_argument("--max-valid-windows", type=int, default=None)
    parser.add_argument("--max-test-windows", type=int, default=None)
    parser.add_argument("--batch-windows", type=int, default=None)
    parser.add_argument("--compile-model", choices=["auto", "true", "false"], default=None)
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    set_global_seed(int(config.get("random_seed", 7)))
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/temporal_inference.log"))

    infer_cfg = dict(config.get("temporal_inference", {}))
    source_path = resolve_path(config, str(infer_cfg.get("prediction_source", config.get("prediction_source", config["prediction_output"]))))
    output_path = resolve_path(config, str(namespace.output or infer_cfg.get("prediction_output", config.get("prediction_output", DEFAULT_OUTPUT))))
    checkpoint_path = resolve_path(config, str(namespace.checkpoint or infer_cfg.get("checkpoint_path", DEFAULT_CHECKPOINT)))
    if source_path.resolve() == output_path.resolve():
        raise RuntimeError("prediction_source va prediction_output phai khac nhau de khong overwrite baseline hien co.")
    if not source_path.exists():
        raise FileNotFoundError(f"Khong tim thay prediction source: {source_path}")
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Khong tim thay temporal checkpoint: {checkpoint_path}")

    model_label = str(infer_cfg.get("model_label", config.get("model_label", "tcn_gpu_stage3")))
    source_batch_rows = int(infer_cfg.get("source_batch_rows", 250_000))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = bool(infer_cfg.get("mixed_precision", True)) and device.type == "cuda"
    pin_memory = bool(infer_cfg.get("pin_memory", True)) and device.type == "cuda"
    logger.info(
        "Temporal inference source=%s output=%s checkpoint=%s model=%s device=%s cuda=%s amp=%s pin_memory=%s.",
        source_path,
        output_path,
        checkpoint_path,
        model_label,
        device,
        torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        use_amp,
        pin_memory,
    )

    model, scaler, checkpoint_meta = load_temporal_checkpoint(checkpoint_path, infer_cfg, device=device)
    model_key = str(checkpoint_meta["model_key"])
    levels = int(checkpoint_meta["levels"])
    window = int(checkpoint_meta["window"])
    input_dim = levels * 4

    batch_windows = int(namespace.batch_windows or infer_cfg.get("eval_batch_windows", 0) or 0)
    if batch_windows <= 0:
        batch_windows = autotune_batch_windows(
            model,
            device=device,
            window=window,
            input_dim=input_dim,
            candidates=[int(value) for value in infer_cfg.get("batch_window_candidates", [2048, 4096, 8192, 16384])],
            use_amp=use_amp,
            pin_memory=pin_memory,
            logger=logger,
        )
    compile_setting = str(namespace.compile_model or infer_cfg.get("compile_model", "auto")).lower()
    model, compile_status = maybe_compile_model(
        model,
        device=device,
        window=window,
        input_dim=input_dim,
        batch_windows=min(batch_windows, int(infer_cfg.get("compile_benchmark_windows", 1024))),
        use_amp=use_amp,
        compile_setting=compile_setting,
        compile_mode=str(infer_cfg.get("compile_mode", "reduce-overhead")),
        logger=logger,
    )

    strides_cfg = infer_cfg.get("strides", {})
    max_windows_cfg = infer_cfg.get("max_windows", {})
    max_windows = {
        "train": override(namespace.max_train_windows, max_windows_cfg.get("train")),
        "valid": override(namespace.max_valid_windows, max_windows_cfg.get("valid")),
        "test": override(namespace.max_test_windows, max_windows_cfg.get("test")),
    }
    splits = [str(split) for split in infer_cfg.get("splits", ["train", "valid", "test"])]
    strides = {split: int(strides_cfg.get(split, 10)) for split in splits}
    metadata_columns = temporal_execution_metadata_columns()

    started = time.perf_counter()
    prediction_rows, split_rows = write_execution_ready_predictions(
        model,
        source_path,
        output_path,
        scaler=scaler,
        device=device,
        model_label=model_label,
        levels=levels,
        window=window,
        splits=splits,
        strides=strides,
        source_batch_rows=source_batch_rows,
        batch_windows=batch_windows,
        max_windows=max_windows,
        metadata_columns=metadata_columns,
        use_amp=use_amp,
        pin_memory=pin_memory,
        logger=logger,
    )
    elapsed = time.perf_counter() - started
    rows_per_second = prediction_rows / elapsed if elapsed > 0 else 0.0

    overall, by_regime = classification_from_parquet(output_path)
    test_rows = int(by_regime["n_rows"].sum()) if not by_regime.empty else 0
    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    overall_row = {
        "model": model_label,
        "model_type": model_key,
        **overall,
        "n_rows": test_rows,
        "prediction_rows": prediction_rows,
        "evaluation_scope": "stage3_temporal_execution_ready",
        "stride_train": strides.get("train"),
        "stride_valid": strides.get("valid"),
        "stride_test": strides.get("test"),
    }
    overall_path = model_stage_table_path(tables, "table_forecasting_overall", args.stage, model_label)
    by_regime_path = model_stage_table_path(tables, "table_forecasting_by_regime", args.stage, model_label)
    pd.DataFrame([overall_row]).to_csv(overall_path, index=False)
    by_regime.insert(0, "model", model_label)
    by_regime.insert(1, "model_type", model_key)
    by_regime.to_csv(by_regime_path, index=False)
    upsert_model_rows(stage_table_path(tables, "table_forecasting_overall_temporal_execution_ready", args.stage), pd.DataFrame([overall_row]), ["model"])
    upsert_model_rows(stage_table_path(tables, "table_forecasting_by_regime_temporal_execution_ready", args.stage), by_regime, ["model", "regime"])

    audit_path = write_stage39_inference_audit(
        resolve_path(config, str(infer_cfg.get("audit_output", "audits/audit_stage3_9_tcn_gpu_execution_ready.md"))),
        run_id=args.run_id,
        model_label=model_label,
        checkpoint_path=checkpoint_path,
        output_path=output_path,
        device=str(device),
        cuda_device=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        overall=overall_row,
        split_rows=split_rows,
        batch_windows=batch_windows,
        compile_status=compile_status,
        use_amp=use_amp,
        pin_memory=pin_memory,
        elapsed_seconds=elapsed,
        rows_per_second=rows_per_second,
    )

    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "14_temporal_inference_execution_ready.py",
        artifacts={
            "source_predictions": source_path,
            "checkpoint": checkpoint_path,
            "execution_ready_predictions": output_path,
            "forecasting_overall": overall_path,
            "forecasting_by_regime": by_regime_path,
            "audit": audit_path,
        },
        extra={
            "model_label": model_label,
            "device": str(device),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "use_amp": use_amp,
            "pin_memory": pin_memory,
            "batch_windows": batch_windows,
            "compile_status": compile_status,
            "prediction_rows": prediction_rows,
            "split_rows": split_rows,
            "rows_per_second": rows_per_second,
            "overall_test": overall,
        },
    )
    logger.info(
        "Temporal execution-ready inference xong rows=%s test_rows=%s windows_per_sec=%.2f output=%s.",
        prediction_rows,
        test_rows,
        rows_per_second,
        output_path,
    )


def load_temporal_checkpoint(checkpoint_path: Path, infer_cfg: dict[str, Any], *, device: torch.device) -> tuple[nn.Module, TemporalFeatureScaler | None, dict[str, object]]:
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state_dict = payload.get("state_dict")
    if state_dict is None:
        raise RuntimeError(f"Checkpoint khong co state_dict: {checkpoint_path}")
    model_key = str(payload.get("model_key", "tcn"))
    levels = int(payload.get("levels", infer_cfg.get("levels", 10)))
    window = int(payload.get("window", infer_cfg.get("window", 100)))
    input_dim = levels * 4
    model_config = dict(payload.get("model_config") or {})
    if model_key == "tcn":
        model_config = {"input_dim": input_dim, "hidden_dim": infer_hidden_dim(state_dict, default=int(model_config.get("hidden_dim", infer_cfg.get("hidden_dim", 64))))}
        model = TemporalCNN(**model_config)
    elif model_key in {"deeplob", "deeplob_faithful_lite"}:
        model_config = {
            "input_dim": input_dim,
            "conv_channels": int(model_config.get("conv_channels", infer_deeplob_conv_channels(state_dict, default=int(infer_cfg.get("deeplob_conv_channels", 16))))),
            "inception_channels": int(model_config.get("inception_channels", infer_deeplob_inception_channels(state_dict, default=int(infer_cfg.get("deeplob_inception_channels", 32))))),
            "hidden_dim": int(model_config.get("hidden_dim", infer_deeplob_hidden_dim(state_dict, default=int(infer_cfg.get("hidden_dim", 64))))),
        }
        model = DeepLOB(**model_config)
    elif model_key == "lob_transformer":
        model_config = {
            "input_dim": input_dim,
            "conv_channels": int(model_config.get("conv_channels", infer_deeplob_conv_channels(state_dict, default=int(infer_cfg.get("transformer_conv_channels", 16))))),
            "inception_channels": int(model_config.get("inception_channels", infer_deeplob_inception_channels(state_dict, default=int(infer_cfg.get("transformer_inception_channels", 32))))),
            "n_heads": int(model_config.get("n_heads", infer_cfg.get("transformer_heads", 4))),
            "n_layers": int(model_config.get("n_layers", infer_cfg.get("transformer_layers", 1))),
            "dropout": float(model_config.get("dropout", infer_cfg.get("transformer_dropout", 0.1))),
        }
        model = LOBTransformerLite(**model_config)
    else:
        raise RuntimeError(f"Temporal checkpoint model_key khong ho tro: {model_key}")
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    scaler_payload = payload.get("scaler")
    scaler = None
    if scaler_payload:
        scaler = TemporalFeatureScaler(
            mean=np.asarray(scaler_payload["mean"], dtype=np.float32),
            std=np.asarray(scaler_payload["std"], dtype=np.float32),
        )
    metadata: dict[str, object] = {"model_key": model_key, "levels": levels, "window": window, "model_config": model_config}
    metadata.update(model_config)
    return model, scaler, metadata


def load_tcn_checkpoint(checkpoint_path: Path, infer_cfg: dict[str, Any], *, device: torch.device) -> tuple[nn.Module, TemporalFeatureScaler | None, dict[str, object]]:
    """Backward-compatible wrapper for tests and older scripts."""
    return load_temporal_checkpoint(checkpoint_path, infer_cfg, device=device)


def infer_hidden_dim(state_dict: dict[str, torch.Tensor], *, default: int) -> int:
    first_conv = state_dict.get("net.0.weight")
    if first_conv is not None and first_conv.ndim >= 1:
        return int(first_conv.shape[0])
    return default


def infer_deeplob_conv_channels(state_dict: dict[str, torch.Tensor], *, default: int) -> int:
    first_conv = state_dict.get("conv1.0.weight")
    if first_conv is not None and first_conv.ndim >= 1:
        return int(first_conv.shape[0])
    return default


def infer_deeplob_inception_channels(state_dict: dict[str, torch.Tensor], *, default: int) -> int:
    first_inception = state_dict.get("inception_1.0.weight")
    if first_inception is not None and first_inception.ndim >= 1:
        return int(first_inception.shape[0])
    return default


def infer_deeplob_hidden_dim(state_dict: dict[str, torch.Tensor], *, default: int) -> int:
    recurrent = state_dict.get("temporal.weight_hh_l0")
    if recurrent is not None and recurrent.ndim == 2:
        return int(recurrent.shape[1])
    return default


def temporal_execution_metadata_columns() -> list[str]:
    return [column for column in execution_columns(include_split=True) if column not in PROBABILITY_COLUMNS]


def autotune_batch_windows(
    model: nn.Module,
    *,
    device: torch.device,
    window: int,
    input_dim: int,
    candidates: list[int],
    use_amp: bool,
    pin_memory: bool,
    logger: Any,
) -> int:
    if device.type != "cuda":
        return min(candidates) if candidates else 2048
    best = min(candidates) if candidates else 2048
    for candidate in candidates:
        try:
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            x_cpu = torch.zeros((candidate, window, input_dim), dtype=torch.float32)
            if pin_memory:
                x_cpu = x_cpu.pin_memory()
            x = x_cpu.to(device, non_blocking=pin_memory)
            with torch.inference_mode(), torch.amp.autocast("cuda", enabled=use_amp):
                _ = model(x)
            torch.cuda.synchronize()
            peak_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
            logger.info("Autotune batch_windows=%s ok peak_cuda_mb=%.1f.", candidate, peak_mb)
            best = candidate
        except RuntimeError as exc:
            if "out of memory" not in str(exc).lower():
                logger.warning("Autotune batch_windows=%s loi: %s", candidate, exc)
            else:
                logger.warning("Autotune batch_windows=%s OOM, dung o best=%s.", candidate, best)
            torch.cuda.empty_cache()
            break
    return best


def maybe_compile_model(
    model: nn.Module,
    *,
    device: torch.device,
    window: int,
    input_dim: int,
    batch_windows: int,
    use_amp: bool,
    compile_setting: str,
    compile_mode: str,
    logger: Any,
) -> tuple[nn.Module, dict[str, object]]:
    status: dict[str, object] = {"requested": compile_setting, "used": False, "reason": "disabled"}
    if compile_setting == "false" or device.type != "cuda" or not hasattr(torch, "compile"):
        return model, status
    x = torch.zeros((max(1, batch_windows), window, input_dim), dtype=torch.float32, device=device)
    try:
        eager_seconds = benchmark_forward(model, x, use_amp=use_amp, repeats=3)
        compiled = torch.compile(model, mode=compile_mode)
        with torch.inference_mode(), torch.amp.autocast("cuda", enabled=use_amp):
            _ = compiled(x)
        torch.cuda.synchronize()
        compiled_seconds = benchmark_forward(compiled, x, use_amp=use_amp, repeats=3)
        status.update(
            {
                "reason": "compiled_benchmark",
                "mode": compile_mode,
                "eager_seconds": eager_seconds,
                "compiled_seconds": compiled_seconds,
            }
        )
        if compile_setting == "true" or compiled_seconds <= eager_seconds * 1.05:
            status["used"] = True
            logger.info("torch.compile duoc dung mode=%s eager=%.6f compiled=%.6f.", compile_mode, eager_seconds, compiled_seconds)
            return compiled, status
        status["reason"] = "compiled_not_faster"
        logger.info("torch.compile khong nhanh hon, dung eager eager=%.6f compiled=%.6f.", eager_seconds, compiled_seconds)
        return model, status
    except Exception as exc:  # noqa: BLE001 - fallback eager is the intended behavior.
        status.update({"reason": f"compile_failed: {type(exc).__name__}: {exc}"})
        logger.warning("torch.compile fallback eager vi loi: %s", exc)
        return model, status


def benchmark_forward(model: nn.Module, x: torch.Tensor, *, use_amp: bool, repeats: int) -> float:
    if x.device.type == "cuda":
        torch.cuda.synchronize()
    started = time.perf_counter()
    with torch.inference_mode(), torch.amp.autocast("cuda", enabled=use_amp):
        for _ in range(repeats):
            _ = model(x)
    if x.device.type == "cuda":
        torch.cuda.synchronize()
    return (time.perf_counter() - started) / max(repeats, 1)


def write_execution_ready_predictions(
    model: nn.Module,
    source_path: Path,
    output_path: Path,
    *,
    scaler: TemporalFeatureScaler | None,
    device: torch.device,
    model_label: str,
    levels: int,
    window: int,
    splits: list[str],
    strides: dict[str, int],
    source_batch_rows: int,
    batch_windows: int,
    max_windows: dict[str, int | None],
    metadata_columns: list[str],
    use_amp: bool,
    pin_memory: bool,
    logger: Any | None = None,
) -> tuple[int, dict[str, int]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    split_rows = {split: 0 for split in splits}
    started = time.perf_counter()
    try:
        for split in splits:
            limit = max_windows.get(split)
            if limit == 0:
                continue
            for batch_idx, batch in enumerate(
                iter_temporal_window_batches(
                    source_path,
                    split=split,
                    levels=levels,
                    window=window,
                    stride=int(strides[split]),
                    scaler=scaler,
                    source_batch_rows=source_batch_rows,
                    output_batch_windows=batch_windows,
                    max_windows=limit,
                    metadata_columns=metadata_columns,
                ),
                start=1,
            ):
                probs, pred_labels = predict_batch(
                    model,
                    batch.x,
                    device=device,
                    use_amp=use_amp,
                    pin_memory=pin_memory,
                )
                frame = batch.metadata.reset_index(drop=True).copy()
                frame["prob_down"] = probs[:, 0]
                frame["prob_flat"] = probs[:, 1]
                frame["prob_up"] = probs[:, 2]
                frame["pred_label"] = pred_labels
                frame["model"] = model_label
                frame = order_execution_ready_frame(frame)
                table = pa.Table.from_pandas(frame, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(temp_path, table.schema, compression="snappy")
                elif table.schema != writer.schema:
                    table = table.cast(writer.schema)
                writer.write_table(table)
                n_rows = int(len(frame))
                total_rows += n_rows
                split_rows[split] += n_rows
                if logger is not None and (batch_idx == 1 or batch_idx % 25 == 0):
                    elapsed = time.perf_counter() - started
                    rate = total_rows / elapsed if elapsed > 0 else 0.0
                    logger.info("Inference split=%s batch=%s split_rows=%s total_rows=%s rows_per_sec=%.2f.", split, batch_idx, split_rows[split], total_rows, rate)
    finally:
        if writer is not None:
            writer.close()
    if total_rows == 0 or not temp_path.exists():
        raise RuntimeError("TCN execution-ready writer khong sinh duoc parquet.")
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)
    return total_rows, split_rows


def predict_batch(
    model: nn.Module,
    x_values: np.ndarray,
    *,
    device: torch.device,
    use_amp: bool,
    pin_memory: bool,
) -> tuple[np.ndarray, list[str]]:
    x_cpu = torch.from_numpy(np.ascontiguousarray(x_values))
    if pin_memory:
        x_cpu = x_cpu.pin_memory()
    x = x_cpu.to(device, non_blocking=pin_memory)
    with torch.inference_mode(), torch.amp.autocast("cuda", enabled=use_amp):
        logits = model(x)
        probs_tensor = torch.softmax(logits.float(), dim=1)
    probs = probs_tensor.detach().cpu().numpy().astype(np.float32)
    pred_idx = probs.argmax(axis=1)
    pred_labels = [ID_TO_LABEL[int(idx)] for idx in pred_idx]
    return probs, pred_labels


def order_execution_ready_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = execution_columns(include_split=True)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"Output temporal execution-ready thieu cot bat buoc: {missing}")
    ordered = ["model", *required]
    extras = [column for column in frame.columns if column not in ordered]
    return frame[ordered + extras]


def upsert_model_rows(path: Path, rows: pd.DataFrame, key_columns: list[str]) -> None:
    if path.exists():
        existing = pd.read_csv(path)
        rows = pd.concat([existing, rows], ignore_index=True, sort=False)
    rows.drop_duplicates(subset=key_columns, keep="last").to_csv(path, index=False)


def write_stage39_inference_audit(
    path: Path,
    *,
    run_id: str,
    model_label: str,
    checkpoint_path: Path,
    output_path: Path,
    device: str,
    cuda_device: str | None,
    overall: dict[str, object],
    split_rows: dict[str, int],
    batch_windows: int,
    compile_status: dict[str, object],
    use_amp: bool,
    pin_memory: bool,
    elapsed_seconds: float,
    rows_per_second: float,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Audit Temporal GPU Execution-Ready Inference

- `run_id`: `{run_id}`
- Model: `{model_label}`
- Checkpoint: `{checkpoint_path}`
- Output: `{output_path}`
- Device: `{device}`
- CUDA device: `{cuda_device}`

## Mục tiêu

Sinh artifact TCN có đủ cột cho execution/RSEP, không ghi đè SGD/XGBoost/pilot artifacts. Đây là bước nối từ forecasting temporal pilot sang validation-only tuning và stress test.

## Cấu hình chính

- Batch windows: `{batch_windows}`
- AMP: `{use_amp}`
- Pinned memory: `{pin_memory}`
- torch.compile: `{compile_status}`
- Split rows: `{split_rows}`
- Runtime seconds: `{elapsed_seconds:.2f}`
- Throughput rows/sec: `{rows_per_second:.2f}`

## Kết quả forecasting trên test windows

- accuracy: `{overall.get('accuracy')}`
- macro-F1: `{overall.get('macro_f1')}`
- weighted-F1: `{overall.get('weighted_f1')}`
- MCC: `{overall.get('mcc')}`
- balanced accuracy: `{overall.get('balanced_accuracy')}`
- test rows: `{overall.get('n_rows')}`

## Đánh giá Principal ML Scientist

Artifact này hợp lệ để chuyển sang execution nếu test rows đủ rộng theo ngày và metric không collapse so với pilot Stage 3.8A. Vì đây vẫn là windowed temporal inference, kết quả chỉ nên so công bằng theo cùng sampling/stride đã ghi trong metadata.

## Đánh giá Reviewer ICDM

Điểm mạnh là baseline temporal giờ có thể đi qua cùng protocol execution/RSEP như SGD và XGBoost. Không được claim TCN tốt hơn full-year benchmark nếu chưa chạy tuned execution, bootstrap và stress trên artifact này.

## Quyết định tạm thời

- Pass kỹ thuật nếu file output không rỗng, đủ `execution_columns(include_split=True)`, và các script tuning/stress đọc được.
- Bước tiếp theo: chạy `09_tune_execution_policies.py`, `07_run_stress_grid.py`, sau đó cập nhật audit với kết quả RSEP/stress.
"""
    path.write_text(text, encoding="utf-8")
    return path


def override(value: int | None, default: object) -> int | None:
    if value is not None:
        return value
    if default is None:
        return None
    return int(default)


if __name__ == "__main__":
    main()
