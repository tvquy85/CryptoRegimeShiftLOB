from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
from torch import nn

from models.deeplob_lite import DeepLOBFaithfulLite
from models.temporal_cnn import TemporalCNN
from models.torch_datasets import _row_groups_matching_split, build_temporal_windows_from_frame, iter_temporal_window_batches, transform_lob_frame


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "13_train_temporal_baseline_from_predictions.py"
    spec = importlib.util.spec_from_file_location("temporal_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_inference_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "14_temporal_inference_execution_ready.py"
    spec = importlib.util.spec_from_file_location("temporal_inference_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lob_frame(rows: int, *, levels: int = 10, split: str = "train", start: str = "2024-01-01 00:00:00") -> pd.DataFrame:
    base_mid = 100.0 + np.arange(rows, dtype=np.float32) * 0.01
    frame = pd.DataFrame(
        {
            "origin_time": pd.date_range(start, periods=rows, freq="s").astype(str),
            "received_time": pd.date_range(start, periods=rows, freq="s").astype(str),
            "sequence_number": np.arange(rows),
            "symbol": ["BTC-USDT"] * rows,
            "exchange": ["BINANCE"] * rows,
            "event_time": pd.date_range(start, periods=rows, freq="s").astype(str),
            "mid_price": base_mid,
            "spread": np.full(rows, 0.1, dtype=np.float32),
            "rel_spread": np.full(rows, 0.001, dtype=np.float32),
            "future_ret_h": np.zeros(rows, dtype=np.float32),
            "cost_threshold_t": np.zeros(rows, dtype=np.float32),
            "label_horizon_events": np.full(rows, 20),
            "label_fee_bps": np.full(rows, 1.0),
            "label": ["DOWN", "FLAT", "UP", "DOWN", "FLAT", "UP"][:rows] if rows <= 6 else (["DOWN", "FLAT", "UP"] * ((rows // 3) + 1))[:rows],
            "regime": ["BALANCED_TRANSITION"] * rows,
            "split": [split] * rows,
        }
    )
    for level in range(levels):
        offset = (level + 1) * 0.01
        frame[f"ask_{level}_price"] = base_mid + offset
        frame[f"ask_{level}_size"] = np.full(rows, level + 1, dtype=np.float32)
        frame[f"bid_{level}_price"] = base_mid - offset
        frame[f"bid_{level}_size"] = np.full(rows, level + 2, dtype=np.float32)
    return frame


def _execution_lob_frame(rows: int, *, split: str = "test", start: str = "2024-01-01 00:00:00") -> pd.DataFrame:
    frame = _lob_frame(rows, levels=20, split=split, start=start)
    frame["latency_sensitivity_score"] = np.linspace(0.0, 1.0, rows, dtype=np.float32)
    frame["liquidity_drought_score"] = np.linspace(1.0, 0.0, rows, dtype=np.float32)
    frame["adverse_selection_score"] = np.full(rows, 0.25, dtype=np.float32)
    frame["prob_down"] = np.ones(rows, dtype=np.float32)
    frame["prob_flat"] = np.zeros(rows, dtype=np.float32)
    frame["prob_up"] = np.zeros(rows, dtype=np.float32)
    frame["pred_label"] = ["DOWN"] * rows
    return frame


def test_lob_transform_uses_forty_deeplob_features() -> None:
    frame = _lob_frame(5, levels=10)
    values = transform_lob_frame(frame, levels=10)
    assert values.shape == (5, 40)
    assert np.isfinite(values).all()
    assert values[:, 0].mean() > 0
    assert values[:, 2].mean() < 0


def test_temporal_models_accept_window_100_by_40() -> None:
    x = torch.zeros((2, 100, 40), dtype=torch.float32)
    tcn_logits = TemporalCNN(input_dim=40, hidden_dim=8)(x)
    deeplob_logits = DeepLOBFaithfulLite(conv_channels=4, inception_channels=8, hidden_dim=8)(x)
    assert tcn_logits.shape == (2, 3)
    assert deeplob_logits.shape == (2, 3)


def test_temporal_windows_are_causal_and_label_at_window_end() -> None:
    frame = _lob_frame(5, levels=2)
    batch = build_temporal_windows_from_frame(frame, levels=2, window=3, stride=1)
    assert batch.x.shape == (3, 3, 8)
    assert batch.y.tolist() == [2, 0, 1]
    transformed = transform_lob_frame(frame, levels=2)
    np.testing.assert_allclose(batch.x[0, -1], transformed[2])
    np.testing.assert_allclose(batch.x[0, 0], transformed[0])


def test_temporal_windows_do_not_cross_day_boundary() -> None:
    first_day = _lob_frame(2, levels=2, start="2024-01-01 00:00:00")
    second_day = _lob_frame(2, levels=2, start="2024-01-02 00:00:00")
    frame = pd.concat([first_day, second_day], ignore_index=True)
    batch = build_temporal_windows_from_frame(frame, levels=2, window=3, stride=1)
    assert len(batch.y) == 0

    first_day = _lob_frame(3, levels=2, start="2024-01-01 00:00:00")
    second_day = _lob_frame(3, levels=2, start="2024-01-02 00:00:00")
    frame = pd.concat([first_day, second_day], ignore_index=True)
    batch = build_temporal_windows_from_frame(frame, levels=2, window=3, stride=1)
    assert len(batch.y) == 2


def test_temporal_prediction_writer_keeps_tabular_artifacts_separate(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    source = root / "data" / "predictions" / "predictions.parquet"
    sgd = root / "data" / "predictions" / "predictions_sgd.parquet"
    xgb = root / "data" / "predictions" / "predictions_stage3_xgboost_gpu.parquet"
    source.parent.mkdir(parents=True)
    frame = pd.concat(
        [
            _lob_frame(5, levels=2, split="valid", start="2024-01-01 00:00:00"),
            _lob_frame(5, levels=2, split="test", start="2024-01-02 00:00:00"),
        ],
        ignore_index=True,
    )
    frame.to_parquet(source, index=False)
    sgd.write_bytes(b"sgd")
    xgb.write_bytes(b"xgb")

    class TinyModel(nn.Module):
        def forward(self, x):
            logits = torch.zeros((x.shape[0], 3), dtype=torch.float32, device=x.device)
            logits[:, 2] = 1.0
            return logits

    output = root / "data" / "predictions" / "predictions_stage3_tcn_gpu_pilot.parquet"
    rows = module.write_temporal_predictions(
        TinyModel(),
        source,
        output,
        scaler=None,
        device=torch.device("cpu"),
        model_label="tcn_gpu_stage3_pilot",
        levels=2,
        window=3,
        strides={"train": 1, "valid": 1, "test": 1},
        source_batch_rows=4,
        batch_windows=2,
        max_windows={"train": 0, "valid": 2, "test": 2},
    )

    predicted = pd.read_parquet(output)
    assert rows == 4
    assert set(predicted["split"]) == {"valid", "test"}
    assert predicted["pred_label"].eq("UP").all()
    assert {"prob_down", "prob_flat", "prob_up"}.issubset(predicted.columns)
    assert sgd.read_bytes() == b"sgd"
    assert xgb.read_bytes() == b"xgb"


def test_execution_ready_temporal_writer_outputs_required_columns(tmp_path: Path) -> None:
    module = _load_inference_script_module()
    source = tmp_path / "source.parquet"
    output = tmp_path / "predictions_stage3_tcn_gpu_execution_ready.parquet"
    frame = pd.concat(
        [
            _execution_lob_frame(5, split="train", start="2024-01-01 00:00:00"),
            _execution_lob_frame(5, split="valid", start="2024-01-02 00:00:00"),
            _execution_lob_frame(5, split="test", start="2024-01-03 00:00:00"),
        ],
        ignore_index=True,
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(source, index=False)

    class TinyModel(nn.Module):
        def forward(self, x):
            logits = torch.zeros((x.shape[0], 3), dtype=torch.float32, device=x.device)
            logits[:, 2] = 1.0
            return logits

    rows, split_rows = module.write_execution_ready_predictions(
        TinyModel(),
        source,
        output,
        scaler=None,
        device=torch.device("cpu"),
        model_label="tcn_gpu_stage3",
        levels=10,
        window=3,
        splits=["train", "valid", "test"],
        strides={"train": 1, "valid": 1, "test": 1},
        source_batch_rows=5,
        batch_windows=2,
        max_windows={"train": 1, "valid": 1, "test": 2},
        metadata_columns=module.temporal_execution_metadata_columns(),
        use_amp=False,
        pin_memory=False,
    )

    predicted = pd.read_parquet(output)
    required = module.execution_columns(include_split=True)
    assert rows == 4
    assert split_rows == {"train": 1, "valid": 1, "test": 2}
    assert set(required).issubset(predicted.columns)
    assert predicted["model"].eq("tcn_gpu_stage3").all()
    assert predicted["pred_label"].eq("UP").all()
    assert predicted["prob_up"].gt(predicted["prob_down"]).all()
    assert predicted["prob_up"].gt(predicted["prob_flat"]).all()
    assert predicted["prob_down"].lt(1.0).all()


def test_tcn_checkpoint_loader_restores_scaler(tmp_path: Path) -> None:
    module = _load_inference_script_module()
    model = TemporalCNN(input_dim=40, hidden_dim=8)
    checkpoint = tmp_path / "tcn.pt"
    torch.save(
        {
            "model_key": "tcn",
            "state_dict": model.state_dict(),
            "levels": 10,
            "window": 100,
            "scaler": {"mean": [0.0] * 40, "std": [1.0] * 40},
        },
        checkpoint,
    )

    loaded, scaler, meta = module.load_tcn_checkpoint(checkpoint, {}, device=torch.device("cpu"))

    assert isinstance(loaded, TemporalCNN)
    assert scaler is not None
    assert scaler.mean.shape == (40,)
    assert meta["hidden_dim"] == 8
    assert meta["levels"] == 10


def test_compile_fallback_returns_eager_when_compile_raises(monkeypatch) -> None:
    module = _load_inference_script_module()
    model = TemporalCNN(input_dim=8, hidden_dim=4)

    def fail_compile(*args, **kwargs):
        raise RuntimeError("compile unavailable")

    monkeypatch.setattr(torch, "compile", fail_compile, raising=False)

    selected, status = module.maybe_compile_model(
        model,
        device=torch.device("cpu"),
        window=3,
        input_dim=8,
        batch_windows=2,
        use_amp=False,
        compile_setting="auto",
        compile_mode="reduce-overhead",
        logger=type("Logger", (), {"warning": lambda *args, **kwargs: None, "info": lambda *args, **kwargs: None})(),
    )

    assert selected is model
    assert status["used"] is False


def test_temporal_window_iterator_respects_exact_max_windows(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    frame = _lob_frame(20, levels=2, split="test")
    frame.to_parquet(source, index=False)
    total = 0
    for batch in iter_temporal_window_batches(
        source,
        split="test",
        levels=2,
        window=3,
        stride=1,
        source_batch_rows=20,
        output_batch_windows=4,
        max_windows=5,
    ):
        total += len(batch.y)
    assert total == 5


def test_temporal_iterator_can_prune_split_row_groups(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    frame = pd.concat(
        [
            _lob_frame(5, levels=10, split="train", start="2024-01-01 00:00:00"),
            _lob_frame(5, levels=10, split="valid", start="2024-01-02 00:00:00"),
            _lob_frame(5, levels=10, split="test", start="2024-01-03 00:00:00"),
        ],
        ignore_index=True,
    )
    frame.to_parquet(source, index=False, row_group_size=5)

    parquet = pq.ParquetFile(source)

    assert _row_groups_matching_split(parquet, "train") == [0]
    assert _row_groups_matching_split(parquet, "valid") == [1]
    assert _row_groups_matching_split(parquet, "test") == [2]


def test_temporal_comparison_deduplicates_baselines(tmp_path: Path) -> None:
    module = _load_script_module()
    tables = tmp_path / "tables"
    tables.mkdir()
    pd.DataFrame(
        [
            {"model": "sgd_stage3", "macro_f1": 0.46},
            {"model": "xgboost_gpu_stage3", "macro_f1": 0.45},
        ]
    ).to_csv(tables / "table_model_forecasting_execution_comparison_stage3.csv", index=False)
    output = tables / "table_temporal_vs_tabular_comparison_stage3.csv"
    pd.DataFrame(
        [
            {"model": "sgd_stage3", "macro_f1": 0.1},
            {"model": "xgboost_gpu_stage3", "macro_f1": 0.1},
            {"model": "tcn_gpu_stage3_pilot", "macro_f1": 0.4},
        ]
    ).to_csv(output, index=False)

    module.write_temporal_comparison(tables, output, {"model": "deeplob_faithful_lite_stage3_pilot", "macro_f1": 0.47})

    comparison = pd.read_csv(output)
    assert comparison["model"].tolist().count("sgd_stage3") == 1
    assert comparison["model"].tolist().count("xgboost_gpu_stage3") == 1
    assert comparison["model"].tolist().count("tcn_gpu_stage3_pilot") == 1
    assert comparison["model"].tolist().count("deeplob_faithful_lite_stage3_pilot") == 1
    assert comparison.loc[comparison["model"] == "sgd_stage3", "macro_f1"].iloc[0] == 0.46
