from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from simulator.market_order_sim import ExecutionConfig, _sweep, simulate_signals


def _book_row(
    *,
    mid: float = 100.0,
    bid_prices: list[float] | None = None,
    bid_sizes: list[float] | None = None,
    ask_prices: list[float] | None = None,
    ask_sizes: list[float] | None = None,
    idx: int = 0,
) -> dict[str, object]:
    bid_prices = _pad(bid_prices or [99.0 - level for level in range(20)], 20, 80.0)
    ask_prices = _pad(ask_prices or [101.0 + level for level in range(20)], 20, 120.0)
    bid_sizes = _pad(bid_sizes or [10.0] * 20, 20, 10.0)
    ask_sizes = _pad(ask_sizes or [10.0] * 20, 20, 10.0)
    row: dict[str, object] = {
        "event_time": pd.Timestamp("2024-01-01T00:00:00Z") + pd.Timedelta(milliseconds=100 * idx),
        "mid_price": mid,
        "spread": float(ask_prices[0] - bid_prices[0]),
        "regime": "CALM_LIQUID",
    }
    for level in range(20):
        row[f"bid_{level}_price"] = bid_prices[level]
        row[f"bid_{level}_size"] = bid_sizes[level]
        row[f"ask_{level}_price"] = ask_prices[level]
        row[f"ask_{level}_size"] = ask_sizes[level]
    return row


def _pad(values: list[float], length: int, fill: float) -> list[float]:
    return [*values, *([fill] * max(0, length - len(values)))]


