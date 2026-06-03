from __future__ import annotations

import gc
import math
import sys
from pathlib import Path

import pandas as pd
import polars as pl
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.bootstrap import paired_day_bootstrap
from evaluation.classification_eval import classification_from_parquet
from evaluation.trading_eval import trading_pack
from features.returns_labels import class_return_means_from_parquet
from policies.tuning import (
    actions_for_selected_policy,
    edge_threshold_grid,
    evaluate_candidate,
    naive_threshold_grid,
    rsep_base_required_edge,
    tune_policy,
)
from simulator.market_order_sim import ExecutionConfig, simulate_signals
from utils.artifacts import artifact_namespace, is_stage2, stage_config_path, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import read_filtered_frame, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.execution_columns import execution_columns


def main() -> None:
    parser = common_parser("Tune execution policies tren validation split.")
    parser.add_argument("--model-label", default="sgd")
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/policy_tuning.log"))
    artifact_ns = artifact_namespace(config)

    predictions_path = resolve_path(config, str(config["prediction_output"]))
    class_returns = class_return_means_from_parquet(predictions_path)
    valid_max_rows = int(config.get("policy_tuning_sample_rows", 5_000_000))
    valid = _read_split_sample(
        predictions_path,
        "valid",
        execution_columns(include_split=True),
        max_rows=valid_max_rows,
    ).reset_index(drop=True)
    if valid.empty:
        raise RuntimeError("Valid split rong, khong the tune policy.")
    valid_rows_used = int(len(valid))

    sim_cfg = ExecutionConfig(**config.get("simulator", {}))
    rsep_cfg = config.get("policies", {}).get("rsep", {})
    rsep_required = rsep_base_required_edge(valid, rsep_cfg, sim_cfg.fee_bps)
    grids = {
        "naive_threshold": naive_threshold_grid(),
        "cost_aware_threshold": edge_threshold_grid(valid, class_returns),
        "RSEP-full": edge_threshold_grid(valid, class_returns, rsep_base_required_edge=rsep_required),
    }

    selected = {}
    candidate_rows = []
    for policy, thresholds in grids.items():
        best, results = tune_policy(
            valid,
            class_returns,
            sim_cfg,
            policy,
            thresholds,
            rsep_cfg=rsep_cfg,
            min_trade_days=5,
        )
        selected[policy] = best
        candidate_rows.extend(result.as_row(namespace.model_label, selected=result == best) for result in results)
        logger.info("Policy %s chon threshold=%s valid_net=%s.", policy, best.threshold, best.metrics.get("net_pnl"))

    del valid
    gc.collect()

    test = read_filtered_frame(
        predictions_path,
        filters=[("split", "==", "test")],
        columns=execution_columns(include_split=True),
    ).reset_index(drop=True)
    test_rows = []
    regime_rows = []
    trade_paths = {}
    selected_trades = {}
    for policy, best in selected.items():
        actions = actions_for_selected_policy(
            test,
            class_returns,
            sim_cfg,
            policy,
            best.threshold,
            rsep_cfg=rsep_cfg,
        )
        trades = simulate_signals(test, actions, sim_cfg, hold_events=int(test["label_horizon_events"].iloc[0]))
        trade_path = resolve_path(
            config,
            f"data/backtests/{namespace.model_label}_{policy.lower().replace('-', '_')}_tuned_trades.parquet",
        )
        write_frame(trades, trade_path)
        trade_paths[policy] = trade_path
        selected_trades[policy] = trades
        overall, by_regime = trading_pack(f"{namespace.model_label}_{policy}_tuned", trades)
        row = overall.iloc[0].to_dict()
        row["model"] = namespace.model_label
        row["base_policy"] = policy
        row["threshold"] = best.threshold
        test_rows.append(row)
        if not by_regime.empty:
            by_regime.insert(0, "model", namespace.model_label)
            by_regime["threshold"] = best.threshold
            regime_rows.append(by_regime)

    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    tuning_table = pd.DataFrame(candidate_rows)
    _upsert_model_rows(stage_table_path(tables, "table_policy_tuning", args.stage, namespace=artifact_ns), tuning_table, namespace.model_label)
    if is_stage2(args.stage):
        _upsert_model_rows(tables / "table_policy_tuning_stage2.csv", tuning_table, namespace.model_label)
    test_table = pd.DataFrame(test_rows)
    _upsert_model_rows(stage_table_path(tables, "table_forecast_to_execution_tuned", args.stage, namespace=artifact_ns), test_table, namespace.model_label)
    if is_stage2(args.stage):
        _upsert_model_rows(tables / "table_forecast_to_execution_tuned_stage2.csv", test_table, namespace.model_label)
    if regime_rows:
        by_regime_table = pd.concat(regime_rows, ignore_index=True)
        _upsert_model_rows(
            stage_table_path(tables, "table_forecast_to_execution_tuned_by_regime", args.stage, namespace=artifact_ns),
            by_regime_table,
            namespace.model_label,
        )
        if is_stage2(args.stage):
            _upsert_model_rows(tables / "table_forecast_to_execution_tuned_by_regime_stage2.csv", by_regime_table, namespace.model_label)

    baseline = selected_trades.get("cost_aware_threshold", pd.DataFrame())
    rsep = selected_trades.get("RSEP-full", pd.DataFrame())
    bootstrap = paired_day_bootstrap(rsep, baseline)
    bootstrap_row = {"model": namespace.model_label, **bootstrap}
    _upsert_model_rows(stage_table_path(tables, "table_rsep_bootstrap_tuned", args.stage, namespace=artifact_ns), pd.DataFrame([bootstrap_row]), namespace.model_label)
    if is_stage2(args.stage):
        _upsert_model_rows(tables / "table_rsep_bootstrap_tuned_stage2.csv", pd.DataFrame([bootstrap_row]), namespace.model_label)

    forecast_metrics, _ = classification_from_parquet(predictions_path)
    best_policy = max(test_rows, key=lambda row: float(row.get("net_pnl", 0.0))) if test_rows else {}
    best_valid_policy = max(selected.values(), key=lambda result: float(result.metrics.get("net_pnl", 0.0)))
    comparison_row = {
        "model": namespace.model_label,
        **forecast_metrics,
        "test_rows": int(len(test)),
        "best_validation_policy": best_valid_policy.policy,
        "best_validation_net_pnl": best_valid_policy.metrics.get("net_pnl", 0.0),
        "best_validation_n_trades": best_valid_policy.metrics.get("n_trades", 0),
        "best_policy": best_policy.get("base_policy", ""),
        "best_policy_net_pnl": best_policy.get("net_pnl", 0.0),
        "best_policy_n_trades": best_policy.get("n_trades", 0),
        "rsep_vs_cost_aware_mean_diff": bootstrap.get("mean_diff", 0.0),
        "rsep_vs_cost_aware_ci_low": bootstrap.get("ci_low", 0.0),
        "rsep_vs_cost_aware_ci_high": bootstrap.get("ci_high", 0.0),
    }
    _upsert_model_rows(stage_table_path(tables, "table_model_comparison", args.stage, namespace=artifact_ns), pd.DataFrame([comparison_row]), namespace.model_label)
    if is_stage2(args.stage):
        _upsert_model_rows(tables / "table_model_comparison_stage2_5.csv", pd.DataFrame([comparison_row]), namespace.model_label)

    tuned_path = stage_config_path(resolve_path(config, "configs"), "tuned_policy", args.stage, namespace=artifact_ns)
    tuned_config = _load_existing_tuned_config(tuned_path)
    tuned_config.setdefault("models", {})[namespace.model_label] = {
        "class_returns": class_returns,
        "selected_thresholds": {policy: result.threshold for policy, result in selected.items()},
        "validation_objective": "max_net_pnl_with_min_trades_and_min_trade_days",
        "min_trades": max(1000, int(0.0005 * valid_rows_used)),
        "min_trade_days": 5,
        "test_bootstrap_rsep_vs_cost_aware": bootstrap,
    }
    with tuned_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(tuned_config, handle, sort_keys=True, allow_unicode=True)
    if is_stage2(args.stage) and not artifact_ns:
        legacy_tuned_path = resolve_path(config, "configs/tuned_policy_stage2.yaml")
        with legacy_tuned_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(tuned_config, handle, sort_keys=True, allow_unicode=True)

    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "09_tune_execution_policies.py",
        artifacts={key: value for key, value in trade_paths.items()},
        extra={
            "model_label": namespace.model_label,
            "selected_thresholds": {policy: result.threshold for policy, result in selected.items()},
            "bootstrap_rsep_vs_cost_aware": bootstrap,
            "valid_rows_used_for_tuning": valid_rows_used,
            "valid_max_rows": valid_max_rows,
        },
    )
    logger.info("Tune policy xong cho model=%s.", namespace.model_label)


def _upsert_model_rows(path: Path, rows: pd.DataFrame, model_label: str) -> None:
    if path.exists():
        existing = pd.read_csv(path)
        if "model" in existing.columns:
            existing = existing[existing["model"] != model_label]
        rows = pd.concat([existing, rows], ignore_index=True)
    rows.to_csv(path, index=False)


def _load_existing_tuned_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _read_split_sample(path: Path, split: str, columns: list[str], *, max_rows: int) -> pd.DataFrame:
    lazy = pl.scan_parquet(str(path)).filter(pl.col("split") == split).select(columns)
    n_rows = int(lazy.select(pl.len()).collect(engine="streaming").item())
    if max_rows > 0 and n_rows > max_rows:
        step = int(math.ceil(n_rows / max_rows))
        lazy = lazy.with_row_index("__sample_index").filter((pl.col("__sample_index") % step) == 0).drop("__sample_index")
    return lazy.collect(engine="streaming").to_pandas()


if __name__ == "__main__":
    main()
