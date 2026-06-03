from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "22_build_ieee_draft_skeleton.py"
    spec = importlib.util.spec_from_file_location("ieee_draft_skeleton_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_stage3_14_inputs(root: Path) -> None:
    paper = root / "outputs" / "paper_assets"
    tables = root / "outputs" / "tables"
    paper.mkdir(parents=True)
    tables.mkdir(parents=True)
    pd.DataFrame(
        [
            {"criterion_id": "C01", "criterion": "Forecasting by regime", "status": "PASS"},
            {"criterion_id": "C08", "criterion": "Asset-held-out", "status": "PASS"},
            {"criterion_id": "C09", "criterion": "Bootstrap", "status": "PARTIAL"},
        ]
    ).to_csv(paper / "table_11_acceptance_bar.csv", index=False)
    pd.DataFrame(
        [
            {
                "claim": "Cross-asset BTC<->ETH forecasting/execution duoc evaluate",
                "status": "SUPPORTED",
                "evidence_artifact": "outputs/tables/table_asset_heldout_execution_stage3.csv",
                "allowed_wording": "Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution; khong claim policy tao loi nhuan pho quat.",
                "banned_wording": "Khong viet policy tao loi nhuan pho quat qua asset.",
                "paper_section": "Forecast-to-execution analysis",
            },
            {
                "claim": "RSEP la policy universal winner",
                "status": "NOT_SUPPORTED",
                "evidence_artifact": "outputs/tables/table_rsep_bootstrap_tuned_stage3.csv",
                "allowed_wording": "RSEP la selective execution baseline/diagnostic, khong phai policy luon chien thang.",
                "banned_wording": "Khong viet RSEP luon chien thang.",
                "paper_section": "Robust selective execution",
            },
        ]
    ).to_csv(paper / "table_13_claim_to_evidence_map.csv", index=False)
    pd.DataFrame(
        [
            {
                "model_label": "sgd_stage3",
                "recommended_role": "main tabular baseline",
                "accuracy": 0.5589,
                "macro_f1": 0.4652,
                "mcc": 0.2363,
                "caveat": "Baseline don gian.",
            },
            {
                "model_label": "tcn_gpu_stage3_stride1",
                "recommended_role": "temporal fairness baseline",
                "accuracy": 0.5281,
                "macro_f1": 0.4688,
                "mcc": 0.2274,
                "caveat": "Execution mixed.",
            },
        ]
    ).to_csv(tables / "table_final_model_selection_stage3.csv", index=False)
    pd.DataFrame(
        [
            {
                "direction": "btc_to_eth",
                "macro_f1": 0.4325,
                "mcc": 0.1486,
                "rsep_net_pnl": -74466.38,
                "cost_aware_net_pnl": -287991.44,
                "rsep_vs_cost_aware_ci_low": 3314.02,
                "rsep_vs_cost_aware_ci_high": 4048.20,
            },
            {
                "direction": "eth_to_btc",
                "macro_f1": 0.4839,
                "mcc": 0.2424,
                "rsep_net_pnl": -1144.75,
                "cost_aware_net_pnl": -3697.46,
                "rsep_vs_cost_aware_ci_low": 34.08,
                "rsep_vs_cost_aware_ci_high": 44.53,
            },
        ]
    ).to_csv(paper / "table_16_cross_asset_forecasting_execution.csv", index=False)
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "mean_diff": 3681.47, "ci_low": 3314.02, "ci_high": 4048.20},
            {"direction": "eth_to_btc", "mean_diff": 39.27, "ci_low": 34.08, "ci_high": 44.53},
        ]
    ).to_csv(paper / "table_17_cross_asset_bootstrap.csv", index=False)
    pd.DataFrame(
        [{"check_id": "N0001", "model_label": "sgd_stage3", "metric_name": "macro_f1", "status": "PASS"}]
    ).to_csv(paper / "table_14_number_consistency_check.csv", index=False)


def test_ieee_draft_skeleton_builds_section_map_without_prediction_mutation(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    predictions = root / "data" / "predictions"
    predictions.mkdir(parents=True)
    (predictions / "predictions.parquet").write_bytes(b"keep-sgd")
    _write_stage3_14_inputs(root)

    paths = module.build_ieee_draft_skeleton(root=root, run_id="test_stage3_14")
    skeleton = paths.skeleton.read_text(encoding="utf-8")
    audit = paths.audit.read_text(encoding="utf-8")

    assert "## 1. Introduction" in skeleton
    assert "## 8. Cross-Asset BTC<->ETH" in skeleton
    assert "Cross-asset BTC<->ETH da duoc evaluate" in skeleton
    assert "outputs/paper_assets/table_16_cross_asset_forecasting_execution.csv" in skeleton
    assert "live-trading-ready" not in skeleton.lower()
    assert "universal profitable policy" not in skeleton.lower()
    assert "profitable cross-asset trading" not in skeleton.lower()
    assert "PASS" in audit
    assert (predictions / "predictions.parquet").read_bytes() == b"keep-sgd"
