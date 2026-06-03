from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_failure_cases(trades: pd.DataFrame, output_path: Path, top_k: int = 25) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if trades.empty:
        pd.DataFrame().to_csv(output_path, index=False)
        return output_path
    failures = trades.sort_values("net_pnl").head(top_k)
    failures.to_csv(output_path, index=False)
    return output_path

