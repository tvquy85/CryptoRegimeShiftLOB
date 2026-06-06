# Licensed Crypto Lake Data

Full numerical reproduction requires licensed raw snapshots under:

```text
data/external/cryptolake/BTC-USDT/book/2024/*.parquet
data/external/cryptolake/ETH-USDT/book/2024/*.parquet
```

These files are not redistributed. If they are absent, `make validate-full-data` reports a clear licensed-data error and `make synthetic` remains available for public pipeline verification.

