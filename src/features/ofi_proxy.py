from __future__ import annotations

import numpy as np
import pandas as pd


def add_ofi_proxy(frame: pd.DataFrame, levels: tuple[int, ...] = (1, 5, 10)) -> pd.DataFrame:
    level_terms: list[pd.Series] = []
    derived: dict[str, pd.Series] = {}
    max_level = max(levels)
    for level in range(max_level):
        bid_price = frame[f"bid_{level}_price"]
        bid_size = frame[f"bid_{level}_size"]
        ask_price = frame[f"ask_{level}_price"]
        ask_size = frame[f"ask_{level}_size"]

        prev_bid_price = bid_price.shift(1)
        prev_bid_size = bid_size.shift(1)
        prev_ask_price = ask_price.shift(1)
        prev_ask_size = ask_size.shift(1)

        delta_bid = np.select(
            [bid_price > prev_bid_price, bid_price == prev_bid_price],
            [bid_size, bid_size - prev_bid_size],
            default=-prev_bid_size,
        )
        delta_ask = np.select(
            [ask_price < prev_ask_price, ask_price == prev_ask_price],
            [ask_size, ask_size - prev_ask_size],
            default=-prev_ask_size,
        )
        term = pd.Series(delta_bid - delta_ask, index=frame.index, dtype="float64").fillna(0.0)
        derived[f"ofi_level_{level + 1}"] = term.astype("float32")
        level_terms.append(term)

    cumulative = pd.concat(level_terms, axis=1).cumsum(axis=1)
    for level in levels:
        derived[f"ofi_{level}"] = cumulative.iloc[:, level - 1].astype("float32")
    return pd.concat([frame, pd.DataFrame(derived, index=frame.index)], axis=1)
