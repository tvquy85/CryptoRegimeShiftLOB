from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from evaluation.trading_eval import trading_pack
from models.calibration import expected_edge_from_probabilities
from policies.forecast_threshold import cost_aware_threshold_actions, naive_threshold_actions
from policies.rsep import rsep_actions
from simulator.market_order_sim import ExecutionConfig, simulate_signals


@dataclass(frozen=True)
class CandidateResult:
    policy: str
    threshold: float
    split: str
    n_trade_days: int
    metrics: dict[str, float]

    def as_row(self, model_label: str, selected: bool = False) -> dict[str, object]:
        return {
            "model": model_label,
            "policy": self.policy,
            "split": self.split,
            "threshold": self.threshold,
            "selected": selected,
            "n_trade_days": self.n_trade_days,
            **self.metrics,
        }


def naive_threshold_grid() -> list[float]:
    return [round(float(value), 2) for value in np.arange(0.50, 0.951, 0.05)]


def edge_threshold_grid(frame: pd.DataFrame, class_returns: dict[str, float], *, rsep_base_required_edge: pd.Series | None = None) -> list[float]:
    edge = expected_edge_from_probabilities(frame, class_returns).abs()
    if rsep_base_required_edge is None:
        base = frame["rel_spread"] + frame.get("label_fee_bps", 1.0) / 10000.0
    else:
        base = rsep_base_required_edge
    positive_margin = (edge - base).clip(lower=0.0)
    positive_margin = positive_margin[positive_margin > 0.0]
    if positive_margin.empty:
        return [0.0]
    quantiles = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.975, 0.99]
    values = [0.0, *[float(positive_margin.quantile(q)) for q in quantiles]]
    return sorted({round(value, 12) for value in values})


def tune_policy(
    frame: pd.DataFrame,
    class_returns: dict[str, float],
    simulator_cfg: ExecutionConfig,
    policy: str,
    thresholds: list[float],
    *,
    rsep_cfg: dict[str, float] | None = None,
    min_trades: int | None = None,
    min_trade_days: int = 5,
) -> tuple[CandidateResult, list[CandidateResult]]:
    minimum = max(1000, int(0.0005 * len(frame))) if min_trades is None else min_trades
    results = [
        evaluate_candidate(frame, class_returns, simulator_cfg, policy, threshold, rsep_cfg=rsep_cfg)
        for threshold in thresholds
    ]
    eligible = [
        result
        for result in results
        if int(result.metrics.get("n_trades", 0)) >= minimum and result.n_trade_days >= min_trade_days
    ]
    pool = eligible or results
    selected = max(pool, key=lambda result: (float(result.metrics.get("net_pnl", 0.0)), -result.threshold))
    return selected, results


def evaluate_candidate(
    frame: pd.DataFrame,
    class_returns: dict[str, float],
    simulator_cfg: ExecutionConfig,
    policy: str,
    threshold: float,
    *,
    rsep_cfg: dict[str, float] | None = None,
    split: str = "valid",
) -> CandidateResult:
    actions = _actions_for_policy(frame, class_returns, policy, threshold, simulator_cfg, rsep_cfg=rsep_cfg)
    trades = simulate_signals(frame, actions, simulator_cfg, hold_events=int(frame["label_horizon_events"].iloc[0]))
    overall, _ = trading_pack(policy, trades)
    metrics = overall.iloc[0].drop(labels=["policy"]).to_dict()
    return CandidateResult(policy=policy, threshold=float(threshold), split=split, n_trade_days=count_trade_days(trades), metrics=metrics)


def actions_for_selected_policy(
    frame: pd.DataFrame,
    class_returns: dict[str, float],
    simulator_cfg: ExecutionConfig,
    policy: str,
    threshold: float,
    *,
    rsep_cfg: dict[str, float] | None = None,
) -> pd.Series:
    return _actions_for_policy(frame, class_returns, policy, threshold, simulator_cfg, rsep_cfg=rsep_cfg)


def count_trade_days(trades: pd.DataFrame) -> int:
    if trades.empty or "event_time" not in trades:
        return 0
    return int(pd.to_datetime(trades["event_time"], utc=True).dt.date.nunique())


def rsep_base_required_edge(frame: pd.DataFrame, config: dict[str, float], fee_bps: float) -> pd.Series:
    zero_theta = {**config, "theta_edge": 0.0}
    _, diagnostics = rsep_actions(frame, {"UP": 0.0, "FLAT": 0.0, "DOWN": 0.0}, zero_theta, fee_bps)
    return diagnostics["required_edge"]


def _actions_for_policy(
    frame: pd.DataFrame,
    class_returns: dict[str, float],
    policy: str,
    threshold: float,
    simulator_cfg: ExecutionConfig,
    *,
    rsep_cfg: dict[str, float] | None,
) -> pd.Series:
    if policy == "naive_threshold":
        return naive_threshold_actions(frame, threshold)
    if policy == "cost_aware_threshold":
        return cost_aware_threshold_actions(frame, class_returns, threshold)
    if policy == "RSEP-full":
        cfg = {**(rsep_cfg or {}), "theta_edge": threshold}
        actions, _ = rsep_actions(frame, class_returns, cfg, simulator_cfg.fee_bps)
        return actions
    raise ValueError(f"Policy khong ho tro: {policy}")
