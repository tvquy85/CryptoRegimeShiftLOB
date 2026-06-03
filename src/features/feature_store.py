from __future__ import annotations

import pandas as pd

from data.audit_schema import clean_book_frame
from features.lob_features import add_lob_features, add_return_features, add_tensor_normalization_columns
from features.ofi_proxy import add_ofi_proxy
from features.regime_features import add_regime_features
from features.returns_labels import add_cost_aware_labels


def build_feature_and_label_frames(
    raw: pd.DataFrame,
    config: dict[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned = clean_book_frame(raw)
    eps = float(config.get("eps", 1.0e-9))
    depth_levels = tuple(int(level) for level in config.get("depth_levels", [1, 3, 5, 10, 20]))
    event_horizons = tuple(int(level) for level in config.get("event_horizons", [10, 50, 100]))
    event_windows = tuple(int(level) for level in config.get("event_windows", [20, 100, 500]))

    features = add_lob_features(cleaned, eps=eps, depth_levels=depth_levels)
    features = add_ofi_proxy(features)
    features = add_return_features(features, event_horizons=event_horizons, event_windows=event_windows, eps=eps)
    if bool(config.get("include_tensor_columns", True)):
        features = add_tensor_normalization_columns(features, eps=eps)

    labels = add_cost_aware_labels(
        features,
        horizon_events=int(config.get("label_horizon_events", 50)),
        fee_bps=float(config.get("fee_bps", 1.0)),
        slippage_buffer_multiplier=float(config.get("slippage_buffer_multiplier", 0.5)),
        eps=eps,
    )
    labels = add_regime_features(labels, eps=eps)
    if bool(config.get("compact_storage", True)):
        labels = labels[_compact_columns(labels, include_label=True)]
    features = labels.drop(columns=["label"], errors="ignore")
    return features, labels


def _compact_columns(frame: pd.DataFrame, include_label: bool) -> list[str]:
    core = [
        "origin_time",
        "received_time",
        "sequence_number",
        "symbol",
        "exchange",
        "event_time",
        "mid_price",
        "spread",
        "rel_spread",
        "microprice_deviation",
        "depth_imbalance_1",
        "depth_imbalance_5",
        "depth_imbalance_10",
        "total_depth_10",
        "ofi_1",
        "ofi_5",
        "realized_vol_20",
        "realized_vol_100",
        "spread_z_1m",
        "depth_z_1m",
        "liquidity_drought_score",
        "adverse_selection_score",
        "momentum_score",
        "choppiness_score",
        "latency_sensitivity_score",
        "depth_drop_top10",
        "vol_score",
        "future_ret_h",
        "cost_threshold_t",
        "label_horizon_events",
        "label_fee_bps",
    ]
    if include_label:
        core.append("label")
    book = []
    for level in range(20):
        book.extend(
            [
                f"bid_{level}_price",
                f"bid_{level}_size",
                f"ask_{level}_price",
                f"ask_{level}_size",
            ]
        )
    return [column for column in [*core, *book] if column in frame.columns]
