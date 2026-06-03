from __future__ import annotations

import pandas as pd


def imbalance_reversion_actions(frame: pd.DataFrame, threshold: float = 0.35) -> pd.Series:
    actions = pd.Series(0, index=frame.index, dtype="int8")
    actions.loc[frame["depth_imbalance_10"] > threshold] = 1
    actions.loc[frame["depth_imbalance_10"] < -threshold] = -1
    return actions

