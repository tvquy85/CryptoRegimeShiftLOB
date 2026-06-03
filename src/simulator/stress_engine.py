from __future__ import annotations

from dataclasses import replace

from simulator.market_order_sim import ExecutionConfig


def apply_stress(base: ExecutionConfig, **overrides: float | int) -> ExecutionConfig:
    return replace(base, **overrides)

