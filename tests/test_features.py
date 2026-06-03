from __future__ import annotations

import numpy as np
import pandas as pd

from features.feature_store import build_feature_and_label_frames
from features.lob_features import add_return_features


def _raw_rows(n_rows: int = 80) -> pd.DataFrame:
    rows = []
    for idx in range(n_rows):
        row = {
            "origin_time": pd.Timestamp("2024-01-01T00:00:00Z") + pd.Timedelta(milliseconds=100 * idx),
            "received_time": pd.Timestamp("2024-01-01T00:00:00Z") + pd.Timedelta(milliseconds=100 * idx),
            "sequence_number": idx,
            "symbol": "BTC-USDT",
            "exchange": "BINANCE",
        }
        mid = 100.0 + idx * 0.01
        for level in range(20):
            row[f"bid_{level}_price"] = mid - 0.05 - level * 0.01
            row[f"bid_{level}_size"] = 2.0 + level
            row[f"ask_{level}_price"] = mid + 0.05 + level * 0.01
            row[f"ask_{level}_size"] = 2.5 + level
        rows.append(row)
    return pd.DataFrame(rows)


def test_feature_store_builds_core_columns() -> None:
    config = {
        "eps": 1.0e-9,
        "depth_levels": [1, 3, 5, 10, 20],
        "event_horizons": [10, 50],
        "event_windows": [20],
        "include_tensor_columns": True,
        "label_horizon_events": 10,
        "fee_bps": 1.0,
        "slippage_buffer_multiplier": 0.5,
    }
    features, labels = build_feature_and_label_frames(_raw_rows(), config)
    assert not features.empty
    assert not labels.empty
    for column in ["mid_price", "rel_spread", "depth_imbalance_10", "ofi_5", "liquidity_drought_score", "label"]:
        assert column in labels.columns


def test_return_features_match_reference_rolling_formulas() -> None:
    frame = pd.DataFrame({"mid_price": 100.0 + np.sin(np.arange(700) / 13.0) + np.arange(700) * 0.001})
    actual = add_return_features(frame.copy(), event_horizons=(10,), event_windows=(20, 100, 500))
    one_step = frame["mid_price"].astype("float64").pct_change().fillna(0.0)

    for window in (20, 100, 500):
        min_periods = max(2, window // 4)
        expected_abs = (
            one_step.rolling(window=window, min_periods=min_periods)
            .apply(lambda values: float(np.abs(values).sum()), raw=True)
            .fillna(0.0)
        )
        expected_autocorr = (
            one_step.rolling(window=window, min_periods=min_periods)
            .apply(_reference_lag1_autocorr, raw=True)
            .fillna(0.0)
        )
        np.testing.assert_allclose(actual[f"abs_return_{window}"], expected_abs, atol=1.0e-6, rtol=1.0e-6)
        np.testing.assert_allclose(actual[f"return_autocorr_{window}"], expected_autocorr, atol=1.0e-6, rtol=1.0e-6)


def test_return_features_are_causal_on_prefix() -> None:
    base = pd.DataFrame({"mid_price": 100.0 + np.cos(np.arange(240) / 9.0) + np.arange(240) * 0.002})
    prefix = base.iloc[:180].copy()
    full_features = add_return_features(base.copy(), event_horizons=(10, 50), event_windows=(20, 100))
    prefix_features = add_return_features(prefix.copy(), event_horizons=(10, 50), event_windows=(20, 100))
    compare_columns = [
        "mid_return_10",
        "log_return_10",
        "mid_return_50",
        "log_return_50",
        "abs_return_20",
        "abs_return_100",
        "return_autocorr_20",
        "return_autocorr_100",
    ]
    for column in compare_columns:
        np.testing.assert_allclose(
            full_features.loc[prefix_features.index, column],
            prefix_features[column],
            atol=1.0e-6,
            rtol=1.0e-6,
        )


def _reference_lag1_autocorr(values: np.ndarray) -> float:
    if len(values) < 3:
        return 0.0
    left = values[:-1]
    right = values[1:]
    if np.std(left) == 0 or np.std(right) == 0:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])
