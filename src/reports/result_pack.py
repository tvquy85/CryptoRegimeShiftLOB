from __future__ import annotations

from pathlib import Path

from reports.make_tables import build_dataset_stats, copy_or_empty_csv, copy_symbol_rows
from utils.artifacts import stage_table_path


def assemble_result_pack(
    project_root: Path,
    *,
    stage: str | None = None,
    paper_assets_dir: Path | None = None,
    tables_dir: Path | None = None,
) -> dict[str, Path]:
    paper = paper_assets_dir or project_root / "outputs" / "paper_assets"
    tables = tables_dir or project_root / "outputs" / "tables"
    paper.mkdir(parents=True, exist_ok=True)
    dataset_stats = build_dataset_stats(
        _dataset_audit_sources(project_root, tables),
        tables / "table_dataset_stats_stage3_by_asset.csv",
    )
    artifacts = {
        "table_1_dataset_stats": copy_or_empty_csv(
            dataset_stats,
            paper / "table_1_dataset_stats.csv",
        ),
        "table_1b_eth_dataset_stats": copy_symbol_rows(
            dataset_stats,
            paper / "table_1b_eth_dataset_stats.csv",
            "ETH-USDT",
        ),
        "table_2_regime_distribution": copy_or_empty_csv(
            tables / "table_regime_counts_by_symbol_month.csv",
            paper / "table_2_regime_distribution.csv",
        ),
        "table_3_forecasting_by_regime": copy_or_empty_csv(
            _prefer_existing(stage_table_path(tables, "table_forecasting_by_regime", stage), tables / "table_forecasting_by_regime.csv"),
            paper / "table_3_forecasting_by_regime.csv",
        ),
        "table_4_forecast_to_execution": copy_or_empty_csv(
            _prefer_first_existing(
                [
                    stage_table_path(tables, "table_forecast_to_execution_tuned", stage),
                    tables / "table_forecast_to_execution_tuned_stage2.csv",
                    tables / "table_forecast_to_execution.csv",
                ]
            ),
            paper / "table_4_forecast_to_execution.csv",
        ),
        "table_5_robust_policy": copy_or_empty_csv(
            _prefer_existing(stage_table_path(tables, "table_robust_policy", stage), tables / "table_robust_policy.csv"),
            paper / "table_5_robust_policy.csv",
        ),
        "table_6_ablation": copy_or_empty_csv(
            _prefer_existing(stage_table_path(tables, "table_rsep_ablation", stage), tables / "table_rsep_ablation.csv"),
            paper / "table_6_ablation.csv",
        ),
    }
    comparison = _prefer_first_existing(
        [
            stage_table_path(tables, "table_model_comparison", stage),
            tables / "table_model_comparison_stage2_5.csv",
        ]
    )
    if comparison.exists():
        artifacts["table_7_model_comparison"] = copy_or_empty_csv(
            comparison,
            paper / "table_7_model_comparison.csv",
        )
    comparative_forecasting_execution = stage_table_path(tables, "table_model_forecasting_execution_comparison", stage)
    if comparative_forecasting_execution.exists():
        artifacts["table_8_model_forecasting_execution_comparison"] = copy_or_empty_csv(
            comparative_forecasting_execution,
            paper / "table_8_model_forecasting_execution_comparison.csv",
        )
    comparative_stress = stage_table_path(tables, "table_model_stress_comparison", stage)
    if comparative_stress.exists():
        artifacts["table_9_model_stress_comparison"] = copy_or_empty_csv(
            comparative_stress,
            paper / "table_9_model_stress_comparison.csv",
        )
    comparative_robustness = stage_table_path(tables, "table_model_robustness_comparison", stage)
    if comparative_robustness.exists():
        artifacts["table_10_model_robustness_comparison"] = copy_or_empty_csv(
            comparative_robustness,
            paper / "table_10_model_robustness_comparison.csv",
        )
    return artifacts


def _prefer_existing(primary: Path, fallback: Path) -> Path:
    return primary if primary.exists() else fallback


def _prefer_first_existing(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _dataset_audit_sources(project_root: Path, tables: Path) -> list[Path]:
    btc_audit = _prefer_first_existing(
        [
            tables / "table_data_audit_stage_3_full_scale.csv",
            project_root / "data" / "interim" / "audit" / "audit_by_day.parquet",
        ]
    )
    eth_audit = _prefer_first_existing(
        [
            tables / "table_data_audit_stage3_eth_usdt.csv",
            tables / "table_data_audit_eth_usdt_stage3.csv",
        ]
    )
    return [path for path in [btc_audit, eth_audit] if path.exists()]
