from __future__ import annotations

import pandas as pd

from data.audit_schema import book_columns, clean_book_frame, validate_schema


def _frame() -> pd.DataFrame:
    row = {
        "origin_time": pd.Timestamp("2024-01-01T00:00:00Z"),
        "received_time": pd.Timestamp("2024-01-01T00:00:00Z"),
        "sequence_number": 1,
        "symbol": "BTC-USDT",
        "exchange": "BINANCE",
    }
    for level in range(20):
        row[f"bid_{level}_price"] = 100.0 - level * 0.1
        row[f"bid_{level}_size"] = 1.0
        row[f"ask_{level}_price"] = 100.1 + level * 0.1
        row[f"ask_{level}_size"] = 1.0
    return pd.DataFrame([row])


def test_validate_schema_accepts_expected_columns() -> None:
    frame = _frame()
    result = validate_schema(frame.columns)
    assert result["ok"] is True
    assert result["missing"] == []


def test_clean_book_frame_drops_crossed_rows() -> None:
    frame = _frame()
    crossed = frame.copy()
    crossed.loc[0, "bid_0_price"] = 101.0
    cleaned = clean_book_frame(pd.concat([frame, crossed], ignore_index=True))
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["bid_0_price"] <= cleaned.iloc[0]["ask_0_price"]

