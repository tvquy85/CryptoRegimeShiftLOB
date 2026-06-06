from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data.audit_schema import book_columns, validate_schema


N_ROWS = 12_000
SYMBOL = "SYNTH-USDT"
EXCHANGE = "BINANCE"


def build_sample(n_rows: int = N_ROWS) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    event_time = pd.date_range("2024-01-01T00:00:00Z", periods=n_rows, freq="100ms")
    segment = np.arange(n_rows) // 750
    trend = np.where(segment % 4 == 0, 0.000025, np.where(segment % 4 == 1, -0.000025, 0.0))
    seasonal = 0.000035 * np.sin(np.arange(n_rows) / 85.0)
    noise = rng.normal(0.0, 0.000018, size=n_rows)
    mid = 2_000.0 * np.exp(np.cumsum(trend + seasonal + noise))
    spread = 0.18 + 0.10 * (np.sin(np.arange(n_rows) / 300.0) > 0.65).astype(float)
    spread += rng.uniform(0.0, 0.015, size=n_rows)

    frame: dict[str, object] = {
        "origin_time": event_time,
        "received_time": event_time + pd.to_timedelta(5, unit="ms"),
        "sequence_number": np.arange(1, n_rows + 1, dtype=np.int64),
        "symbol": np.repeat(SYMBOL, n_rows),
        "exchange": np.repeat(EXCHANGE, n_rows),
    }
    for level in range(20):
        distance = (level + 0.5) * spread
        frame[f"bid_{level}_price"] = (mid - distance).astype("float32")
        frame[f"ask_{level}_price"] = (mid + distance).astype("float32")
    base_size = 4.0 + 2.0 * np.cos(np.arange(n_rows) / 400.0)
    for level in range(20):
        level_decay = 1.0 / (1.0 + 0.08 * level)
        bid_size = base_size * level_decay + rng.gamma(2.0, 0.25, size=n_rows)
        ask_size = base_size * level_decay + rng.gamma(2.0, 0.25, size=n_rows)
        frame[f"bid_{level}_size"] = bid_size.astype("float32")
        frame[f"ask_{level}_size"] = ask_size.astype("float32")

    sample = pd.DataFrame(frame)
    ordered = ["origin_time", "received_time", "sequence_number", "symbol", "exchange"]
    for level in range(20):
        ordered.extend(
            [
                f"bid_{level}_price",
                f"bid_{level}_size",
                f"ask_{level}_price",
                f"ask_{level}_size",
            ]
        )
    sample = sample[ordered]
    schema = validate_schema(sample.columns, levels=20)
    if not schema["ok"]:
        raise RuntimeError(f"Synthetic schema invalid: {schema}")
    return sample


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "sample_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    sample = build_sample()
    canonical = output_dir / "l2_synthetic_sample.parquet"
    loader_path = output_dir / "BOOK_BINANCE_SYNTH-USDT_JAN-2024.parquet"
    sample.to_parquet(canonical, index=False)
    sample.to_parquet(loader_path, index=False)
    print(f"Wrote {len(sample)} rows to {canonical}")
    print(f"Wrote loader-compatible copy to {loader_path}")


if __name__ == "__main__":
    main()
