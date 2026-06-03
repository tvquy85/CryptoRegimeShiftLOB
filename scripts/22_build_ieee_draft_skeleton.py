from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.cli import as_common_args, common_parser  # noqa: E402
from utils.config import load_config, project_root  # noqa: E402
from utils.io import write_run_metadata  # noqa: E402
from utils.logging import configure_logging  # noqa: E402


FORBIDDEN_EXACT_PHRASES = (
    "live-trading-ready",
    "universal profitable policy",
    "profitable cross-asset trading",
    "sota trading profit",
)


@dataclass(frozen=True)
class IEEEDraftSkeletonPaths:
    skeleton: Path
    audit: Path


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _safe_float(value: object, default: float = np.nan) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _money(value: object) -> str:
    return f"{_safe_float(value, 0.0):,.2f}"


def _status_count(acceptance: pd.DataFrame, status: str) -> int:
    if acceptance.empty or "status" not in acceptance.columns:
        return 0
    return int(acceptance["status"].astype(str).eq(status).sum())


def _claim_row(claim_map: pd.DataFrame, needle: str) -> pd.Series:
    if claim_map.empty or "claim" not in claim_map.columns:
        return pd.Series(dtype=object)
    rows = claim_map.loc[claim_map["claim"].astype(str).str.contains(needle, case=False, na=False, regex=False)]
    if rows.empty:
        return pd.Series(dtype=object)
    return rows.iloc[0]


def _claim_wording(claim_map: pd.DataFrame, needle: str, fallback: str) -> str:
    row = _claim_row(claim_map, needle)
    if row.empty:
        return _sanitize_wording(fallback)
    return _sanitize_wording(str(row.get("allowed_wording") or row.get("recommended_paper_wording") or fallback))


def _sanitize_wording(text: str) -> str:
    replacements = {
        "universal profitable policy": "policy tao loi nhuan pho quat",
        "profitable cross-asset trading": "giao dich cross-asset tao loi nhuan",
        "live-trading-ready": "san sang giao dich live",
        "SOTA trading profit": "SOTA ve loi nhuan giao dich",
        "sota trading profit": "SOTA ve loi nhuan giao dich",
    }
    sanitized = text
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)
    return sanitized


def _cross_asset_bullets(cross_asset: pd.DataFrame) -> list[str]:
    if cross_asset.empty:
        return ["- Chua co table cross-asset canonical; khong dua claim cross-asset vao skeleton main result."]
    bullets: list[str] = []
    for _, row in cross_asset.iterrows():
        direction = str(row.get("direction", "unknown"))
        bullets.append(
            "- "
            f"`{direction}`: macro-F1 `{_safe_float(row.get('macro_f1')):.4f}`, "
            f"MCC `{_safe_float(row.get('mcc')):.4f}`, "
            f"RSEP net `{_money(row.get('rsep_net_pnl'))}`, "
            f"cost-aware net `{_money(row.get('cost_aware_net_pnl'))}`, "
            f"bootstrap CI [`{_money(row.get('rsep_vs_cost_aware_ci_low'))}`, "
            f"`{_money(row.get('rsep_vs_cost_aware_ci_high'))}`]."
        )
    return bullets


def _model_bullets(final_models: pd.DataFrame) -> list[str]:
    if final_models.empty:
        return ["- Chua co final model selection table; can regenerate Stage 3.11/3.12 truoc khi viet model section."]
    bullets: list[str] = []
    for _, row in final_models.iterrows():
        bullets.append(
            "- "
            f"`{row.get('model_label')}`: {row.get('recommended_role', 'supporting baseline')}; "
            f"accuracy `{_safe_float(row.get('accuracy')):.4f}`, "
            f"macro-F1 `{_safe_float(row.get('macro_f1')):.4f}`, "
            f"MCC `{_safe_float(row.get('mcc')):.4f}`; "
            f"caveat: {row.get('caveat', 'doc cung execution/stress evidence')}."
        )
    return bullets


def _section(
    title: str,
    claim: str,
    evidence: list[str],
    allowed: str,
    banned: str,
    safe_sentence: str,
) -> list[str]:
    return [
        f"## {title}",
        "",
        f"- Claim chinh: {claim}",
        "- Evidence can trich:",
        *[f"  - `{item}`" if item else "  - " for item in evidence],
        f"- Wording duoc phep: {allowed}",
        f"- Wording khong duoc dung: {banned}",
        f"- Cau viet an toan: {safe_sentence}",
        "",
    ]


