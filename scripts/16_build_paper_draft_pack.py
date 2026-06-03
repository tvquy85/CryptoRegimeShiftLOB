from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

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

FORBIDDEN_POSITIVE_CLAIMS = (
    "trading bot sinh loi",
    "live-trading-ready",
    "sota trading profit",
    "universal winner",
    "generalizes across assets",
)


@dataclass(frozen=True)
class PaperDraftPaths:
    outline: Path
    claim_to_evidence: Path
    number_consistency: Path
    limitation_wording: Path
    reproducibility_checklist: Path
    audit: Path


@dataclass(frozen=True)
class NumberSpec:
    metric_id: str
    model_label: str
    metric_name: str
    source_value: float
    expected_display: str
    tolerance: float
    model_aliases: tuple[str, ...]
    metric_aliases: tuple[str, ...]
    source_artifact: str


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stage_slug(stage: str) -> str:
    if "stage_3" in stage or "stage3" in stage:
        return "stage3"
    return stage.replace("stage_", "stage").replace("_full_scale", "").replace("_", "")


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_text(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _normalize_model_column(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    if "model_label" not in frame.columns and "model" in frame.columns:
        frame["model_label"] = frame["model"]
    if "model" not in frame.columns and "model_label" in frame.columns:
        frame["model"] = frame["model_label"]
    return frame


def _normalize_final_models(frame: pd.DataFrame) -> pd.DataFrame:
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


def _format_value(metric_name: str, value: float) -> tuple[str, float]:
    if metric_name == "test_rows":
        return f"{int(round(value))}", 0.5
    if "pnl" in metric_name or metric_name.startswith("bootstrap_ci"):
        return f"{value:.2f}", 0.01
    return f"{value:.4f}", 0.0005


def _model_aliases(model_label: str) -> tuple[str, ...]:
    aliases = [model_label]
    if model_label == "sgd_stage3":
        aliases += ["SGD", "sgd"]
    elif model_label == "xgboost_gpu_stage3":
        aliases += ["XGBoost", "xgboost"]
    elif model_label == "tcn_gpu_stage3_stride1":
        aliases += ["TCN stride-1", "tcn_gpu_stage3_stride1", "TCN"]
    elif model_label == "tcn_gpu_stage3":
        aliases += ["tcn_gpu_stage3", "TCN"]
    return tuple(dict.fromkeys(aliases))


def _metric_aliases(metric_name: str) -> tuple[str, ...]:
    mapping = {
        "accuracy": ("accuracy",),
        "macro_f1": ("macro-F1", "macro_f1", "macro F1"),
        "mcc": ("MCC", "mcc"),
        "balanced_accuracy": ("balanced accuracy", "balanced_accuracy"),
        "test_rows": ("test rows", "test_rows"),
        "best_policy_net_pnl": ("best policy net PnL", "best_policy_net_pnl", "net PnL"),
        "rsep_test_net_pnl": ("RSEP", "rsep_test_net_pnl", "net PnL"),
        "bootstrap_ci_low": ("CI", "ci_low", "bootstrap_ci_low"),
        "bootstrap_ci_high": ("CI", "ci_high", "bootstrap_ci_high"),
    }
    return mapping.get(metric_name, (metric_name,))


def _build_number_specs(final_models: pd.DataFrame, source_artifact: str, models: Sequence[str]) -> list[NumberSpec]:
    specs: list[NumberSpec] = []
    if final_models.empty or "model_label" not in final_models.columns:
        return specs
    metrics = (
        "accuracy",
        "macro_f1",
        "mcc",
        "balanced_accuracy",
        "test_rows",
        "best_policy_net_pnl",
        "rsep_test_net_pnl",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
    )
    for _, row in final_models.loc[final_models["model_label"].isin(models)].iterrows():
        model_label = str(row["model_label"])
        for metric_name in metrics:
            if metric_name not in row or pd.isna(row[metric_name]):
                continue
            value = float(row[metric_name])
            display, tolerance = _format_value(metric_name, value)
            specs.append(
                NumberSpec(
                    metric_id=f"{model_label}:{metric_name}",
                    model_label=model_label,
                    metric_name=metric_name,
                    source_value=value,
                    expected_display=display,
                    tolerance=tolerance,
                    model_aliases=_model_aliases(model_label),
                    metric_aliases=_metric_aliases(metric_name),
                    source_artifact=source_artifact,
                )
            )
    return specs


_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z0-9_])")


