from __future__ import annotations

import pandas as pd


def chronological_split(
    frame: pd.DataFrame,
    train_fraction: float = 0.6,
    valid_fraction: float = 0.2,
    *,
    purge_gap_events: int = 0,
) -> pd.DataFrame:
    split = frame.copy().sort_values("event_time", kind="mergesort").reset_index(drop=True)
    train_end = int(len(split) * train_fraction)
    valid_end = int(len(split) * (train_fraction + valid_fraction))
    split["split"] = "test"
    train_label_end = max(train_end - int(purge_gap_events), 0)
    valid_label_end = max(valid_end - int(purge_gap_events), train_end)
    if train_label_end > 0:
        split.loc[: train_label_end - 1, "split"] = "train"
    if valid_label_end > train_end:
        split.loc[train_end: valid_label_end - 1, "split"] = "valid"
    if purge_gap_events > 0:
        purge_mask = ((split.index >= train_label_end) & (split.index < train_end)) | (
            (split.index >= valid_label_end) & (split.index < valid_end)
        )
        split = split.loc[~purge_mask].reset_index(drop=True)
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
