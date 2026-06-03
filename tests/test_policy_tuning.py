from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models import tabular_baselines
from policies.tuning import edge_threshold_grid, tune_policy
from simulator.market_order_sim import ExecutionConfig


def _frame(n_rows: int = 120) -> pd.DataFrame:
    rows = {
        "event_time": pd.date_range("2024-01-01", periods=n_rows, freq="min", tz="UTC"),
        "label_horizon_events": np.full(n_rows, 1, dtype=np.int16),
        "mid_price": np.linspace(100.0, 101.0, n_rows),
        "spread": np.full(n_rows, 0.01),
        "rel_spread": np.full(n_rows, 0.000001),
        "label_fee_bps": np.full(n_rows, 1.0),
        "prob_down": np.full(n_rows, 0.05),
        "prob_flat": np.full(n_rows, 0.05),
        "prob_up": np.full(n_rows, 0.90),
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


def test_tuning_rejects_no_trade_candidate() -> None:
    frame = _frame()
    selected, results = tune_policy(
        frame,
        {"UP": 0.002, "FLAT": 0.0, "DOWN": -0.002},
        ExecutionConfig(latency_events=0, fee_bps=0.0, cooldown_events=1),
        "naive_threshold",
        [0.95, 0.50],
        min_trades=10,
        min_trade_days=1,
    )
    no_trade = [result for result in results if result.threshold == 0.95][0]
    assert no_trade.metrics["n_trades"] == 0
    assert selected.threshold == 0.50
    assert selected.metrics["n_trades"] >= 10


def test_edge_threshold_grid_uses_only_passed_frame() -> None:
    valid = _frame(60)
    test_like = _frame(60)
    test_like["prob_up"] = 0.01
    test_like["prob_down"] = 0.98
    class_returns = {"UP": 0.002, "FLAT": 0.0, "DOWN": -0.002}
    grid_valid = edge_threshold_grid(valid, class_returns)
    grid_with_unseen_test_only = edge_threshold_grid(valid, class_returns)
    assert grid_valid == grid_with_unseen_test_only
    assert grid_valid[0] == 0.0


class _FailingEstimator(BaseEstimator, ClassifierMixin):
    def fit(self, x, y):
        raise RuntimeError("gpu unavailable")


class _WorkingEstimator(BaseEstimator, ClassifierMixin):
    def fit(self, x, y):
        self.classes_ = np.unique(y)
        return self

    def predict_proba(self, x):
        values = np.zeros((len(x), 3), dtype=float)
        values[:, 1] = 1.0
        return values


def test_xgboost_gpu_falls_back_to_cpu(monkeypatch) -> None:
    def fake_estimator(config, *, use_gpu):
        return _FailingEstimator() if use_gpu else _WorkingEstimator()

    monkeypatch.setattr(tabular_baselines, "_xgboost_estimator", fake_estimator)
    frame = pd.DataFrame(
        {
            "feature": [0.0, 1.0, 2.0, 3.0],
            "label": ["DOWN", "FLAT", "UP", "UP"],
        }
    )
    bundle = tabular_baselines.train_tabular_model(
        frame,
        frame,
        ["feature"],
        "xgboost",
        {"xgboost": {"use_gpu": True}, "random_seed": 7},
    )
    assert bundle.model_name == "xgboost_cpu_fallback"
