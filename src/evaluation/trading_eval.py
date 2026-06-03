from __future__ import annotations

import pandas as pd

from simulator.metrics import summarize_by_regime, summarize_trades


def trading_pack(policy_name: str, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    overall = pd.DataFrame([{"policy": policy_name, **summarize_trades(trades)}])
    by_regime = summarize_by_regime(trades)
    if not by_regime.empty:
        by_regime.insert(0, "policy", policy_name)
    return overall, by_regime

