from __future__ import annotations

import pandas as pd

from models.calibration import expected_edge_from_probabilities


def naive_threshold_actions(frame: pd.DataFrame, threshold: float) -> pd.Series:
    actions = pd.Series(0, index=frame.index, dtype="int8")
    actions.loc[frame["prob_up"] > threshold] = 1
    actions.loc[frame["prob_down"] > threshold] = -1
    both = (frame["prob_up"] > threshold) & (frame["prob_down"] > threshold)
    actions.loc[both] = 0
    return actions


def cost_aware_threshold_actions(
    frame: pd.DataFrame,
    class_returns: dict[str, float],
    threshold: float = 0.0,
) -> pd.Series:
    edge = expected_edge_from_probabilities(frame, class_returns)
    estimated_cost = frame["rel_spread"] + frame.get("label_fee_bps", 1.0) / 10000.0
    actions = pd.Series(0, index=frame.index, dtype="int8")
    actions.loc[edge > estimated_cost + threshold] = 1
    actions.loc[edge < -(estimated_cost + threshold)] = -1
    return actions

