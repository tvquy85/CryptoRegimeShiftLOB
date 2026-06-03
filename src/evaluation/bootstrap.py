from __future__ import annotations

import numpy as np
import pandas as pd


def paired_day_bootstrap(
    trades_a: pd.DataFrame,
    trades_b: pd.DataFrame,
    metric: str = "net_pnl",
    n_bootstrap: int = 1000,
    seed: int = 7,
) -> dict[str, float]:
    if trades_a.empty or trades_b.empty:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n_days": 0, "n_bootstrap": n_bootstrap}
    left = _daily_metric(trades_a, metric)
    right = _daily_metric(trades_b, metric)
    merged = left.join(right, how="outer", lsuffix="_a", rsuffix="_b").fillna(0.0)
    diffs = merged[f"{metric}_a"] - merged[f"{metric}_b"]
    rng = np.random.default_rng(seed)
    samples = []
    values = diffs.to_numpy(dtype=float)
    for _ in range(n_bootstrap):
        sample = rng.choice(values, size=len(values), replace=True)
        samples.append(float(sample.mean()))
    return {
        "mean_diff": float(values.mean()),
        "ci_low": float(np.quantile(samples, 0.025)),
        "ci_high": float(np.quantile(samples, 0.975)),
        "n_days": int(len(values)),
        "n_bootstrap": int(n_bootstrap),
    }


def _daily_metric(trades: pd.DataFrame, metric: str) -> pd.DataFrame:
    current = trades.copy()
    current["day"] = pd.to_datetime(current["event_time"], utc=True).dt.date.astype(str)
    return current.groupby("day", dropna=False)[metric].sum().to_frame(metric)
