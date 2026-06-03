from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from models.tabular_baselines import train_streaming_sgd


def _load_script_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "18_train_asset_heldout_sgd.py"
    spec = importlib.util.spec_from_file_location("asset_heldout_sgd", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_resolve_model_input_path_falls_back_to_prediction_output(tmp_path: Path) -> None:
    module = _load_script_module()
    prediction_path = tmp_path / "predictions.parquet"
    pd.DataFrame({"split": ["test"], "label": ["UP"]}).to_parquet(prediction_path, index=False)

    config = {
        "_config_path": str(tmp_path / "config.yaml"),
        "project_root": str(tmp_path),
        "split_output": "missing_split.parquet",
        "prediction_output": "predictions.parquet",
    }

    assert module.resolve_model_input_path(config) == prediction_path.resolve()


def test_upsert_csv_replaces_only_matching_composite_key(tmp_path: Path) -> None:
    module = _load_script_module()
    path = tmp_path / "table.csv"
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "regime": "A", "value": 1},
            {"direction": "btc_to_eth", "regime": "B", "value": 2},
            {"direction": "eth_to_btc", "regime": "A", "value": 3},
        ]
    ).to_csv(path, index=False)

    module.upsert_csv(
        path,
        pd.DataFrame([{"direction": "btc_to_eth", "regime": "A", "value": 10}]),
        key_columns=["direction", "regime"],
    )

    current = pd.read_csv(path).sort_values(["direction", "regime"]).reset_index(drop=True)
    assert len(current) == 3
    assert current.loc[(current["direction"] == "btc_to_eth") & (current["regime"] == "A"), "value"].iloc[0] == 10
    assert current.loc[(current["direction"] == "btc_to_eth") & (current["regime"] == "B"), "value"].iloc[0] == 2
    assert current.loc[(current["direction"] == "eth_to_btc") & (current["regime"] == "A"), "value"].iloc[0] == 3


def test_stream_target_test_predictions_writes_only_target_test(tmp_path: Path) -> None:
    module = _load_script_module()
    source = pd.DataFrame(
        {
            "feature_a": np.linspace(-1.0, 1.0, 90, dtype=np.float32),
            "feature_b": np.sin(np.linspace(0.0, 3.0, 90)).astype(np.float32),
            "label": ["DOWN", "FLAT", "UP"] * 30,
            "split": ["train"] * 60 + ["valid"] * 15 + ["test"] * 15,
        }
    )
    source_path = tmp_path / "source.parquet"
    source.to_parquet(source_path, index=False)
    bundle = train_streaming_sgd(
        source_path,
        ["feature_a", "feature_b"],
        {"sgd": {"alpha": 0.0001, "streaming_epochs": 1}, "random_seed": 7},
        batch_size=17,
    )

    target = source.copy()
    target["regime"] = ["A"] * len(target)
    target["prob_up"] = 0.5
    target["pred_label"] = "UP"
    target_path = tmp_path / "target.parquet"
    target.to_parquet(target_path, index=False)

    output_path = tmp_path / "asset_predictions.parquet"
    rows = module.stream_target_test_predictions(target_path, output_path, bundle, batch_size=19)

    output = pd.read_parquet(output_path)
    assert rows == 15
    assert len(output) == 15
    assert set(output["split"]) == {"test"}
    assert {"prob_down", "prob_flat", "prob_up", "pred_label"}.issubset(output.columns)
    assert pq.ParquetFile(output_path).metadata.num_rows == 15
