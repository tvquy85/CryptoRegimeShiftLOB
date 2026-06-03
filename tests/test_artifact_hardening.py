from __future__ import annotations

from pathlib import Path

import pandas as pd

from policies.rsep_variants import build_rsep_variants
from reports.result_pack import assemble_result_pack
from utils.artifacts import (
    artifact_namespace,
    is_stage2,
    model_stage_table_path,
    namespaced_dir,
    safe_slug,
    stage_config_path,
    stage_namespace_slug,
    stage_table_path,
    stage_slug,
)


def test_stage_artifact_names_are_canonical() -> None:
    assert stage_slug("stage_3_full_scale") == "stage3"
    assert stage_slug("stage_2_medium_scale") == "stage2"
    assert safe_slug("SGD Stage3") == "sgd_stage3"
    assert stage_table_path(Path("tables"), "table_policy_tuning", "stage_3_full_scale").as_posix() == "tables/table_policy_tuning_stage3.csv"
    assert not is_stage2("stage_3_full_scale")
    assert is_stage2("stage_2_medium_scale")


def test_artifact_namespace_keeps_eth_stage3_separate() -> None:
    config = {"artifact_namespace": "eth_usdt_stage3"}
    assert artifact_namespace(config) == "eth_usdt_stage3"
    assert stage_namespace_slug("stage_3_full_scale", config) == "stage3_eth_usdt"
    assert stage_table_path(Path("tables"), "table_data_audit", "stage_3_full_scale", namespace=config).as_posix() == (
        "tables/table_data_audit_stage3_eth_usdt.csv"
    )
    assert model_stage_table_path(Path("tables"), "table_forecasting_overall", "stage_3_full_scale", "sgd_eth_stage3", namespace=config).as_posix() == (
        "tables/table_forecasting_overall_stage3_eth_usdt_sgd_eth_stage3.csv"
    )
    assert stage_config_path(Path("configs"), "tuned_policy", "stage_3_full_scale", namespace=config).as_posix() == (
        "configs/tuned_policy_stage3_eth_usdt.yaml"
    )
    assert namespaced_dir(Path("parts"), config).as_posix() == "parts/eth_usdt_stage3"


def test_result_pack_prefers_stage_specific_tables(tmp_path: Path) -> None:
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame([{"source": "legacy"}]).to_csv(tables / "table_forecast_to_execution_tuned_stage2.csv", index=False)
    pd.DataFrame([{"source": "stage3"}]).to_csv(tables / "table_forecast_to_execution_tuned_stage3.csv", index=False)
    pd.DataFrame([{"source": "stage3_model"}]).to_csv(tables / "table_model_comparison_stage3.csv", index=False)
    pd.DataFrame([{"source": "stage3_comparative"}]).to_csv(
        tables / "table_model_stress_comparison_stage3.csv",
        index=False,
    )

    artifacts = assemble_result_pack(tmp_path, stage="stage_3_full_scale")

    forecast_to_execution = pd.read_csv(artifacts["table_4_forecast_to_execution"])
    model_comparison = pd.read_csv(artifacts["table_7_model_comparison"])
    model_stress = pd.read_csv(artifacts["table_9_model_stress_comparison"])
    assert forecast_to_execution["source"].iloc[0] == "stage3"
    assert model_comparison["source"].iloc[0] == "stage3_model"
    assert model_stress["source"].iloc[0] == "stage3_comparative"
    assert artifacts["table_7_model_comparison"].name == "table_7_model_comparison.csv"


def test_rsep_no_cost_gate_is_explicit_opt_in() -> None:
    base = {"theta_edge": 0.0}
    default_variants = build_rsep_variants(base)
    opt_in_variants = build_rsep_variants(base, include_no_cost_gate=True)
    assert "RSEP-no-cost-gate" not in default_variants
    assert "RSEP-no-cost-gate" in opt_in_variants
