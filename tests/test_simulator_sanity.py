from __future__ import annotations

import pandas as pd

from simulator.market_order_sim import ExecutionConfig, simulate_signals


def _market_frame(n_rows: int = 8, depth_size: float = 10.0) -> pd.DataFrame:
    rows = []
    for idx in range(n_rows):
        row = {
            "event_time": pd.Timestamp("2024-01-01T00:00:00Z") + pd.Timedelta(milliseconds=100 * idx),
            "mid_price": 100.0,
            "spread": 0.2,
            "regime": "CALM_LIQUID",
        }
        for level in range(20):
            row[f"bid_{level}_price"] = 99.9 - level * 0.01
            row[f"ask_{level}_price"] = 100.1 + level * 0.01
            row[f"bid_{level}_size"] = depth_size
            row[f"ask_{level}_size"] = depth_size
        rows.append(row)
    return pd.DataFrame(rows)


def test_no_trade_produces_empty_trade_frame() -> None:
    frame = _market_frame()
    trades = simulate_signals(frame, pd.Series([0] * len(frame)), ExecutionConfig(), hold_events=1)
    assert trades.empty


def test_round_trip_constant_price_is_negative_after_costs() -> None:
    frame = _market_frame()
    actions = pd.Series([1] + [0] * (len(frame) - 1))
    trades = simulate_signals(frame, actions, ExecutionConfig(latency_events=0, fee_bps=1.0, cooldown_events=0), hold_events=1)
    assert len(trades) == 1
    assert trades.iloc[0]["net_pnl"] < 0.0


def test_higher_fee_reduces_net_pnl() -> None:
    frame = _market_frame()
    actions = pd.Series([1] + [0] * (len(frame) - 1))
    low_fee = simulate_signals(frame, actions, ExecutionConfig(latency_events=0, fee_bps=0.0, cooldown_events=0), hold_events=1)
    high_fee = simulate_signals(frame, actions, ExecutionConfig(latency_events=0, fee_bps=10.0, cooldown_events=0), hold_events=1)
    assert high_fee.iloc[0]["net_pnl"] <= low_fee.iloc[0]["net_pnl"]


def test_higher_latency_changes_entry_index() -> None:
    frame = _market_frame()
    actions = pd.Series([1] + [0] * (len(frame) - 1))
    no_latency = simulate_signals(frame, actions, ExecutionConfig(latency_events=0, cooldown_events=0), hold_events=1)
    latency = simulate_signals(frame, actions, ExecutionConfig(latency_events=2, cooldown_events=0), hold_events=1)
    assert latency.iloc[0]["entry_index"] == no_latency.iloc[0]["entry_index"] + 2


def test_lower_depth_reduces_fill_ratio() -> None:
    frame = _market_frame(depth_size=0.001)
    actions = pd.Series([1] + [0] * (len(frame) - 1))
    full_depth = simulate_signals(frame, actions, ExecutionConfig(latency_events=0, depth_multiplier=1.0, min_fill_ratio=0.0, cooldown_events=0), hold_events=1)
    lower_depth = simulate_signals(frame, actions, ExecutionConfig(latency_events=0, depth_multiplier=0.5, min_fill_ratio=0.0, cooldown_events=0), hold_events=1)
    assert lower_depth.iloc[0]["fill_ratio"] <= full_depth.iloc[0]["fill_ratio"]

