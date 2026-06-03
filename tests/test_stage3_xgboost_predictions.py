from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.preprocessing import LabelEncoder


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "11_train_xgboost_gpu_from_predictions.py"
    spec = importlib.util.spec_from_file_location("stage3_xgboost_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_read_split_sample_uses_requested_split_only(tmp_path: Path) -> None:
    module = _load_script_module()
    frame = pd.DataFrame(
        {
            "feature": np.arange(30, dtype=np.float32),
            "label": ["UP"] * 10 + ["DOWN"] * 10 + ["FLAT"] * 10,
            "split": ["train"] * 10 + ["valid"] * 10 + ["test"] * 10,
        }
    )
    path = tmp_path / "source.parquet"
    frame.to_parquet(path, index=False)

    sample, total = module.read_split_sample(path, "train", ["feature", "label", "split"], max_rows=4)

    assert total == 10
    assert set(sample["split"]) == {"train"}
    assert len(sample) <= 4
    assert sample["feature"].max() < 10


def test_stream_predictions_writes_separate_output_and_replaces_probabilities(tmp_path: Path) -> None:
    module = _load_script_module()
    source = tmp_path / "source.parquet"
    output = tmp_path / "xgb.parquet"
    frame = pd.DataFrame(
        {
            "feature": np.arange(6, dtype=np.float32),
            "label": ["DOWN", "FLAT", "UP", "DOWN", "FLAT", "UP"],
            "split": ["train", "valid", "test", "test", "test", "test"],
            "regime": ["A"] * 6,
            "prob_down": np.ones(6, dtype=np.float32),
            "prob_flat": np.zeros(6, dtype=np.float32),
            "prob_up": np.zeros(6, dtype=np.float32),
            "pred_label": ["DOWN"] * 6,
        }
    )
    frame.to_parquet(source, index=False)

    class Pipeline:
        def predict_proba(self, x):
            values = np.zeros((len(x), 3), dtype=np.float32)
            values[:, 2] = 1.0
            return values

    class Bundle:
        features = ["feature"]
        pipeline = Pipeline()
        label_encoder = LabelEncoder().fit(["DOWN", "FLAT", "UP"])

    n_rows = module.stream_predictions_from_source(source, output, Bundle(), batch_size=2)

    assert source.exists()
    assert output.exists()
    assert n_rows == pq.ParquetFile(source).metadata.num_rows
    predicted = pd.read_parquet(output)
    assert predicted["prob_up"].eq(1.0).all()
    assert predicted["prob_down"].eq(0.0).all()
    assert predicted["pred_label"].eq("UP").all()
