from __future__ import annotations

import pandas as pd


def event_stride(frame: pd.DataFrame, stride: int) -> pd.DataFrame:
    if stride <= 1 or frame.empty:
        return frame.copy()
    return frame.iloc[::stride].reset_index(drop=True)

