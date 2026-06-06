from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from simulator.market_order_sim import ExecutionConfig
from simulator.stress_engine import apply_stress
from utils.config import load_config
from utils.stress_grid import load_stress_grid, normalize_stress_grid


def _load_asset_execution_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "20_run_asset_heldout_execution.py"
    spec = importlib.util.spec_from_file_location("asset_heldout_execution", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_stress_grid_levels_match_benchmark_config() -> None:
    config = load_config(Path(__file__).resolve().parents[1] / "configs" / "simulator.yaml")
    grid = load_stress_grid(config)

    assert grid["fee_bps"] == [0.0, 1.0, 2.0, 5.0, 10.0]
    assert grid["latency_events"] == [0, 1, 5, 10]
    assert grid["spread_multiplier"] == [1.0, 1.5, 2.0]
    assert grid["depth_multiplier"] == [1.0, 0.75, 0.5]


def test_inline_stress_grid_fallback_and_axis_validation() -> None:
    inline = normalize_stress_grid({"fee_bps": [0, 1], "latency_events": [0.0, 2.0]})
    assert inline == {"fee_bps": [0.0, 1.0], "latency_events": [0, 2]}

    try:
        normalize_stress_grid({"unknown_axis": [1.0]})
    except ValueError as exc:
        assert "unknown_axis" in str(exc)
    else:
        raise AssertionError("Unknown stress axis should fail.")


def test_apply_stress_changes_only_requested_axis() -> None:
    base = ExecutionConfig(
        latency_events=1,
        fee_bps=1.0,
        spread_multiplier=1.0,
        depth_multiplier=1.0,
        trade_notional=1000.0,
    )
    stressed = apply_stress(base, fee_bps=10.0)

    assert stressed.fee_bps == 10.0
    assert stressed.latency_events == base.latency_events
    assert stressed.spread_multiplier == base.spread_multiplier
    assert stressed.depth_multiplier == base.depth_multiplier
    assert stressed.trade_notional == base.trade_notional


def test_asset_heldout_stress_uses_fixed_actions_and_threshold(monkeypatch) -> None:
    module = _load_asset_execution_module()
    target = pd.DataFrame(
        {
            "event_time": pd.date_range("2024-01-01", periods=4, freq="s", tz="UTC"),
            "label_horizon_events": np.full(4, 1),
        }
    )
    base_actions = pd.Series([1, 0, -1, 0])
    action_calls: list[dict[str, object]] = []
    replay_configs: list[ExecutionConfig] = []

    def fake_actions_for_selected_policy(frame, class_returns, simulator_cfg, policy, threshold, *, rsep_cfg=None):
        action_calls.append({"policy": policy, "threshold": threshold, "fee_bps": simulator_cfg.fee_bps})
        return base_actions.copy()

    def fake_simulate_signals(frame, actions, config, hold_events):
        replay_configs.append(config)
        pd.testing.assert_series_equal(actions.reset_index(drop=True), base_actions, check_names=False)
        return pd.DataFrame(
            {
                "event_time": [pd.Timestamp("2024-01-01T00:00:00Z")],
                "regime": ["CALM_LIQUID"],
                "gross_pnl": [1.0],
                "net_pnl": [-float(config.fee_bps)],
                "total_cost": [float(config.fee_bps)],
                "quantity": [1.0],
            }
        )

    monkeypatch.setattr(module, "actions_for_selected_policy", fake_actions_for_selected_policy)
    monkeypatch.setattr(module, "simulate_signals", fake_simulate_signals)

    stress, _ = module.run_rsep_stress(
        target,
        {"UP": 0.1, "FLAT": 0.0, "DOWN": -0.1},
        ExecutionConfig(fee_bps=1.0, latency_events=1),
        {"lambda_latency": 0.25},
        0.123,
        {"fee_bps": [0.0, 10.0], "latency_events": [0]},
        "btc_to_eth",
        "BTC-USDT",
        "ETH-USDT",
    )

    assert len(action_calls) == 1
    assert action_calls[0]["threshold"] == 0.123
    assert action_calls[0]["fee_bps"] == 1.0
    assert [config.fee_bps for config in replay_configs[:2]] == [0.0, 10.0]
    assert set(stress["stress_axis"]) == {"fee_bps", "latency_events"}


def test_stress_runner_source_does_not_import_training_or_tuning() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "07_run_stress_grid.py"
    source = script.read_text(encoding="utf-8")

    forbidden = ["train_streaming_sgd", "train_tabular_model", "tune_policy("]
    assert all(token not in source for token in forbidden)
    assert "read_filtered_frame" in source
    assert "simulate_signals" in source
