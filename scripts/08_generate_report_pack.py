from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reports.failure_case_studies import save_failure_cases
from reports.make_figures import plot_model_stress_comparison, plot_stress_curve, plot_worst_regime
from reports.result_pack import assemble_result_pack
from utils.artifacts import artifact_namespace, namespaced_name, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, project_root, resolve_path
from utils.io import read_frame, write_run_metadata
from utils.logging import configure_logging


def main() -> None:
    parser = common_parser("Sinh report pack và paper assets.")
    parser.add_argument("--model-label", default="")
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/report.log"))
    tables = resolve_path(config, "outputs/tables")
    paper = resolve_path(config, str(config.get("paper_assets_output", "outputs/paper_assets")))
    paper.mkdir(parents=True, exist_ok=True)
    artifacts = assemble_result_pack(root, stage=args.stage, paper_assets_dir=paper, tables_dir=tables)
    artifact_ns = artifact_namespace(config)
    stress_path = _prefer_existing(
        stage_table_path(tables, "table_stress_grid_tuned", args.stage, namespace=artifact_ns),
        stage_table_path(tables, "table_stress_grid", args.stage, namespace=artifact_ns),
        tables / "table_stress_grid.csv",
    )
    rsep_regime_path = _prefer_existing(stage_table_path(tables, "table_rsep_by_regime", args.stage, namespace=artifact_ns), tables / "table_rsep_by_regime.csv")
    tuned_regime_path = stage_table_path(tables, "table_forecast_to_execution_tuned_by_regime", args.stage, namespace=artifact_ns)
    legacy_tuned_regime_path = tables / "table_forecast_to_execution_tuned_by_regime_stage2.csv"
    if namespace.model_label and tuned_regime_path.exists():
        rsep_regime_path = tuned_regime_path
    elif namespace.model_label and legacy_tuned_regime_path.exists():
        rsep_regime_path = legacy_tuned_regime_path
    stress = pd.read_csv(stress_path) if stress_path.exists() else pd.DataFrame()
    comparative_stress_path = stage_table_path(tables, "table_model_stress_comparison", args.stage, namespace=artifact_ns)
    comparative_stress = pd.read_csv(comparative_stress_path) if comparative_stress_path.exists() else pd.DataFrame()
    by_regime = pd.read_csv(rsep_regime_path) if rsep_regime_path.exists() else pd.DataFrame()
    figure_artifacts = {}
    if not stress.empty:
        figure_artifacts["fig_4_fee_stress"] = plot_stress_curve(stress, "fee_bps", paper / "fig_4_fee_stress.png")
        figure_artifacts["fig_5_latency_decay"] = plot_stress_curve(stress, "latency_events", paper / "fig_5_latency_decay.png")
    if not comparative_stress.empty:
        figure_artifacts["fig_7_model_fee_stress"] = plot_model_stress_comparison(
            comparative_stress,
            "fee_bps",
            paper / "fig_7_model_fee_stress.png",
        )
        figure_artifacts["fig_8_model_latency_stress"] = plot_model_stress_comparison(
            comparative_stress,
            "latency_events",
            paper / "fig_8_model_latency_stress.png",
        )
    if not by_regime.empty:
        rsep_policy = f"{namespace.model_label}_RSEP-full_tuned" if namespace.model_label else "RSEP-full"
        figure_artifacts["fig_6_worst_regime"] = plot_worst_regime(by_regime[by_regime["policy"] == rsep_policy], paper / "fig_6_worst_regime.png")

    rsep_full_trades_path = resolve_path(config, f"data/backtests/{namespaced_name('rsep-full_trades', artifact_ns, suffix='.parquet')}")
    if namespace.model_label:
        tuned_path = resolve_path(config, f"data/backtests/{namespace.model_label}_rsep_full_tuned_trades.parquet")
        if tuned_path.exists():
            rsep_full_trades_path = tuned_path
    failure_path = paper / "failure_case_studies.csv"
    trades = read_frame(rsep_full_trades_path) if rsep_full_trades_path.exists() else pd.DataFrame()
    save_failure_cases(trades, failure_path)
    all_artifacts = {**artifacts, **figure_artifacts, "failure_cases": failure_path}
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "08_generate_report_pack.py",
        artifacts=all_artifacts,
    )
    logger.info("Report pack xong với %s artifacts.", len(all_artifacts))


def _prefer_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[-1]


if __name__ == "__main__":
    main()
