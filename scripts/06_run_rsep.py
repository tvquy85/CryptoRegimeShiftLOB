from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.bootstrap import paired_day_bootstrap
from evaluation.robustness_eval import regime_gap, worst_regime_return
from evaluation.trading_eval import trading_pack
from features.returns_labels import class_return_means_from_parquet
from policies.rsep import rsep_actions
from policies.rsep_variants import build_rsep_variants
from simulator.market_order_sim import ExecutionConfig, simulate_signals
from utils.artifacts import artifact_namespace, namespaced_name, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import read_filtered_frame, read_frame, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.execution_columns import execution_columns


def main() -> None:
    parser = common_parser("Chạy RSEP và ablation tối thiểu.")
    parser.add_argument("--include-no-cost-gate", action="store_true")
    namespace = parser.parse_args()
    args = as_common_args(namespace)
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/rsep.log"))
    predictions_path = resolve_path(config, str(config["prediction_output"]))
    test = read_filtered_frame(
        predictions_path,
        filters=[("split", "==", "test")],
        columns=execution_columns(include_split=True),
    ).reset_index(drop=True)
    class_returns = class_return_means_from_parquet(predictions_path)
    simulator_cfg = ExecutionConfig(**config.get("simulator", {}))
    base_policy_cfg = config.get("policies", {}).get("rsep", {})
    include_no_cost_gate = bool(base_policy_cfg.get("include_no_cost_gate", False)) or bool(namespace.include_no_cost_gate)
    artifact_ns = artifact_namespace(config)
    model_label = str(config.get("model_label", artifact_ns or ""))

    variants = build_rsep_variants(base_policy_cfg, include_no_cost_gate=include_no_cost_gate)
    overall_rows = []
    regime_rows = []
    trade_paths = {}
    full_trades = pd.DataFrame()
    for name, policy_cfg in variants.items():
        actions, diagnostics = rsep_actions(test, class_returns, policy_cfg, simulator_cfg.fee_bps)
        trades = simulate_signals(test, actions, simulator_cfg, hold_events=int(test["label_horizon_events"].iloc[0]))
        trade_stem = f"{name.lower().replace(' ', '_')}_trades"
        trades_path = resolve_path(config, f"data/backtests/{namespaced_name(trade_stem, model_label or artifact_ns, suffix='.parquet')}")
        write_frame(trades, trades_path)
        trade_paths[name] = trades_path
        overall, by_regime = trading_pack(name, trades)
        overall["worst_regime_return"] = worst_regime_return(by_regime)
        overall["regime_gap"] = regime_gap(by_regime)
        overall_rows.append(overall)
        regime_rows.append(by_regime)
        if name == "RSEP-full":
            full_trades = trades
            diagnostics_path = resolve_path(config, f"data/backtests/{namespaced_name('rsep_full_diagnostics', model_label or artifact_ns, suffix='.parquet')}")
            write_frame(pd.concat([test[["event_time", "regime"]], diagnostics], axis=1), diagnostics_path)

    overall_table = pd.concat(overall_rows, ignore_index=True)
    by_regime_table = pd.concat(regime_rows, ignore_index=True)
    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    overall_table.to_csv(stage_table_path(tables, "table_robust_policy", args.stage, namespace=artifact_ns), index=False)
    overall_table.to_csv(stage_table_path(tables, "table_rsep_ablation", args.stage, namespace=artifact_ns), index=False)
    by_regime_table.to_csv(stage_table_path(tables, "table_rsep_by_regime", args.stage, namespace=artifact_ns), index=False)
    if not artifact_ns:
        overall_table.to_csv(tables / "table_robust_policy.csv", index=False)
        overall_table.to_csv(tables / "table_rsep_ablation.csv", index=False)
        by_regime_table.to_csv(tables / "table_rsep_by_regime.csv", index=False)

    baseline_path = resolve_path(config, f"data/backtests/{namespaced_name('cost_aware_threshold_trades', model_label or artifact_ns, suffix='.parquet')}")
    baseline = read_frame(baseline_path) if baseline_path.exists() else pd.DataFrame()
    bootstrap = paired_day_bootstrap(full_trades, baseline)
    if not artifact_ns:
        pd.DataFrame([bootstrap]).to_csv(tables / "table_rsep_bootstrap_vs_cost_aware.csv", index=False)
    pd.DataFrame([bootstrap]).to_csv(stage_table_path(tables, "table_rsep_bootstrap", args.stage, namespace=artifact_ns), index=False)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "06_run_rsep.py",
        artifacts={key: value for key, value in trade_paths.items()},
        extra={
            "bootstrap_vs_cost_aware": bootstrap,
            "include_no_cost_gate": include_no_cost_gate,
            "omitted_variants": [] if include_no_cost_gate else ["RSEP-no-cost-gate"],
        },
    )
    logger.info("RSEP xong với %s biến thể.", len(variants))


if __name__ == "__main__":
    main()
