from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reports.make_figures import plot_model_stress_comparison
from reports.make_tables import copy_or_empty_csv
from utils.artifacts import stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, project_root
from utils.io import write_run_metadata
from utils.logging import configure_logging


DEFAULT_MODELS = ("sgd_stage3", "xgboost_gpu_stage3")


def main() -> None:
    parser = common_parser("Tao model-comparative stress pack cho Stage 3.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    root = project_root(config)
    logger = configure_logging(root / "outputs" / "logs" / args.run_id / "comparative_stress_pack.log")
    models = [model.strip() for model in namespace.models.split(",") if model.strip()]
    artifacts = build_comparative_pack(root, stage=args.stage, models=models)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "12_build_model_comparative_stress_pack.py",
        artifacts=artifacts,
        extra={"models": models},
    )
    logger.info("Model-comparative stress pack xong voi %s artifacts.", len(artifacts))


def build_comparative_pack(root: Path, *, stage: str, models: Sequence[str] = DEFAULT_MODELS) -> dict[str, Path]:
    tables = root / "outputs" / "tables"
    figures = root / "outputs" / "figures"
    paper = root / "outputs" / "paper_assets"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    paper.mkdir(parents=True, exist_ok=True)

    model_summary = build_model_summary(tables, stage=stage, models=models)
    model_summary_path = stage_table_path(tables, "table_model_forecasting_execution_comparison", stage)
    model_summary.to_csv(model_summary_path, index=False)

    stress = load_model_rows(
        stress_candidate_paths(tables, "table_stress_grid_tuned", stage),
        models=models,
        key_columns=("model", "axis", "level"),
    )
    stress_path = stage_table_path(tables, "table_model_stress_comparison", stage)
    stress.to_csv(stress_path, index=False)

    robustness = load_model_rows(
        stress_candidate_paths(tables, "table_robustness_summary_tuned", stage),
        models=models,
        key_columns=("model", "axis"),
    )
    robustness_path = stage_table_path(tables, "table_model_robustness_comparison", stage)
    robustness.to_csv(robustness_path, index=False)

    fee_figure = plot_model_stress_comparison(stress, "fee_bps", figures / "model_fee_stress_stage3.png")
    latency_figure = plot_model_stress_comparison(stress, "latency_events", figures / "model_latency_stress_stage3.png")

    artifacts = {
        "model_forecasting_execution_comparison": model_summary_path,
        "model_stress_comparison": stress_path,
        "model_robustness_comparison": robustness_path,
        "model_fee_stress_figure": fee_figure,
        "model_latency_stress_figure": latency_figure,
        "paper_table_8_model_forecasting_execution_comparison": copy_or_empty_csv(
            model_summary_path,
            paper / "table_8_model_forecasting_execution_comparison.csv",
        ),
        "paper_table_9_model_stress_comparison": copy_or_empty_csv(
            stress_path,
            paper / "table_9_model_stress_comparison.csv",
        ),
        "paper_table_10_model_robustness_comparison": copy_or_empty_csv(
            robustness_path,
            paper / "table_10_model_robustness_comparison.csv",
        ),
        "paper_fig_7_model_fee_stress": plot_model_stress_comparison(
            stress,
            "fee_bps",
            paper / "fig_7_model_fee_stress.png",
        ),
        "paper_fig_8_model_latency_stress": plot_model_stress_comparison(
            stress,
            "latency_events",
            paper / "fig_8_model_latency_stress.png",
        ),
    }
    return artifacts


