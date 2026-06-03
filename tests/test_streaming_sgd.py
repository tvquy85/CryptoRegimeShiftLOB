from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.tabular_baselines import predict_probabilities, train_streaming_sgd
from evaluation.classification_eval import classification_from_parquet, classification_summary


def test_streaming_sgd_trains_and_predicts(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "feature_a": np.linspace(-1.0, 1.0, 90, dtype=np.float32),
            "feature_b": np.sin(np.linspace(0.0, 4.0, 90)).astype(np.float32),
            "label": ["DOWN", "FLAT", "UP"] * 30,
            "split": ["train"] * 60 + ["valid"] * 15 + ["test"] * 15,
        }
    )
    path = tmp_path / "splits.parquet"
    frame.to_parquet(path, index=False)

    bundle = train_streaming_sgd(
        path,
        ["feature_a", "feature_b"],
        {"sgd": {"alpha": 0.0001, "streaming_epochs": 1}, "random_seed": 7},
        batch_size=17,
    )
    probabilities = predict_probabilities(bundle, frame)

    assert bundle.model_name == "sgd"
    assert set(["prob_down", "prob_flat", "prob_up", "pred_label"]).issubset(probabilities.columns)
    assert len(probabilities) == len(frame)


def test_streaming_classification_matches_in_memory(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "label": ["DOWN", "DOWN", "FLAT", "UP", "UP", "UP"],
            "pred_label": ["DOWN", "UP", "FLAT", "UP", "DOWN", "UP"],
            "regime": ["A", "A", "B", "B", "B", "A"],
            "split": ["test"] * 6,
        }
    )
    path = tmp_path / "predictions.parquet"
    frame.to_parquet(path, index=False)

    overall, by_regime = classification_from_parquet(path)

    expected = classification_summary(frame)
    assert overall == expected
    assert set(by_regime["regime"]) == {"A", "B"}
