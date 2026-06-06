# Schema

## Raw L2 Snapshot Schema

Each row is one L2 order-book snapshot.

| Group | Columns | Expected type | Notes |
|---|---|---|---|
| Timestamp | `origin_time` | UTC timestamp | Primary event time when valid |
| Timestamp | `received_time` | UTC timestamp | Fallback timestamp |
| Sequence | `sequence_number` | int64 | Tie-breaker for sorting |
| Metadata | `symbol` | string | Example: `BTC-USDT`, `ETH-USDT` |
| Metadata | `exchange` | string | Example: `BINANCE` |
| Bid prices | `bid_0_price` ... `bid_19_price` | float | Level 0 is best bid |
| Bid sizes | `bid_0_size` ... `bid_19_size` | float | Visible size |
| Ask prices | `ask_0_price` ... `ask_19_price` | float | Level 0 is best ask |
| Ask sizes | `ask_0_size` ... `ask_19_size` | float | Visible size |

The production loader expects monthly raw parquet files named like:

```text
BOOK_<EXCHANGE>_<SYMBOL>_<MON>-2024.parquet
```

The public synthetic sample also provides a loader-compatible filename:

```text
sample_data/BOOK_BINANCE_SYNTH-USDT_JAN-2024.parquet
```

## Cleaning and Ordering

- Use `origin_time` when valid; otherwise fall back to `received_time`.
- Sort by event time and use `sequence_number` as a tie-breaker.
- Remove invalid best bid/ask rows by default.
- Remove crossed best-level books by default.
- Keep all feature construction causal with respect to the decision time.

## Derived Columns

Important derived columns include:

- `event_time`, `mid_price`, `spread`, `rel_spread`;
- `future_ret_h`, `cost_threshold_t`, `label`, `label_horizon_events`;
- `regime`, `split`;
- risk and regime diagnostic scores;
- `prob_down`, `prob_flat`, `prob_up`, `pred_label` for predictions.

## Execution Columns

Execution and RSEP replay require probabilities, labels, regimes, split, mid and
spread columns, risk scores, and all 20-level bid/ask price and size columns.
The required column list is implemented in:

```text
src/utils/execution_columns.py
```
