from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "16_build_paper_draft_pack.py"
    spec = importlib.util.spec_from_file_location("paper_draft_pack_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_stage3_11_inputs(root: Path) -> None:
    tables = root / "outputs" / "tables"
    paper = root / "outputs" / "paper_assets"
    audits = root / "audits"
    configs = root / "configs"
    tables.mkdir(parents=True)
    paper.mkdir(parents=True)
    audits.mkdir(parents=True)
    configs.mkdir(parents=True)

    pd.DataFrame(
        [
            {"criterion_id": "C01", "criterion": "Forecasting performance varies by regime", "status": "PASS"},
            {"criterion_id": "C02", "criterion": "Forecast-to-execution degradation", "status": "PASS"},
            {"criterion_id": "C07", "criterion": "Results hold across both BTC and ETH", "status": "BLOCKED"},
            {"criterion_id": "C09", "criterion": "Bootstrap confidence intervals support the main claim", "status": "PARTIAL"},
        ]
    ).to_csv(tables / "table_acceptance_bar_stage3.csv", index=False)
    pd.DataFrame(
        [
            {
                "claim": "Benchmark BTC L2 full-year cho regime-aware forecast-to-execution",
                "status": "SUPPORTED",
                "evidence_artifact": "outputs/tables/table_model_forecasting_execution_comparison_stage3.csv",
                "recommended_paper_wording": "Chung toi de xuat benchmark BTC L2 full-year.",
            },
            {
                "claim": "Ket qua generalize qua asset BTC va ETH",
                "status": "BLOCKED",
                "evidence_artifact": "",
                "recommended_paper_wording": "Gioi han hien tai la BTC-only; cross-asset la extension.",
            },
            {
                "claim": "He thong san sang live trading hoac co profitability",
                "status": "NOT_CLAIMED",
                "evidence_artifact": "",
                "recommended_paper_wording": "Khong claim live trading hoac profit.",
            },
        ]
    ).to_csv(tables / "table_claim_support_matrix_stage3.csv", index=False)
    pd.DataFrame(
        [
            {
                "model_label": "sgd_stage3",
                "recommended_role": "main tabular baseline",
                "accuracy": 0.558924,
                "macro_f1": 0.465194,
                "mcc": 0.236334,
                "balanced_accuracy": 0.463737,
                "test_rows": 33550262,
                "best_policy": "RSEP-full",
                "best_policy_net_pnl": -4437.492425,
                "rsep_test_net_pnl": -4437.492425,
                "bootstrap_ci_low": 59.67646,
                "bootstrap_ci_high": 77.229226,
                "caveat": "Baseline don gian.",
            },
            {
                "model_label": "tcn_gpu_stage3_stride1",
                "recommended_role": "main temporal fairness baseline",
                "accuracy": 0.528107,
                "macro_f1": 0.468775,
                "mcc": 0.227389,
                "balanced_accuracy": 0.469091,
                "test_rows": 33543827,
                "best_policy": "cost_aware_threshold",
                "best_policy_net_pnl": -787.997967,
                "rsep_test_net_pnl": -814.166889,
                "bootstrap_ci_low": -4.460466,
                "bootstrap_ci_high": 4.449435,
                "caveat": "RSEP khong thang cost-aware.",
            },
        ]
    ).to_csv(tables / "table_final_model_selection_stage3.csv", index=False)
    for name in [
        "table_model_forecasting_execution_comparison_stage3.csv",
        "table_model_stress_comparison_stage3.csv",
        "table_rsep_bootstrap_tuned_stage3.csv",
    ]:
        pd.DataFrame([{"ok": 1}]).to_csv(tables / name, index=False)
    (paper / "result_narrative_stage3_11_vi.md").write_text(
        "sgd_stage3: macro-F1=0.4652, MCC=0.2363. "
        "tcn_gpu_stage3_stride1: macro-F1=0.4688, MCC=0.2274.\n",
        encoding="utf-8",
    )
    (audits / "audit_stage3_11_icdm_evidence_hardening.md").write_text(
        "sgd_stage3 macro-F1 `0.4652`, MCC `0.2363`. "
        "tcn_gpu_stage3_stride1 macro-F1 `0.4688`, MCC `0.2274`.\n",
        encoding="utf-8",
    )
    (root / "MoTa.md").write_text(
        "TCN stride-1 co macro-F1 0.4688 va SGD macro-F1 0.4652.\n",
        encoding="utf-8",
    )
    (root / "ThucNghiem.md").write_text(
        "sgd_stage3 macro-F1=0.4652, MCC=0.2363. "
        "tcn_gpu_stage3_stride1 macro-F1=0.4688, MCC=0.2274.\n",
        encoding="utf-8",
    )
    (configs / "simulator_stage3_tcn_stride1_gpu.yaml").write_text("project_root: ..\n", encoding="utf-8")


def test_paper_draft_pack_builds_claim_map_and_keeps_predictions(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    predictions = root / "data" / "predictions"
    predictions.mkdir(parents=True)
    (predictions / "predictions.parquet").write_bytes(b"keep-me")
    _write_stage3_11_inputs(root)

    paths = module.build_paper_draft_pack(
        root=root,
        stage="stage_3_full_scale",
        models=["sgd_stage3", "tcn_gpu_stage3_stride1"],
        run_id="test_stage3_12",
    )

    claim_map = pd.read_csv(paths.claim_to_evidence)
    number_checks = pd.read_csv(paths.number_consistency)
    limitations = paths.limitation_wording.read_text(encoding="utf-8")

    assert {"SUPPORTED", "BLOCKED", "NOT_CLAIMED"}.issubset(set(claim_map["status"]))
    assert "BLOCKED" in set(claim_map.loc[claim_map["claim"].str.contains("BTC va ETH", regex=False), "status"])
    assert not number_checks.empty
    assert "FAIL" not in set(number_checks["status"])
    assert "ThucNghiem.md" in set(number_checks["target_artifact"])
    assert "SOTA trading strategy" in limitations
    assert paths.outline.stat().st_size > 0
    assert paths.audit.stat().st_size > 0
    assert (predictions / "predictions.parquet").read_bytes() == b"keep-me"


def test_number_consistency_detects_explicit_mismatch(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    _write_stage3_11_inputs(root)
    final_models = pd.read_csv(root / "outputs" / "tables" / "table_final_model_selection_stage3.csv")
    mismatch_doc = root / "bad_narrative.md"
    mismatch_doc.write_text("sgd_stage3 macro-F1=0.1111 va MCC=0.2363.\n", encoding="utf-8")

    checks = module.build_number_consistency_table(
        root=root,
        final_models=final_models,
        models=["sgd_stage3"],
        target_docs=[mismatch_doc],
        source_artifact="outputs/tables/table_final_model_selection_stage3.csv",
    )

    mismatch_rows = checks.loc[(checks["metric_name"] == "macro_f1") & (checks["status"] == "FAIL")]
    assert not mismatch_rows.empty


def test_paper_draft_pack_scans_thucnghiem_for_number_mismatch(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    _write_stage3_11_inputs(root)
    (root / "ThucNghiem.md").write_text("sgd_stage3 macro-F1=0.1111.\n", encoding="utf-8")

    paths = module.build_paper_draft_pack(
        root=root,
        stage="stage_3_full_scale",
        models=["sgd_stage3", "tcn_gpu_stage3_stride1"],
        run_id="test_stage3_12_bad_thucnghiem",
    )
    checks = pd.read_csv(paths.number_consistency)
    failed = checks.loc[
        checks["target_artifact"].eq("ThucNghiem.md")
        & checks["model_label"].eq("sgd_stage3")
        & checks["metric_name"].eq("macro_f1")
        & checks["status"].eq("FAIL")
    ]
    assert not failed.empty
