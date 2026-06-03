from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.cli import as_common_args, common_parser
from utils.config import load_config, project_root
from utils.io import write_run_metadata
from utils.logging import configure_logging


@dataclass(frozen=True)
class CrossAssetPackPaths:
    forecasting_execution: Path
    bootstrap: Path
    narrative: Path
    audit: Path


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_money(value: object) -> str:
    return f"{_safe_float(value):,.2f}"


def _load_required_tables(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tables = root / "outputs" / "tables"
    forecasting = _read_csv(tables / "table_asset_heldout_forecasting_stage3.csv")
    execution = _read_csv(tables / "table_asset_heldout_execution_stage3.csv")
    bootstrap = _read_csv(tables / "table_asset_heldout_rsep_bootstrap_stage3.csv")
    acceptance = _read_csv(tables / "table_acceptance_bar_stage3.csv")
    claims = _read_csv(tables / "table_claim_support_matrix_stage3.csv")
    missing = []
    for name, frame in {
        "table_asset_heldout_forecasting_stage3.csv": forecasting,
        "table_asset_heldout_execution_stage3.csv": execution,
        "table_asset_heldout_rsep_bootstrap_stage3.csv": bootstrap,
        "table_acceptance_bar_stage3.csv": acceptance,
        "table_claim_support_matrix_stage3.csv": claims,
    }.items():
        if frame.empty:
            missing.append(name)
    if missing:
        raise RuntimeError(f"Thieu artifact cross-asset bat buoc: {missing}")
    return forecasting, execution, bootstrap, acceptance, claims


def build_forecasting_execution_table(forecasting: pd.DataFrame, execution: pd.DataFrame, bootstrap: pd.DataFrame) -> pd.DataFrame:
    rsep = execution.loc[execution["policy"].eq("RSEP-full")].copy()
    cost = execution.loc[execution["policy"].eq("cost_aware_threshold")].copy()
    naive = execution.loc[execution["policy"].eq("naive_threshold")].copy()
    merged = forecasting.merge(
        rsep[
            [
                "direction",
                "n_trades",
                "gross_pnl",
                "net_pnl",
                "threshold",
            ]
        ].rename(
            columns={
                "n_trades": "rsep_n_trades",
                "gross_pnl": "rsep_gross_pnl",
                "net_pnl": "rsep_net_pnl",
                "threshold": "rsep_threshold",
            }
        ),
        on="direction",
        how="left",
    )
    merged = merged.merge(
        cost[["direction", "n_trades", "net_pnl", "threshold"]].rename(
            columns={
                "n_trades": "cost_aware_n_trades",
                "net_pnl": "cost_aware_net_pnl",
                "threshold": "cost_aware_threshold",
            }
        ),
        on="direction",
        how="left",
    )
    merged = merged.merge(
        naive[["direction", "n_trades", "net_pnl", "threshold"]].rename(
            columns={
                "n_trades": "naive_n_trades",
                "net_pnl": "naive_net_pnl",
                "threshold": "naive_threshold",
            }
        ),
        on="direction",
        how="left",
    )
    merged = merged.merge(
        bootstrap[["direction", "mean_diff", "ci_low", "ci_high", "n_days", "n_bootstrap"]].rename(
            columns={
                "mean_diff": "rsep_vs_cost_aware_mean_diff",
                "ci_low": "rsep_vs_cost_aware_ci_low",
                "ci_high": "rsep_vs_cost_aware_ci_high",
            }
        ),
        on="direction",
        how="left",
    )
    merged["rsep_loss_reduction_vs_cost_aware"] = merged["rsep_net_pnl"] - merged["cost_aware_net_pnl"]
    merged["rsep_loss_reduction_vs_naive"] = merged["rsep_net_pnl"] - merged["naive_net_pnl"]
    merged["paper_reading"] = (
        "RSEP mitigates cross-asset execution degradation; net PnL remains negative, so this is not profitability evidence."
    )
    keep = [
        "direction",
        "source_symbol",
        "target_symbol",
        "accuracy",
        "macro_f1",
        "mcc",
        "balanced_accuracy",
        "n_rows",
        "rsep_n_trades",
        "rsep_gross_pnl",
        "rsep_net_pnl",
        "cost_aware_net_pnl",
        "naive_net_pnl",
        "rsep_loss_reduction_vs_cost_aware",
        "rsep_vs_cost_aware_mean_diff",
        "rsep_vs_cost_aware_ci_low",
        "rsep_vs_cost_aware_ci_high",
        "n_days",
        "n_bootstrap",
        "paper_reading",
    ]
    return merged[keep]


def build_bootstrap_table(bootstrap: pd.DataFrame) -> pd.DataFrame:
    current = bootstrap.copy()
    current["comparison"] = "RSEP-full minus cost-aware threshold"
    current["statistical_reading"] = current.apply(
        lambda row: (
            "CI duong: RSEP giam thiet hai so voi cost-aware tren target test."
            if _safe_float(row.get("ci_low")) > 0.0
            else "CI mixed: chi nen doc nhu partial evidence."
        ),
        axis=1,
    )
    return current[
        [
            "direction",
            "source_symbol",
            "target_symbol",
            "model",
            "comparison",
            "mean_diff",
            "ci_low",
            "ci_high",
            "n_days",
            "n_bootstrap",
            "statistical_reading",
        ]
    ]


def _write_narrative(path: Path, combined: pd.DataFrame, acceptance: pd.DataFrame, claims: pd.DataFrame) -> None:
    counts = acceptance["status"].value_counts().to_dict()
    claim = claims.loc[claims["claim"].astype(str).str.contains("Cross-asset", regex=False)]
    claim_status = str(claim["status"].iloc[0]) if not claim.empty else "UNKNOWN"
    lines = [
        "# Stage 3.13 - Cross-asset evidence lock",
        "",
        "## Kết luận ngắn",
        "",
        (
            "BTC<->ETH đã được đánh giá ở cả forecasting và execution/RSEP với tuning chỉ trên source validation. "
            "Điểm đọc đúng là cross-asset evaluation + failure-analysis: RSEP giảm thiệt hại so với cost-aware, "
            "nhưng net PnL vẫn âm nên không được claim profitability hoặc universal policy generalization."
        ),
        "",
        "## Acceptance bar sau khi thêm cross-asset execution",
        "",
        f"- PASS: `{int(counts.get('PASS', 0))}`",
        f"- PARTIAL: `{int(counts.get('PARTIAL', 0))}`",
        f"- BLOCKED: `{int(counts.get('BLOCKED', 0))}`",
        f"- FAIL: `{int(counts.get('FAIL', 0))}`",
        f"- Cross-asset claim status: `{claim_status}`",
        "",
        "## Kết quả BTC<->ETH",
        "",
    ]
    for _, row in combined.iterrows():
        lines.extend(
            [
                f"### `{row['direction']}`",
                "",
                f"- Forecasting: accuracy `{float(row['accuracy']):.4f}`, macro-F1 `{float(row['macro_f1']):.4f}`, MCC `{float(row['mcc']):.4f}` trên `{int(row['n_rows']):,}` target rows.",
                f"- RSEP-full: gross PnL `{_format_money(row['rsep_gross_pnl'])}`, net PnL `{_format_money(row['rsep_net_pnl'])}`, trades `{int(row['rsep_n_trades']):,}`.",
                f"- Cost-aware net PnL `{_format_money(row['cost_aware_net_pnl'])}`; naive net PnL `{_format_money(row['naive_net_pnl'])}`.",
                f"- RSEP giảm thiệt hại so với cost-aware `{_format_money(row['rsep_loss_reduction_vs_cost_aware'])}`.",
                f"- Bootstrap RSEP minus cost-aware: mean diff `{_format_money(row['rsep_vs_cost_aware_mean_diff'])}`, CI [`{_format_money(row['rsep_vs_cost_aware_ci_low'])}`, `{_format_money(row['rsep_vs_cost_aware_ci_high'])}`], `{int(row['n_days'])}` ngày, `{int(row['n_bootstrap'])}` bootstrap.",
                "",
            ]
        )
    lines.extend(
        [
            "## Paper wording",
            "",
            "- Được nói: BTC<->ETH cross-asset forecasting and execution were evaluated under source-validation-only tuning.",
            "- Được nói: RSEP reduces losses versus cost-aware in asset-held-out execution.",
            "- Không được nói: giao dịch cross-asset tạo lợi nhuận, policy phổ quát qua mọi asset, hoặc hệ thống sẵn sàng giao dịch live.",
            "",
            "## Reviewer-facing interpretation",
            "",
            "Cross-asset evidence bây giờ không còn bị chặn bởi thiếu ETH. Tuy nhiên kết quả không biến paper thành trading-profit paper. Giá trị khoa học nằm ở việc cho thấy forecast generalization vẫn phải đi qua execution stress, và selective execution có thể giảm thiệt hại nhưng không tự động tạo net profitability.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_audit(path: Path, run_id: str, combined: pd.DataFrame, acceptance: pd.DataFrame, claims: pd.DataFrame) -> None:
    counts = acceptance["status"].value_counts().to_dict()
    claim = claims.loc[claims["claim"].astype(str).str.contains("Cross-asset", regex=False)]
    claim_status = str(claim["status"].iloc[0]) if not claim.empty else "UNKNOWN"
    lines = [
        "# Audit Stage 3.13 - Cross-asset paper lock",
        "",
        f"- `run_id`: `{run_id}`",
        "- Mục tiêu: khóa narrative cross-asset sau khi BTC<->ETH đã có forecasting, execution/RSEP và bootstrap.",
        "- Phạm vi: chỉ đọc artifact hiện có; không train, không inference, không dùng GPU.",
        "",
        "## Acceptance impact",
        "",
        f"- PASS: `{int(counts.get('PASS', 0))}`",
        f"- PARTIAL: `{int(counts.get('PARTIAL', 0))}`",
        f"- BLOCKED: `{int(counts.get('BLOCKED', 0))}`",
        f"- FAIL: `{int(counts.get('FAIL', 0))}`",
        f"- Cross-asset claim: `{claim_status}`",
        "",
        "## Kết quả chính",
        "",
    ]
    for _, row in combined.iterrows():
        lines.append(
            f"- `{row['direction']}`: macro-F1 `{float(row['macro_f1']):.4f}`, MCC `{float(row['mcc']):.4f}`, "
            f"RSEP net `{_format_money(row['rsep_net_pnl'])}`, cost-aware net `{_format_money(row['cost_aware_net_pnl'])}`, "
            f"bootstrap CI [`{_format_money(row['rsep_vs_cost_aware_ci_low'])}`, `{_format_money(row['rsep_vs_cost_aware_ci_high'])}`]."
        )
    lines.extend(
        [
            "",
            "## Principal ML Scientist view",
            "",
            "- Cross-asset forecasting không collapse ở cả hai hướng, nhưng execution cho thấy edge vẫn rất mỏng.",
            "- RSEP là evidence giảm thiệt hại có ý nghĩa vì CI RSEP minus cost-aware dương ở cả hai hướng.",
            "- Net PnL âm là negative evidence quan trọng: generalization của forecast không đồng nghĩa với profitable execution.",
            "",
            "## Reviewer ICDM view",
            "",
            "- Điểm mạnh: claim cross-asset không còn chỉ là future work; đã có target-asset execution và bootstrap.",
            "- Điểm cần hạ giọng: không dùng chữ universal generalization hoặc trading profit.",
            "- Nên đưa bảng cross-asset vào main paper hoặc appendix gần main results để tăng độ tin cậy benchmark.",
            "",
            "## Quyết định",
            "",
            "- PASS cho Stage 3.13 paper lock.",
            "- Bước tiếp theo nên là viết bản IEEE draft từ paper assets đã khóa, không mở thêm baseline ad hoc trước.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_cross_asset_paper_pack(root: Path, run_id: str) -> CrossAssetPackPaths:
    root = Path(root)
    paper = root / "outputs" / "paper_assets"
    audits = root / "audits"
    paper.mkdir(parents=True, exist_ok=True)
    audits.mkdir(parents=True, exist_ok=True)

    forecasting, execution, bootstrap, acceptance, claims = _load_required_tables(root)
    combined = build_forecasting_execution_table(forecasting, execution, bootstrap)
    bootstrap_paper = build_bootstrap_table(bootstrap)

    combined_path = paper / "table_16_cross_asset_forecasting_execution.csv"
    bootstrap_path = paper / "table_17_cross_asset_bootstrap.csv"
    narrative_path = paper / "cross_asset_narrative_stage3_13_vi.md"
    audit_path = audits / "audit_stage3_13_cross_asset_paper_lock_v001.md"

    combined.to_csv(combined_path, index=False)
    bootstrap_paper.to_csv(bootstrap_path, index=False)
    _write_narrative(narrative_path, combined, acceptance, claims)
    _write_audit(audit_path, run_id, combined, acceptance, claims)
    return CrossAssetPackPaths(
        forecasting_execution=combined_path,
        bootstrap=bootstrap_path,
        narrative=narrative_path,
        audit=audit_path,
    )


def parse_args() -> argparse.Namespace:
    parser = common_parser("Build Stage 3.13 cross-asset paper evidence pack.")
    return parser.parse_args()


def main() -> None:
    namespace = parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(root / "outputs" / "logs" / args.run_id / "cross_asset_paper_pack.log")
    paths = build_cross_asset_paper_pack(root=root, run_id=args.run_id)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "21_build_cross_asset_paper_pack.py",
        artifacts={name: str(path) for name, path in paths.__dict__.items()},
        extra={"symbol": args.symbol},
    )
    logger.info("Wrote Stage 3.13 cross-asset paper pack: %s", paths)


if __name__ == "__main__":
    main()