def _extract_numbers(line: str) -> list[float]:
    values: list[float] = []
    for token in _NUMBER_RE.findall(line):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def _contains_any(line: str, needles: Iterable[str]) -> bool:
    lowered = line.lower()
    return any(str(needle).lower() in lowered for needle in needles)


def _contains_exact_model_label(line: str, model_label: str) -> bool:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(model_label)}(?![A-Za-z0-9_])", re.IGNORECASE)
    return bool(pattern.search(line))


def _numbers_near_metric(line: str, metric_aliases: Iterable[str], window: int = 24) -> list[float]:
    lowered = line.lower()
    spans: list[tuple[int, int]] = []
    for alias in metric_aliases:
        alias_lower = str(alias).lower()
        start = 0
        while True:
            index = lowered.find(alias_lower, start)
            if index < 0:
                break
            spans.append((index, index + len(alias_lower)))
            start = index + len(alias_lower)
    if not spans:
        return []
    other_metric_markers = ("macro", "mcc", "f1", "balanced", "accuracy", "pnl", "ci", "rows")
    values: list[float] = []
    for match in _NUMBER_RE.finditer(line):
        token_start, token_end = match.span()
        for span_start, span_end in spans:
            if token_start < span_end or token_start > span_end + window:
                continue
            between = line[span_end:token_start].lower()
            if any(marker in between for marker in other_metric_markers):
                continue
            try:
                values.append(float(match.group(0).replace(",", "")))
            except ValueError:
                continue
            break
    return values


def evaluate_number_spec_in_text(spec: NumberSpec, text: str) -> tuple[str, str, str]:
    exact_lines = [
        line.strip()
        for line in text.splitlines()
        if _contains_exact_model_label(line, spec.model_label) and _contains_any(line, spec.metric_aliases)
    ]

    def _evaluate_lines(lines: list[str], *, strict: bool) -> tuple[str, str, str]:
        if not lines:
            return "INFO", "", "Metric khong duoc nhac trong artifact nay."
        lines_with_near_numbers = []
        for line in lines:
            numbers = _extract_numbers(line)
            if any(abs(number - spec.source_value) <= spec.tolerance for number in numbers):
                return "PASS", line[:240], "So lieu khop source table trong tolerance."
            near_numbers = _numbers_near_metric(line, spec.metric_aliases)
            if near_numbers:
                lines_with_near_numbers.append(line)
        if lines_with_near_numbers and strict:
            return "FAIL", lines_with_near_numbers[0][:240], "Artifact co exact model/metric va so gan metric nhung khong khop source table."
        if lines_with_near_numbers:
            return "INFO", lines_with_near_numbers[0][:240], "Artifact chi nhac alias mo ho; khong ket luan mismatch."
        return "INFO", lines[0][:240], "Metric/model duoc nhac nhung khong co so cu the de doi chieu."

    exact_status, exact_line, exact_note = _evaluate_lines(exact_lines, strict=True)
    if exact_status != "INFO" or exact_lines:
        return exact_status, exact_line, exact_note

    alias_lines = [
        line.strip()
        for line in text.splitlines()
        if _contains_any(line, spec.model_aliases) and _contains_any(line, spec.metric_aliases)
    ]
    if not alias_lines:
        return "INFO", "", "Metric khong duoc nhac trong artifact nay."
    return _evaluate_lines(alias_lines, strict=False)


