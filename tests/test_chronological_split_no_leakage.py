from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from models.tabular_baselines import train_streaming_sgd
from policies.tuning import edge_threshold_grid, tune_policy
from regimes.regime_splits import chronological_split
from regimes.rule_regime_labeler import fit_thresholds
from simulator.market_order_sim import ExecutionConfig


def _load_split_audit_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "23_build_split_audit.py"
    spec = importlib.util.spec_from_file_location("split_audit_module", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_chronological_split_purges_horizon_boundary_rows() -> None:
    frame = pd.DataFrame(
        {
            "row_id": np.arange(20),
            "event_time": pd.date_range("2024-01-01", periods=20, freq="s", tz="UTC"),
        }
    )
    split = chronological_split(frame, train_fraction=0.6, valid_fraction=0.2, purge_gap_events=2)

    assert split.loc[split["split"].eq("train"), "row_id"].tolist() == list(range(10))
    assert split.loc[split["split"].eq("valid"), "row_id"].tolist() == [12, 13]
    assert split.loc[split["split"].eq("test"), "row_id"].tolist() == [16, 17, 18, 19]
    assert (split.loc[split["split"].eq("train"), "row_id"] + 2 < 12).all()
    assert (split.loc[split["split"].eq("valid"), "row_id"] + 2 < 16).all()


def test_split_audit_detects_unpurged_horizon_overlap() -> None:
    module = _load_split_audit_module()
    rows = 140
    frame = pd.DataFrame(
        {
            "event_time": pd.date_range("2024-01-01", periods=rows, freq="100ms", tz="UTC"),
            "split": ["train"] * 80 + ["valid"] * 30 + ["test"] * 30,
            "label_horizon_events": np.full(rows, 50, dtype=np.int16),
        }
    )
    audit = module.audit_split_frame(frame, symbol="BTC-USDT", source_artifact="synthetic.parquet")
    boundary = audit.loc[audit["split"].isin(["train", "valid"])]

    assert set(boundary["horizon_overlap_rows"]) == {50}
    assert set(boundary["status"]) == {"WARN_BOUNDARY_OVERLAP"}


def test_streaming_sgd_scaler_fits_train_split_only(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "feature": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 1000.0, 1001.0, -1000.0, -1001.0],
            "label": ["DOWN", "FLAT", "UP", "DOWN", "FLAT", "UP", "UP", "UP", "DOWN", "DOWN"],
            "split": ["train"] * 6 + ["valid"] * 2 + ["test"] * 2,
        }
    )
    path = tmp_path / "splits.parquet"
    frame.to_parquet(path, index=False)
    bundle = train_streaming_sgd(
        path,
        ["feature"],
        {"sgd": {"streaming_epochs": 1, "alpha": 0.0001}, "random_seed": 7},
        batch_size=4,
    )

    scaler = bundle.pipeline.named_steps["scaler"]
    assert np.isclose(float(scaler.mean_[0]), float(np.mean([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])))


def test_regime_quantile_thresholds_fit_train_prefix_only() -> None:
    train = _regime_frame(6, rel_spread=0.001, vol_score=0.1, total_depth=10.0)
    future_extreme = _regime_frame(4, rel_spread=0.9, vol_score=9.0, total_depth=999.0)
    full = pd.concat([train, future_extreme], ignore_index=True)
    quantiles = {"low": 0.4, "mid": 0.5, "high": 0.7, "very_high": 0.8, "very_low": 0.1}

    actual = fit_thresholds(full, train_fraction=0.6, quantiles=quantiles)
    expected = fit_thresholds(train, train_fraction=1.0, quantiles=quantiles)

    for key in ["spread_q70", "vol_q70", "depth_q60", "stress_q80"]:
        assert np.isclose(actual[key], expected[key])


def test_policy_tuning_uses_validation_frame_not_test_frame() -> None:
    valid = _execution_frame(120, prob_up=0.9, prob_down=0.05)
    altered_test = _execution_frame(120, prob_up=0.01, prob_down=0.98)
    class_returns = {"UP": 0.002, "FLAT": 0.0, "DOWN": -0.002}
    sim_cfg = ExecutionConfig(latency_events=0, fee_bps=0.0, cooldown_events=1)

    grid_before = edge_threshold_grid(valid, class_returns)
    altered_test["prob_up"] = 0.99
    grid_after = edge_threshold_grid(valid, class_returns)
    selected_before, _ = tune_policy(valid, class_returns, sim_cfg, "naive_threshold", [0.50, 0.95], min_trades=5, min_trade_days=1)
    selected_after, _ = tune_policy(valid, class_returns, sim_cfg, "naive_threshold", [0.50, 0.95], min_trades=5, min_trade_days=1)

    assert grid_before == grid_after
    assert selected_before.threshold == selected_after.threshold


def _regime_frame(n_rows: int, *, rel_spread: float, vol_score: float, total_depth: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "vol_score": np.full(n_rows, vol_score),
            "rel_spread": np.full(n_rows, rel_spread),
            "total_depth_10": np.full(n_rows, total_depth),
            "depth_drop_top10": np.zeros(n_rows),
            "spread_z_1m": np.full(n_rows, rel_spread),
            "momentum_score": np.zeros(n_rows),
            "adverse_selection_score": np.zeros(n_rows),
            "choppiness_score": np.zeros(n_rows),
            "depth_z_1m": np.full(n_rows, total_depth),
            "liquidity_drought_score": np.zeros(n_rows),
        }
    )


def _execution_frame(n_rows: int, *, prob_up: float, prob_down: float) -> pd.DataFrame:
    rows = {
        "event_time": pd.date_range("2024-01-01", periods=n_rows, freq="min", tz="UTC"),
        "label_horizon_events": np.full(n_rows, 1, dtype=np.int16),
        "mid_price": np.linspace(100.0, 101.0, n_rows),
        "spread": np.full(n_rows, 0.01),
        "rel_spread": np.full(n_rows, 0.000001),
        "label_fee_bps": np.full(n_rows, 1.0),
        "prob_down": np.full(n_rows, prob_down),
        "prob_flat": np.full(n_rows, max(0.0, 1.0 - prob_up - prob_down)),
        "prob_up": np.full(n_rows, prob_up),
        "regime": np.full(n_rows, "BALANCED_TRANSITION"),
        "label": np.full(n_rows, "UP"),
        "future_ret_h": np.full(n_rows, 0.001),
    }
    for level in range(20):
        rows[f"ask_{level}_price"] = np.linspace(100.01 + level * 0.01, 101.01 + level * 0.01, n_rows)
        rows[f"bid_{level}_price"] = np.linspace(99.99 - level * 0.01, 100.99 - level * 0.01, n_rows)
        rows[f"ask_{level}_size"] = np.full(n_rows, 100.0)
        rows[f"bid_{level}_size"] = np.full(n_rows, 100.0)
    return pd.DataFrame(rows)
