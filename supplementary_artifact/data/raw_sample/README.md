# Raw-Format Minimal Sample

Place a provider-public or license-permitted minimal sample here:

```text
data/raw_sample/cryptolake_minimal/*.parquet
```

Expected schema:

```text
origin_time, received_time, sequence_number, symbol, exchange,
bid_0_price, bid_0_size, ..., bid_19_price, bid_19_size,
ask_0_price, ask_0_size, ..., ask_19_price, ask_19_size
```

This sample is used only to verify schema compatibility and loader behavior. It is not the full dataset and is not used to support paper numerical claims.

If no raw-format sample is included, run `make synthetic` for public pipeline verification.

