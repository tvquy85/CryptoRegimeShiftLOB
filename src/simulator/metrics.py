from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_trades(trades: pd.DataFrame) -> dict[str, float]:
    if trades.empty:
        return {
            "n_trades": 0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "total_cost": 0.0,
            "turnover": 0.0,
            "net_pnl_per_trade": 0.0,
            "cost_survival": np.nan,
            "max_drawdown": 0.0,
        }
    equity = trades["net_pnl"].cumsum()
    drawdown = equity - equity.cummax()
    gross = float(trades["gross_pnl"].sum())
    net = float(trades["net_pnl"].sum())
    return {
        "n_trades": int(len(trades)),
        "gross_pnl": gross,
        "net_pnl": net,
        "total_cost": float(trades["total_cost"].sum()),
        "turnover": float(trades["quantity"].abs().sum()),
        "net_pnl_per_trade": float(trades["net_pnl"].mean()),
        "cost_survival": float(net / gross) if gross > 0 else np.nan,
        "max_drawdown": float(drawdown.min()),
    }


def summarize_by_regime(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["regime", "gross_pnl", "net_pnl", "n_trades"])
    grouped = trades.groupby("regime", dropna=False).agg(
        gross_pnl=("gross_pnl", "sum"),
        net_pnl=("net_pnl", "sum"),
        n_trades=("net_pnl", "size"),
    )
    return grouped.reset_index()