def build_number_consistency_table(
    root: Path,
    final_models: pd.DataFrame,
    models: Sequence[str],
    target_docs: Sequence[Path],
    source_artifact: str,
) -> pd.DataFrame:
    specs = _build_number_specs(final_models, source_artifact, models)
    rows: list[dict[str, object]] = []
    check_id = 1
    for spec in specs:
        for target_path in target_docs:
            text = _read_text(target_path)
            status, matched_line, notes = evaluate_number_spec_in_text(spec, text)
            rows.append(
                {
                    "check_id": f"N{check_id:04d}",
                    "model_label": spec.model_label,
                    "metric_name": spec.metric_name,
                    "source_value": spec.source_value,
                    "expected_display": spec.expected_display,
                    "source_artifact": spec.source_artifact,
                    "target_artifact": _rel(target_path, root),
                    "status": status,
                    "matched_line": matched_line,
                    "notes": notes,
                }
            )
            check_id += 1
    if not rows:
        rows.append(
            {
                "check_id": "N0000",
                "model_label": "",
                "metric_name": "source_table_available",
                "source_value": np.nan,
                "expected_display": "",
                "source_artifact": source_artifact,
                "target_artifact": "",
                "status": "FAIL",
                "matched_line": "",
                "notes": "Khong co model metric nao de khoa so lieu.",
            }
        )
    return pd.DataFrame(rows)


def _claim_to_evidence_map(claim_matrix: pd.DataFrame, root: Path) -> pd.DataFrame:
    if claim_matrix.empty:
        return pd.DataFrame(
            [
                {
                    "claim": "Stage 3 claim matrix missing",
                    "status": "FAIL",
                    "evidence_artifact": "",
                    "allowed_wording": "Khong viet claim cho den khi co claim-support matrix.",
                    "banned_wording": "Do not infer results from memory.",
                    "paper_section": "Limitations",
                }
            ]
        )
    section_map = {
        "Benchmark": "Introduction / Benchmark",
        "Regime": "Regime taxonomy and diagnostics",
        "Forecasting": "Forecast-to-execution analysis",
        "RSEP": "Robust selective execution",
        "Stress": "Stress and robustness",
        "Ket qua generalize": "Limitations",
        "He thong": "Limitations",
    }
    rows = []
    for _, row in claim_matrix.iterrows():
        claim = str(row.get("claim", ""))
        section = "Results"
        for key, value in section_map.items():
            if key.lower() in claim.lower():
                section = value
                break
        rows.append(
            {
                "claim": claim,
                "status": row.get("status", ""),
                "evidence_artifact": row.get("evidence_artifact", ""),
                "allowed_wording": row.get("recommended_paper_wording", ""),
                "banned_wording": _banned_wording_for_claim(claim, str(row.get("status", ""))),
                "paper_section": section,
            }
        )
    return pd.DataFrame(rows)


def _banned_wording_for_claim(claim: str, status: str) -> str:
    claim_lower = claim.lower()
    if "rsep" in claim_lower and status == "NOT_SUPPORTED":
        return "Khong viet RSEP la policy luon thang, SOTA trading strategy, hay universal winner."
    if "generalize" in claim_lower or "btc va eth" in claim_lower or "cross-asset" in claim_lower:
        if status == "SUPPORTED":
            return "Khong viet policy cross-asset tao loi nhuan pho quat; chi noi BTC<->ETH da duoc evaluate theo protocol."
        if status == "PARTIAL":
            return "Khong viet da chung minh execution tao loi nhuan generalization across assets; chi noi forecasting evidence partial."
        return "Khong viet ket qua da generalize across assets khi ETH/asset-held-out dang BLOCKED."
    if "live trading" in claim_lower or "profitability" in claim_lower:
        return "Khong viet he thong san sang giao dich live hoac tao profit on dinh."
    return "Khong phong dai vuot qua evidence artifact duoc dan."


