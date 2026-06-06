from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.io import write_run_metadata


FEATURE_VERSION = "lob_features_stage3_v1"
LABEL_VERSION = "cost_aware_h50_fee1bps_kappa0.5"
RSEP_GRID = "configs/rsep_grid.yaml; lambda singleton grid, theta quantile grid"

PREDICTION_ARTIFACTS = {
    "sgd_stage3": "data/predictions/predictions.parquet",
    "xgboost_gpu_stage3": "data/predictions/predictions_stage3_xgboost_gpu.parquet",
    "tcn_gpu_stage3": "data/predictions/predictions_stage3_tcn_gpu_execution_ready.parquet",
    "tcn_gpu_stage3_stride1": "data/predictions/predictions_stage3_tcn_gpu_stride1_execution_ready.parquet",
    "sgd_eth_stage3": "data/predictions/predictions_eth_stage3_sgd.parquet",
    "asset_btc_to_eth_sgd": "data/predictions/predictions_asset_btc_to_eth_sgd.parquet",
    "asset_eth_to_btc_sgd": "data/predictions/predictions_asset_eth_to_btc_sgd.parquet",
    "tcn_gpu_stage3_pilot": "data/predictions/predictions_stage3_tcn_gpu_pilot.parquet",
    "deeplob_faithful_lite_stage3_pilot": "data/predictions/predictions_stage3_deeplob_faithful_lite_pilot.parquet",
    "deeplob_stage3_pilot": "data/predictions/predictions_stage3_deeplob_pilot.parquet",
    "lob_transformer_stage3_pilot": "data/predictions/predictions_stage3_lob_transformer_pilot.parquet",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Build model-selection and data-snooping audit artifacts.")
    parser.add_argument("--stage", default="stage_3_full_scale")
    parser.add_argument("--run-id", default="p1_11_model_selection_audit_v001")
    return parser.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return payload or {}


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    number = safe_float(value, float(default))
    if not np.isfinite(number):
        return default
    return int(number)


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def model_family(model: str) -> str:
    name = str(model).lower()
    if name.startswith("asset_"):
        return "asset_heldout_streaming_sgd"
    if "xgboost" in name:
        return "xgboost_gpu_tabular"
    if "tcn" in name:
        return "temporal_tcn"
    if "deeplob" in name:
        return "deeplob_cnn_lstm"
    if "transformer" in name:
        return "lob_transformer_lite"
    if "sgd" in name:
        return "streaming_sgd_tabular"
    return "unknown"


def prediction_artifact(model: str) -> str:
    return PREDICTION_ARTIFACTS.get(str(model), "")


def threshold_grid_summary(values: pd.Series) -> str:
    numeric = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if numeric.empty:
        return "no numeric threshold candidates"
    rounded = [float(f"{value:.12g}") for value in numeric.tolist()]
    if len(rounded) <= 12:
        return json_dumps(rounded)
    return f"{len(rounded)} candidates; min={numeric.min():.12g}; max={numeric.max():.12g}"


def validation_source_for_row(row: pd.Series) -> str:
    tuning_split = str(row.get("tuning_split", "") or "")
    if tuning_split:
        return tuning_split
    split = str(row.get("split", "") or "")
    if split == "valid":
        return "valid"
    return split or "unknown"


def selected_uses_test(row: pd.Series) -> bool:
    source = validation_source_for_row(row).lower()
    split = str(row.get("split", "") or "").lower()
    if "test" in source:
        return True
    if split == "test":
        return True
    return False


def selection_status(row: pd.Series) -> str:
    return "FAIL_TEST_SELECTION" if selected_uses_test(row) else "PASS_VALIDATION_ONLY"


def lookup_execution_result(execution: pd.DataFrame, *, model: str, policy: str, direction: str = "") -> dict[str, Any]:
    if execution.empty:
        return {}
    frame = execution.copy()
    mask = pd.Series(True, index=frame.index)
    if direction and "direction" in frame.columns:
        mask &= frame["direction"].astype(str).eq(direction)
    if "model" in frame.columns:
        mask &= frame["model"].astype(str).eq(model)
    if "base_policy" in frame.columns:
        mask &= frame["base_policy"].astype(str).eq(policy)
    elif "policy" in frame.columns:
        mask &= frame["policy"].astype(str).eq(policy)
    match = frame[mask]
    if match.empty:
        return {}
    row = match.iloc[0]
    return {
        "net_pnl": safe_float(row.get("net_pnl")),
        "gross_pnl": safe_float(row.get("gross_pnl")),
        "n_trades": safe_int(row.get("n_trades")),
        "net_pnl_per_trade": safe_float(row.get("net_pnl_per_trade")),
    }


def lookup_model_result(model_table: pd.DataFrame, model: str) -> dict[str, Any]:
    if model_table.empty or "model" not in model_table.columns:
        return {}
    match = model_table[model_table["model"].astype(str).eq(str(model))]
    if match.empty:
        return {}
    row = match.iloc[0]
    return {
        "accuracy": safe_float(row.get("accuracy")),
        "macro_f1": safe_float(row.get("macro_f1")),
        "mcc": safe_float(row.get("mcc")),
        "balanced_accuracy": safe_float(row.get("balanced_accuracy")),
        "test_rows": safe_int(row.get("test_rows")),
        "best_validation_policy": row.get("best_validation_policy", ""),
        "best_policy_reported_on_test": row.get("best_policy", ""),
    }


def policy_rows_from_tuning(
    tuning: pd.DataFrame,
    *,
    execution: pd.DataFrame,
    model_table: pd.DataFrame,
    scope: str,
    asset_or_direction: str,
    source_artifact: str,
) -> pd.DataFrame:
    if tuning.empty:
        return pd.DataFrame(columns=ledger_columns())
    rows: list[dict[str, Any]] = []
    for (model, policy), group in tuning.groupby(["model", "policy"], dropna=False):
        selected = group[group["selected"].astype(str).str.lower().isin(["true", "1", "yes"])]
        if selected.empty:
            selected = group.sort_values("net_pnl", ascending=False).head(1)
        row = selected.iloc[0]
        direction = str(row.get("direction", "") or "")
        test_result = lookup_execution_result(execution, model=str(model), policy=str(policy), direction=direction)
        model_result = lookup_model_result(model_table, str(model))
        validation_result = {
            "net_pnl": safe_float(row.get("net_pnl")),
            "n_trades": safe_int(row.get("n_trades")),
            "n_trade_days": safe_int(row.get("n_trade_days")),
            "split": row.get("split", ""),
            "tuning_split": row.get("tuning_split", ""),
        }
        note_bits = [
            f"source_artifact={source_artifact}",
            "threshold selected by validation net PnL under min-trades/min-days constraints",
        ]
        if direction:
            note_bits.append("asset-held-out target test not used for threshold selection")
        if model_result.get("best_policy_reported_on_test") and model_result.get("best_validation_policy"):
            if str(model_result["best_policy_reported_on_test"]) != str(model_result["best_validation_policy"]):
                note_bits.append(
                    "test-best policy differs from validation-selected policy; paper must treat it as reporting diagnostic"
                )
        rows.append(
            {
                "scope": scope,
                "asset_or_direction": direction or asset_or_direction,
                "model": str(model),
                "model_family": model_family(str(model)),
                "feature_version": FEATURE_VERSION,
                "label_version": LABEL_VERSION,
                "prediction_artifact": prediction_artifact(str(model)),
                "threshold_grid": threshold_grid_summary(group["threshold"]),
                "rsep_grid": RSEP_GRID if str(policy) == "RSEP-full" else "not_applicable",
                "validation_metric": "max_net_pnl_with_min_trades_and_min_trade_days",
                "selected_policy": str(policy),
                "selected_thresholds": json_dumps({str(policy): safe_float(row.get("threshold"))}),
                "validation_result": json_dumps(validation_result),
                "test_result": json_dumps(test_result),
                "selection_source": validation_source_for_row(row),
                "test_used_for_selection": bool(selected_uses_test(row)),
                "selection_audit_status": selection_status(row),
                "notes": "; ".join(note_bits),
            }
        )
    return pd.DataFrame(rows, columns=ledger_columns())


def candidate_counts_from_tuning(
    tuning: pd.DataFrame,
    *,
    scope: str,
    asset_or_direction: str,
    source_artifact: str,
) -> pd.DataFrame:
    if tuning.empty:
        return pd.DataFrame(
            columns=[
                "scope",
                "asset_or_direction",
                "model",
                "policy",
                "n_candidates",
                "n_selected",
                "selection_sources",
                "selected_thresholds",
                "selection_audit_status",
                "source_artifact",
            ]
        )
    rows: list[dict[str, Any]] = []
    for (model, policy), group in tuning.groupby(["model", "policy"], dropna=False):
        selected = group[group["selected"].astype(str).str.lower().isin(["true", "1", "yes"])]
        direction = ""
        if "direction" in group.columns and group["direction"].notna().any():
            direction = str(group["direction"].dropna().astype(str).iloc[0])
        test_used = bool(any(selected.apply(selected_uses_test, axis=1))) if not selected.empty else False
        sources = sorted({validation_source_for_row(row) for _, row in selected.iterrows()}) if not selected.empty else []
        rows.append(
            {
                "scope": scope,
                "asset_or_direction": direction or asset_or_direction,
                "model": str(model),
                "policy": str(policy),
                "n_candidates": int(len(group)),
                "n_selected": int(len(selected)),
                "selection_sources": ",".join(sources),
                "selected_thresholds": threshold_grid_summary(selected["threshold"]) if not selected.empty else "",
                "selection_audit_status": "FAIL_TEST_SELECTION" if test_used else "PASS_VALIDATION_ONLY",
                "source_artifact": source_artifact,
            }
        )
    return pd.DataFrame(rows)


def model_reporting_rows(
    model_table: pd.DataFrame,
    *,
    scope: str,
    asset_or_direction: str,
    source_artifact: str,
) -> pd.DataFrame:
    if model_table.empty or "model" not in model_table.columns:
        return pd.DataFrame(columns=ledger_columns())
    rows: list[dict[str, Any]] = []
    for _, row in model_table.iterrows():
        model = str(row.get("model", ""))
        selected_policy = str(row.get("best_validation_policy", "") or "")
        test_policy = str(row.get("best_policy", "") or "")
        test_result = {
            "accuracy": safe_float(row.get("accuracy")),
            "macro_f1": safe_float(row.get("macro_f1")),
            "mcc": safe_float(row.get("mcc")),
            "balanced_accuracy": safe_float(row.get("balanced_accuracy")),
            "test_rows": safe_int(row.get("test_rows")),
            "best_policy_reported_on_test": test_policy,
            "best_policy_net_pnl": safe_float(row.get("best_policy_net_pnl")),
            "rsep_vs_cost_aware_ci_low": safe_float(row.get("rsep_vs_cost_aware_ci_low")),
            "rsep_vs_cost_aware_ci_high": safe_float(row.get("rsep_vs_cost_aware_ci_high")),
        }
        notes = [
            f"source_artifact={source_artifact}",
            "forecast/model rows are reported as evidence, not selected by test profitability",
        ]
        if selected_policy and test_policy and selected_policy != test_policy:
            notes.append("validation-selected policy differs from test-best diagnostic policy")
        rows.append(
            {
                "scope": scope,
                "asset_or_direction": asset_or_direction,
                "model": model,
                "model_family": model_family(model),
                "feature_version": FEATURE_VERSION,
                "label_version": LABEL_VERSION,
                "prediction_artifact": prediction_artifact(model),
                "threshold_grid": "see policy tuning ledger when execution-tuned",
                "rsep_grid": RSEP_GRID if selected_policy == "RSEP-full" else "not_applicable",
                "validation_metric": "forecasting metrics reported; policy selection uses validation table if present",
                "selected_policy": selected_policy or "not_selected_for_execution",
                "selected_thresholds": "{}",
                "validation_result": json_dumps(
                    {
                        "best_validation_policy": selected_policy,
                        "best_validation_net_pnl": safe_float(row.get("best_validation_net_pnl")),
                        "best_validation_n_trades": safe_int(row.get("best_validation_n_trades")),
                    }
                ),
                "test_result": json_dumps(test_result),
                "selection_source": "valid" if selected_policy else "not_applicable",
                "test_used_for_selection": False,
                "selection_audit_status": "PASS_VALIDATION_ONLY",
                "notes": "; ".join(notes),
            }
        )
    return pd.DataFrame(rows, columns=ledger_columns())


def pilot_rows_from_forecasting(overall_tables: list[Path], root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in overall_tables:
        frame = read_csv(path)
        if frame.empty or "model" not in frame.columns:
            continue
        for _, row in frame.iterrows():
            model = str(row.get("model", ""))
            if model in {"sgd_stage3", "xgboost_gpu_stage3", "tcn_gpu_stage3", "tcn_gpu_stage3_stride1"}:
                continue
            rows.append(
                {
                    "scope": "temporal_or_deep_pilot",
                    "asset_or_direction": "BTC-USDT pilot sample",
                    "model": model,
                    "model_family": model_family(model),
                    "feature_version": "temporal_window_100x40_train_only_scaler",
                    "label_version": LABEL_VERSION,
                    "prediction_artifact": prediction_artifact(model),
                    "threshold_grid": "not_run_for_execution",
                    "rsep_grid": "not_applicable",
                    "validation_metric": "pilot/smoke forecasting only",
                    "selected_policy": "not_selected_for_execution",
                    "selected_thresholds": "{}",
                    "validation_result": json_dumps({"evaluation_scope": row.get("evaluation_scope", "")}),
                    "test_result": json_dumps(
                        {
                            "accuracy": safe_float(row.get("accuracy")),
                            "macro_f1": safe_float(row.get("macro_f1")),
                            "mcc": safe_float(row.get("mcc")),
                            "balanced_accuracy": safe_float(row.get("balanced_accuracy")),
                            "n_rows": safe_int(row.get("n_rows")),
                        }
                    ),
                    "selection_source": "pilot_not_model_selection",
                    "test_used_for_selection": False,
                    "selection_audit_status": "PASS_NOT_SELECTED",
                    "notes": f"source_artifact={path.relative_to(root).as_posix()}; pilot retained as supporting/negative evidence",
                }
            )
    return pd.DataFrame(rows, columns=ledger_columns())


def ledger_columns() -> list[str]:
    return [
        "scope",
        "asset_or_direction",
        "model",
        "model_family",
        "feature_version",
        "label_version",
        "prediction_artifact",
        "threshold_grid",
        "rsep_grid",
        "validation_metric",
        "selected_policy",
        "selected_thresholds",
        "validation_result",
        "test_result",
        "selection_source",
        "test_used_for_selection",
        "selection_audit_status",
        "notes",
    ]


def overfitting_diagnostic_summary(candidate_counts: pd.DataFrame, *, has_per_candidate_daily_returns: bool) -> pd.DataFrame:
    n_candidates = int(candidate_counts["n_candidates"].sum()) if not candidate_counts.empty else 0
    n_config_groups = int(len(candidate_counts))
    if not has_per_candidate_daily_returns:
        return pd.DataFrame(
            [
                {
                    "diagnostic": "RealityCheck_PBO_CSCV",
                    "status": "INFEASIBLE_FROM_CURRENT_SAVED_ARTIFACTS",
                    "n_candidate_groups": n_config_groups,
                    "n_threshold_candidates": n_candidates,
                    "reason": (
                        "Current artifacts save aggregate validation metrics for all threshold candidates and daily/trade "
                        "returns only for selected policies; conservative PBO/Reality-Check diagnostics require "
                        "per-candidate per-period returns."
                    ),
                    "conservative_control_used": (
                        "ledger of tried candidates, validation-only selection, test-only reporting, day-level bootstrap, "
                        "stress no-retuning, and negative evidence retained"
                    ),
                }
            ]
        )
    return pd.DataFrame(
        [
            {
                "diagnostic": "RealityCheck_PBO_CSCV",
                "status": "READY",
                "n_candidate_groups": n_config_groups,
                "n_threshold_candidates": n_candidates,
                "reason": "Per-candidate daily returns are available.",
                "conservative_control_used": "direct overfitting diagnostic can be computed",
            }
        ]
    )


def write_audit_doc(path: Path, *, run_id: str, ledger: pd.DataFrame, candidate_counts: pd.DataFrame, overfit: pd.DataFrame) -> None:
    n_rows = int(len(ledger))
    n_fail = int(ledger["selection_audit_status"].astype(str).str.contains("FAIL", na=False).sum()) if not ledger.empty else 0
    n_models = int(ledger["model"].nunique()) if not ledger.empty else 0
    n_candidates = int(candidate_counts["n_candidates"].sum()) if not candidate_counts.empty else 0
    scope_counts = ledger["scope"].value_counts().to_dict() if not ledger.empty else {}
    scope_lines = [f"- `{scope}`: `{count}` ledger rows" for scope, count in sorted(scope_counts.items())]
    if not scope_lines:
        scope_lines = ["- Khong co row ledger."]

    overfit_status = overfit.iloc[0].to_dict() if not overfit.empty else {}
    lines = [
        "# Model-selection and data-snooping audit",
        "",
        f"- `run_id`: `{run_id}`",
        "- Muc tieu: chung minh selection model/policy trong paper duoc trace bang artifact va khong dung test de tune.",
        "- Pham vi: Stage 3 BTC, ETH within-asset, BTC<->ETH asset-held-out, va deep/temporal pilot da co.",
        "- Khong train lai, khong replay lai, khong dung raw data.",
        "",
        "## Tom tat ledger",
        "",
        f"- So row ledger: `{n_rows}`.",
        f"- So model/config label duy nhat: `{n_models}`.",
        f"- Tong threshold candidates trong tuning tables: `{n_candidates}`.",
        f"- Selection audit FAIL rows: `{n_fail}`.",
        "",
        *scope_lines,
        "",
        "## Quy tac selection da audit",
        "",
        "- Forecasting models duoc bao cao theo vai tro bang chung; paper khong chon winner bang test profitability.",
        "- Policy thresholds trong `09_tune_execution_policies.py` duoc chon tren validation net PnL voi rang buoc min-trades/min-days.",
        "- Asset-held-out execution trong `20_run_asset_heldout_execution.py` tune tren source validation only; target test chi dung de report.",
        "- RSEP lambda la singleton benchmark grid; `theta_edge` duoc chon tu validation margin grid.",
        "- Stress grid khong retrain, khong recompute probabilities, khong retune thresholds/RSEP.",
        "",
        "## PBO/Reality Check diagnostic",
        "",
        f"- Trang thai: `{overfit_status.get('status', 'UNKNOWN')}`.",
        f"- Ly do: {overfit_status.get('reason', '')}",
        f"- Conservative controls: {overfit_status.get('conservative_control_used', '')}",
        "",
        "## Principal ML Scientist view",
        "",
        "Ledger nay khong loai bo hoan toan data-snooping risk trong workflow nghien cuu lap di lap lai. Tuy nhien no lam ro surface da thu, split dung de chon threshold, va giu negative evidence nhu TCN stride-1/DeepLOB/Transformer pilot thay vi chi bao cao cau hinh dep.",
        "",
        "## Reviewer ICDM view",
        "",
        "Diem manh la moi row selection co artifact nguon va `selection_source`. Diem can ha giong la paper khong nen claim da co Reality Check/PBO chinh thuc khi chua save per-candidate daily returns. Nen viet la validation-only controls + day-level bootstrap + full ledger, khong phai guarantee khong overfit.",
        "",
        "## Decision",
        "",
        "- PASS neu `selection_audit_status` khong co `FAIL_TEST_SELECTION`.",
        "- Remaining risk: finite model family va iterative research workflow; can ghi ro trong Threats to Validity.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_model_selection_audit(root: Path, *, run_id: str) -> dict[str, Path]:
    root = Path(root)
    tables = root / "outputs" / "tables"
    artifacts = root / "artifacts"
    docs = root / "docs"
    paper = root / "outputs" / "paper_assets"
    artifacts.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    paper.mkdir(parents=True, exist_ok=True)

    btc_tuning_path = tables / "table_policy_tuning_stage3.csv"
    eth_tuning_path = tables / "table_policy_tuning_stage3_eth_usdt.csv"
    asset_tuning_path = tables / "table_asset_heldout_policy_tuning_stage3.csv"
    btc_execution_path = tables / "table_forecast_to_execution_tuned_stage3.csv"
    eth_execution_path = tables / "table_forecast_to_execution_tuned_stage3_eth_usdt.csv"
    asset_execution_path = tables / "table_asset_heldout_execution_stage3.csv"
    btc_model_path = tables / "table_model_comparison_stage3.csv"
    eth_model_path = tables / "table_model_comparison_stage3_eth_usdt.csv"
    temporal_model_path = tables / "table_temporal_vs_tabular_comparison_stage3.csv"

    btc_tuning = read_csv(btc_tuning_path)
    eth_tuning = read_csv(eth_tuning_path)
    asset_tuning = read_csv(asset_tuning_path)
    btc_execution = read_csv(btc_execution_path)
    eth_execution = read_csv(eth_execution_path)
    asset_execution = read_csv(asset_execution_path)
    btc_model = read_csv(btc_model_path)
    eth_model = read_csv(eth_model_path)
    temporal_model = read_csv(temporal_model_path)

    ledgers = [
        policy_rows_from_tuning(
            btc_tuning,
            execution=btc_execution,
            model_table=btc_model,
            scope="btc_within_asset_stage3",
            asset_or_direction="BTC-USDT",
            source_artifact="outputs/tables/table_policy_tuning_stage3.csv",
        ),
        policy_rows_from_tuning(
            eth_tuning,
            execution=eth_execution,
            model_table=eth_model,
            scope="eth_within_asset_stage3",
            asset_or_direction="ETH-USDT",
            source_artifact="outputs/tables/table_policy_tuning_stage3_eth_usdt.csv",
        ),
        policy_rows_from_tuning(
            asset_tuning,
            execution=asset_execution,
            model_table=pd.DataFrame(),
            scope="asset_heldout_stage3",
            asset_or_direction="BTC<->ETH",
            source_artifact="outputs/tables/table_asset_heldout_policy_tuning_stage3.csv",
        ),
        model_reporting_rows(
            btc_model,
            scope="btc_full_year_model_reporting",
            asset_or_direction="BTC-USDT",
            source_artifact="outputs/tables/table_model_comparison_stage3.csv",
        ),
        model_reporting_rows(
            eth_model,
            scope="eth_full_year_model_reporting",
            asset_or_direction="ETH-USDT",
            source_artifact="outputs/tables/table_model_comparison_stage3_eth_usdt.csv",
        ),
    ]
    if not temporal_model.empty:
        pilot = temporal_model[
            temporal_model.get("evaluation_scope", pd.Series(dtype=str)).astype(str).str.contains("pilot", case=False, na=False)
        ]
        ledgers.append(
            pilot_rows_from_forecasting(
                [
                    tables / "table_forecasting_overall_stage3_deeplob_faithful_lite_stage3_pilot.csv",
                    tables / "table_forecasting_overall_stage3_deeplob_stage3_pilot.csv",
                    tables / "table_forecasting_overall_stage3_lob_transformer_stage3_pilot.csv",
                    tables / "table_forecasting_overall_stage3_tcn_gpu_stage3_pilot.csv",
                ],
                root,
            )
        )
        ledgers.append(
            model_reporting_rows(
                temporal_model[
                    temporal_model.get("evaluation_scope", pd.Series(dtype=str)).astype(str).eq("full_year_test")
                ],
                scope="temporal_tabular_comparative_reporting",
                asset_or_direction="BTC-USDT",
                source_artifact="outputs/tables/table_temporal_vs_tabular_comparison_stage3.csv",
            )
        )
    ledger = pd.concat([frame for frame in ledgers if not frame.empty], ignore_index=True, sort=False)
    if not ledger.empty:
        ledger = ledger.drop_duplicates(subset=["scope", "asset_or_direction", "model", "selected_policy"], keep="first")

    count_frames = [
        candidate_counts_from_tuning(
            btc_tuning,
            scope="btc_within_asset_stage3",
            asset_or_direction="BTC-USDT",
            source_artifact="outputs/tables/table_policy_tuning_stage3.csv",
        ),
        candidate_counts_from_tuning(
            eth_tuning,
            scope="eth_within_asset_stage3",
            asset_or_direction="ETH-USDT",
            source_artifact="outputs/tables/table_policy_tuning_stage3_eth_usdt.csv",
        ),
        candidate_counts_from_tuning(
            asset_tuning,
            scope="asset_heldout_stage3",
            asset_or_direction="BTC<->ETH",
            source_artifact="outputs/tables/table_asset_heldout_policy_tuning_stage3.csv",
        ),
    ]
    candidate_counts = pd.concat([frame for frame in count_frames if not frame.empty], ignore_index=True, sort=False)
    overfit = overfitting_diagnostic_summary(candidate_counts, has_per_candidate_daily_returns=False)

    ledger_path = artifacts / "model_selection_ledger.csv"
    counts_path = artifacts / "model_selection_candidate_counts.csv"
    overfit_path = artifacts / "model_selection_overfitting_diagnostic.csv"
    doc_path = docs / "model_selection_audit.md"
    paper_path = paper / "model_selection_data_snooping_controls_p1_11.md"

    ledger.to_csv(ledger_path, index=False)
    candidate_counts.to_csv(counts_path, index=False)
    overfit.to_csv(overfit_path, index=False)
    write_audit_doc(doc_path, run_id=run_id, ledger=ledger, candidate_counts=candidate_counts, overfit=overfit)
    paper_path.write_text(
        "\n".join(
            [
                "# Model-selection and data-snooping controls",
                "",
                "All policy thresholds in the main benchmark are selected on validation rows only. "
                "Within-asset policies use the chronological validation split, while asset-held-out policies use source-asset validation and reserve target-asset test rows for final reporting. "
                "RSEP risk weights are fixed benchmark constants from a singleton grid, and only the edge threshold is validation-selected. "
                "Stress-grid evaluations keep predictions and selected thresholds fixed; they do not retrain models or retune execution gates.",
                "",
                "The model-selection ledger records every saved Stage 3 policy-threshold grid candidate and the selected validation row. "
                "The current artifacts do not contain per-candidate daily returns for all candidates, so a formal Reality Check/PBO analysis is not claimed. "
                "Instead, the paper reports a conservative audit trail: candidate counts, validation-only selection, day-level bootstrap on selected policies, stress no-retuning, and retained negative evidence.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "ledger": ledger_path,
        "candidate_counts": counts_path,
        "overfitting_diagnostic": overfit_path,
        "audit_doc": doc_path,
        "paper_controls": paper_path,
    }


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = build_model_selection_audit(root, run_id=args.run_id)
    metadata_config = {
        "_config_path": str(root / "scripts" / "26_build_model_selection_audit.py"),
        "project_root": str(root),
        "stage_ranges": {args.stage: {"start": None, "end": None}},
    }
    write_run_metadata(
        metadata_config,
        args.run_id,
        args.stage,
        "26_build_model_selection_audit.py",
        artifacts=paths,
        extra={
            "scope": "Stage 3 BTC, ETH, asset-held-out, temporal/deep pilot",
            "test_data_selection_rule": "test rows are final-reporting only",
            "overfitting_diagnostic": "PBO/Reality Check infeasible without per-candidate daily returns",
        },
    )
    print(f"Wrote model-selection audit artifacts: {paths}")


if __name__ == "__main__":
    main()
