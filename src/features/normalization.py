from __future__ import annotations

import pandas as pd


def fit_standardizer(frame: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for column in columns:
        values = frame[column].astype("float64")
        stats[column] = {"mean": float(values.mean()), "std": float(values.std() or 1.0)}
    return stats


def apply_standardizer(frame: pd.DataFrame, stats: dict[str, dict[str, float]]) -> pd.DataFrame:
    normalized = frame.copy()
    for column, column_stats in stats.items():
        if column not in normalized:
            continue
        std = column_stats["std"] or 1.0
        normalized[column] = ((normalized[column] - column_stats["mean"]) / std).astype("float32")
    return normalized

