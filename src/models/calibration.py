from __future__ import annotations

import pandas as pd


def expected_edge_from_probabilities(frame: pd.DataFrame, class_returns: dict[str, float]) -> pd.Series:
    return (
        frame["prob_up"] * float(class_returns.get("UP", 0.0))
        + frame["prob_flat"] * float(class_returns.get("FLAT", 0.0))
        + frame["prob_down"] * float(class_returns.get("DOWN", 0.0))
    )

