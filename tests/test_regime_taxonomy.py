from __future__ import annotations

import pandas as pd

from regimes.rule_regime_labeler import apply_rule_regimes, fit_thresholds


def _frame() -> pd.DataFrame:
    rows = []
    for idx in range(200):
        rows.append(
            {
                "vol_score": -0.5 + idx * 0.01,
                "rel_spread": 0.0001 + idx * 0.000001,
                "total_depth_10": 10.0 + (idx % 20),
                "depth_drop_top10": -0.2 + (idx % 10) * 0.02,
                "spread_z_1m": -0.5 + (idx % 30) * 0.05,
                "momentum_score": -1.0 + idx * 0.01,
                "adverse_selection_score": -0.8 + idx * 0.01,
                "choppiness_score": (idx % 10) / 10.0,
                "liquidity_drought_score": -0.5 + (idx % 20) * 0.1,
                "depth_z_1m": -0.4 + (idx % 25) * 0.04,
            }
        )
    return pd.DataFrame(rows)


def test_thresholds_fit_on_train_prefix_only() -> None:
    frame = _frame()
    thresholds_prefix = fit_thresholds(frame, 0.5, {"low": 0.4, "mid": 0.5, "high": 0.7, "very_high": 0.8, "very_low": 0.1})
    mutated = frame.copy()
    mutated.loc[150:, "vol_score"] = 999.0
    thresholds_mutated = fit_thresholds(mutated, 0.5, {"low": 0.4, "mid": 0.5, "high": 0.7, "very_high": 0.8, "very_low": 0.1})
    assert thresholds_prefix["vol_q70"] == thresholds_mutated["vol_q70"]
    assert thresholds_prefix["stress_q60"] == thresholds_mutated["stress_q60"]


def test_priority_regime_not_overwritten_by_residual_assignment() -> None:
    frame = _frame()
    frame.loc[0, "depth_drop_top10"] = -10.0
    frame.loc[0, "spread_z_1m"] = 10.0
    thresholds = fit_thresholds(frame, 0.6, {"low": 0.4, "mid": 0.5, "high": 0.7, "very_high": 0.8, "very_low": 0.1})
    labeled = apply_rule_regimes(frame, thresholds)
    assert labeled.loc[0, "regime"] == "LIQUIDITY_DROUGHT"


def test_residual_taxonomy_reduces_unknown_on_structured_middle_region() -> None:
    frame = _frame()
    thresholds = fit_thresholds(frame, 0.6, {"low": 0.4, "mid": 0.5, "high": 0.7, "very_high": 0.8, "very_low": 0.1})
    labeled = apply_rule_regimes(frame, thresholds)
    assert "BALANCED_TRANSITION" in set(labeled["regime"]) or "MILD_LIQUIDITY_STRESS" in set(labeled["regime"])
    assert labeled["regime"].eq("UNKNOWN").mean() < 0.5

