# SCHEMA.md

## Raw L2 snapshot schema

Mỗi row là một L2 order book snapshot tại một thời điểm quyết định.

| Nhóm | Cột | Kiểu kỳ vọng | Ghi chú |
|---|---|---|---|
| Timestamp | `origin_time` | timestamp UTC | timestamp chính nếu hợp lệ |
| Timestamp | `received_time` | timestamp UTC | fallback khi `origin_time` thiếu |
| Sequence | `sequence_number` | int64 | tie-break khi sort |
| Metadata | `symbol` | string | ví dụ `BTC-USDT`, `ETH-USDT`, `SYNTH-USDT` |
| Metadata | `exchange` | string | ví dụ `BINANCE` |
| Bid prices | `bid_0_price` ... `bid_19_price` | float32/float64 | level 0 là best bid |
| Bid sizes | `bid_0_size` ... `bid_19_size` | float32/float64 | visible size |
| Ask prices | `ask_0_price` ... `ask_19_price` | float32/float64 | level 0 là best ask |
| Ask sizes | `ask_0_size` ... `ask_19_size` | float32/float64 | visible size |

Loader nhận diện raw parquet theo pattern:

```text
BOOK_<EXCHANGE>_<SYMBOL>_<MON>-2024.parquet
```

Ví dụ public smoke:

```text
sample_data/BOOK_BINANCE_SYNTH-USDT_JAN-2024.parquet
```

## Cleaning và ordering

- Event time = `origin_time` nếu hợp lệ, fallback `received_time`.
- Loại row best bid/ask không dương hoặc size best level không dương.
- Loại crossed book ở best level khi cleaning mặc định.
- Sort theo `event_time`, tie-break bằng `sequence_number`.

## Derived core columns

Sau feature/label pipeline, các cột quan trọng gồm:

- `event_time`, `mid_price`, `spread`, `rel_spread`.
- `future_ret_h`, `cost_threshold_t`, `label`, `label_horizon_events`, `label_fee_bps`.
- Regime features như `liquidity_drought_score`, `adverse_selection_score`, `momentum_score`, `choppiness_score`.
- `regime` và `split`.
- Forecasting probabilities: `prob_down`, `prob_flat`, `prob_up`, `pred_label`.

## Execution columns

Execution/RSEP cần đủ các cột trong `src/utils/execution_columns.py`, bao gồm probabilities, label/regime/split, mid/spread/risk scores và toàn bộ 20-level book columns.