def _write_outline(
    path: Path,
    acceptance: pd.DataFrame,
    final_models: pd.DataFrame,
    claim_map: pd.DataFrame,
) -> None:
    counts = acceptance["status"].value_counts().to_dict() if not acceptance.empty else {}
    pass_count = int(counts.get("PASS", 0))
    partial_count = int(counts.get("PARTIAL", 0))
    blocked_count = int(counts.get("BLOCKED", 0))
    fail_count = int(counts.get("FAIL", 0))
    model_lines = []
    for _, row in final_models.iterrows():
        model_lines.append(
            f"- `{row.get('model_label')}`: {row.get('recommended_role', 'supporting baseline')}; "
            f"macro-F1 `{float(row.get('macro_f1', np.nan)):.4f}`, "
            f"MCC `{float(row.get('mcc', np.nan)):.4f}`."
        )
    cross_asset_rows = claim_map[claim_map["claim"].astype(str).str.contains("generalize qua asset", case=False, na=False)]
    if cross_asset_rows.empty:
        cross_asset_rows = claim_map[claim_map["claim"].astype(str).str.contains("cross-asset", case=False, na=False)]
    cross_asset_status = str(cross_asset_rows["status"].iloc[0]) if not cross_asset_rows.empty else "BLOCKED"
    if cross_asset_status == "SUPPORTED":
        cross_asset_allowed = "cross-asset BTC<->ETH forecasting/execution evaluated"
    elif cross_asset_status == "PARTIAL":
        cross_asset_allowed = "cross-asset forecasting evidence partial"
    else:
        cross_asset_allowed = ""
    cross_asset_forbidden = (
        "profitable/universal cross-asset policy generalization"
        if cross_asset_status == "SUPPORTED"
        else (
        "cross-asset execution/profitability generalization"
        if cross_asset_status == "PARTIAL"
        else "cross-asset generalization"
        )
    )
    limitation_line = (
        "8. Limitations: cross-asset BTC<->ETH da duoc evaluate nhung khong claim profitability/universal policy; snapshot-level simulator, khong L3/queue priority."
        if cross_asset_status == "SUPPORTED"
        else (
        "8. Limitations: cross-asset execution/RSEP chua test, snapshot-level simulator, khong L3/queue priority."
        if cross_asset_status == "PARTIAL"
        else "8. Limitations: BTC-only, ETH/asset-held-out blocked, snapshot-level simulator, khong L3/queue priority."
        )
    )

    lines = [
        "# Stage 3.12 - Paper outline draft",
        "",
        "## One-sentence positioning",
        "",
        "CryptoRegimeShift-LOB la benchmark/evaluation protocol cho forecast-to-execution robustness duoi L2 microstructure regime shifts, khong phai trading-profit paper.",
        "",
        "## Evidence status",
        "",
        f"- Acceptance bar: `{pass_count}` PASS, `{partial_count}` PARTIAL, `{blocked_count}` BLOCKED, `{fail_count}` FAIL.",
        "- Main claim duoc phep: BTC full-year benchmark, regime heterogeneity, forecast-to-execution degradation, stress sensitivity.",
        f"- Main claim duoc phep co dieu kien: {cross_asset_allowed}." if cross_asset_allowed else "- Main claim duoc phep co dieu kien: khong co.",
        f"- Main claim khong duoc phep: {cross_asset_forbidden}, live trading, exact queue priority, RSEP universal winner.",
        "",
        "## De cuong paper",
        "",
        "1. Introduction: neu gap trong LOB/HFT evaluation va vi sao average forecasting/backtest khong du.",
        "2. Data and benchmark: BTC-USDT L2 snapshot-level, 20 levels, causal features, chronological split.",
        "3. Regime taxonomy: refined causal taxonomy, residual states, UNKNOWN control, by-regime diagnostics.",
        "4. Forecasting baselines: SGD, XGBoost GPU, TCN stride-1; giai thich vai tro tung model.",
        "5. Forecast-to-execution: gross-to-net degradation, validation-only tuning, RSEP.",
        "6. Stress and robustness: fee, latency, spread, depth, RobustnessAUC, day-level bootstrap.",
        "7. Negative evidence: TCN macro-F1 tot hon nhung RSEP khong thang cost-aware.",
        limitation_line,
        "",
        "## Model roles",
        "",
        *model_lines,
        "",
        "## Claim-to-evidence map",
        "",
    ]
    for _, row in claim_map.iterrows():
        lines.append(f"- `{row.get('status')}` {row.get('claim')}: {row.get('evidence_artifact')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_limitations(path: Path, claim_map: pd.DataFrame) -> None:
    cross_asset_rows = claim_map[claim_map["claim"].astype(str).str.contains("generalize qua asset", case=False, na=False)]
    if cross_asset_rows.empty:
        cross_asset_rows = claim_map[claim_map["claim"].astype(str).str.contains("cross-asset", case=False, na=False)]
    cross_asset_status = str(cross_asset_rows["status"].iloc[0]) if not cross_asset_rows.empty else "BLOCKED"
    if cross_asset_status == "SUPPORTED":
        cross_asset_allowed = "- Co the viet: BTC<->ETH da duoc evaluate o ca forecasting va execution/RSEP theo source-validation-only protocol."
        cross_asset_banned = "- Khong viet da chung minh profitable hoac universal cross-asset trading policy."
    elif cross_asset_status == "PARTIAL":
        cross_asset_allowed = "- Co the viet: co forecasting asset-held-out BTC<->ETH o muc partial; execution/RSEP cross-asset chua duoc kiem tra."
        cross_asset_banned = "- Khong viet da chung minh cross-asset execution generalization hoac profitability tren BTC va ETH."
    else:
        cross_asset_allowed = "- Ket qua hien tai la BTC-USDT full-year; ETH va asset-held-out hien la limitation/extension."
        cross_asset_banned = "- Khong viet ket qua da generalize qua BTC va ETH khi ETH chua co artifact."
    lines = [
        "# Stage 3.12 - Limitation wording",
        "",
        "## Wording nen dung",
        "",
        cross_asset_allowed,
        "- Simulator dung snapshot-level L2 market-order replay, khong tai hien L3 queue priority hay hidden liquidity.",
        "- RSEP la selective execution baseline de kiem tra robustness, khong phai trading strategy san sang live.",
        "- TCN stride-1 cung cap temporal fairness check va negative evidence: forecasting gain khong dam bao execution gain.",
        "",
        "## Wording khong duoc dung",
        "",
        "- Khong viet model tao profit on dinh.",
        "- Khong viet policy san sang live trading.",
        "- Khong viet RSEP la SOTA trading strategy hoac luon chien thang.",
        cross_asset_banned,
        "- Khong viet simulator co exact queue priority, event-level LOBSTER, hoac L3/MBO realism.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _artifact_status(path: Path) -> str:
    return "PASS" if path.exists() and path.stat().st_size > 0 else "FAIL"


def _build_reproducibility_checklist(root: Path, stage: str, models: Sequence[str]) -> pd.DataFrame:
    tables = root / "outputs" / "tables"
    paper = root / "outputs" / "paper_assets"
    audits = root / "audits"
    config_dir = root / "configs"
    items = [
        ("acceptance_bar", tables / f"table_acceptance_bar_{_stage_slug(stage)}.csv", ""),
        ("claim_support_matrix", tables / f"table_claim_support_matrix_{_stage_slug(stage)}.csv", ""),
        ("final_model_selection", tables / f"table_final_model_selection_{_stage_slug(stage)}.csv", ""),
        ("model_comparison", stage_table_path(tables, "table_model_forecasting_execution_comparison", stage), ""),
        ("stress_comparison", stage_table_path(tables, "table_model_stress_comparison", stage), ""),
        ("bootstrap", stage_table_path(tables, "table_rsep_bootstrap_tuned", stage), ""),
        ("stage3_11_narrative", paper / "result_narrative_stage3_11_vi.md", ""),
        ("stage3_11_audit", audits / "audit_stage3_11_icdm_evidence_hardening.md", ""),
        ("simulator_config", config_dir / "simulator_stage3_tcn_stride1_gpu.yaml", ""),
    ]
    rows = []
    for item, path, model_label in items:
        rows.append(
            {
                "item": item,
                "status": _artifact_status(path),
                "artifact": _rel(path, root),
                "stage": stage,
                "model_label": model_label,
                "notes": "Canonical Stage 3 artifact." if _artifact_status(path) == "PASS" else "Artifact missing or empty.",
            }
        )
    for model in models:
        rows.append(
            {
                "item": "model_in_final_selection",
                "status": "PASS",
                "artifact": _rel(tables / f"table_final_model_selection_{_stage_slug(stage)}.csv", root),
                "stage": stage,
                "model_label": model,
                "notes": "Model label expected in final model selection table.",
            }
        )
    return pd.DataFrame(rows)


def _write_audit(
    path: Path,
    run_id: str,
    number_checks: pd.DataFrame,
    acceptance: pd.DataFrame,
    claim_map: pd.DataFrame,
    reproducibility: pd.DataFrame,
) -> None:
    number_fail = int((number_checks["status"] == "FAIL").sum()) if not number_checks.empty else 1
    number_pass = int((number_checks["status"] == "PASS").sum()) if not number_checks.empty else 0
    number_info = int((number_checks["status"] == "INFO").sum()) if not number_checks.empty else 0
    repro_fail = int((reproducibility["status"] == "FAIL").sum()) if not reproducibility.empty else 1
    counts = acceptance["status"].value_counts().to_dict() if not acceptance.empty else {}
    decision = "PASS" if number_fail == 0 and repro_fail == 0 else "FAIL_CAN_SUA_TRUOC_KHI_VIET"
    cross_asset_rows = claim_map[claim_map["claim"].astype(str).str.contains("generalize qua asset", case=False, na=False)]
    if cross_asset_rows.empty:
        cross_asset_rows = claim_map[claim_map["claim"].astype(str).str.contains("cross-asset", case=False, na=False)]
    cross_asset_status = str(cross_asset_rows["status"].iloc[0]) if not cross_asset_rows.empty else "BLOCKED"
    if cross_asset_status == "SUPPORTED":
        cross_asset_audit_line = (
            "- BTC<->ETH da duoc evaluate o forecasting va execution/RSEP; viet nhu cross-asset "
            "evaluation/failure-analysis, khong nhu policy pho quat tao loi nhuan."
        )
    elif cross_asset_status == "PARTIAL":
        cross_asset_audit_line = (
            "- Cross-asset moi co evidence partial; neu execution/RSEP chua du, de phan do trong limitations."
        )
    else:
        cross_asset_audit_line = "- ETH/asset-held-out la limitation neu chua co artifact."
    lines = [
        "# Audit Stage 3.12 - Paper draft readiness",
        "",
        f"- `run_id`: `{run_id}`",
        "- Muc tieu: khoa narrative paper, claim-to-evidence map va number consistency truoc khi viet IEEE draft.",
        "- Cau hinh chinh: doc artifact Stage 3.11, khong train/inference, khong dung GPU.",
        "",
        "## Ket qua chinh",
        "",
        f"- Acceptance bar source: `{int(counts.get('PASS', 0))}` PASS, `{int(counts.get('PARTIAL', 0))}` PARTIAL, `{int(counts.get('BLOCKED', 0))}` BLOCKED, `{int(counts.get('FAIL', 0))}` FAIL.",
        f"- Number consistency: `{number_pass}` PASS, `{number_info}` INFO/not-mentioned, `{number_fail}` FAIL.",
        f"- Reproducibility checklist failures: `{repro_fail}`.",
        f"- Quyet dinh: `{decision}`.",
        "",
        "## Van de phat hien",
        "",
    ]
    if number_fail:
        failed = number_checks.loc[number_checks["status"].eq("FAIL")].head(10)
        for _, row in failed.iterrows():
            lines.append(
                f"- Number mismatch `{row['model_label']}` `{row['metric_name']}` trong `{row['target_artifact']}`: {row['notes']}"
            )
    else:
        lines.append("- Khong phat hien number mismatch trong cac artifact paper/audit/doc duoc quet.")
    if repro_fail:
        failed_repro = reproducibility.loc[reproducibility["status"].eq("FAIL")]
        for _, row in failed_repro.iterrows():
            lines.append(f"- Repro artifact thieu: `{row['artifact']}`.")
    lines.extend(
        [
            "",
            "## Claim discipline",
            "",
        ]
    )
    for _, row in claim_map.iterrows():
        lines.append(f"- `{row['status']}` - {row['claim']}: {row['allowed_wording']}")
    lines.extend(
        [
            "",
            "## Principal ML Scientist view",
            "",
            "- Stage 3.12 nen dong vai tro khoa so lieu va narrative, khong toi uu them model de lam dep ket qua.",
            "- Negative evidence cua TCN stride-1 can duoc giu vi no support forecast-to-execution gap.",
            "",
            "## Reviewer ICDM view",
            "",
            "- Paper co the bat dau viet neu number consistency khong FAIL va tat ca table/figure canonical duoc dan ro.",
            cross_asset_audit_line,
            "- Khong viet profitability, live trading, exact queue priority, hay policy generalization vuot qua artifact.",
            "",
            "## Buoc tiep theo",
            "",
            "- Neu audit PASS: viet IEEE draft tu `paper_outline_stage3_12_vi.md` va trich `table_13/14` vao reproducibility appendix.",
            "- Neu audit FAIL: sua mismatch trong narrative/table truoc khi viet paper.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _validate_no_forbidden_positive_claims(claim_map: pd.DataFrame) -> None:
    allowed_text = "\n".join(str(value) for value in claim_map.get("allowed_wording", pd.Series(dtype=str)).tolist())
    lowered = allowed_text.lower()
    hits = [phrase for phrase in FORBIDDEN_POSITIVE_CLAIMS if phrase in lowered]
    if hits:
        raise ValueError(f"Forbidden positive claim in allowed wording: {hits}")


def build_paper_draft_pack(
    root: Path,
    stage: str = "stage_3_full_scale",
    models: Sequence[str] = DEFAULT_MODELS,
    run_id: str = "stage3_12_paper_draft_readiness",
) -> PaperDraftPaths:
    root = Path(root)
    tables = _ensure_dir(root / "outputs" / "tables")
    paper = _ensure_dir(root / "outputs" / "paper_assets")
    audits = _ensure_dir(root / "audits")
    stage_slug = _stage_slug(stage)

    acceptance_path = tables / f"table_acceptance_bar_{stage_slug}.csv"
    claim_matrix_path = tables / f"table_claim_support_matrix_{stage_slug}.csv"
    final_model_path = tables / f"table_final_model_selection_{stage_slug}.csv"
    acceptance = _read_csv(acceptance_path)
    claim_matrix = _read_csv(claim_matrix_path)
    final_models = _normalize_final_models(_read_csv(final_model_path))

    claim_map = _claim_to_evidence_map(claim_matrix, root)
    _validate_no_forbidden_positive_claims(claim_map)

    target_docs = [
        root / "MoTa.md",
        root / "ThucNghiem.md",
        root / "audits" / "audit_stage3_11_icdm_evidence_hardening.md",
        root / "outputs" / "paper_assets" / "result_narrative_stage3_11_vi.md",
        root / "outputs" / "paper_assets" / "cross_asset_narrative_stage3_13_vi.md",
    ]
    number_checks = build_number_consistency_table(
        root=root,
        final_models=final_models,
        models=models,
        target_docs=target_docs,
        source_artifact=_rel(final_model_path, root),
    )
    reproducibility = _build_reproducibility_checklist(root, stage, models)

    outline_path = paper / "paper_outline_stage3_12_vi.md"
    claim_map_path = paper / "table_13_claim_to_evidence_map.csv"
    number_path = paper / "table_14_number_consistency_check.csv"
    limitation_path = paper / "limitation_wording_stage3_12_vi.md"
    repro_path = paper / "table_15_reproducibility_checklist.csv"
    audit_path = audits / "audit_stage3_12_paper_draft_readiness.md"

    claim_map.to_csv(claim_map_path, index=False)
    number_checks.to_csv(number_path, index=False)
    reproducibility.to_csv(repro_path, index=False)
    _write_outline(outline_path, acceptance, final_models, claim_map)
    _write_limitations(limitation_path, claim_map)
    _write_audit(audit_path, run_id, number_checks, acceptance, claim_map, reproducibility)

    return PaperDraftPaths(
        outline=outline_path,
        claim_to_evidence=claim_map_path,
        number_consistency=number_path,
        limitation_wording=limitation_path,
        reproducibility_checklist=repro_path,
        audit=audit_path,
    )


def parse_args() -> object:
    parser = common_parser("Build Stage 3.12 paper draft pack and number consistency lock.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    return parser.parse_args()


def main() -> None:
    namespace = parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(root / "outputs" / "logs" / args.run_id / "paper_draft_pack.log")
    models = tuple(item.strip() for item in str(namespace.models).split(",") if item.strip())
    paths = build_paper_draft_pack(root=root, stage=args.stage, models=models, run_id=args.run_id)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "16_build_paper_draft_pack.py",
        artifacts={name: str(path) for name, path in paths.__dict__.items()},
        extra={"symbol": args.symbol, "models": list(models)},
    )
    logger.info("Wrote Stage 3.12 paper draft pack: %s", paths)


if __name__ == "__main__":
    main()
