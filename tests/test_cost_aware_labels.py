from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from features.returns_labels import add_cost_aware_labels
from utils.config import load_config


def _two_row_frame(future_mid: float, *, rel_spread: float = 0.001, split: str | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "mid_price": [100.0, future_mid],
            "rel_spread": [rel_spread, rel_spread],
        }
    )
    if split is not None:
        frame["split"] = [split, split]
    return frame


def test_cost_aware_label_assigns_up_down_and_flat() -> None:
    kwargs = {"horizon_events": 1, "fee_bps": 1.0, "slippage_buffer_multiplier": 0.5}

    up = add_cost_aware_labels(_two_row_frame(100.17), **kwargs)
    assert up.loc[0, "label"] == "UP"

    down = add_cost_aware_labels(_two_row_frame(99.83), **kwargs)
    assert down.loc[0, "label"] == "DOWN"

    flat = add_cost_aware_labels(_two_row_frame(100.15), **kwargs)
    assert flat.loc[0, "label"] == "FLAT"


def test_cost_aware_label_equality_boundary_is_flat() -> None:
    labeled = add_cost_aware_labels(
        _two_row_frame(101.0, rel_spread=0.01),
        horizon_events=1,
        fee_bps=0.0,
        slippage_buffer_multiplier=0.0,
    )
    assert np.isclose(labeled.loc[0, "future_ret_h"], labeled.loc[0, "cost_threshold_t"])
    assert labeled.loc[0, "label"] == "FLAT"


def test_cost_threshold_matches_benchmark_formula() -> None:
    fee_bps = 1.0
    kappa = 0.5
    rel_spread = 0.001
    labeled = add_cost_aware_labels(
        _two_row_frame(100.15, rel_spread=rel_spread),
        horizon_events=1,
        fee_bps=fee_bps,
        slippage_buffer_multiplier=kappa,
    )
    expected_tau = (1.0 + kappa) * rel_spread + fee_bps / 10000.0
    assert np.isclose(labeled.loc[0, "cost_threshold_t"], expected_tau)


def test_split_column_does_not_change_cost_threshold_or_label() -> None:
    kwargs = {"horizon_events": 1, "fee_bps": 1.0, "slippage_buffer_multiplier": 0.5}
    valid = add_cost_aware_labels(_two_row_frame(100.17, split="valid"), **kwargs)
    test = add_cost_aware_labels(_two_row_frame(100.17, split="test"), **kwargs)

    assert valid.loc[0, "cost_threshold_t"] == test.loc[0, "cost_threshold_t"]
    assert valid.loc[0, "label"] == test.loc[0, "label"]


def test_benchmark_default_config_matches_operational_label_config() -> None:
    root = Path(__file__).resolve().parents[1]
    benchmark_path = root / "configs" / "benchmark_default.yaml"
    labels_path = root / "configs" / "labels.yaml"

    benchmark_raw = yaml.safe_load(benchmark_path.read_text(encoding="utf-8"))
    labels = load_config(labels_path)
    benchmark_label = benchmark_raw["benchmark_label"]

    assert labels["label_horizon_events"] == benchmark_label["horizon_events"]
    assert labels["fee_bps"] == benchmark_label["fee_bps"]
    assert labels["slippage_buffer_multiplier"] == benchmark_label["slippage_buffer_multiplier"]
    assert labels["eps"] == benchmark_label["eps"]
