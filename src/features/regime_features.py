from __future__ import annotations

import numpy as np
import pandas as pd


def add_regime_features(frame: pd.DataFrame, eps: float = 1.0e-9) -> pd.DataFrame:
    vol = frame.get("realized_vol_100", pd.Series(0.0, index=frame.index))
    spread = frame["rel_spread"]
    depth = frame.get("total_depth_10", pd.Series(0.0, index=frame.index))
    imbalance = frame.get("depth_imbalance_10", pd.Series(0.0, index=frame.index))
    ofi = frame.get("ofi_5", pd.Series(0.0, index=frame.index))
    ret = frame.get("mid_return_50", pd.Series(0.0, index=frame.index))
    flip = frame.get("up_down_flip_rate_100", pd.Series(0.0, index=frame.index))

    spread_z = _rolling_z(spread, 300, eps)
    depth_z = _rolling_z(depth, 300, eps)
    rolling_depth_median = depth.rolling(window=300, min_periods=60).median().fillna(depth.median())
    derived = {
        "vol_score": _rolling_z(vol, 300, eps),
        "spread_score": spread_z,
        "depth_score": depth_z,
        "imbalance_score": imbalance.abs().astype("float32"),
        "ofi_proxy_score": _rolling_z(ofi.abs(), 300, eps),
        "depth_drop_top10": ((depth - rolling_depth_median) / (rolling_depth_median.abs() + eps)).astype("float32"),
        "spread_z_1m": spread_z,
        "depth_z_1m": depth_z,
        "top_level_depletion_flag": (frame.get("top_depth_share_bid", 0.0) < 0.05).astype("int8"),
        "spread_widening_flag": (spread_z > 1.0).astype("int8"),
        "liquidity_drought_score": (spread_z - depth_z).astype("float32"),
        "momentum_score": _rolling_z(ret, 300, eps),
        "choppiness_score": flip.astype("float32"),
        "latency_sensitivity_score": (vol.abs() + spread.abs()).astype("float32"),
    }
    trailing_adverse_proxy = ret.abs()
    derived["adverse_selection_score"] = _rolling_z(trailing_adverse_proxy, 300, eps)
    return pd.concat([frame, pd.DataFrame(derived, index=frame.index)], axis=1)


def _rolling_z(series: pd.Series, window: int, eps: float) -> pd.Series:
    rolling_mean = series.rolling(window=window, min_periods=max(20, window // 5)).mean()
    rolling_std = series.rolling(window=window, min_periods=max(20, window // 5)).std()
    return ((series - rolling_mean) / (rolling_std.abs() + eps)).fillna(0.0).astype("float32")
