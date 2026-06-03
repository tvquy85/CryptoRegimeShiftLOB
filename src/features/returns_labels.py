from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl


LABEL_ORDER = ["DOWN", "FLAT", "UP"]


def add_cost_aware_labels(
    frame: pd.DataFrame,
    horizon_events: int = 50,
    fee_bps: float = 1.0,
    slippage_buffer_multiplier: float = 0.5,
    eps: float = 1.0e-9,
) -> pd.DataFrame:
    mid = frame["mid_price"].astype("float64")
    future_mid = mid.shift(-horizon_events)
    future_ret_h = ((future_mid - mid) / (mid + eps)).astype("float32")
    cost_threshold_t = (
        frame["rel_spread"] + fee_bps / 10000.0 + slippage_buffer_multiplier * frame["rel_spread"]
    ).astype("float32")
    conditions = [
        future_ret_h > cost_threshold_t,
        future_ret_h < -cost_threshold_t,
    ]
    derived = pd.DataFrame(
        {
            "future_ret_h": future_ret_h,
            "cost_threshold_t": cost_threshold_t,
            "label": np.select(conditions, ["UP", "DOWN"], default="FLAT"),
            "label_horizon_events": int(horizon_events),
            "label_fee_bps": float(fee_bps),
        },
        index=frame.index,
    )
    labeled = pd.concat([frame, derived], axis=1)
    if horizon_events > 0:
        labeled = labeled.iloc[:-horizon_events]
    else:
        labeled = labeled[future_ret_h.notna()]
    return labeled


def class_return_means(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {label: 0.0 for label in LABEL_ORDER}
    grouped = frame.groupby("label")["future_ret_h"].mean().to_dict()
    return {label: float(grouped.get(label, 0.0)) for label in LABEL_ORDER}


def class_return_means_from_parquet(path, *, split: str = "train") -> dict[str, float]:
    grouped = (
        pl.scan_parquet(str(path))
        .filter(pl.col("split") == split)
        .group_by("label")
        .agg(pl.col("future_ret_h").mean().alias("future_ret_h"))
        .collect(engine="streaming")
        .to_pandas()
    )
    values = dict(zip(grouped["label"], grouped["future_ret_h"]))
    return {label: float(values.get(label, 0.0)) for label in LABEL_ORDER}
