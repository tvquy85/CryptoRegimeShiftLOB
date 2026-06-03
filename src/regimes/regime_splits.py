from __future__ import annotations

import pandas as pd


def chronological_split(frame: pd.DataFrame, train_fraction: float = 0.6, valid_fraction: float = 0.2) -> pd.DataFrame:
    split = frame.copy().sort_values("event_time", kind="mergesort").reset_index(drop=True)
    train_end = int(len(split) * train_fraction)
    valid_end = int(len(split) * (train_fraction + valid_fraction))
    split["split"] = "test"
    split.loc[: max(train_end - 1, 0), "split"] = "train"
    split.loc[train_end: max(valid_end - 1, train_end), "split"] = "valid"
    return split


def regime_held_out_split(frame: pd.DataFrame, regime: str) -> pd.DataFrame:
    split = frame.copy()
    split["split"] = "train"
    split.loc[split["regime"].eq(regime), "split"] = "test"
    return split


def asset_held_out_manifest(symbols: list[str]) -> pd.DataFrame:
    rows = []
    for train_symbol in symbols:
        for test_symbol in symbols:
            if train_symbol == test_symbol:
                continue
            rows.append({"train_symbol": train_symbol, "test_symbol": test_symbol, "available": False})
    return pd.DataFrame(rows)