def build_model_summary(tables: Path, *, stage: str, models: Sequence[str]) -> pd.DataFrame:
    model_comparison = _read_csv(stage_table_path(tables, "table_model_comparison", stage))
    if model_comparison.empty:
        model_comparison = _forecasting_summary_from_overall_tables(tables, stage=stage, models=models)
    model_comparison = _filter_models(model_comparison, models)

    tuned = _filter_models(_read_csv(stage_table_path(tables, "table_forecast_to_execution_tuned", stage)), models)
    if not tuned.empty and "base_policy" in tuned.columns:
        rsep = tuned[tuned["base_policy"] == "RSEP-full"].copy()
    else:
        rsep = pd.DataFrame()
    rsep_columns = [
        column
        for column in [
            "model",
            "policy",
            "n_trades",
            "gross_pnl",
            "net_pnl",
            "total_cost",
            "turnover",
            "net_pnl_per_trade",
            "cost_survival",
            "max_drawdown",
            "threshold",
        ]
        if column in rsep.columns
    ]
    rsep = rsep[rsep_columns].rename(
        columns={column: f"rsep_test_{column}" for column in rsep_columns if column != "model"}
    )

    bootstrap = _filter_models(_read_csv(stage_table_path(tables, "table_rsep_bootstrap_tuned", stage)), models)
    bootstrap = bootstrap.rename(
        columns={
            "mean_diff": "bootstrap_rsep_vs_cost_aware_mean_diff",
            "ci_low": "bootstrap_rsep_vs_cost_aware_ci_low",
            "ci_high": "bootstrap_rsep_vs_cost_aware_ci_high",
        }
    )

    summary = pd.DataFrame({"model": list(models)})
    summary = summary.merge(model_comparison, on="model", how="left")
    if not rsep.empty:
        summary = summary.merge(rsep, on="model", how="left")
    if not bootstrap.empty:
        summary = summary.merge(bootstrap, on="model", how="left")
    return _sort_by_model(summary, models)


def load_model_rows(paths: Iterable[Path], *, models: Sequence[str], key_columns: Sequence[str]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = _read_csv(path)
        if frame.empty or "model" not in frame.columns:
            continue
        frames.append(_filter_models(frame, models))
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["model"])
    existing_keys = [column for column in key_columns if column in combined.columns]
    if existing_keys:
        combined = combined.drop_duplicates(subset=existing_keys, keep="first")
    return _sort_by_model(combined, models)


def stress_candidate_paths(tables: Path, stem: str, stage: str) -> list[Path]:
    stage_path = stage_table_path(tables, stem, stage)
    return [
        stage_path,
        tables / f"{stem}_stage3.csv",
        tables / f"{stem}_stage2.csv",
        tables / f"{stem}.csv",
    ]


def _forecasting_summary_from_overall_tables(tables: Path, *, stage: str, models: Sequence[str]) -> pd.DataFrame:
    rows = []
    for model in models:
        if model == "sgd_stage3":
            path = stage_table_path(tables, "table_forecasting_overall", stage)
        elif model == "xgboost_gpu_stage3":
            path = tables / "table_forecasting_overall_stage3_xgboost_gpu.csv"
        else:
            path = tables / f"table_forecasting_overall_{model}.csv"
        frame = _read_csv(path)
        if frame.empty:
            rows.append({"model": model})
            continue
        row = frame.iloc[0].to_dict()
        row["model"] = row.get("model", model)
        rows.append(row)
    return pd.DataFrame(rows)


def _filter_models(frame: pd.DataFrame, models: Sequence[str]) -> pd.DataFrame:
    if frame.empty:
        return frame
    if "model" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["model"].isin(models)].copy()


def _sort_by_model(frame: pd.DataFrame, models: Sequence[str]) -> pd.DataFrame:
    if frame.empty or "model" not in frame.columns:
        return frame
    order = {model: rank for rank, model in enumerate(models)}
    sorted_frame = frame.copy()
    sorted_frame["_model_order"] = sorted_frame["model"].map(order).fillna(len(order))
    sort_columns = ["_model_order"]
    if "axis" in sorted_frame.columns:
        sort_columns.append("axis")
    if "level" in sorted_frame.columns:
        sort_columns.append("level")
    sorted_frame = sorted_frame.sort_values(sort_columns).drop(columns=["_model_order"])
    return sorted_frame.reset_index(drop=True)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


if __name__ == "__main__":
    main()
