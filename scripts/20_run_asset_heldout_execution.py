from __future__ import annotations

import argparse
import gc
import math
import sys
from pathlib import Path

import joblib
import pandas as pd
import polars as pl
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.bootstrap import paired_day_bootstrap
from evaluation.robustness_eval import latency_half_life, robustness_auc
from evaluation.trading_eval import trading_pack
from features.returns_labels import class_return_means_from_parquet
from models.tabular_baselines import predict_probabilities
from policies.tuning import (
    actions_for_selected_policy,
    edge_threshold_grid,
    naive_threshold_grid,
    rsep_base_required_edge,
    tune_policy,
)
from simulator.market_order_sim import ExecutionConfig, simulate_signals
from simulator.stress_engine import apply_stress
from utils.config import load_config, project_root, resolve_path
from utils.execution_columns import execution_columns
from utils.io import read_filtered_frame, write_frame, write_run_metadata
from utils.logging import configure_logging


PREDICTION_COLUMNS = {"prob_down", "prob_flat", "prob_up", "pred_label"}
VALID_POLICIES = ("naive_threshold", "cost_aware_threshold", "RSEP-full")


def main() -> None:
    args = parse_args()
    source_config = load_config(args.source_config)
    target_config = load_config(args.target_config)
    root = project_root(source_config)
    logger = configure_logging(root / "outputs" / "logs" / args.run_id / "asset_heldout_execution.log")

    checkpoint = resolve_path(source_config, args.checkpoint)
    target_predictions = resolve_path(source_config, args.target_predictions)
    if not checkpoint.exists():
        raise FileNotFoundError(f"Khong tim thay checkpoint asset-held-out: {checkpoint}")
    if not target_predictions.exists():
        raise FileNotFoundError(f"Khong tim thay target predictions: {target_predictions}")
    validate_required_columns(target_predictions, execution_columns(include_split=True), "target_predictions")

    bundle = joblib.load(checkpoint)
    source_input = resolve_model_input_path(source_config)
    validate_required_columns(source_input, source_validation_columns(bundle.features), "source_validation_input")

    class_returns = class_return_means_from_parquet(source_input, split="train")
    valid_max_rows = int(source_config.get("policy_tuning_sample_rows", target_config.get("policy_tuning_sample_rows", 5_000_000)))
    logger.info(
        "Tune asset-held-out execution direction=%s source=%s target=%s checkpoint=%s.",
        args.direction,
        args.source_symbol,
        args.target_symbol,
        checkpoint,
    )
    valid = read_source_validation_predictions(source_input, bundle, max_rows=valid_max_rows).reset_index(drop=True)
    if valid.empty:
        raise RuntimeError("Source validation rong, khong the tune cross-asset policy.")
    valid_rows_used = int(len(valid))

    sim_cfg = ExecutionConfig(**target_config.get("simulator", source_config.get("simulator", {})))
    rsep_cfg = target_config.get("policies", source_config.get("policies", {})).get("rsep", {})
    selected, tuning_rows = tune_asset_heldout_policies(
        valid,
        class_returns,
        sim_cfg,
        rsep_cfg,
        args.direction,
        valid_rows_used=valid_rows_used,
    )
    del valid
    gc.collect()

    target = read_filtered_frame(
        target_predictions,
        filters=[("split", "==", "test")],
        columns=execution_columns(include_split=True),
    ).reset_index(drop=True)
    if target.empty:
        raise RuntimeError("Target test rong, khong the evaluate asset-held-out execution.")
    target_rows = int(len(target))
    logger.info("Loaded target test rows=%s cho direction=%s.", target_rows, args.direction)

    test_rows, by_regime_rows, selected_trades, trade_paths = evaluate_on_target(
        target,
        class_returns,
        sim_cfg,
        rsep_cfg,
        selected,
        args.direction,
        args.source_symbol,
        args.target_symbol,
        source_config,
    )
    bootstrap = paired_day_bootstrap(
        selected_trades.get("RSEP-full", pd.DataFrame()),
        selected_trades.get("cost_aware_threshold", pd.DataFrame()),
    )
    stress, robustness = run_rsep_stress(
        target,
        class_returns,
        sim_cfg,
        rsep_cfg,
        selected["RSEP-full"].threshold,
        target_config.get("stress_grid", source_config.get("stress_grid", {})),
        args.direction,
        args.source_symbol,
        args.target_symbol,
    )
    del target
    gc.collect()

    tables_dir = root / "outputs" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    upsert_csv(
        tables_dir / "table_asset_heldout_policy_tuning_stage3.csv",
        pd.DataFrame(tuning_rows),
        key_columns=["direction", "policy", "threshold"],
    )
    upsert_csv(
        tables_dir / "table_asset_heldout_execution_stage3.csv",
        pd.DataFrame(test_rows),
        key_columns=["direction", "policy"],
    )
    if by_regime_rows:
        upsert_csv(
            tables_dir / "table_asset_heldout_execution_by_regime_stage3.csv",
            pd.concat(by_regime_rows, ignore_index=True),
            key_columns=["direction", "policy", "regime"],
        )
    bootstrap_row = {
        "direction": args.direction,
        "source_symbol": args.source_symbol,
        "target_symbol": args.target_symbol,
        "model": f"asset_{args.direction}_sgd",
        **bootstrap,
    }
    upsert_csv(
        tables_dir / "table_asset_heldout_rsep_bootstrap_stage3.csv",
        pd.DataFrame([bootstrap_row]),
        key_columns=["direction"],
    )
    if not stress.empty:
        upsert_csv(
            tables_dir / "table_asset_heldout_stress_stage3.csv",
            stress,
            key_columns=["direction", "policy", "stress_axis", "level"],
        )
    if not robustness.empty:
        upsert_csv(
            tables_dir / "table_asset_heldout_robustness_stage3.csv",
            robustness,
            key_columns=["direction", "policy", "stress_axis"],
        )

    tuned_path = root / "configs" / "tuned_policy_asset_heldout_stage3.yaml"
    tuned_config = load_existing_yaml(tuned_path)
    tuned_config.setdefault("directions", {})[args.direction] = {
        "source_symbol": args.source_symbol,
        "target_symbol": args.target_symbol,
        "checkpoint": str(checkpoint),
        "target_predictions": str(target_predictions),
        "class_returns_source_train": class_returns,
        "selected_thresholds": {policy: result.threshold for policy, result in selected.items()},
        "validation_objective": "source_valid_max_net_pnl_with_min_trades_and_min_trade_days",
        "valid_rows_used_for_tuning": valid_rows_used,
        "target_test_rows": target_rows,
        "target_bootstrap_rsep_vs_cost_aware": bootstrap,
    }
    tuned_path.write_text(yaml.safe_dump(tuned_config, sort_keys=True, allow_unicode=True), encoding="utf-8")

    audit_path = root / "audits" / "audit_stage_eth_4_asset_heldout_execution_rsep_v001.md"
    write_audit(root, audit_path, args.run_id)
    write_run_metadata(
        source_config,
        args.run_id,
        args.stage,
        "20_run_asset_heldout_execution.py",
        artifacts={
            "source_input": source_input,
            "target_predictions": target_predictions,
            "checkpoint": checkpoint,
            "tuned_policy": tuned_path,
            "audit": audit_path,
            **trade_paths,
        },
        extra={
            "direction": args.direction,
            "source_symbol": args.source_symbol,
            "target_symbol": args.target_symbol,
            "valid_rows_used_for_tuning": valid_rows_used,
            "target_test_rows": target_rows,
            "selected_thresholds": {policy: result.threshold for policy, result in selected.items()},
            "bootstrap_rsep_vs_cost_aware": bootstrap,
        },
    )
    logger.info("Asset-held-out execution xong cho %s; target rows=%s.", args.direction, target_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Run asset-held-out execution/RSEP with source-validation tuning.")
    parser.add_argument("--source-config", required=True)
    parser.add_argument("--target-config", required=True)
    parser.add_argument("--source-symbol", required=True)
    parser.add_argument("--target-symbol", required=True)
    parser.add_argument("--direction", choices=["btc_to_eth", "eth_to_btc"], required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--target-predictions", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", default="stage_3_full_scale")
    return parser.parse_args()


def resolve_model_input_path(config: dict[str, object]) -> Path:
    for key in ("split_output", "prediction_output"):
        value = config.get(key)
        if not value:
            continue
        path = resolve_path(config, str(value))
        if path.exists():
            return path
    raise FileNotFoundError("Khong tim thay split_output hoac prediction_output ton tai cho source config.")


def validate_required_columns(path: Path, columns: list[str], context: str) -> None:
    import pyarrow.parquet as pq

    available = set(pq.ParquetFile(path).schema_arrow.names)
    missing = [column for column in columns if column not in available]
    if missing:
        raise RuntimeError(f"{context} thieu cot bat buoc: {missing[:20]}")


def source_validation_columns(features: list[str]) -> list[str]:
    base = [column for column in execution_columns(include_split=True) if column not in PREDICTION_COLUMNS]
    return list(dict.fromkeys([*base, *features]))


def read_source_validation_predictions(path: Path, bundle, *, max_rows: int) -> pd.DataFrame:
    columns = source_validation_columns(bundle.features)
    lazy = pl.scan_parquet(str(path)).filter(pl.col("split") == "valid").select(columns)
    n_rows = int(lazy.select(pl.len()).collect(engine="streaming").item())
    if max_rows > 0 and n_rows > max_rows:
        step = int(math.ceil(n_rows / max_rows))
        lazy = lazy.with_row_index("__sample_index").filter((pl.col("__sample_index") % step) == 0).drop("__sample_index")
    frame = lazy.collect(engine="streaming").to_pandas()
    frame = frame.drop(columns=[column for column in PREDICTION_COLUMNS if column in frame.columns], errors="ignore")
    probs = predict_probabilities(bundle, frame)
    return frame.reset_index(drop=True).join(probs.reset_index(drop=True))


def tune_asset_heldout_policies(
    valid: pd.DataFrame,
    class_returns: dict[str, float],
    sim_cfg: ExecutionConfig,
    rsep_cfg: dict[str, float],
    direction: str,
    *,
    valid_rows_used: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rsep_required = rsep_base_required_edge(valid, rsep_cfg, sim_cfg.fee_bps)
    grids = {
        "naive_threshold": naive_threshold_grid(),
        "cost_aware_threshold": edge_threshold_grid(valid, class_returns),
        "RSEP-full": edge_threshold_grid(valid, class_returns, rsep_base_required_edge=rsep_required),
    }
    selected = {}
    candidate_rows: list[dict[str, object]] = []
    for policy, thresholds in grids.items():
        best, results = tune_policy(
            valid,
            class_returns,
            sim_cfg,
            policy,
            thresholds,
            rsep_cfg=rsep_cfg,
            min_trades=max(1000, int(0.0005 * valid_rows_used)),
            min_trade_days=5,
        )
        selected[policy] = best
        for result in results:
            row = result.as_row(f"asset_{direction}_sgd", selected=result == best)
            row["direction"] = direction
            row["tuning_split"] = "source_valid"
            candidate_rows.append(row)
    return selected, candidate_rows


def evaluate_on_target(
    target: pd.DataFrame,
    class_returns: dict[str, float],
    sim_cfg: ExecutionConfig,
    rsep_cfg: dict[str, float],
    selected: dict[str, object],
    direction: str,
    source_symbol: str,
    target_symbol: str,
    config: dict[str, object],
) -> tuple[list[dict[str, object]], list[pd.DataFrame], dict[str, pd.DataFrame], dict[str, Path]]:
    test_rows: list[dict[str, object]] = []
    by_regime_rows: list[pd.DataFrame] = []
    selected_trades: dict[str, pd.DataFrame] = {}
    trade_paths: dict[str, Path] = {}
    hold_events = int(target["label_horizon_events"].iloc[0])
    for policy in VALID_POLICIES:
        best = selected[policy]
        actions = actions_for_selected_policy(
            target,
            class_returns,
            sim_cfg,
            policy,
            best.threshold,
            rsep_cfg=rsep_cfg,
        )
        trades = simulate_signals(target, actions, sim_cfg, hold_events=hold_events)
        trade_path = resolve_path(
            config,
            f"data/backtests/asset_{direction}_{policy.lower().replace('-', '_')}_tuned_trades.parquet",
        )
        write_frame(trades, trade_path)
        trade_paths[f"{policy}_trades"] = trade_path
        selected_trades[policy] = trades
        overall, by_regime = trading_pack(f"asset_{direction}_{policy}_tuned", trades)
        row = overall.iloc[0].to_dict()
        row.update(
            {
                "direction": direction,
                "source_symbol": source_symbol,
                "target_symbol": target_symbol,
                "model": f"asset_{direction}_sgd",
                "policy": policy,
                "threshold": best.threshold,
                "tuning_split": "source_valid",
            }
        )
        test_rows.append(row)
        if not by_regime.empty:
            by_regime.insert(0, "target_symbol", target_symbol)
            by_regime.insert(0, "source_symbol", source_symbol)
            by_regime.insert(0, "model", f"asset_{direction}_sgd")
            by_regime.insert(0, "direction", direction)
            by_regime["policy"] = policy
            by_regime["threshold"] = best.threshold
            by_regime_rows.append(by_regime)
    return test_rows, by_regime_rows, selected_trades, trade_paths


def run_rsep_stress(
    target: pd.DataFrame,
    class_returns: dict[str, float],
    sim_cfg: ExecutionConfig,
    rsep_cfg: dict[str, float],
    threshold: float,
    stress_grid: dict[str, list[float]],
    direction: str,
    source_symbol: str,
    target_symbol: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not stress_grid:
        return pd.DataFrame(), pd.DataFrame()
    rows: list[dict[str, object]] = []
    hold_events = int(target["label_horizon_events"].iloc[0])
    policy_cfg = {**rsep_cfg, "theta_edge": threshold}
    for axis, levels in stress_grid.items():
        for level in levels:
            stressed = apply_stress(sim_cfg, **{axis: level})
            actions = actions_for_selected_policy(
                target,
                class_returns,
                stressed,
                "RSEP-full",
                threshold,
                rsep_cfg=policy_cfg,
            )
            trades = simulate_signals(target, actions, stressed, hold_events=hold_events)
            overall, _ = trading_pack(f"asset_{direction}_RSEP-full_stress", trades)
            row = overall.iloc[0].drop(labels=["policy"]).to_dict()
            row.update(
                {
                    "direction": direction,
                    "source_symbol": source_symbol,
                    "target_symbol": target_symbol,
                    "model": f"asset_{direction}_sgd",
                    "policy": "RSEP-full",
                    "stress_axis": axis,
                    "level": float(level),
                    axis: float(level),
                }
            )
            rows.append(row)
    stress = pd.DataFrame(rows)
    robustness_rows: list[dict[str, object]] = []
    if not stress.empty:
        for axis in stress["stress_axis"].dropna().unique():
            subset = stress[stress["stress_axis"] == axis]
            robustness_rows.append(
                {
                    "direction": direction,
                    "source_symbol": source_symbol,
                    "target_symbol": target_symbol,
                    "model": f"asset_{direction}_sgd",
                    "policy": "RSEP-full",
                    "stress_axis": axis,
                    "robustness_auc": robustness_auc(subset, "level"),
                }
            )
        latency_curve = stress[stress["stress_axis"] == "latency_events"].copy()
        if "latency_events" not in latency_curve.columns:
            latency_curve["latency_events"] = latency_curve["level"]
        robustness_rows.append(
            {
                "direction": direction,
                "source_symbol": source_symbol,
                "target_symbol": target_symbol,
                "model": f"asset_{direction}_sgd",
                "policy": "RSEP-full",
                "stress_axis": "latency_half_life",
                "robustness_auc": latency_half_life(latency_curve),
            }
        )
    return stress, pd.DataFrame(robustness_rows)


def upsert_csv(path: Path, rows: pd.DataFrame, *, key_columns: list[str]) -> None:
    if rows.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = rows.copy()
    for column in key_columns:
        if column not in rows.columns:
            rows[column] = ""
    if path.exists() and path.stat().st_size > 0:
        current = pd.read_csv(path)
        for column in key_columns:
            if column not in current.columns:
                current[column] = ""
        new_keys = set(map(tuple, rows[key_columns].astype(str).to_numpy()))
        keep_mask = ~current[key_columns].astype(str).apply(tuple, axis=1).isin(new_keys)
        current = current[keep_mask]
        rows = pd.concat([current, rows], ignore_index=True, sort=False)
    rows.to_csv(path, index=False)


def load_existing_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def write_audit(root: Path, path: Path, run_id: str) -> None:
    tables = root / "outputs" / "tables"
    execution = _read_csv(tables / "table_asset_heldout_execution_stage3.csv")
    bootstrap = _read_csv(tables / "table_asset_heldout_rsep_bootstrap_stage3.csv")
    stress = _read_csv(tables / "table_asset_heldout_stress_stage3.csv")
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Audit Stage ETH-4 - Asset-held-out execution/RSEP",
        "",
        f"- `run_id`: `{run_id}`",
        "- Mục tiêu: kiểm tra cross-asset execution/RSEP khi policy được tune trên source validation và evaluate trên target test.",
        "- Phạm vi: BTC->ETH và ETH->BTC với checkpoint SGD asset-held-out đã có; không train thêm model và không dùng target test để tune.",
        "- Boundary: không claim profitability, không claim universal policy generalization.",
        "",
        "## Kết quả execution theo hướng",
        "",
    ]
    if execution.empty:
        lines.append("- Chưa có bảng execution asset-held-out.")
    else:
        for direction, group in execution.groupby("direction", dropna=False):
            lines.append(f"### `{direction}`")
            for _, row in group.sort_values("policy").iterrows():
                lines.append(
                    f"- `{row.get('policy')}`: trades `{int(row.get('n_trades', 0))}`, "
                    f"gross `{float(row.get('gross_pnl', 0.0)):.2f}`, "
                    f"net `{float(row.get('net_pnl', 0.0)):.2f}`, "
                    f"turnover `{float(row.get('turnover', 0.0)):.2f}`."
                )
    lines.extend(["", "## Bootstrap RSEP vs cost-aware", ""])
    if bootstrap.empty:
        lines.append("- Chưa có bootstrap asset-held-out.")
    else:
        for _, row in bootstrap.iterrows():
            lines.append(
                f"- `{row.get('direction')}`: mean diff `{float(row.get('mean_diff', 0.0)):.2f}`, "
                f"CI [`{float(row.get('ci_low', 0.0)):.2f}`, `{float(row.get('ci_high', 0.0)):.2f}`], "
                f"n_days `{int(row.get('n_days', 0))}`, n_bootstrap `{int(row.get('n_bootstrap', 0))}`."
            )
    lines.extend(["", "## Stress/RSEP", ""])
    if stress.empty:
        lines.append("- Chưa có stress asset-held-out hoặc stress bị bỏ qua.")
    else:
        axes = ", ".join(sorted(str(axis) for axis in stress["stress_axis"].dropna().unique()))
        lines.append(f"- Stress axes đã chạy: {axes}.")
        for direction, group in stress.groupby("direction", dropna=False):
            fee = group[group["stress_axis"] == "fee_bps"].sort_values("level")
            if not fee.empty:
                first = fee.iloc[0]
                last = fee.iloc[-1]
                lines.append(
                    f"- `{direction}` fee stress: net từ `{float(first.get('net_pnl', 0.0)):.2f}` "
                    f"ở level `{float(first.get('level', 0.0)):.2f}` xuống `{float(last.get('net_pnl', 0.0)):.2f}` "
                    f"ở level `{float(last.get('level', 0.0)):.2f}`."
                )
    lines.extend(
        [
            "",
            "## Principal ML Scientist view",
            "",
            "- Thiết kế tune source-validation-only là đúng để tránh leakage cross-asset.",
            "- Nếu net PnL âm, kết quả vẫn có giá trị vì nó kiểm tra liệu forecasting generalization có chuyển thành execution edge hay không.",
            "- Nếu RSEP chỉ thắng một hướng hoặc CI mixed, nên trình bày là partial cross-asset execution evidence.",
            "",
            "## Reviewer ICDM view",
            "",
            "- Điểm mạnh: cross-asset không còn dừng ở forecasting; có execution, bootstrap và stress theo target asset.",
            "- Điểm cần hạ giọng: không được viết như universal profitable cross-asset policy.",
            "- Evidence này nên dùng để nâng claim từ `forecasting-only` lên `forecasting + execution evaluated`.",
            "",
            "## Quyết định",
            "",
            "- PASS kỹ thuật nếu cả hai hướng có execution table, bootstrap n_days > 1 và stress không rỗng.",
            "- Kết luận khoa học phụ thuộc CI/stress: SUPPORTED nếu ổn định, PARTIAL nếu mixed hoặc net âm nặng.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
