from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from simulator.execution_costs import fee_cost

REPLAY_LEVELS = 20
EPS = 1.0e-9


@dataclass(frozen=True)
class ExecutionConfig:
    latency_events: int = 1
    fee_bps: float = 1.0
    spread_multiplier: float = 1.0
    depth_multiplier: float = 1.0
    partial_fill: bool = True
    min_fill_ratio: float = 0.5
    trade_notional: float = 1000.0
    cooldown_events: int = 3


def simulate_signals(frame: pd.DataFrame, actions: pd.Series, config: ExecutionConfig, hold_events: int = 50) -> pd.DataFrame:
    _validate_replay_columns(frame)
    trades: list[dict[str, object]] = []
    last_exec = -10**12
    values = frame.reset_index(drop=True)
    action_values = actions.reset_index(drop=True)
    max_index = len(values) - 1

    signal_indices = np.flatnonzero(action_values.to_numpy(dtype="int8", copy=False) != 0)
    for signal_idx in signal_indices:
        action = action_values.iloc[int(signal_idx)]
        side = int(action)
        entry_idx = signal_idx + config.latency_events
        exit_idx = entry_idx + hold_events
        if entry_idx >= max_index or exit_idx >= max_index or entry_idx - last_exec < config.cooldown_events:
            continue
        entry = values.iloc[entry_idx]
        exit_row = values.iloc[exit_idx]
        entry_fill = _sweep(entry, side=side, notional=config.trade_notional, config=config)
        exit_fill = _sweep(exit_row, side=-side, notional=config.trade_notional, config=config)
        if entry_fill["fill_ratio"] < config.min_fill_ratio or exit_fill["fill_ratio"] < config.min_fill_ratio:
            continue
        qty = min(entry_fill["quantity"], exit_fill["quantity"])
        if qty <= 0:
            continue
        entry_px = entry_fill["price"]
        exit_px = exit_fill["price"]
        gross_pnl = qty * ((exit_px - entry_px) if side > 0 else (entry_px - exit_px))
        total_fee = fee_cost(qty * entry_px, config.fee_bps) + fee_cost(qty * exit_px, config.fee_bps)
        net_pnl = gross_pnl - total_fee
        trades.append(
            {
                "signal_index": signal_idx,
                "entry_index": entry_idx,
                "exit_index": exit_idx,
                "event_time": entry.get("event_time"),
                "regime": entry.get("regime", "UNKNOWN"),
                "action": side,
                "quantity": qty,
                "entry_price": entry_px,
                "exit_price": exit_px,
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "total_cost": total_fee,
                "fill_ratio": min(entry_fill["fill_ratio"], exit_fill["fill_ratio"]),
                "entry_slippage": entry_fill["slippage"],
                "exit_slippage": exit_fill["slippage"],
            }
        )
        last_exec = entry_idx
    return pd.DataFrame.from_records(trades)


def _sweep(row: pd.Series, side: int, notional: float, config: ExecutionConfig) -> dict[str, float]:
    if not _valid_top_of_book(row):
        return _empty_fill()

    mid = float(row["mid_price"])
    target_qty = notional / max(mid, EPS)
    remaining = target_qty
    filled_qty = 0.0
    total_value = 0.0
    best_px = None
    for level in range(REPLAY_LEVELS):
        if side > 0:
            raw_price = _positive_float(row.get(f"ask_{level}_price"))
            raw_size = _positive_float(row.get(f"ask_{level}_size"))
            if raw_price is None or raw_size is None:
                continue
            price = mid + (raw_price - mid) * config.spread_multiplier
            size = raw_size * config.depth_multiplier
        else:
            raw_price = _positive_float(row.get(f"bid_{level}_price"))
            raw_size = _positive_float(row.get(f"bid_{level}_size"))
            if raw_price is None or raw_size is None:
                continue
            price = mid - (mid - raw_price) * config.spread_multiplier
            size = raw_size * config.depth_multiplier
        if not np.isfinite(price) or price <= 0 or not np.isfinite(size) or size <= 0:
            continue
        if best_px is None:
            best_px = price
        take = min(remaining, size)
        total_value += take * price
        filled_qty += take
        remaining -= take
        if remaining <= 1.0e-12:
            break
    fill_ratio = filled_qty / max(target_qty, EPS)
    if not config.partial_fill and fill_ratio < 1.0:
        filled_qty = 0.0
        total_value = 0.0
        fill_ratio = 0.0
    if filled_qty <= 0:
        return _empty_fill()
    avg_price = total_value / max(filled_qty, EPS)
    slippage = abs(avg_price - float(best_px or avg_price))
    return {"price": avg_price, "quantity": filled_qty, "fill_ratio": fill_ratio, "slippage": slippage}


def _required_replay_columns() -> list[str]:
    columns = ["mid_price"]
    for level in range(REPLAY_LEVELS):
        columns.extend(
            [
                f"bid_{level}_price",
                f"bid_{level}_size",
                f"ask_{level}_price",
                f"ask_{level}_size",
            ]
        )
    return columns


def _validate_replay_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in _required_replay_columns() if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required L2 replay columns: {missing}")


def _valid_top_of_book(row: pd.Series) -> bool:
    mid = _positive_float(row.get("mid_price"))
    bid = _positive_float(row.get("bid_0_price"))
    ask = _positive_float(row.get("ask_0_price"))
    bid_size = _positive_float(row.get("bid_0_size"))
    ask_size = _positive_float(row.get("ask_0_size"))
    if any(value is None for value in [mid, bid, ask, bid_size, ask_size]):
        return False
    return bool(bid <= ask)


def _positive_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number) or number <= 0:
        return None
    return number


def _empty_fill() -> dict[str, float]:
    return {"price": 0.0, "quantity": 0.0, "fill_ratio": 0.0, "slippage": 0.0}
