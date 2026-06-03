from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.tabular_baselines import train_streaming_sgd


def _load_script_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "20_run_asset_heldout_execution.py"
    spec = importlib.util.spec_from_file_location("asset_heldout_execution", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _execution_frame(n_rows: int = 180) -> pd.DataFrame:
    rows = {
        "event_time": pd.date_range("2024-01-01", periods=n_rows, freq="min", tz="UTC"),
        "label_horizon_events": np.full(n_rows, 1, dtype=np.int16),
        "mid_price": np.linspace(100.0, 102.0, n_rows),
        "spread": np.full(n_rows, 0.01, dtype=np.float32),
        "rel_spread": np.full(n_rows, 0.000001, dtype=np.float32),
        "label_fee_bps": np.full(n_rows, 1.0, dtype=np.float32),
        "future_ret_h": np.full(n_rows, 0.001, dtype=np.float32),
        "label": ["DOWN", "FLAT", "UP"] * (n_rows // 3),
        "regime": np.full(n_rows, "BALANCED_TRANSITION"),
        "latency_sensitivity_score": np.zeros(n_rows, dtype=np.float32),
        "liquidity_drought_score": np.zeros(n_rows, dtype=np.float32),
        "adverse_selection_score": np.zeros(n_rows, dtype=np.float32),
        "split": ["train"] * 90 + ["valid"] * 60 + ["test"] * 30,
        "feature_a": np.linspace(-1.0, 1.0, n_rows, dtype=np.float32),
        "prob_up": np.full(n_rows, 0.99, dtype=np.float32),
        "prob_down": np.full(n_rows, 0.0, dtype=np.float32),
        "prob_flat": np.full(n_rows, 0.01, dtype=np.float32),
        "pred_label": np.full(n_rows, "UP"),
    }
    for level in range(20):
        rows[f"ask_{level}_price"] = np.linspace(100.01 + level * 0.01, 102.01 + level * 0.01, n_rows)
        rows[f"bid_{level}_price"] = np.linspace(99.99 - level * 0.01, 101.99 - level * 0.01, n_rows)
        rows[f"ask_{level}_size"] = np.full(n_rows, 100.0, dtype=np.float32)
        rows[f"bid_{level}_size"] = np.full(n_rows, 100.0, dtype=np.float32)
    return pd.DataFrame(rows)


def test_source_validation_recomputes_checkpoint_probabilities(tmp_path: Path) -> None:
    module = _load_script_module()
    frame = _execution_frame()
    source_path = tmp_path / "source.parquet"
    frame.to_parquet(source_path, index=False)
    bundle = train_streaming_sgd(
        source_path,
        ["feature_a"],
        {"sgd": {"alpha": 0.0001, "streaming_epochs": 1}, "random_seed": 7},
        batch_size=31,
    )

    valid = module.read_source_validation_predictions(source_path, bundle, max_rows=1000)

    assert len(valid) == 60
    assert {"prob_down", "prob_flat", "prob_up", "pred_label"}.issubset(valid.columns)
    assert not np.allclose(valid["prob_up"].to_numpy(dtype=float), 0.99)


def test_target_execution_column_validation_fails_fast(tmp_path: Path) -> None:
    module = _load_script_module()
    bad_path = tmp_path / "bad_target.parquet"
    pd.DataFrame({"split": ["test"], "label": ["UP"]}).to_parquet(bad_path, index=False)

    try:
        module.validate_required_columns(bad_path, module.execution_columns(include_split=True), "target")
    except RuntimeError as exc:
        assert "thieu cot bat buoc" in str(exc)
    else:
        raise AssertionError("Expected missing execution columns to fail fast.")


def test_asset_execution_upsert_uses_direction_policy_key(tmp_path: Path) -> None:
    module = _load_script_module()
    path = tmp_path / "execution.csv"
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "policy": "RSEP-full", "net_pnl": -1.0},
            {"direction": "btc_to_eth", "policy": "cost_aware_threshold", "net_pnl": -2.0},
            {"direction": "eth_to_btc", "policy": "RSEP-full", "net_pnl": -3.0},
        ]
    ).to_csv(path, index=False)

    module.upsert_csv(
        path,
        pd.DataFrame([{"direction": "btc_to_eth", "policy": "RSEP-full", "net_pnl": 10.0}]),
        key_columns=["direction", "policy"],
    )

    current = pd.read_csv(path)
    assert len(current) == 3
    assert current.loc[(current["direction"] == "btc_to_eth") & (current["policy"] == "RSEP-full"), "net_pnl"].iloc[0] == 10.0
    assert current.loc[(current["direction"] == "eth_to_btc") & (current["policy"] == "RSEP-full"), "net_pnl"].iloc[0] == -3.0
