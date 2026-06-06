from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "26_build_model_selection_audit.py"
    spec = importlib.util.spec_from_file_location("model_selection_audit", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_tuning(*, selected_split: str = "valid", tuning_split: str = "") -> pd.DataFrame:
    rows = []
    for threshold, net_pnl, selected in [(0.50, -10.0, False), (0.60, -5.0, True), (0.70, -7.0, False)]:
        row = {
            "model": "sgd_stage3",
            "policy": "naive_threshold",
            "split": selected_split if selected else "valid",
            "threshold": threshold,
            "selected": selected,
            "n_trade_days": 6,
            "n_trades": 1000,
            "gross_pnl": 1.0,
            "net_pnl": net_pnl,
            "total_cost": 2.0,
            "turnover": 1.0,
            "net_pnl_per_trade": net_pnl / 1000,
            "cost_survival": -1.0,
            "max_drawdown": net_pnl,
        }
        if tuning_split:
            row["direction"] = "btc_to_eth"
            row["tuning_split"] = tuning_split
            row["model"] = "asset_btc_to_eth_sgd"
        rows.append(row)
    return pd.DataFrame(rows)


def test_policy_ledger_marks_validation_selection_as_safe() -> None:
    module = _load_script_module()
    tuning = _synthetic_tuning()
    execution = pd.DataFrame(
        {
            "model": ["sgd_stage3"],
            "base_policy": ["naive_threshold"],
            "net_pnl": [-12.0],
            "gross_pnl": [3.0],
            "n_trades": [50],
            "net_pnl_per_trade": [-0.24],
        }
    )

    ledger = module.policy_rows_from_tuning(
        tuning,
        execution=execution,
        model_table=pd.DataFrame(),
        scope="unit",
        asset_or_direction="BTC-USDT",
        source_artifact="unit.csv",
    )

    assert len(ledger) == 1
    assert bool(ledger.loc[0, "test_used_for_selection"]) is False
    assert ledger.loc[0, "selection_audit_status"] == "PASS_VALIDATION_ONLY"
    assert ledger.loc[0, "selection_source"] == "valid"
    assert '"naive_threshold": 0.6' in ledger.loc[0, "selected_thresholds"]


def test_policy_ledger_flags_test_selected_row() -> None:
    module = _load_script_module()
    tuning = _synthetic_tuning(selected_split="test")

    ledger = module.policy_rows_from_tuning(
        tuning,
        execution=pd.DataFrame(),
        model_table=pd.DataFrame(),
        scope="unit",
        asset_or_direction="BTC-USDT",
        source_artifact="unit.csv",
    )

    assert bool(ledger.loc[0, "test_used_for_selection"]) is True
    assert ledger.loc[0, "selection_audit_status"] == "FAIL_TEST_SELECTION"
    assert ledger.loc[0, "selection_source"] == "test"


def test_candidate_counts_match_threshold_grid_and_status() -> None:
    module = _load_script_module()
    tuning = _synthetic_tuning()

    counts = module.candidate_counts_from_tuning(
        tuning,
        scope="unit",
        asset_or_direction="BTC-USDT",
        source_artifact="unit.csv",
    )

    assert int(counts.loc[0, "n_candidates"]) == 3
    assert int(counts.loc[0, "n_selected"]) == 1
    assert counts.loc[0, "selection_sources"] == "valid"
    assert counts.loc[0, "selection_audit_status"] == "PASS_VALIDATION_ONLY"


def test_asset_heldout_source_valid_selection_is_not_target_tuning() -> None:
    module = _load_script_module()
    tuning = _synthetic_tuning(tuning_split="source_valid")

    ledger = module.policy_rows_from_tuning(
        tuning,
        execution=pd.DataFrame(),
        model_table=pd.DataFrame(),
        scope="asset_heldout_stage3",
        asset_or_direction="BTC<->ETH",
        source_artifact="unit_asset.csv",
    )

    assert ledger.loc[0, "selection_source"] == "source_valid"
    assert bool(ledger.loc[0, "test_used_for_selection"]) is False
    assert "target test not used" in ledger.loc[0, "notes"]


def test_overfitting_diagnostic_does_not_fabricate_p_values() -> None:
    module = _load_script_module()
    candidate_counts = pd.DataFrame({"n_candidates": [3, 9], "model": ["a", "b"]})

    diagnostic = module.overfitting_diagnostic_summary(candidate_counts, has_per_candidate_daily_returns=False)

    assert diagnostic.loc[0, "status"] == "INFEASIBLE_FROM_CURRENT_SAVED_ARTIFACTS"
    assert "per-candidate per-period returns" in diagnostic.loc[0, "reason"]
    assert "p_value" not in set(diagnostic.columns)
