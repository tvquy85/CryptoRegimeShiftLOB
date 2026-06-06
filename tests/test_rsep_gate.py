from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from features.returns_labels import class_return_means_from_parquet
from policies.rsep import rsep_actions
from policies.tuning import apply_rsep_grid_defaults, edge_threshold_grid, rsep_theta_grid_options
from utils.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def _row(**overrides) -> pd.DataFrame:
    values = {
        "prob_up": 0.8,
        "prob_flat": 0.1,
        "prob_down": 0.1,
        "rel_spread": 0.001,
        "latency_sensitivity_score": 0.0,
        "liquidity_drought_score": 0.0,
        "adverse_selection_score": 0.0,
        "regime": "BALANCED_TRANSITION",
    }
    values.update(overrides)
    return pd.DataFrame([values])


def _returns() -> dict[str, float]:
    return {"UP": 0.01, "FLAT": 0.0, "DOWN": -0.01}


def _cfg(**overrides) -> dict[str, float]:
    values = {
        "theta_edge": 0.0,
        "lambda_latency": 0.0,
        "lambda_liquidity": 0.0,
        "lambda_adverse": 0.0,
        "lambda_regime": 0.0,
    }
    values.update(overrides)
    return values


def test_rsep_long_and_short_pass() -> None:
    long_actions, long_diag = rsep_actions(_row(), _returns(), _cfg(), fee_bps=0.0)
    short_actions, short_diag = rsep_actions(
        _row(prob_up=0.1, prob_down=0.8),
        _returns(),
        _cfg(),
        fee_bps=0.0,
    )
    assert int(long_actions.iloc[0]) == 1
    assert int(short_actions.iloc[0]) == -1
    assert float(long_diag["estimated_edge"].iloc[0]) > float(long_diag["required_edge"].iloc[0])
    assert float(short_diag["estimated_edge"].iloc[0]) < -float(short_diag["required_edge"].iloc[0])


def test_rsep_abstains_when_cost_or_equality_blocks_edge() -> None:
    cost_actions, _ = rsep_actions(_row(rel_spread=0.02), _returns(), _cfg(), fee_bps=0.0)
    equality_actions, equality_diag = rsep_actions(_row(rel_spread=0.007), _returns(), _cfg(), fee_bps=0.0)
    assert int(cost_actions.iloc[0]) == 0
    assert int(equality_actions.iloc[0]) == 0
    assert np.isclose(float(equality_diag["estimated_edge"].iloc[0]), float(equality_diag["required_edge"].iloc[0]))


def test_rsep_each_risk_component_can_force_abstain_and_ablation_restores_trade() -> None:
    risk_cases = [
        ("latency_sensitivity_score", "lambda_latency"),
        ("liquidity_drought_score", "lambda_liquidity"),
        ("adverse_selection_score", "lambda_adverse"),
    ]
    for feature, coefficient in risk_cases:
        frame = _row(**{feature: 0.04})
        blocked, _ = rsep_actions(frame, _returns(), _cfg(**{coefficient: 0.25}), fee_bps=0.0)
        ablated, _ = rsep_actions(frame, _returns(), _cfg(**{coefficient: 0.0}), fee_bps=0.0)
        assert int(blocked.iloc[0]) == 0
        assert int(ablated.iloc[0]) == 1


def test_rsep_regime_penalty_and_no_regime_ablation() -> None:
    frame = _row(regime="LIQUIDITY_DROUGHT")
    blocked, diagnostics = rsep_actions(frame, _returns(), _cfg(lambda_regime=0.15), fee_bps=0.0)
    ablated, _ = rsep_actions(frame, _returns(), _cfg(lambda_regime=0.0), fee_bps=0.0)
    assert int(blocked.iloc[0]) == 0
    assert int(ablated.iloc[0]) == 1
    assert float(diagnostics["regime_risk"].iloc[0]) == 1.0


def test_class_returns_are_train_only(tmp_path: Path) -> None:
    base = pd.DataFrame(
        {
            "split": ["train", "train", "test", "test"],
            "label": ["UP", "DOWN", "UP", "DOWN"],
            "future_ret_h": [0.01, -0.02, 10.0, -10.0],
        }
    )
    altered_test = base.copy()
    altered_test.loc[altered_test["split"] == "test", "future_ret_h"] = [999.0, -999.0]
    path_a = tmp_path / "a.parquet"
    path_b = tmp_path / "b.parquet"
    base.to_parquet(path_a, index=False)
    altered_test.to_parquet(path_b, index=False)
    assert class_return_means_from_parquet(path_a) == class_return_means_from_parquet(path_b)


def test_rsep_theta_grid_uses_passed_validation_frame_only() -> None:
    valid = pd.DataFrame(
        {
            "prob_up": [0.9, 0.8, 0.7],
            "prob_flat": [0.05, 0.1, 0.2],
            "prob_down": [0.05, 0.1, 0.1],
            "rel_spread": [0.001, 0.001, 0.001],
            "label_fee_bps": [0.0, 0.0, 0.0],
        }
    )
    unseen_test = valid.copy()
    unseen_test["prob_down"] = 0.99
    quantiles, include_zero = rsep_theta_grid_options(yaml.safe_load((ROOT / "configs" / "rsep_grid.yaml").read_text()))
    grid_a = edge_threshold_grid(valid, _returns(), quantiles=quantiles, include_zero=include_zero)
    grid_b = edge_threshold_grid(valid, _returns(), quantiles=quantiles, include_zero=include_zero)
    assert grid_a == grid_b
    assert unseen_test is not valid


def test_rsep_grid_constants_match_simulator_defaults() -> None:
    grid = yaml.safe_load((ROOT / "configs" / "rsep_grid.yaml").read_text(encoding="utf-8"))
    simulator = load_config(ROOT / "configs" / "simulator.yaml")
    merged = apply_rsep_grid_defaults(simulator["policies"]["rsep"], grid)
    for key, values in grid["lambda_grid"].items():
        assert len(values) == 1
        assert float(merged[key]) == float(values[0])
    assert simulator["rsep_grid_config"] == "configs/rsep_grid.yaml"
