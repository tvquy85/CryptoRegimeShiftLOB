from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.io import write_run_metadata


DEFAULT_MODELS = ("sgd_stage3", "xgboost_gpu_stage3", "tcn_gpu_stage3_stride1")
DEFAULT_POLICIES = ("naive_threshold", "cost_aware_threshold", "RSEP-full")
POLICY_FILE_TOKENS = {
    "naive_threshold": "naive_threshold",
    "cost_aware_threshold": "cost_aware_threshold",
    "RSEP-full": "rsep_full",
}
POLICY_DISPLAY = {
    "naive_threshold": "Naive",
    "cost_aware_threshold": "Cost-aware",
    "RSEP-full": "RSEP-full",
}
MODEL_DISPLAY = {
    "sgd_stage3": "SGD",
    "xgboost_gpu_stage3": "XGBoost",
    "tcn_gpu_stage3_stride1": "TCN stride-1",
}


def trade_path(backtests_dir: Path, model: str, policy: str) -> Path:
    token = POLICY_FILE_TOKENS[policy]
    return backtests_dir / f"{model}_{token}_tuned_trades.parquet"


def read_trade_artifact(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing tuned trade artifact: {path}")
    columns = ["event_time", "gross_pnl", "net_pnl", "total_cost"]
    trades = pd.read_parquet(path, columns=columns)
    if trades.empty:
        return pd.DataFrame(columns=["day", "gross_pnl", "net_pnl", "total_cost"])
    trades["event_time"] = pd.to_datetime(trades["event_time"], utc=True)
    trades["day"] = trades["event_time"].dt.date.astype(str)
    return trades


def daily_execution_frame(trades: pd.DataFrame, all_days: Iterable[str] | None = None) -> pd.DataFrame:
    current = trades.copy()
    if not current.empty and "day" not in current.columns:
        current["event_time"] = pd.to_datetime(current["event_time"], utc=True)
        current["day"] = current["event_time"].dt.date.astype(str)
    if current.empty:
        grouped = pd.DataFrame(columns=["gross_pnl", "net_pnl", "total_cost", "n_trades"])
        grouped.index.name = "day"
    else:
        grouped = current.groupby("day", dropna=False).agg(
            gross_pnl=("gross_pnl", "sum"),
            net_pnl=("net_pnl", "sum"),
            total_cost=("total_cost", "sum"),
            n_trades=("net_pnl", "size"),
        )
    if all_days is not None:
        grouped = grouped.reindex(list(all_days), fill_value=0.0)
    grouped["n_trades"] = grouped["n_trades"].astype(int)
    return grouped.sort_index()


def _bootstrap_policy_arrays(daily: pd.DataFrame, *, seed: int, n_bootstrap: int) -> tuple[np.ndarray, np.ndarray]:
    values = daily["net_pnl"].to_numpy(dtype=float)
    trades = daily["n_trades"].to_numpy(dtype=float)
    if len(values) == 0:
        return np.zeros(n_bootstrap, dtype=float), np.zeros(n_bootstrap, dtype=float)
    rng = np.random.default_rng(seed)
    net_samples = np.empty(n_bootstrap, dtype=float)
    per_trade_samples = np.empty(n_bootstrap, dtype=float)
    for idx in range(n_bootstrap):
        selected = rng.integers(0, len(values), size=len(values))
        net_sum = float(values[selected].sum())
        trade_sum = float(trades[selected].sum())
        net_samples[idx] = net_sum
        per_trade_samples[idx] = net_sum / trade_sum if trade_sum > 0 else np.nan
    return net_samples, per_trade_samples


def _ci(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return 0.0, 0.0
    return float(np.quantile(finite, 0.025)), float(np.quantile(finite, 0.975))


def bootstrap_policy_row(
    *,
    model: str,
    policy: str,
    daily: pd.DataFrame,
    source_artifact: Path,
    seed: int,
    n_bootstrap: int,
) -> dict[str, object]:
    net_samples, per_trade_samples = _bootstrap_policy_arrays(daily, seed=seed, n_bootstrap=n_bootstrap)
    net_low, net_high = _ci(net_samples)
    per_low, per_high = _ci(per_trade_samples)
    n_trades = int(daily["n_trades"].sum()) if not daily.empty else 0
    net_pnl = float(daily["net_pnl"].sum()) if not daily.empty else 0.0
    return {
        "row_type": "policy",
        "model": model,
        "model_display": MODEL_DISPLAY.get(model, model),
        "policy": policy,
        "policy_display": POLICY_DISPLAY.get(policy, policy),
        "comparison_policy": "",
        "diff_target": "",
        "n_trades": n_trades,
        "gross_pnl": float(daily["gross_pnl"].sum()) if not daily.empty else 0.0,
        "net_pnl_mean": net_pnl,
        "net_pnl_ci_low": net_low,
        "net_pnl_ci_high": net_high,
        "total_cost": float(daily["total_cost"].sum()) if not daily.empty else 0.0,
        "net_per_trade_mean": net_pnl / n_trades if n_trades > 0 else 0.0,
        "net_per_trade_ci_low": per_low,
        "net_per_trade_ci_high": per_high,
        "n_days": int(len(daily)),
        "n_bootstrap": int(n_bootstrap),
        "seed": int(seed),
        "source_artifact": str(source_artifact),
    }


def _bootstrap_difference_arrays(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    seed: int,
    n_bootstrap: int,
) -> tuple[np.ndarray, np.ndarray]:
    if not left.index.equals(right.index):
        days = sorted(set(left.index) | set(right.index))
        left = left.reindex(days, fill_value=0.0)
        right = right.reindex(days, fill_value=0.0)
    left_net = left["net_pnl"].to_numpy(dtype=float)
    right_net = right["net_pnl"].to_numpy(dtype=float)
    left_trades = left["n_trades"].to_numpy(dtype=float)
    right_trades = right["n_trades"].to_numpy(dtype=float)
    if len(left_net) == 0:
        return np.zeros(n_bootstrap, dtype=float), np.zeros(n_bootstrap, dtype=float)
    rng = np.random.default_rng(seed)
    net_samples = np.empty(n_bootstrap, dtype=float)
    per_trade_samples = np.empty(n_bootstrap, dtype=float)
    for idx in range(n_bootstrap):
        selected = rng.integers(0, len(left_net), size=len(left_net))
        left_sum = float(left_net[selected].sum())
        right_sum = float(right_net[selected].sum())
        left_trade_sum = float(left_trades[selected].sum())
        right_trade_sum = float(right_trades[selected].sum())
        left_per_trade = left_sum / left_trade_sum if left_trade_sum > 0 else np.nan
        right_per_trade = right_sum / right_trade_sum if right_trade_sum > 0 else np.nan
        net_samples[idx] = left_sum - right_sum
        per_trade_samples[idx] = left_per_trade - right_per_trade
    return net_samples, per_trade_samples


def bootstrap_difference_row(
    *,
    model: str,
    left_policy: str,
    right_policy: str,
    left_daily: pd.DataFrame,
    right_daily: pd.DataFrame,
    seed: int,
    n_bootstrap: int,
) -> dict[str, object]:
    days = sorted(set(left_daily.index) | set(right_daily.index))
    left = left_daily.reindex(days, fill_value=0.0)
    right = right_daily.reindex(days, fill_value=0.0)
    net_samples, per_trade_samples = _bootstrap_difference_arrays(left, right, seed=seed, n_bootstrap=n_bootstrap)
    net_low, net_high = _ci(net_samples)
    per_low, per_high = _ci(per_trade_samples)
    left_net = float(left["net_pnl"].sum())
    right_net = float(right["net_pnl"].sum())
    left_trades = int(left["n_trades"].sum())
    right_trades = int(right["n_trades"].sum())
    left_per_trade = left_net / left_trades if left_trades > 0 else 0.0
    right_per_trade = right_net / right_trades if right_trades > 0 else 0.0
    diff_target = (
        "rsep_minus_cost_aware"
        if right_policy == "cost_aware_threshold"
        else "rsep_minus_naive"
        if right_policy == "naive_threshold"
        else f"{left_policy}_minus_{right_policy}"
    )
    return {
        "row_type": "difference",
        "model": model,
        "model_display": MODEL_DISPLAY.get(model, model),
        "policy": left_policy,
        "policy_display": POLICY_DISPLAY.get(left_policy, left_policy),
        "comparison_policy": right_policy,
        "diff_target": diff_target,
        "n_trades": left_trades,
        "gross_pnl": 0.0,
        "net_pnl_mean": left_net - right_net,
        "net_pnl_ci_low": net_low,
        "net_pnl_ci_high": net_high,
        "total_cost": 0.0,
        "net_per_trade_mean": left_per_trade - right_per_trade,
        "net_per_trade_ci_low": per_low,
        "net_per_trade_ci_high": per_high,
        "n_days": int(len(days)),
        "n_bootstrap": int(n_bootstrap),
        "seed": int(seed),
        "source_artifact": "paired_policy_daily_union",
    }


def build_bootstrap_table(
    *,
    backtests_dir: Path,
    models: Iterable[str],
    policies: Iterable[str],
    seed: int,
    n_bootstrap: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    policy_list = list(policies)
    for model in models:
        trades_by_policy: dict[str, pd.DataFrame] = {}
        days: set[str] = set()
        paths: dict[str, Path] = {}
        for policy in policy_list:
            path = trade_path(backtests_dir, model, policy)
            paths[policy] = path
            trades = read_trade_artifact(path)
            trades_by_policy[policy] = trades
            days.update(trades["day"].dropna().astype(str).unique().tolist())
        all_days = sorted(days)
        daily_by_policy = {
            policy: daily_execution_frame(trades_by_policy[policy], all_days=all_days) for policy in policy_list
        }
        for policy in policy_list:
            rows.append(
                bootstrap_policy_row(
                    model=model,
                    policy=policy,
                    daily=daily_by_policy[policy],
                    source_artifact=paths[policy],
                    seed=seed,
                    n_bootstrap=n_bootstrap,
                )
            )
        if "RSEP-full" in daily_by_policy:
            for comparison in ("cost_aware_threshold", "naive_threshold"):
                if comparison in daily_by_policy:
                    rows.append(
                        bootstrap_difference_row(
                            model=model,
                            left_policy="RSEP-full",
                            right_policy=comparison,
                            left_daily=daily_by_policy["RSEP-full"],
                            right_daily=daily_by_policy[comparison],
                            seed=seed,
                            n_bootstrap=n_bootstrap,
                        )
                    )
    return pd.DataFrame(rows)


def parse_csv_arg(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser("Bootstrap day-level confidence intervals for main execution results.")
    parser.add_argument("--stage", default="stage_3_full_scale")
    parser.add_argument("--run-id", default="p0_07_execution_ci_v001")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--policies", default=",".join(DEFAULT_POLICIES))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--backtests-dir", default="data/backtests")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    backtests_dir = (root / args.backtests_dir).resolve()
    table = build_bootstrap_table(
        backtests_dir=backtests_dir,
        models=parse_csv_arg(args.models),
        policies=parse_csv_arg(args.policies),
        seed=args.seed,
        n_bootstrap=args.n_bootstrap,
    )

    artifacts_dir = root / "artifacts"
    tables_dir = root / "outputs" / "tables"
    paper_dir = root / "outputs" / "paper_assets"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifacts_dir / "bootstrap_main_table.csv"
    table_path = tables_dir / "table_execution_ci_stage3.csv"
    paper_path = paper_dir / "table_22_execution_ci_stage3.csv"
    table.to_csv(artifact_path, index=False)
    table.to_csv(table_path, index=False)
    table.to_csv(paper_path, index=False)

    metadata_config = {
        "_config_path": str(root / "scripts" / "bootstrap_execution_ci.py"),
        "project_root": str(root),
        "stage_ranges": {args.stage: {"start": None, "end": None}},
    }
    write_run_metadata(
        metadata_config,
        args.run_id,
        args.stage,
        "bootstrap_execution_ci.py",
        artifacts={
            "bootstrap_main_table": artifact_path,
            "execution_ci_table": table_path,
            "paper_execution_ci_table": paper_path,
        },
        extra={
            "models": parse_csv_arg(args.models),
            "policies": parse_csv_arg(args.policies),
            "seed": args.seed,
            "n_bootstrap": args.n_bootstrap,
            "bootstrap_unit": "UTC calendar day from event_time",
            "source": str(backtests_dir),
        },
    )
    print(f"Wrote {len(table)} rows to {artifact_path}")


if __name__ == "__main__":
    main()
