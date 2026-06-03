from __future__ import annotations

import pandas as pd

from models.calibration import expected_edge_from_probabilities


def rsep_actions(
    frame: pd.DataFrame,
    class_returns: dict[str, float],
    config: dict[str, float],
    fee_bps: float,
) -> tuple[pd.Series, pd.DataFrame]:
    diagnostics = frame.copy()
    diagnostics["estimated_edge"] = expected_edge_from_probabilities(frame, class_returns)
    diagnostics["estimated_cost"] = frame["rel_spread"] + fee_bps / 10000.0
    diagnostics["latency_risk"] = frame.get("latency_sensitivity_score", 0.0).abs()
    diagnostics["liquidity_risk"] = frame.get("liquidity_drought_score", 0.0).clip(lower=0.0)
    diagnostics["adverse_risk"] = frame.get("adverse_selection_score", 0.0).clip(lower=0.0)
    regime_penalty = {
        "LIQUIDITY_DROUGHT": 1.0,
        "VOLATILE_ILLIQUID": 0.75,
        "MOMENTUM_TOXIC": 0.5,
        "CHOPPY_MEAN_REVERTING": 0.25,
    }
    diagnostics["regime_risk"] = frame["regime"].map(regime_penalty).fillna(0.0)
    diagnostics["required_edge"] = (
        diagnostics["estimated_cost"]
        + float(config.get("lambda_latency", 0.25)) * diagnostics["latency_risk"]
        + float(config.get("lambda_liquidity", 0.25)) * diagnostics["liquidity_risk"]
        + float(config.get("lambda_adverse", 0.25)) * diagnostics["adverse_risk"]
        + float(config.get("lambda_regime", 0.15)) * diagnostics["regime_risk"]
        + float(config.get("theta_edge", 0.0))
    )
    actions = pd.Series(0, index=frame.index, dtype="int8")
    actions.loc[diagnostics["estimated_edge"] > diagnostics["required_edge"]] = 1
    actions.loc[diagnostics["estimated_edge"] < -diagnostics["required_edge"]] = -1
    return actions, diagnostics[
        [
            "estimated_edge",
            "estimated_cost",
            "latency_risk",
            "liquidity_risk",
            "adverse_risk",
            "regime_risk",
            "required_edge",
        ]
    ]

