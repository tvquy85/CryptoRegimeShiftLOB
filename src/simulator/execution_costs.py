from __future__ import annotations


def fee_cost(notional: float, fee_bps: float) -> float:
    return float(notional) * float(fee_bps) / 10000.0