def _frame(*rows: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame([{**row, "event_time": row.get("event_time")} for row in rows])


def test_market_buy_sweeps_asks_and_computes_exact_vwap() -> None:
    row = pd.Series(_book_row(ask_prices=[101.0, 102.0], ask_sizes=[3.0, 10.0]))
    fill = _sweep(row, side=1, notional=500.0, config=ExecutionConfig(trade_notional=500.0))
    assert fill["quantity"] == pytest.approx(5.0)
    assert fill["fill_ratio"] == pytest.approx(1.0)
    assert fill["price"] == pytest.approx((3.0 * 101.0 + 2.0 * 102.0) / 5.0)
    assert fill["slippage"] == pytest.approx(0.4)


def test_market_sell_sweeps_bids_and_computes_exact_vwap() -> None:
    row = pd.Series(_book_row(bid_prices=[99.0, 98.0], bid_sizes=[3.0, 10.0]))
    fill = _sweep(row, side=-1, notional=500.0, config=ExecutionConfig(trade_notional=500.0))
    assert fill["quantity"] == pytest.approx(5.0)
    assert fill["fill_ratio"] == pytest.approx(1.0)
    assert fill["price"] == pytest.approx((3.0 * 99.0 + 2.0 * 98.0) / 5.0)
    assert fill["slippage"] == pytest.approx(0.4)


def test_long_round_trip_pnl_and_fee_are_manual() -> None:
    frame = _frame(
        _book_row(ask_prices=[101.0, 102.0], ask_sizes=[3.0, 10.0], idx=0),
        _book_row(bid_prices=[103.0, 102.0], bid_sizes=[3.0, 10.0], ask_prices=[104.0, 105.0], idx=1),
        _book_row(idx=2),
    )
    trades = simulate_signals(
        frame,
        pd.Series([1, 0, 0]),
        ExecutionConfig(latency_events=0, fee_bps=10.0, trade_notional=500.0, cooldown_events=0),
        hold_events=1,
    )
    assert len(trades) == 1
    trade = trades.iloc[0]
    entry_price = 101.4
    exit_price = 102.6
    gross = 5.0 * (exit_price - entry_price)
    fee = 10.0 / 10000.0 * (5.0 * entry_price + 5.0 * exit_price)
    assert trade["entry_price"] == pytest.approx(entry_price)
    assert trade["exit_price"] == pytest.approx(exit_price)
    assert trade["gross_pnl"] == pytest.approx(gross)
    assert trade["total_cost"] == pytest.approx(fee)
    assert trade["net_pnl"] == pytest.approx(gross - fee)


def test_short_round_trip_pnl_and_fee_are_manual() -> None:
    frame = _frame(
        _book_row(bid_prices=[99.0, 98.0], bid_sizes=[3.0, 10.0], idx=0),
        _book_row(bid_prices=[96.0, 95.0], ask_prices=[97.0, 98.0], ask_sizes=[3.0, 10.0], idx=1),
        _book_row(idx=2),
    )
    trades = simulate_signals(
        frame,
        pd.Series([-1, 0, 0]),
        ExecutionConfig(latency_events=0, fee_bps=10.0, trade_notional=500.0, cooldown_events=0),
        hold_events=1,
    )
    assert len(trades) == 1
    trade = trades.iloc[0]
    entry_price = 98.6
    exit_price = 97.4
    gross = 5.0 * (entry_price - exit_price)
    fee = 10.0 / 10000.0 * (5.0 * entry_price + 5.0 * exit_price)
    assert trade["entry_price"] == pytest.approx(entry_price)
    assert trade["exit_price"] == pytest.approx(exit_price)
    assert trade["gross_pnl"] == pytest.approx(gross)
    assert trade["total_cost"] == pytest.approx(fee)
    assert trade["net_pnl"] == pytest.approx(gross - fee)


def test_fee_uses_matched_filled_notional_not_requested_notional() -> None:
    frame = _frame(
        _book_row(ask_prices=[101.0], ask_sizes=[10.0], idx=0),
        _book_row(bid_prices=[102.0] + [80.0] * 19, bid_sizes=[3.0] + [0.0] * 19, ask_prices=[103.0], idx=1),
        _book_row(idx=2),
    )
    trades = simulate_signals(
        frame,
        pd.Series([1, 0, 0]),
        ExecutionConfig(latency_events=0, fee_bps=10.0, trade_notional=500.0, min_fill_ratio=0.5, cooldown_events=0),
        hold_events=1,
    )
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["quantity"] == pytest.approx(3.0)
    assert trade["fill_ratio"] == pytest.approx(0.6)
    assert trade["total_cost"] == pytest.approx(10.0 / 10000.0 * (3.0 * 101.0 + 3.0 * 102.0))


def test_depth_exhaustion_and_partial_fill_rules() -> None:
    frame = _frame(
        _book_row(ask_prices=[101.0], ask_sizes=[3.0] + [0.0] * 19, idx=0),
        _book_row(bid_prices=[102.0] + [80.0] * 19, bid_sizes=[3.0] + [0.0] * 19, ask_prices=[103.0], idx=1),
        _book_row(idx=2),
    )
    accepted = simulate_signals(
        frame,
        pd.Series([1, 0, 0]),
        ExecutionConfig(latency_events=0, trade_notional=500.0, min_fill_ratio=0.5, partial_fill=True, cooldown_events=0),
        hold_events=1,
    )
    rejected_by_ratio = simulate_signals(
        frame,
        pd.Series([1, 0, 0]),
        ExecutionConfig(latency_events=0, trade_notional=500.0, min_fill_ratio=0.7, partial_fill=True, cooldown_events=0),
        hold_events=1,
    )
    rejected_by_full_fill = simulate_signals(
        frame,
        pd.Series([1, 0, 0]),
        ExecutionConfig(latency_events=0, trade_notional=500.0, min_fill_ratio=0.0, partial_fill=False, cooldown_events=0),
        hold_events=1,
    )
    assert len(accepted) == 1
    assert rejected_by_ratio.empty
    assert rejected_by_full_fill.empty


def test_latency_and_cooldown_indexing_are_exact() -> None:
    frame = _frame(*[_book_row(idx=idx) for idx in range(8)])
    latency_trades = simulate_signals(
        frame,
        pd.Series([1, 0, 0, 0, 0, 0, 0, 0]),
        ExecutionConfig(latency_events=2, cooldown_events=0),
        hold_events=1,
    )
    assert latency_trades.iloc[0]["entry_index"] == 2
    assert latency_trades.iloc[0]["exit_index"] == 3

    cooldown_trades = simulate_signals(
        frame,
        pd.Series([1, 1, 0, 0, 1, 0, 0, 0]),
        ExecutionConfig(latency_events=0, cooldown_events=3),
        hold_events=1,
    )
    assert cooldown_trades["signal_index"].tolist() == [0, 4]


def test_spread_and_depth_stress_change_replay_fill() -> None:
    row = pd.Series(_book_row(ask_prices=[101.0, 102.0], ask_sizes=[3.0, 4.0] + [0.0] * 18))
    widened = _sweep(
        row,
        side=1,
        notional=500.0,
        config=ExecutionConfig(trade_notional=500.0, spread_multiplier=2.0),
    )
    thinned = _sweep(
        row,
        side=1,
        notional=500.0,
        config=ExecutionConfig(trade_notional=500.0, depth_multiplier=0.5),
    )
    assert widened["price"] == pytest.approx((3.0 * 102.0 + 2.0 * 104.0) / 5.0)
    assert thinned["quantity"] == pytest.approx(3.5)
    assert thinned["fill_ratio"] == pytest.approx(0.7)


def test_invalid_deeper_levels_are_unavailable_depth() -> None:
    row = pd.Series(_book_row(ask_prices=[101.0, math.nan, 103.0], ask_sizes=[3.0, 10.0, 10.0]))
    fill = _sweep(row, side=1, notional=500.0, config=ExecutionConfig(trade_notional=500.0))
    assert fill["quantity"] == pytest.approx(5.0)
    assert fill["price"] == pytest.approx((3.0 * 101.0 + 2.0 * 103.0) / 5.0)


def test_crossed_or_invalid_top_book_produces_no_trade() -> None:
    crossed = _book_row(bid_prices=[102.0], ask_prices=[101.0], idx=0)
    frame = _frame(crossed, _book_row(idx=1), _book_row(idx=2))
    trades = simulate_signals(
        frame,
        pd.Series([1, 0, 0]),
        ExecutionConfig(latency_events=0, min_fill_ratio=0.0, cooldown_events=0),
        hold_events=1,
    )
    assert trades.empty

    invalid = pd.Series(_book_row(ask_sizes=[0.0] + [10.0] * 19))
    fill = _sweep(invalid, side=1, notional=500.0, config=ExecutionConfig(trade_notional=500.0))
    assert fill["fill_ratio"] == 0.0


def test_missing_required_replay_columns_raise_value_error() -> None:
    frame = _frame(_book_row(idx=0), _book_row(idx=1), _book_row(idx=2)).drop(columns=["ask_19_size"])
    with pytest.raises(ValueError, match="Missing required L2 replay columns"):
        simulate_signals(frame, pd.Series([1, 0, 0]), ExecutionConfig(latency_events=0), hold_events=1)
