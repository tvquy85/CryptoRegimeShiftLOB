from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "15_build_icdm_evidence_pack.py"
    spec = importlib.util.spec_from_file_location("icdm_evidence_pack_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_minimal_stage3_tables(root: Path) -> None:
    tables = root / "outputs" / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "model_label": "sgd_stage3",
                "accuracy": 0.5589,
                "macro_f1": 0.4652,
                "mcc": 0.2363,
                "balanced_accuracy": 0.4637,
                "test_rows": 1000,
                "best_policy": "RSEP-full",
                "best_policy_net_pnl": -100.0,
                "rsep_test_gross_pnl": 50.0,
                "rsep_test_net_pnl": -100.0,
                "bootstrap_mean_diff_vs_cost_aware": 2.0,
                "bootstrap_ci_low": 0.3,
                "bootstrap_ci_high": 4.0,
            },
            {
                "model_label": "tcn_gpu_stage3_stride1",
                "accuracy": 0.5281,
                "macro_f1": 0.4688,
                "mcc": 0.2274,
                "balanced_accuracy": 0.4691,
                "test_rows": 1000,
                "best_policy": "cost_aware_threshold",
                "best_policy_net_pnl": -80.0,
                "rsep_test_gross_pnl": 40.0,
                "rsep_test_net_pnl": -90.0,
                "bootstrap_mean_diff_vs_cost_aware": -0.4,
                "bootstrap_ci_low": -4.0,
                "bootstrap_ci_high": 4.5,
            },
        ]
    ).to_csv(tables / "table_model_forecasting_execution_comparison_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"regime": "BALANCED_TRANSITION", "macro_f1": 0.50},
            {"regime": "MILD_LIQUIDITY_STRESS", "macro_f1": 0.46},
            {"regime": "LIQUIDITY_DROUGHT", "macro_f1": 0.38},
        ]
    ).to_csv(tables / "table_forecasting_by_regime_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"policy": "naive_threshold", "gross_pnl": 5.0, "net_pnl": -20.0},
            {"policy": "cost_aware_threshold", "gross_pnl": 4.0, "net_pnl": -10.0},
        ]
    ).to_csv(tables / "table_forecast_to_execution_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model_label": "sgd_stage3", "policy": "naive_threshold", "regime": "A", "net_pnl": -20.0},
            {"model_label": "sgd_stage3", "policy": "naive_threshold", "regime": "B", "net_pnl": 5.0},
            {"model_label": "sgd_stage3", "policy": "RSEP-full", "regime": "A", "net_pnl": -10.0},
            {"model_label": "sgd_stage3", "policy": "RSEP-full", "regime": "B", "net_pnl": 2.0},
            {"model_label": "tcn_gpu_stage3_stride1", "policy": "cost_aware_threshold", "regime": "A", "net_pnl": -8.0},
            {"model_label": "tcn_gpu_stage3_stride1", "policy": "RSEP-full", "regime": "A", "net_pnl": -9.0},
        ]
    ).to_csv(tables / "table_forecast_to_execution_tuned_by_regime_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model_label": "sgd_stage3", "mean_diff": 2.0, "ci_low": 0.3, "ci_high": 4.0, "n_days": 65, "n_bootstrap": 1000},
            {
                "model_label": "tcn_gpu_stage3_stride1",
                "mean_diff": -0.4,
                "ci_low": -4.0,
                "ci_high": 4.5,
                "n_days": 65,
                "n_bootstrap": 1000,
            },
        ]
    ).to_csv(tables / "table_rsep_bootstrap_tuned_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model_label": "sgd_stage3", "stress_axis": "fee_bps", "fee_bps": 0.0, "net_pnl": 10.0},
            {"model_label": "sgd_stage3", "stress_axis": "fee_bps", "fee_bps": 10.0, "net_pnl": -30.0},
            {"model_label": "sgd_stage3", "stress_axis": "latency_events", "latency_events": 0, "net_pnl": -5.0},
            {"model_label": "sgd_stage3", "stress_axis": "spread_multiplier", "spread_multiplier": 1.0, "net_pnl": -5.0},
            {"model_label": "sgd_stage3", "stress_axis": "depth_multiplier", "depth_multiplier": 1.0, "net_pnl": -5.0},
        ]
    ).to_csv(tables / "table_model_stress_comparison_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model_label": "sgd_stage3", "stress_axis": "fee_bps", "robustness_auc": -10.0},
            {"model_label": "sgd_stage3", "stress_axis": "latency_events", "robustness_auc": -5.0},
            {"model_label": "sgd_stage3", "stress_axis": "spread_multiplier", "robustness_auc": -6.0},
        ]
    ).to_csv(tables / "table_model_robustness_comparison_stage3.csv", index=False)


