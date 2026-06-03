from __future__ import annotations

import numpy as np
import pandas as pd


def worst_regime_return(by_regime: pd.DataFrame) -> float:
    if by_regime.empty:
        return 0.0
    return float(by_regime["net_pnl"].min())


def regime_gap(by_regime: pd.DataFrame) -> float:
    if by_regime.empty:
        return 0.0
    return float(by_regime["net_pnl"].max() - by_regime["net_pnl"].min())


def robustness_auc(curve: pd.DataFrame, x_col: str, y_col: str = "net_pnl") -> float:
    if curve.empty or curve[x_col].nunique() < 2:
        return float("nan")
    ordered = curve.sort_values(x_col)
    x = ordered[x_col].to_numpy(dtype=float)
    y = ordered[y_col].to_numpy(dtype=float)
    denom = max(x.max() - x.min(), 1.0e-9)
    return float(np.trapz(y, x) / denom)


def latency_half_life(curve: pd.DataFrame) -> float | None:
    if curve.empty:
        return None
    ordered = curve.sort_values("latency_events")
    base = ordered.iloc[0]["net_pnl"]
    if base <= 0:
        return None
    threshold = 0.5 * base
    candidates = ordered[ordered["net_pnl"] <= threshold]
    return float(candidates.iloc[0]["latency_events"]) if not candidates.empty else None

