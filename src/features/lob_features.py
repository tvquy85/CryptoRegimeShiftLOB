from __future__ import annotations

import numpy as np
import pandas as pd


def add_lob_features(frame: pd.DataFrame, eps: float = 1.0e-9, depth_levels: tuple[int, ...] = (1, 3, 5, 10, 20)) -> pd.DataFrame:
    mid_price = ((frame["bid_0_price"] + frame["ask_0_price"]) / 2.0).astype("float32")
    spread = (frame["ask_0_price"] - frame["bid_0_price"]).astype("float32")
    rel_spread = (spread / (mid_price + eps)).astype("float32")
    denominator = frame["bid_0_size"] + frame["ask_0_size"] + eps
    microprice = (
        (frame["ask_0_price"] * frame["bid_0_size"] + frame["bid_0_price"] * frame["ask_0_size"]) / denominator
    ).astype("float32")
    derived: dict[str, pd.Series] = {
        "mid_price": mid_price,
        "spread": spread,
        "rel_spread": rel_spread,
        "microprice": microprice,
        "microprice_deviation": ((microprice - mid_price) / (mid_price + eps)).astype("float32"),
    }

    for level in depth_levels:
        bid_cols = [f"bid_{idx}_size" for idx in range(level)]
        ask_cols = [f"ask_{idx}_size" for idx in range(level)]
        bid_depth = frame[bid_cols].sum(axis=1)
        ask_depth = frame[ask_cols].sum(axis=1)
        total = bid_depth + ask_depth
        derived[f"bid_depth_{level}"] = bid_depth.astype("float32")
        derived[f"ask_depth_{level}"] = ask_depth.astype("float32")
        derived[f"total_depth_{level}"] = total.astype("float32")
        derived[f"depth_imbalance_{level}"] = ((bid_depth - ask_depth) / (total + eps)).astype("float32")
        derived[f"depth_ratio_{level}"] = (bid_depth / (ask_depth + eps)).astype("float32")
        derived[f"book_slope_bid_{level}"] = (
            bid_depth / ((frame["bid_0_price"] - frame[f"bid_{level - 1}_price"]).abs() + eps)
        ).astype("float32")
        derived[f"book_slope_ask_{level}"] = (
            ask_depth / ((frame[f"ask_{level - 1}_price"] - frame["ask_0_price"]).abs() + eps)
        ).astype("float32")

    bid_weighted = []
    ask_weighted = []
    for idx in range(20):
        bid_distance = (frame["bid_0_price"] - frame[f"bid_{idx}_price"]) / (mid_price + eps)
        ask_distance = (frame[f"ask_{idx}_price"] - frame["ask_0_price"]) / (mid_price + eps)
        derived[f"bid_price_distance_{idx}"] = bid_distance.astype("float32")
        derived[f"ask_price_distance_{idx}"] = ask_distance.astype("float32")
        bid_weighted.append(bid_distance * frame[f"bid_{idx}_size"])
        ask_weighted.append(ask_distance * frame[f"ask_{idx}_size"])

    derived["bid_depth_weighted_distance"] = (
        pd.concat(bid_weighted, axis=1).sum(axis=1) / (derived["bid_depth_20"] + eps)
    ).astype("float32")
    derived["ask_depth_weighted_distance"] = (
        pd.concat(ask_weighted, axis=1).sum(axis=1) / (derived["ask_depth_20"] + eps)
    ).astype("float32")
    derived["top_depth_share_bid"] = (derived["bid_depth_1"] / (derived["bid_depth_20"] + eps)).astype("float32")
    derived["top_depth_share_ask"] = (derived["ask_depth_1"] / (derived["ask_depth_20"] + eps)).astype("float32")
    return pd.concat([frame, pd.DataFrame(derived, index=frame.index)], axis=1)


def add_return_features(
    frame: pd.DataFrame,
    event_horizons: tuple[int, ...] = (10, 50, 100),
    event_windows: tuple[int, ...] = (20, 100, 500),
    eps: float = 1.0e-9,
) -> pd.DataFrame:
    mid = frame["mid_price"].astype("float64")
    one_step = mid.pct_change().fillna(0.0)
    sign = np.sign(one_step)
    flip = pd.Series(sign, index=frame.index).ne(pd.Series(sign, index=frame.index).shift(1)).astype("float32")
    derived: dict[str, pd.Series] = {}

    for horizon in event_horizons:
        past = mid.shift(horizon)
        derived[f"mid_return_{horizon}"] = ((mid - past) / (past + eps)).fillna(0.0).astype("float32")
        derived[f"log_return_{horizon}"] = np.log((mid + eps) / (past + eps)).replace([np.inf, -np.inf], 0.0).fillna(0.0).astype("float32")

    for window in event_windows:
        min_periods = max(2, window // 4)
        rolling = one_step.rolling(window=window, min_periods=min_periods)
        derived[f"realized_vol_{window}"] = rolling.std().fillna(0.0).astype("float32")
        derived[f"abs_return_{window}"] = (
            one_step.abs().rolling(window=window, min_periods=min_periods).sum().fillna(0.0).astype("float32")
        )
        derived[f"return_autocorr_{window}"] = (
            one_step.shift(1)
            .rolling(window=window - 1, min_periods=max(2, min_periods - 1))
            .corr(one_step)
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
            .astype("float32")
        )
        derived[f"up_down_flip_rate_{window}"] = (
            flip.rolling(window=window, min_periods=min_periods).mean().fillna(0.0).astype("float32")
        )
    return pd.concat([frame, pd.DataFrame(derived, index=frame.index)], axis=1)


def add_tensor_normalization_columns(frame: pd.DataFrame, eps: float = 1.0e-9) -> pd.DataFrame:
    mid = frame["mid_price"] + eps
    derived: dict[str, pd.Series] = {}
    for idx in range(20):
        derived[f"ask_price_{idx}_norm"] = ((frame[f"ask_{idx}_price"] - frame["mid_price"]) / mid).astype("float32")
        derived[f"bid_price_{idx}_norm"] = ((frame[f"bid_{idx}_price"] - frame["mid_price"]) / mid).astype("float32")
        derived[f"ask_size_{idx}_log1p"] = np.log1p(frame[f"ask_{idx}_size"].clip(lower=0)).astype("float32")
        derived[f"bid_size_{idx}_log1p"] = np.log1p(frame[f"bid_{idx}_size"].clip(lower=0)).astype("float32")
    return pd.concat([frame, pd.DataFrame(derived, index=frame.index)], axis=1)


def _lag1_autocorr(values: np.ndarray) -> float:
    if len(values) < 3:
        return 0.0
    x = values[:-1]
    y = values[1:]
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])
