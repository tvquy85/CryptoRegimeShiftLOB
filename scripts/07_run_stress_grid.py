from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.robustness_eval import latency_half_life, robustness_auc
from features.returns_labels import class_return_means_from_parquet
from policies.rsep import rsep_actions
from simulator.market_order_sim import ExecutionConfig, simulate_signals
from simulator.metrics import summarize_trades
from simulator.stress_engine import apply_stress
from utils.artifacts import artifact_namespace, is_stage2, stage_config_path, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import read_filtered_frame, write_run_metadata
from utils.logging import configure_logging
from utils.execution_columns import execution_columns
from utils.stress_grid import load_stress_grid, stress_grid_source


def main() -> None:
    parser = common_parser("Chạy stress grid execution cho RSEP-full.")
    parser.add_argument("--model-label", default="")
    parser.add_argument("--use-tuned-policy", action="store_true")
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/stress.log"))
    predictions_path = resolve_path(config, str(config["prediction_output"]))
    artifact_ns = artifact_namespace(config)
    test = read_filtered_frame(
        predictions_path,
        filters=[("split", "==", "test")],
        columns=execution_columns(include_split=True),
    ).reset_index(drop=True)
    class_returns = class_return_means_from_parquet(predictions_path)
    base_sim = ExecutionConfig(**config.get("simulator", {}))
    stress_grid = load_stress_grid(config)
    policy_cfg = config.get("policies", {}).get("rsep", {})
    if namespace.use_tuned_policy:
        tuned_path = stage_config_path(resolve_path(config, "configs"), "tuned_policy", args.stage, namespace=artifact_ns)
        if not tuned_path.exists() and not artifact_ns:
            tuned_path = resolve_path(config, "configs/tuned_policy_stage2.yaml")
        tuned = _load_tuned_policy(tuned_path, namespace.model_label)
        theta = tuned.get("selected_thresholds", {}).get("RSEP-full")
        if theta is None:
            raise RuntimeError(f"Khong tim thay RSEP-full tuned threshold cho model={namespace.model_label}.")
        policy_cfg = {**policy_cfg, "theta_edge": float(theta)}
    actions, _ = rsep_actions(test, class_returns, policy_cfg, base_sim.fee_bps)
    hold_events = int(test["label_horizon_events"].iloc[0])
    rows = []
    for axis, levels in stress_grid.items():
        for level in levels:
            stressed = apply_stress(base_sim, **{axis: level})
            trades = simulate_signals(test, actions, stressed, hold_events=hold_events)
            rows.append({"axis": axis, "level": float(level), **summarize_trades(trades)})
    stress = pd.DataFrame(rows)
    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    stress.to_csv(stage_table_path(tables, "table_stress_grid", args.stage, namespace=artifact_ns), index=False)
    if not artifact_ns:
        stress.to_csv(tables / "table_stress_grid.csv", index=False)
    if namespace.use_tuned_policy:
        tuned_stress = stress.copy()
        tuned_stress.insert(0, "model", namespace.model_label)
        _upsert_model_rows(stage_table_path(tables, "table_stress_grid_tuned", args.stage, namespace=artifact_ns), tuned_stress, namespace.model_label)
        if is_stage2(args.stage):
            _upsert_model_rows(tables / "table_stress_grid_tuned_stage2.csv", tuned_stress, namespace.model_label)
    auc_rows = []
    for axis in stress["axis"].dropna().unique():
        subset = stress[stress["axis"] == axis]
        auc_rows.append({"axis": axis, "robustness_auc": robustness_auc(subset, "level")})
    latency_curve = stress[stress["axis"] == "latency_events"].rename(columns={"level": "latency_events"})
    auc_rows.append({"axis": "latency_half_life", "robustness_auc": latency_half_life(latency_curve)})
    robustness = pd.DataFrame(auc_rows)
    robustness.to_csv(stage_table_path(tables, "table_robustness_summary", args.stage, namespace=artifact_ns), index=False)
    if not artifact_ns:
        robustness.to_csv(tables / "table_robustness_summary.csv", index=False)
    if namespace.use_tuned_policy:
        tuned_robustness = robustness.copy()
        tuned_robustness.insert(0, "model", namespace.model_label)
        _upsert_model_rows(stage_table_path(tables, "table_robustness_summary_tuned", args.stage, namespace=artifact_ns), tuned_robustness, namespace.model_label)
        if is_stage2(args.stage):
            _upsert_model_rows(tables / "table_robustness_summary_tuned_stage2.csv", tuned_robustness, namespace.model_label)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "07_run_stress_grid.py",
        artifacts={"stress_table": tables / "table_stress_grid.csv", "robustness_table": tables / "table_robustness_summary.csv"},
        extra={
            "stress_grid_source": stress_grid_source(config),
            "stress_grid": stress_grid,
            "protocol": "fixed predictions and fixed tuned thresholds; one execution axis perturbed at a time",
        },
    )
    logger.info("Stress grid xong với %s dòng summary.", len(stress))


def _load_tuned_policy(path: Path, model_label: str) -> dict[str, object]:
    if not path.exists():
        raise RuntimeError(f"Khong tim thay tuned policy config: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    model_cfg = data.get("models", {}).get(model_label)
    if not model_cfg:
        raise RuntimeError(f"Khong tim thay tuned policy cho model={model_label}.")
    return model_cfg


def _upsert_model_rows(path: Path, rows: pd.DataFrame, model_label: str) -> None:
    if path.exists():
        existing = pd.read_csv(path)
        if "model" in existing.columns:
            existing = existing[existing["model"] != model_label]
        rows = pd.concat([existing, rows], ignore_index=True, sort=False)
    rows.to_csv(path, index=False)


if __name__ == "__main__":
    main()