def _validate_skeleton_text(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in FORBIDDEN_EXACT_PHRASES if phrase in lowered]


def _write_skeleton(
    path: Path,
    root: Path,
    acceptance: pd.DataFrame,
    claim_map: pd.DataFrame,
    final_models: pd.DataFrame,
    cross_asset: pd.DataFrame,
    bootstrap: pd.DataFrame,
    number_checks: pd.DataFrame,
) -> None:
    pass_count = _status_count(acceptance, "PASS")
    partial_count = _status_count(acceptance, "PARTIAL")
    blocked_count = _status_count(acceptance, "BLOCKED")
    fail_count = _status_count(acceptance, "FAIL")
    number_fail = int(number_checks["status"].astype(str).eq("FAIL").sum()) if not number_checks.empty else -1

    model_lines = _model_bullets(final_models)
    cross_lines = _cross_asset_bullets(cross_asset)
    rsep_claim = _claim_wording(
        claim_map,
        "RSEP la policy universal winner",
        "RSEP la selective execution baseline/diagnostic, khong phai policy luon chien thang.",
    )
    cross_claim = _claim_wording(
        claim_map,
        "Cross-asset",
        "Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution; khong claim policy tao loi nhuan pho quat.",
    )

    lines: list[str] = [
        "# Stage 3.14 - IEEE draft skeleton",
        "",
        "## Cach dung file nay",
        "",
        "File nay la skeleton de viet ban IEEE/ICDM tu artifact da khoa. No khong thay the paper draft, "
        "nhung khoa section, claim, evidence path va wording an toan de tranh overclaim.",
        "",
        "## Evidence lock",
        "",
        f"- Acceptance bar: `{pass_count}` PASS, `{partial_count}` PARTIAL, `{blocked_count}` BLOCKED, `{fail_count}` FAIL.",
        f"- Number consistency FAIL: `{number_fail}`.",
        "- Huong paper: benchmark/failure-analysis + robust selective execution co dieu kien.",
        "- Cross-asset status: BTC<->ETH da co forecasting, execution/RSEP va bootstrap; khong viet nhu trading system tao loi nhuan.",
        "",
        "## Model snapshot",
        "",
        *model_lines,
        "",
        "## Cross-asset snapshot",
        "",
        *cross_lines,
        "",
    ]

    lines.extend(
        _section(
            "1. Introduction",
            "Average forecasting metric khong du de danh gia HFT policy duoi L2 regime shifts.",
            [
                "outputs/paper_assets/table_11_acceptance_bar.csv",
                "outputs/paper_assets/table_12_claim_support_matrix.csv",
                "outputs/paper_assets/result_narrative_stage3_11_vi.md",
            ],
            "Mo ta gap evaluation: forecasting signal co the bien mat khi qua cost, latency va liquidity stress.",
            "Khong viet paper la trading bot hoac strategy tao loi nhuan on dinh.",
            "Chung toi nghien cuu khoang cach forecast-to-execution tren L2 microstructure regimes thay vi toi uu loi nhuan giao dich.",
        )
    )
    lines.extend(
        _section(
            "2. Related Work Positioning",
            "Paper dung DeepLOB/LOB forecasting nhu baseline context, nhung contribution nam o evaluation protocol va execution degradation.",
            [
                "CryptoRegimeShift/MoTa.md",
                "CryptoRegimeShift/ThucNghiem.md",
            ],
            "Dat SGD, XGBoost GPU va TCN nhu baseline phuc vu benchmark; khong claim model moi SOTA.",
            "Khong viet incremental model improvement la novelty chinh.",
            "Khac voi cac paper chi bao forecasting score, thuc nghiem nay noi forecasting voi cost-aware execution va stress.",
        )
    )
    lines.extend(
        _section(
            "3. Data and Benchmark",
            "Benchmark gom BTC-USDT va ETH-USDT L2 snapshot-level full-year voi split theo thoi gian.",
            [
                "CryptoRegimeShift/ThucNghiem.md",
                "outputs/paper_assets/table_1_dataset_stats.csv",
                "outputs/paper_assets/table_15_reproducibility_checklist.csv",
            ],
            "Ghi ro snapshot-level L2, 20 levels, khong L3/MBO queue priority.",
            "Khong viet simulator co exact queue position hoac live market realism.",
            "Du lieu duoc xu ly theo causal pipeline, giu gioi han snapshot-level de dam bao claim dung voi artifact.",
        )
    )
    lines.extend(
        _section(
            "4. Regime Taxonomy",
            "Causal refined taxonomy giam UNKNOWN co ky luat va cho phep by-regime evaluation.",
            [
                "outputs/tables/table_regime_share_stage3.csv",
                "outputs/tables/table_unknown_daily_share_stage3.csv",
                "audits/audit_regime_refinement_v001.md",
            ],
            "Mo ta regime nhu microstructure context co the interpret duoc, khong phai oracle.",
            "Khong viet regime label la ground truth tuyet doi cua market state.",
            "Regime taxonomy duoc dung de do heterogeneity va failure modes, khong de tao nhan tuong lai.",
        )
    )
    lines.extend(
        _section(
            "5. Forecasting Baselines",
            "SGD, XGBoost GPU va TCN stride-1 cung cap baseline tu simple den temporal.",
            [
                "outputs/tables/table_final_model_selection_stage3.csv",
                "outputs/paper_assets/table_8_model_forecasting_execution_comparison.csv",
                "outputs/tables/table_forecasting_by_regime_stage3.csv",
            ],
            "Bao cao accuracy, macro-F1, MCC, balanced accuracy va by-regime thay vi chi mot metric.",
            "Khong viet XGBoost/TCN luon tot hon neu macro-F1/MCC/execution mixed.",
            "TCN stride-1 co macro-F1 cao hon nhung MCC va execution khong tu dong tot hon, nen la negative evidence quan trong.",
        )
    )
    lines.extend(
        _section(
            "6. Forecast-to-Execution",
            "Forecasting edge bi phi, spread, latency va liquidity cost an mon khi dua vao simulator.",
            [
                "outputs/tables/table_model_forecasting_execution_comparison_stage3.csv",
                "outputs/paper_assets/table_4_forecast_to_execution.csv",
                "outputs/paper_assets/table_5_robust_policy.csv",
            ],
            rsep_claim,
            "Khong viet RSEP luon chien thang hoac la strategy san sang giao dich that.",
            "RSEP nen duoc doc nhu selective execution baseline: giam exposure khi edge khong du bu cost/risk.",
        )
    )
    lines.extend(
        _section(
            "7. Stress and Robustness",
            "Stress grid do sensitivity voi fee, latency, spread va depth thay vi chi PnL aggregate.",
            [
                "outputs/paper_assets/table_9_model_stress_comparison.csv",
                "outputs/paper_assets/table_10_model_robustness_comparison.csv",
                "outputs/paper_assets/fig_7_model_fee_stress.png",
                "outputs/paper_assets/fig_8_model_latency_stress.png",
            ],
            "Dung stress curves de chung minh edge mong va OOD sensitivity.",
            "Khong bien mot stress setting thuan loi thanh claim ve loi nhuan on dinh.",
            "RobustnessAUC va stress curves cho thay model/policy phai duoc doc theo dieu kien cost/liquidity.",
        )
    )
    lines.extend(
        _section(
            "8. Cross-Asset BTC<->ETH",
            "BTC<->ETH da duoc evaluate voi source-validation-only tuning o ca forecasting va target-asset execution.",
            [
                "outputs/paper_assets/table_16_cross_asset_forecasting_execution.csv",
                "outputs/paper_assets/table_17_cross_asset_bootstrap.csv",
                "outputs/paper_assets/cross_asset_narrative_stage3_13_vi.md",
            ],
            cross_claim,
            "Khong viet policy co loi nhuan pho quat qua asset hoac ap dung pho quat cho moi market.",
            "Cross-asset evidence cho thay forecast khong collapse va RSEP giam thiet hai, nhung net PnL am nen claim dung la evaluation/failure-analysis.",
        )
    )
    lines.extend(
        _section(
            "9. Limitations",
            "Boundary cua paper la snapshot-level L2 benchmark, khong phai live execution system.",
            [
                "outputs/paper_assets/limitation_wording_stage3_12_vi.md",
                "audits/audit_stage3_13_cross_asset_paper_lock_v001.md",
            ],
            "Ghi ro net PnL am, simulator khong co exact queue priority, va RSEP support khong universal.",
            "Khong bo qua negative evidence cua TCN stride-1 hoac cross-asset net PnL am.",
            "Ket qua am duoc trinh bay nhu bang chung khoa hoc ve forecast-to-execution gap, khong phai that bai can che giau.",
        )
    )

    text = "\n".join(lines) + "\n"
    forbidden_hits = _validate_skeleton_text(text)
    if forbidden_hits:
        raise ValueError(f"Forbidden exact wording in IEEE skeleton: {forbidden_hits}")
    path.write_text(text, encoding="utf-8")


