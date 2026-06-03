from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.trading_eval import trading_pack
from features.returns_labels import class_return_means_from_parquet
from policies.forecast_threshold import cost_aware_threshold_actions, naive_threshold_actions
from simulator.market_order_sim import ExecutionConfig, simulate_signals
from utils.artifacts import artifact_namespace, namespaced_name, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import read_filtered_frame, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.execution_columns import execution_columns


def main() -> None:
    parser = common_parser("Backtest forecast probabilities qua simulator.")
    args = as_common_args(parser.parse_args())
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/backtest.log"))
    predictions_path = resolve_path(config, str(config["prediction_output"]))
    test = read_filtered_frame(
        predictions_path,
        filters=[("split", "==", "test")],
        columns=execution_columns(include_split=True),
    ).reset_index(drop=True)
    class_returns = class_return_means_from_parquet(predictions_path)
    sim_cfg = ExecutionConfig(**config.get("simulator", {}))
    theta = float(config.get("policies", {}).get("naive_threshold", 0.55))
    edge_threshold = float(config.get("policies", {}).get("cost_aware_edge_threshold", 0.0))
    naive_actions = naive_threshold_actions(test, theta)
    cost_actions = cost_aware_threshold_actions(test, class_returns, edge_threshold)
    naive_trades = simulate_signals(test, naive_actions, sim_cfg, hold_events=int(test["label_horizon_events"].iloc[0]))
    cost_trades = simulate_signals(test, cost_actions, sim_cfg, hold_events=int(test["label_horizon_events"].iloc[0]))

    namespace = artifact_namespace(config)
    model_label = str(config.get("model_label", namespace or ""))
    output_root = resolve_path(config, "data/backtests")
    prefix = model_label if model_label else namespace
    naive_path = output_root / namespaced_name("naive_threshold_trades", prefix, suffix=".parquet")
    cost_path = output_root / namespaced_name("cost_aware_threshold_trades", prefix, suffix=".parquet")
    write_frame(naive_trades, naive_path)
    write_frame(cost_trades, cost_path)
    overall_frames = []
    regime_frames = []
    for name, trades in [("naive_threshold", naive_trades), ("cost_aware_threshold", cost_trades)]:
        overall, regime = trading_pack(name, trades)
        overall_frames.append(overall)
        regime_frames.append(regime)
    overall_table = pd.concat(overall_frames, ignore_index=True)
    regime_table = pd.concat(regime_frames, ignore_index=True)
    tables = resolve_path(config, "outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    if not namespace:
        overall_table.to_csv(tables / "table_forecast_to_execution.csv", index=False)
        regime_table.to_csv(tables / "table_forecast_to_execution_by_regime.csv", index=False)
    overall_table.to_csv(stage_table_path(tables, "table_forecast_to_execution", args.stage, namespace=namespace), index=False)
    regime_table.to_csv(stage_table_path(tables, "table_forecast_to_execution_by_regime", args.stage, namespace=namespace), index=False)
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "05_backtest_forecasts.py",
        artifacts={"naive_trades": naive_path, "cost_trades": cost_path},
        extra={"class_returns": class_returns},
    )
    logger.info("Backtest xong: naive=%s trades, cost-aware=%s trades.", len(naive_trades), len(cost_trades))


if __name__ == "__main__":
    main()
