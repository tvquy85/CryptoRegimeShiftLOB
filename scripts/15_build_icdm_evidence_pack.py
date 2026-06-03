from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.artifacts import stage_table_path  # noqa: E402
from utils.cli import as_common_args, common_parser  # noqa: E402
from utils.config import load_config, project_root  # noqa: E402
from utils.io import write_run_metadata  # noqa: E402
from utils.logging import configure_logging  # noqa: E402


DEFAULT_MODELS = (
    "sgd_stage3",
    "xgboost_gpu_stage3",
    "tcn_gpu_stage3",
    "tcn_gpu_stage3_stride1",
)


@dataclass(frozen=True)
class EvidencePaths:
    acceptance_bar: Path
    claim_support: Path
    final_model_selection: Path
    paper_acceptance_bar: Path
    paper_claim_support: Path
    narrative: Path
    audit: Path


def _stage_slug(stage: str) -> str:
    if "stage_3" in stage or "stage3" in stage:
        return "stage3"
    return stage.replace("stage_", "stage").replace("_full_scale", "").replace("_", "")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _normalize_model_column(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    if "model_label" not in frame.columns and "model" in frame.columns:
        frame["model_label"] = frame["model"]
    if "model" not in frame.columns and "model_label" in frame.columns:
        frame["model"] = frame["model_label"]
    return frame


def _normalize_axis_column(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    if "stress_axis" not in frame.columns and "axis" in frame.columns:
        frame["stress_axis"] = frame["axis"]
    if "axis" not in frame.columns and "stress_axis" in frame.columns:
        frame["axis"] = frame["stress_axis"]
    return frame


def _normalize_model_summary(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_model_column(frame)
    if frame.empty:
        return frame
    aliases = {
        "bootstrap_rsep_vs_cost_aware_mean_diff": "bootstrap_mean_diff_vs_cost_aware",
        "bootstrap_rsep_vs_cost_aware_ci_low": "bootstrap_ci_low",
        "bootstrap_rsep_vs_cost_aware_ci_high": "bootstrap_ci_high",
        "rsep_vs_cost_aware_mean_diff": "bootstrap_mean_diff_vs_cost_aware",
        "rsep_vs_cost_aware_ci_low": "bootstrap_ci_low",
        "rsep_vs_cost_aware_ci_high": "bootstrap_ci_high",
    }
    for source, target in aliases.items():
        if target not in frame.columns and source in frame.columns:
            frame[target] = frame[source]
    return frame


def _normalize_bootstrap(frame: pd.DataFrame) -> pd.DataFrame:
    return _normalize_model_column(frame)


def _normalize_stress(frame: pd.DataFrame) -> pd.DataFrame:
    return _normalize_axis_column(_normalize_model_column(frame))


def _safe_float(value: object, default: float = np.nan) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _evidence_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _status(
    status: str,
    criterion: str,
    summary: str,
    artifact: Path | None,
    root: Path,
    interpretation: str,
) -> dict[str, str]:
    return {
        "criterion": criterion,
        "status": status,
        "evidence_summary": summary,
        "evidence_artifact": _evidence_path(artifact, root) if artifact else "",
        "paper_interpretation": interpretation,
    }


def _forecasting_by_regime_status(by_regime: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    if by_regime.empty:
        return _status(
            "FAIL",
            "Forecasting performance varies by regime",
            "Khong tim thay bang forecasting by-regime.",
            artifact,
            root,
            "Can sinh lai bang by-regime truoc khi claim regime heterogeneity.",
        )
    metric_col = "macro_f1" if "macro_f1" in by_regime.columns else "accuracy"
    values = pd.to_numeric(by_regime.get(metric_col), errors="coerce").dropna()
    regime_count = int(by_regime["regime"].nunique()) if "regime" in by_regime.columns else len(by_regime)
    spread = float(values.max() - values.min()) if not values.empty else 0.0
    status = "PASS" if regime_count >= 3 and spread >= 0.03 else "PARTIAL"
    return _status(
        status,
        "Forecasting performance varies by regime",
        f"Co {regime_count} regime; spread {metric_col} theo regime = {spread:.4f}.",
        artifact,
        root,
        "Dung lam bang chung microstructure regimes anh huong ro den forecasting.",
    )


def _forecast_to_execution_status(model_summary: pd.DataFrame, default_exec: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    gross_positive_net_negative = False
    if not model_summary.empty:
        for _, row in model_summary.iterrows():
            gross = _safe_float(row.get("rsep_test_gross_pnl"))
            net = _safe_float(row.get("rsep_test_net_pnl"))
            if gross > 0 and net < 0:
                gross_positive_net_negative = True
                break
    default_negative = False
    if not default_exec.empty and "net_pnl" in default_exec.columns:
        net_values = pd.to_numeric(default_exec["net_pnl"], errors="coerce").dropna()
        default_negative = bool((net_values < 0).any())
    status = "PASS" if gross_positive_net_negative or default_negative else "PARTIAL"
    summary = "Co bang chung gross edge bi phi/spread/latency an mon thanh net PnL am."
    if not gross_positive_net_negative and default_negative:
        summary = "Baseline execution mac dinh co net PnL am; can doc chung voi stress/cost table."
    return _status(
        status,
        "Forecasting score does not guarantee actionable execution edge",
        summary,
        artifact,
        root,
        "Claim nen la forecast-to-execution degradation, khong claim trading bot sinh loi.",
    )


def _stress_degradation_status(stress: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    if stress.empty or "stress_axis" not in stress.columns or "net_pnl" not in stress.columns:
        return _status(
            "FAIL",
            "Stress grid shows cost/latency/liquidity degradation",
            "Khong tim thay stress grid hop le.",
            artifact,
            root,
            "Can stress grid de paper co OOD/cost sensitivity.",
        )
    fee = stress.loc[stress["stress_axis"].eq("fee_bps")].copy()
    degraded = False
    detail = "Stress grid ton tai nhung chua du de ket luan monotonic degradation."
    if not fee.empty and ("fee_bps" in fee.columns or "level" in fee.columns):
        level_col = "fee_bps" if "fee_bps" in fee.columns else "level"
        for model_label, group in fee.groupby("model_label", dropna=False):
            group = group.sort_values(level_col)
            net = pd.to_numeric(group["net_pnl"], errors="coerce").dropna()
            if len(net) >= 2 and net.iloc[-1] < net.iloc[0]:
                degraded = True
                detail = f"Fee stress lam net PnL giam cho model {model_label}."
                break
    return _status(
        "PASS" if degraded else "PARTIAL",
        "Stress grid shows cost/latency/liquidity degradation",
        detail,
        artifact,
        root,
        "Dua stress curves vao main/appendix de chung minh robustness khong chi la average metric.",
    )


def _policy_by_regime_metrics(tuned_by_regime: pd.DataFrame) -> pd.DataFrame:
    if tuned_by_regime.empty or not {"model_label", "policy", "regime", "net_pnl"}.issubset(tuned_by_regime.columns):
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (model_label, policy), group in tuned_by_regime.groupby(["model_label", "policy"], dropna=False):
        net = pd.to_numeric(group["net_pnl"], errors="coerce").dropna()
        if net.empty:
            continue
        rows.append(
            {
                "model_label": model_label,
                "policy": policy,
                "worst_regime_return": float(net.min()),
                "regime_gap": float(net.max() - net.min()),
                "mean_regime_return": float(net.mean()),
            }
        )
    return pd.DataFrame(rows)


def _rsep_worst_regime_status(tuned_by_regime: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    metrics = _policy_by_regime_metrics(tuned_by_regime)
    if metrics.empty:
        return _status(
            "PARTIAL",
            "RSEP improves worst-regime behavior versus threshold baselines",
            "Thieu bang tuned execution by-regime de so sanh worst-regime.",
            artifact,
            root,
            "Khong nen claim worst-regime improvement neu artifact by-regime chua day du.",
        )
    wins = 0
    comparisons = 0
    for model_label, group in metrics.groupby("model_label"):
        rsep = group.loc[group["policy"].astype(str).str.contains("RSEP-full", case=False, regex=False)]
        baselines = group.loc[~group["policy"].astype(str).str.contains("RSEP-full", case=False, regex=False)]
        if rsep.empty or baselines.empty:
            continue
        comparisons += 1
        best_baseline = baselines["worst_regime_return"].max()
        if float(rsep["worst_regime_return"].max()) >= float(best_baseline):
            wins += 1
    if comparisons == 0:
        status = "PARTIAL"
        summary = "Co by-regime table nhung thieu baseline hoac RSEP cung model."
    else:
        status = "PASS" if wins > 0 else "FAIL"
        summary = f"RSEP dat worst-regime >= baseline trong {wins}/{comparisons} so sanh model."
    return _status(
        status,
        "RSEP improves worst-regime behavior versus threshold baselines",
        summary,
        artifact,
        root,
        "Neu mixed, viet la selective policy giup mot so baseline nhung khong universal.",
    )


def _rsep_regime_gap_status(tuned_by_regime: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    metrics = _policy_by_regime_metrics(tuned_by_regime)
    if metrics.empty:
        return _status(
            "PARTIAL",
            "RSEP reduces RegimeGap without hiding average degradation",
            "Thieu bang by-regime de tinh RegimeGap tuned.",
            artifact,
            root,
            "Chi nen dua RegimeGap neu co bang doi chieu policy.",
        )
    wins = 0
    comparisons = 0
    for model_label, group in metrics.groupby("model_label"):
        rsep = group.loc[group["policy"].astype(str).str.contains("RSEP-full", case=False, regex=False)]
        baselines = group.loc[~group["policy"].astype(str).str.contains("RSEP-full", case=False, regex=False)]
        if rsep.empty or baselines.empty:
            continue
        comparisons += 1
        best_baseline_gap = baselines["regime_gap"].min()
        if float(rsep["regime_gap"].min()) <= float(best_baseline_gap):
            wins += 1
    status = "PASS" if comparisons and wins > 0 else "PARTIAL"
    summary = f"RSEP co RegimeGap <= baseline trong {wins}/{comparisons} so sanh model." if comparisons else "Chua co so sanh policy hop le."
    return _status(
        status,
        "RSEP reduces RegimeGap without hiding average degradation",
        summary,
        artifact,
        root,
        "Giu claim o muc robustness/failure-analysis neu RegimeGap mixed.",
    )


def _robustness_auc_status(robustness: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    if robustness.empty:
        return _status(
            "PARTIAL",
            "RobustnessAUC summarizes degradation under stress",
            "Chua co bang RobustnessAUC canonical.",
            artifact,
            root,
            "Co the dua stress curves thay the neu RobustnessAUC chua du doi chieu.",
        )
    axes = sorted(str(axis) for axis in robustness.get("stress_axis", pd.Series(dtype=str)).dropna().unique())
    status = "PASS" if len(axes) >= 3 else "PARTIAL"
    return _status(
        status,
        "RobustnessAUC summarizes degradation under stress",
        f"Robustness table co {len(axes)} stress axes: {', '.join(axes)}.",
        artifact,
        root,
        "Dung nhu summary metric; neu chua matched baseline thi khong noi RSEP universal winner.",
    )


def _bootstrap_status(bootstrap: pd.DataFrame, artifact: Path, root: Path) -> dict[str, str]:
    if bootstrap.empty:
        return _status(
            "FAIL",
            "Day-level bootstrap supports the statistical reading",
            "Khong tim thay bootstrap tuned stage 3.",
            artifact,
            root,
            "Can day-level bootstrap de tranh ket luan dua tren aggregate duy nhat.",
        )
    n_days = pd.to_numeric(bootstrap.get("n_days"), errors="coerce").dropna()
    n_boot = pd.to_numeric(bootstrap.get("n_bootstrap"), errors="coerce").dropna()
    positive_ci = pd.to_numeric(bootstrap.get("ci_low"), errors="coerce").dropna()
    has_valid_bootstrap = bool((n_days > 1).all() and (n_boot >= 1000).any())
    has_positive = bool((positive_ci > 0).any())
    has_mixed = bool((positive_ci <= 0).any())
    if has_valid_bootstrap and has_positive and has_mixed:
        status = "PARTIAL"
        summary = "Bootstrap hop le; SGD/XGBoost co CI duong, TCN stride-1 mixed/khong thang cost-aware."
    elif has_valid_bootstrap and has_positive:
        status = "PASS"
        summary = "Bootstrap hop le va co CI duong cho main comparison."
    else:
        status = "PARTIAL" if has_valid_bootstrap else "FAIL"
        summary = "Bootstrap ton tai nhung chua support main comparison ro rang."
    return _status(
        status,
        "Day-level bootstrap supports the statistical reading",
        summary,
        artifact,
        root,
        "Trinh bay CI theo model; khong gom thanh mot claim universal.",
    )


def _build_acceptance_bar(
    root: Path,
    tables: Path,
    stage: str,
    model_summary: pd.DataFrame,
    by_regime: pd.DataFrame,
    default_exec: pd.DataFrame,
    tuned_by_regime: pd.DataFrame,
    bootstrap: pd.DataFrame,
    stress: pd.DataFrame,
    robustness: pd.DataFrame,
) -> pd.DataFrame:
    by_regime_path = stage_table_path(tables, "table_forecasting_by_regime", stage)
    exec_path = stage_table_path(tables, "table_model_forecasting_execution_comparison", stage)
    stress_path = stage_table_path(tables, "table_model_stress_comparison", stage)
    by_regime_exec_path = stage_table_path(tables, "table_forecast_to_execution_tuned_by_regime", stage)
    robustness_path = stage_table_path(tables, "table_model_robustness_comparison", stage)
    bootstrap_path = stage_table_path(tables, "table_rsep_bootstrap_tuned", stage)
    eth_model_path = stage_table_path(tables, "table_model_comparison", stage, namespace="eth_usdt_stage3")
    asset_heldout_path = tables / "table_asset_heldout_forecasting_stage3.csv"
    asset_heldout_execution_path = tables / "table_asset_heldout_execution_stage3.csv"
    asset_heldout_bootstrap_path = tables / "table_asset_heldout_rsep_bootstrap_stage3.csv"
    has_eth_within_asset = eth_model_path.exists()
    has_asset_heldout = asset_heldout_path.exists()
    asset_execution = _read_csv(asset_heldout_execution_path)
    asset_bootstrap = _read_csv(asset_heldout_bootstrap_path)
    has_asset_heldout_execution = (
        not asset_execution.empty
        and not asset_bootstrap.empty
        and asset_execution.get("direction", pd.Series(dtype=str)).nunique() >= 2
        and asset_bootstrap.get("direction", pd.Series(dtype=str)).nunique() >= 2
        and bool((pd.to_numeric(asset_bootstrap.get("n_days"), errors="coerce").fillna(0) > 1).all())
        and bool((pd.to_numeric(asset_bootstrap.get("n_bootstrap"), errors="coerce").fillna(0) >= 1000).all())
    )

    rows = [
        _forecasting_by_regime_status(by_regime, by_regime_path, root),
        _forecast_to_execution_status(model_summary, default_exec, exec_path, root),
        _stress_degradation_status(stress, stress_path, root),
        _rsep_worst_regime_status(tuned_by_regime, by_regime_exec_path, root),
        _rsep_regime_gap_status(tuned_by_regime, by_regime_exec_path, root),
        _robustness_auc_status(robustness, robustness_path, root),
        _status(
            "PARTIAL" if has_eth_within_asset else "BLOCKED",
            "Results hold across both BTC and ETH",
            (
                "ETH within-asset forecasting/execution da chay; net PnL van am va can doc nhu replication/failure-analysis."
                if has_eth_within_asset
                else "Hien tai data/full2024 chua co ETH artifact de chay asset-level replication."
            ),
            eth_model_path if has_eth_within_asset else None,
            root,
            (
                "Co the trinh bay ETH la replication asset; khong claim cross-asset policy generalization."
                if has_eth_within_asset
                else "Chi claim BTC full-year; ETH la future/blocked evidence."
            ),
        ),
        _status(
            "PASS" if has_asset_heldout_execution else ("PARTIAL" if has_asset_heldout else "BLOCKED"),
            "Asset-held-out or cross-asset generalization is evaluated",
            (
                "Da co asset-held-out forecasting va execution/RSEP BTC->ETH, ETH->BTC voi tuning source-validation-only."
                if has_asset_heldout_execution
                else "Da co asset-held-out forecasting BTC->ETH va ETH->BTC; chua co asset-held-out execution/RSEP."
                if has_asset_heldout
                else "Asset-held-out BTC<->ETH bi chan do thieu ETH."
            ),
            asset_heldout_execution_path if has_asset_heldout_execution else (asset_heldout_path if has_asset_heldout else None),
            root,
            (
                "Co the claim cross-asset forecasting/execution duoc evaluate; khong claim policy tao loi nhuan pho quat."
                if has_asset_heldout_execution
                else "Chi claim cross-asset forecasting evidence; de execution generalization la limitation/next step."
                if has_asset_heldout
                else "Khong dung ngon ngu generalization across assets trong main claim."
            ),
        ),
        _bootstrap_status(bootstrap, bootstrap_path, root),
    ]
    for index, row in enumerate(rows, start=1):
        row["criterion_id"] = f"C{index:02d}"
    return pd.DataFrame(rows)[
        ["criterion_id", "criterion", "status", "evidence_summary", "evidence_artifact", "paper_interpretation"]
    ]


def _build_claim_support_matrix(root: Path, tables: Path, stage: str) -> pd.DataFrame:
    comparison_path = stage_table_path(tables, "table_model_forecasting_execution_comparison", stage)
    stress_path = stage_table_path(tables, "table_model_stress_comparison", stage)
    bootstrap_path = stage_table_path(tables, "table_rsep_bootstrap_tuned", stage)
    asset_heldout_path = tables / "table_asset_heldout_forecasting_stage3.csv"
    asset_heldout_execution_path = tables / "table_asset_heldout_execution_stage3.csv"
    asset_heldout_bootstrap_path = tables / "table_asset_heldout_rsep_bootstrap_stage3.csv"
    has_asset_heldout = asset_heldout_path.exists()
    asset_execution = _read_csv(asset_heldout_execution_path)
    asset_bootstrap = _read_csv(asset_heldout_bootstrap_path)
    has_asset_heldout_execution = (
        not asset_execution.empty
        and not asset_bootstrap.empty
        and asset_execution.get("direction", pd.Series(dtype=str)).nunique() >= 2
        and asset_bootstrap.get("direction", pd.Series(dtype=str)).nunique() >= 2
    )
    return pd.DataFrame(
        [
            {
                "claim": "Benchmark BTC L2 full-year cho regime-aware forecast-to-execution",
                "status": "SUPPORTED",
                "evidence_summary": "Co pipeline full-year BTC voi forecasting, tuned execution, stress, bootstrap va audit.",
                "recommended_paper_wording": "Chung toi de xuat benchmark/evaluation protocol tren BTC L2 full-year.",
                "evidence_artifact": _evidence_path(comparison_path, root),
            },
            {
                "claim": "Regime shifts lam forecasting va execution metric khac nhau theo regime",
                "status": "SUPPORTED",
                "evidence_summary": "By-regime forecasting/execution tables va regime diagnostics da du de dua vao paper.",
                "recommended_paper_wording": "Ket qua cho thay metric thay doi dang ke giua cac microstructure regimes.",
                "evidence_artifact": _evidence_path(stage_table_path(tables, "table_forecasting_by_regime", stage), root),
            },
            {
                "claim": "Forecasting tot hon khong dam bao execution tot hon",
                "status": "SUPPORTED",
                "evidence_summary": "TCN stride-1 co macro-F1 cao nhung RSEP khong thang cost-aware; gross edge bi cost an mon.",
                "recommended_paper_wording": "Forecasting gain can duoc kiem tra qua cost-aware execution, khong nen doc rieng accuracy/F1.",
                "evidence_artifact": _evidence_path(comparison_path, root),
            },
            {
                "claim": "RSEP la policy universal winner",
                "status": "NOT_SUPPORTED",
                "evidence_summary": "RSEP co support cho SGD/XGBoost nhung khong thang cost-aware tren TCN stride-1.",
                "recommended_paper_wording": "RSEP la selective execution baseline/diagnostic, khong phai policy luon chien thang.",
                "evidence_artifact": _evidence_path(bootstrap_path, root),
            },
            {
                "claim": "Stress grid chung minh edge nhay cam voi fee, latency, spread, depth",
                "status": "SUPPORTED",
                "evidence_summary": "Stress comparison co fee/latency/spread/depth axes cho nhieu model.",
                "recommended_paper_wording": "Robustness duoc bao cao theo stress axes thay vi mot PnL aggregate.",
                "evidence_artifact": _evidence_path(stress_path, root),
            },
            {
                "claim": "Cross-asset BTC<->ETH forecasting/execution duoc evaluate",
                "status": "SUPPORTED" if has_asset_heldout_execution else ("PARTIAL" if has_asset_heldout else "BLOCKED"),
                "evidence_summary": (
                    "Co forecasting, execution/RSEP va bootstrap asset-held-out BTC->ETH, ETH->BTC."
                    if has_asset_heldout_execution
                    else "Co forecasting asset-held-out BTC->ETH va ETH->BTC; chua co execution/RSEP asset-held-out."
                    if has_asset_heldout
                    else "ETH/asset-held-out chua co artifact."
                ),
                "recommended_paper_wording": (
                    "Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution; khong claim policy tao loi nhuan pho quat."
                    if has_asset_heldout_execution
                    else "Ket qua forecasting co evidence cross-asset; execution generalization van la limitation."
                    if has_asset_heldout
                    else "Gioi han hien tai la BTC-only; cross-asset duoc dat la future work hoac extension."
                ),
                "evidence_artifact": (
                    _evidence_path(asset_heldout_execution_path, root)
                    if has_asset_heldout_execution
                    else (_evidence_path(asset_heldout_path, root) if has_asset_heldout else "")
                ),
            },
            {
                "claim": "He thong san sang live trading hoac co profitability",
                "status": "NOT_CLAIMED",
                "evidence_summary": "Simulator snapshot-level L2, khong co L3 queue priority/live execution.",
                "recommended_paper_wording": "Khong claim profitability; chi claim benchmark va failure-analysis.",
                "evidence_artifact": "",
            },
        ]
    )


def _cross_asset_rows(claim_matrix: pd.DataFrame) -> pd.DataFrame:
    if claim_matrix.empty or "claim" not in claim_matrix.columns:
        return pd.DataFrame()
    claim_text = claim_matrix["claim"].astype(str)
    mask = claim_text.str.contains(
        r"cross-asset|generalize qua asset|btc<->eth|btc va eth",
        case=False,
        na=False,
        regex=True,
    )
    rows = claim_matrix.loc[mask].copy()
    if rows.empty:
        return rows
    priority = {"SUPPORTED": 0, "PARTIAL": 1, "BLOCKED": 2}
    rows["_status_priority"] = rows["status"].map(priority).fillna(99)
    return rows.sort_values("_status_priority").drop(columns=["_status_priority"])


def _cross_asset_status(claim_matrix: pd.DataFrame) -> str:
    rows = _cross_asset_rows(claim_matrix)
    if rows.empty:
        return "BLOCKED"
    return str(rows["status"].iloc[0])


def _cross_asset_narrative_line(claim_matrix: pd.DataFrame) -> str:
    status = _cross_asset_status(claim_matrix)
    if status == "SUPPORTED":
        return (
            "- Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution/RSEP voi "
            "source-validation-only tuning; RSEP giam thiet hai so voi cost-aware nhung net PnL van am, "
            "nen khong claim profitable hoac universal policy."
        )
    if status == "PARTIAL":
        return (
            "- Cross-asset hien co forecasting evidence BTC<->ETH nhung execution/RSEP generalization "
            "van phai ha giong."
        )
    return "- Ket qua hien tai la BTC-only; ETH/asset-held-out phai de la BLOCKED/limitation."


def _cross_asset_reviewer_line(claim_matrix: pd.DataFrame) -> str:
    status = _cross_asset_status(claim_matrix)
    if status == "SUPPORTED":
        return (
            "- Diem manh: cross-asset BTC<->ETH da co forecasting, target-asset execution/RSEP "
            "va bootstrap; claim duoc viet la evaluated, khong viet profitability/universal policy."
        )
    if status == "PARTIAL":
        return (
            "- Diem yeu: cross-asset execution/RSEP chua duoc test; chi duoc claim forecasting "
            "asset-held-out la PARTIAL."
        )
    return "- Diem yeu: BTC-only; ETH/asset-held-out hien bi BLOCKED nen khong duoc claim generalization across assets."


def _role_for_model(row: pd.Series) -> str:
    model = str(row.get("model_label", ""))
    if model == "sgd_stage3":
        return "main tabular baseline"
    if model == "xgboost_gpu_stage3":
        return "strong GPU tabular baseline / secondary baseline"
    if model == "tcn_gpu_stage3_stride1":
        return "main temporal fairness baseline with negative execution evidence"
    if model == "tcn_gpu_stage3":
        return "temporal pilot diagnostic / appendix"
    return "supporting baseline"


def _model_caveat(row: pd.Series) -> str:
    model = str(row.get("model_label", ""))
    if model == "xgboost_gpu_stage3":
        return "Accuracy cao hon SGD nhung macro-F1/balanced accuracy thap hon; execution chi cai thien nhe."
    if model == "tcn_gpu_stage3_stride1":
        return "Macro-F1 cao nhat nhung MCC thap hon SGD/XGBoost va RSEP khong thang cost-aware."
    if model == "tcn_gpu_stage3":
        return "Stride-10 sample-window khong nen so truc tiep voi full-row execution."
    if model == "sgd_stage3":
        return "Baseline don gian, de tai lap; dung lam diem neo cho failure-analysis."
    return "Can doc cung protocol va artifact tuong ung."


def _build_final_model_selection(model_summary: pd.DataFrame, models: Sequence[str]) -> pd.DataFrame:
    if model_summary.empty:
        return pd.DataFrame(
            columns=[
                "model_label",
                "recommended_role",
                "accuracy",
                "macro_f1",
                "mcc",
                "balanced_accuracy",
                "test_rows",
                "best_policy",
                "best_policy_net_pnl",
                "rsep_test_net_pnl",
                "bootstrap_mean_diff_vs_cost_aware",
                "bootstrap_ci_low",
                "bootstrap_ci_high",
                "caveat",
            ]
        )
    selection = model_summary.loc[model_summary["model_label"].isin(models)].copy()
    if selection.empty:
        selection = model_summary.copy()
    keep_cols = [
        "model_label",
        "accuracy",
        "macro_f1",
        "mcc",
        "balanced_accuracy",
        "test_rows",
        "best_policy",
        "best_policy_net_pnl",
        "rsep_test_net_pnl",
        "bootstrap_mean_diff_vs_cost_aware",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
    ]
    for col in keep_cols:
        if col not in selection.columns:
            selection[col] = np.nan
    selection["recommended_role"] = selection.apply(_role_for_model, axis=1)
    selection["caveat"] = selection.apply(_model_caveat, axis=1)
    return selection[["model_label", "recommended_role", *keep_cols[1:], "caveat"]]


def _write_narrative(
    path: Path,
    acceptance: pd.DataFrame,
    claim_matrix: pd.DataFrame,
    final_models: pd.DataFrame,
) -> None:
    counts = acceptance["status"].value_counts().to_dict()
    pass_count = int(counts.get("PASS", 0))
    partial_count = int(counts.get("PARTIAL", 0))
    blocked_count = int(counts.get("BLOCKED", 0))
    fail_count = int(counts.get("FAIL", 0))

    best_macro = final_models.sort_values("macro_f1", ascending=False).head(1)
    best_macro_text = "chua xac dinh"
    if not best_macro.empty:
        row = best_macro.iloc[0]
        best_macro_text = f"{row['model_label']} voi macro-F1 {float(row['macro_f1']):.4f}"
    cross_asset_caveat = _cross_asset_narrative_line(claim_matrix)

    lines = [
        "# Stage 3.11 - Narrative evidence pack",
        "",
        "## Ket luan ngan",
        "",
        (
            f"Acceptance bar hien co {pass_count} PASS, {partial_count} PARTIAL, "
            f"{blocked_count} BLOCKED va {fail_count} FAIL. Cach doc phu hop nhat la "
            "benchmark/failure-analysis + robust selective execution, khong phai trading bot sinh loi."
        ),
        "",
        f"Ve forecasting, model manh nhat theo macro-F1 trong bang hien tai la {best_macro_text}. "
        "Tuy nhien TCN stride-1 cho thay bai hoc quan trong: cai thien macro-F1 khong tu dong chuyen thanh "
        "execution/RSEP tot hon.",
        "",
        "## Claim nen giu",
        "",
        "- Regime-aware evaluation la can thiet vi metric forecasting/execution thay doi theo microstructure regime.",
        "- Forecast-to-execution degradation la core evidence: gross edge co the bi phi, spread va stress an mon.",
        "- Stress grid va bootstrap nen duoc dua vao paper de tranh doc ket qua theo mot aggregate duy nhat.",
        "",
        "## Claim phai ha giong",
        "",
        "- RSEP khong nen duoc viet nhu policy universal winner; voi TCN stride-1, bootstrap khong support RSEP thang cost-aware.",
        cross_asset_caveat,
        "- Khong claim profitability, live trading readiness, L3 queue priority hay exact execution realism.",
        "",
        "## Bang nen dua vao paper",
        "",
        "- `table_11_acceptance_bar.csv`: gate reviewer-facing theo 9 tieu chi.",
        "- `table_12_claim_support_matrix.csv`: claim nao supported, partial, blocked hoac not claimed.",
        "- `table_final_model_selection_stage3.csv`: vai tro cong bang cua SGD, XGBoost GPU, TCN pilot va TCN stride-1.",
        "",
        "## Model selection",
        "",
    ]
    for _, row in final_models.iterrows():
        lines.append(
            f"- `{row['model_label']}`: {row['recommended_role']}; "
            f"macro-F1={_safe_float(row.get('macro_f1')):.4f}, MCC={_safe_float(row.get('mcc')):.4f}. "
            f"{row['caveat']}"
        )
    lines.extend(
        [
            "",
            "## Claim matrix summary",
            "",
        ]
    )
    for _, row in claim_matrix.iterrows():
        lines.append(f"- `{row['status']}` - {row['claim']}: {row['recommended_paper_wording']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_audit(
    path: Path,
    run_id: str,
    acceptance: pd.DataFrame,
    claim_matrix: pd.DataFrame,
    final_models: pd.DataFrame,
) -> None:
    counts = acceptance["status"].value_counts().to_dict()
    pass_count = int(counts.get("PASS", 0))
    blocked_count = int(counts.get("BLOCKED", 0))
    partial_count = int(counts.get("PARTIAL", 0))
    fail_count = int(counts.get("FAIL", 0))
    model_lines = []
    for _, row in final_models.iterrows():
        model_lines.append(
            f"- `{row['model_label']}`: role `{row['recommended_role']}`, "
            f"accuracy `{_safe_float(row.get('accuracy')):.4f}`, "
            f"macro-F1 `{_safe_float(row.get('macro_f1')):.4f}`, "
            f"MCC `{_safe_float(row.get('mcc')):.4f}`, caveat: {row['caveat']}"
        )
    criteria_lines = []
    for _, row in acceptance.iterrows():
        criteria_lines.append(
            f"- `{row['criterion_id']}` `{row['status']}` - {row['criterion']}: {row['evidence_summary']}"
        )
    claim_lines = []
    for _, row in claim_matrix.iterrows():
        claim_lines.append(f"- `{row['status']}` - {row['claim']}: {row['recommended_paper_wording']}")
    cross_asset_reviewer_line = _cross_asset_reviewer_line(claim_matrix)
    cross_asset_status = _cross_asset_status(claim_matrix)

    recommendation = (
        "Evidence du de viet paper theo huong benchmark/failure-analysis va selective execution co dieu kien."
        if pass_count >= 4
        else "Can reposition manh hon ve benchmark/failure-analysis; chua du de nhan vao policy improvement."
    )
    lines = [
        "# Audit Stage 3.11 - ICDM evidence hardening",
        "",
        f"- `run_id`: `{run_id}`",
        "- Muc tieu: chot evidence reviewer-facing tu artifact da co, khong train/inference them.",
        "- Pham vi: BTC full-year Stage 3, ETH replication/asset-held-out artifacts neu da co, model tabular va temporal da co.",
        "",
        "## Ket qua acceptance bar",
        "",
        f"- PASS: `{pass_count}`",
        f"- PARTIAL: `{partial_count}`",
        f"- BLOCKED: `{blocked_count}`",
        f"- FAIL: `{fail_count}`",
        "",
        *criteria_lines,
        "",
        "## Model selection",
        "",
        *model_lines,
        "",
        "## Claim-support matrix",
        "",
        *claim_lines,
        "",
        "## Principal ML Scientist view",
        "",
        "- Bang chung manh nhat nam o giao diem regime-aware forecasting, forecast-to-execution degradation, stress grid va bootstrap.",
        "- TCN stride-1 la negative evidence co gia tri: temporal model co macro-F1 tot hon nhung execution khong tu dong tot hon.",
        "- RSEP nen duoc trinh bay nhu baseline selective execution co gate/tuning validation-only, khong phai policy universal winner.",
        "",
        "## Reviewer ICDM view",
        "",
        "- Diem cong: benchmark lon, split theo thoi gian, stress/OOD, bootstrap day-level, claim discipline.",
        cross_asset_reviewer_line,
        "- Can dua negative evidence vao paper thay vi che di: no la bang chung cho thesis forecast-to-execution gap.",
        "",
        "## Go/no-go",
        "",
        f"- Ket luan: {recommendation}",
        (
            "- Buoc tiep theo hop ly: khoa evidence pack va viet IEEE draft tu narrative da co cross-asset."
            if cross_asset_status == "SUPPORTED"
            else "- Buoc tiep theo hop ly: khoa evidence pack, viet narrative paper, hoac bo sung ETH neu muon claim cross-asset."
        ),
        "- Khong can mo them model ad hoc truoc khi draft paper trich ro cac bang Stage 3.11.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_icdm_evidence_pack(
    root: Path,
    stage: str = "stage_3_full_scale",
    models: Sequence[str] = DEFAULT_MODELS,
    run_id: str = "stage3_11_icdm_evidence_hardening",
) -> EvidencePaths:
    root = Path(root)
    tables = _ensure_dir(root / "outputs" / "tables")
    paper = _ensure_dir(root / "outputs" / "paper_assets")
    audits = _ensure_dir(root / "audits")
    stage_slug = _stage_slug(stage)

    model_summary_path = stage_table_path(tables, "table_model_forecasting_execution_comparison", stage)
    model_summary = _normalize_model_summary(_read_csv(model_summary_path))
    by_regime_path = stage_table_path(tables, "table_forecasting_by_regime", stage)
    by_regime = _read_csv(by_regime_path)
    default_exec = _read_csv(stage_table_path(tables, "table_forecast_to_execution", stage))
    tuned_by_regime = _normalize_model_column(
        _read_csv(stage_table_path(tables, "table_forecast_to_execution_tuned_by_regime", stage))
    )
    bootstrap = _normalize_bootstrap(_read_csv(stage_table_path(tables, "table_rsep_bootstrap_tuned", stage)))
    stress = _normalize_stress(_read_csv(stage_table_path(tables, "table_model_stress_comparison", stage)))
    robustness = _normalize_stress(_read_csv(stage_table_path(tables, "table_model_robustness_comparison", stage)))

    acceptance = _build_acceptance_bar(
        root=root,
        tables=tables,
        stage=stage,
        model_summary=model_summary,
        by_regime=by_regime,
        default_exec=default_exec,
        tuned_by_regime=tuned_by_regime,
        bootstrap=bootstrap,
        stress=stress,
        robustness=robustness,
    )
    claim_matrix = _build_claim_support_matrix(root=root, tables=tables, stage=stage)
    final_models = _build_final_model_selection(model_summary=model_summary, models=models)

    acceptance_path = tables / f"table_acceptance_bar_{stage_slug}.csv"
    claim_path = tables / f"table_claim_support_matrix_{stage_slug}.csv"
    final_model_path = tables / f"table_final_model_selection_{stage_slug}.csv"
    paper_acceptance_path = paper / "table_11_acceptance_bar.csv"
    paper_claim_path = paper / "table_12_claim_support_matrix.csv"
    narrative_path = paper / "result_narrative_stage3_11_vi.md"
    audit_path = audits / "audit_stage3_11_icdm_evidence_hardening.md"

    acceptance.to_csv(acceptance_path, index=False)
    claim_matrix.to_csv(claim_path, index=False)
    final_models.to_csv(final_model_path, index=False)
    shutil.copyfile(acceptance_path, paper_acceptance_path)
    shutil.copyfile(claim_path, paper_claim_path)
    _write_narrative(narrative_path, acceptance, claim_matrix, final_models)
    _write_audit(audit_path, run_id, acceptance, claim_matrix, final_models)

    return EvidencePaths(
        acceptance_bar=acceptance_path,
        claim_support=claim_path,
        final_model_selection=final_model_path,
        paper_acceptance_bar=paper_acceptance_path,
        paper_claim_support=paper_claim_path,
        narrative=narrative_path,
        audit=audit_path,
    )


def parse_args() -> object:
    parser = common_parser("Build ICDM Stage 3 evidence pack from existing artifacts.")
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated model labels to include in final model selection.",
    )
    return parser.parse_args()


def main() -> None:
    namespace = parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(root / "outputs" / "logs" / args.run_id / "icdm_evidence_pack.log")
    models_raw = getattr(namespace, "models", ",".join(DEFAULT_MODELS))
    models = tuple(item.strip() for item in str(models_raw).split(",") if item.strip())
    paths = build_icdm_evidence_pack(root=root, stage=args.stage, models=models, run_id=args.run_id)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "15_build_icdm_evidence_pack.py",
        artifacts={name: str(path) for name, path in paths.__dict__.items()},
        extra={
            "symbol": args.symbol,
            "models": list(models),
        },
    )
    logger.info("Wrote Stage 3.11 ICDM evidence pack: %s", paths)


if __name__ == "__main__":
    main()