def _write_audit(
    path: Path,
    run_id: str,
    skeleton_path: Path,
    root: Path,
    acceptance: pd.DataFrame,
    number_checks: pd.DataFrame,
) -> None:
    pass_count = _status_count(acceptance, "PASS")
    partial_count = _status_count(acceptance, "PARTIAL")
    blocked_count = _status_count(acceptance, "BLOCKED")
    fail_count = _status_count(acceptance, "FAIL")
    number_fail = int(number_checks["status"].astype(str).eq("FAIL").sum()) if not number_checks.empty else -1
    decision = "PASS" if number_fail == 0 and fail_count == 0 else "FAIL_CAN_SUA"
    lines = [
        "# Audit Stage 3.14 - Paper asset consistency and IEEE draft skeleton",
        "",
        f"- `run_id`: `{run_id}`",
        "- Muc tieu: sua stale narrative cross-asset, khoa evidence asset va tao skeleton IEEE reviewer-facing.",
        "- Cau hinh: chi doc artifact hien co, khong train/inference, khong dung GPU.",
        "",
        "## Ket qua",
        "",
        f"- Acceptance bar: `{pass_count}` PASS, `{partial_count}` PARTIAL, `{blocked_count}` BLOCKED, `{fail_count}` FAIL.",
        f"- Number consistency FAIL: `{number_fail}`.",
        f"- IEEE skeleton: `{_rel(skeleton_path, root)}`.",
        f"- Quyet dinh: `{decision}`.",
        "",
        "## Principal ML Scientist view",
        "",
        "- Narrative hien tai nen dong bang theo evidence: BTC/ETH within-asset, asset-held-out BTC<->ETH va negative evidence TCN stride-1.",
        "- Khong can mo them model ad hoc truoc khi viet draft; neu draft review thay thieu baseline moi quay lai thiet ke Stage 3.15.",
        "",
        "## Reviewer ICDM view",
        "",
        "- Skeleton da map moi section sang table/figure canonical, giup reviewer thay reproducibility va claim discipline.",
        "- Cross-asset duoc viet la evaluated, khong phai loi nhuan hoac policy pho quat.",
        "- Negative evidence duoc giu trong narrative chinh, lam paper dang tin hon.",
        "",
        "## Buoc tiep theo",
        "",
        "- Viet ban IEEE tu `ieee_draft_skeleton_stage3_14_vi.md`.",
        "- Khi viet xong, chay lai number consistency lock truoc khi polish abstract/introduction.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_ieee_draft_skeleton(
    root: Path,
    run_id: str = "stage3_14_paper_asset_consistency_and_draft",
) -> IEEEDraftSkeletonPaths:
    root = Path(root)
    paper = _ensure_dir(root / "outputs" / "paper_assets")
    audits = _ensure_dir(root / "audits")
    tables = root / "outputs" / "tables"

    acceptance = _read_csv(paper / "table_11_acceptance_bar.csv")
    claim_map = _read_csv(paper / "table_13_claim_to_evidence_map.csv")
    final_models = _read_csv(tables / "table_final_model_selection_stage3.csv")
    cross_asset = _read_csv(paper / "table_16_cross_asset_forecasting_execution.csv")
    bootstrap = _read_csv(paper / "table_17_cross_asset_bootstrap.csv")
    number_checks = _read_csv(paper / "table_14_number_consistency_check.csv")

    skeleton_path = paper / "ieee_draft_skeleton_stage3_14_vi.md"
    audit_path = audits / "audit_stage3_14_paper_asset_consistency_and_draft_v001.md"
    _write_skeleton(skeleton_path, root, acceptance, claim_map, final_models, cross_asset, bootstrap, number_checks)
    _write_audit(audit_path, run_id, skeleton_path, root, acceptance, number_checks)
    return IEEEDraftSkeletonPaths(skeleton=skeleton_path, audit=audit_path)


def parse_args() -> object:
    return common_parser("Build Stage 3.14 IEEE draft skeleton from locked paper assets.").parse_args()


def main() -> None:
    namespace = parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(root / "outputs" / "logs" / args.run_id / "ieee_draft_skeleton.log")
    paths = build_ieee_draft_skeleton(root=root, run_id=args.run_id)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "22_build_ieee_draft_skeleton.py",
        artifacts={name: str(path) for name, path in paths.__dict__.items()},
        extra={"symbol": args.symbol},
    )
    logger.info("Wrote Stage 3.14 IEEE draft skeleton: %s", paths)


if __name__ == "__main__":
    main()