def test_icdm_evidence_pack_builds_reviewer_tables_without_touching_predictions(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    predictions = root / "data" / "predictions"
    predictions.mkdir(parents=True)
    (predictions / "predictions.parquet").write_bytes(b"sgd-full-year")
    (predictions / "predictions_stage3_tcn_gpu_stride1_execution_ready.parquet").write_bytes(b"tcn-stride1")
    _write_minimal_stage3_tables(root)

    paths = module.build_icdm_evidence_pack(
        root=root,
        stage="stage_3_full_scale",
        models=["sgd_stage3", "tcn_gpu_stage3_stride1"],
        run_id="test_stage3_11",
    )

    acceptance = pd.read_csv(paths.acceptance_bar)
    claims = pd.read_csv(paths.claim_support)
    final_models = pd.read_csv(paths.final_model_selection)

    assert len(acceptance) == 9
    assert {"PASS", "PARTIAL", "BLOCKED"}.issubset(set(acceptance["status"]))
    eth_rows = acceptance.loc[acceptance["criterion"].str.contains("BTC and ETH", regex=False)]
    assert not eth_rows.empty
    assert set(eth_rows["status"]) == {"BLOCKED"}
    assert "BLOCKED" in set(claims.loc[claims["claim"].str.contains("Cross-asset", regex=False), "status"])
    assert "NOT_CLAIMED" in set(claims.loc[claims["claim"].str.contains("live trading", case=False), "status"])
    assert set(final_models["model_label"]) == {"sgd_stage3", "tcn_gpu_stage3_stride1"}
    assert paths.paper_acceptance_bar.stat().st_size > 0
    assert paths.paper_claim_support.stat().st_size > 0
    assert paths.narrative.stat().st_size > 0
    assert paths.audit.stat().st_size > 0
    assert (predictions / "predictions.parquet").read_bytes() == b"sgd-full-year"
    assert (predictions / "predictions_stage3_tcn_gpu_stride1_execution_ready.parquet").read_bytes() == b"tcn-stride1"


def test_icdm_evidence_pack_marks_cross_asset_supported_when_execution_exists(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    _write_minimal_stage3_tables(root)
    tables = root / "outputs" / "tables"
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "accuracy": 0.43, "macro_f1": 0.43},
            {"direction": "eth_to_btc", "accuracy": 0.54, "macro_f1": 0.48},
        ]
    ).to_csv(tables / "table_asset_heldout_forecasting_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "policy": "RSEP-full", "net_pnl": -10.0},
            {"direction": "eth_to_btc", "policy": "RSEP-full", "net_pnl": -20.0},
        ]
    ).to_csv(tables / "table_asset_heldout_execution_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "mean_diff": 1.0, "ci_low": -1.0, "ci_high": 3.0, "n_days": 58, "n_bootstrap": 1000},
            {"direction": "eth_to_btc", "mean_diff": 2.0, "ci_low": 0.5, "ci_high": 4.0, "n_days": 65, "n_bootstrap": 1000},
        ]
    ).to_csv(tables / "table_asset_heldout_rsep_bootstrap_stage3.csv", index=False)

    paths = module.build_icdm_evidence_pack(root=root, stage="stage_3_full_scale", run_id="test_cross_asset_execution")
    acceptance = pd.read_csv(paths.acceptance_bar)
    claims = pd.read_csv(paths.claim_support)

    cross_asset = acceptance.loc[acceptance["criterion"].str.contains("Asset-held-out", regex=False)]
    assert not cross_asset.empty
    assert set(cross_asset["status"]) == {"PASS"}
    supported_claims = claims.loc[claims["claim"].str.contains("Cross-asset", regex=False)]
    assert set(supported_claims["status"]) == {"SUPPORTED"}
    narrative = paths.narrative.read_text(encoding="utf-8")
    audit = paths.audit.read_text(encoding="utf-8")
    assert "Cross-asset BTC<->ETH da duoc evaluate" in narrative
    assert "BTC-only; ETH/asset-held-out" not in narrative
    assert "ETH/asset-held-out phai de la BLOCKED" not in narrative
    assert "cross-asset BTC<->ETH da co forecasting" in audit
    assert "ETH/asset-held-out hien bi BLOCKED" not in audit
