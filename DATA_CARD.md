# Data Card

## Dataset Purpose

CryptoRegimeShift-LOB evaluates how L2 order-book forecasting signals degrade
when they are passed through cost-aware labels, microstructure regimes, visible
L2 replay, stress tests, bootstrap uncertainty, and BTC-USDT/ETH-USDT transfer
diagnostics.

The dataset is used for benchmark and failure-analysis purposes. It is not used
to claim a profitable or deployment-ready trading strategy.

## Main Experimental Data

- Provider: Crypto Lake, under commercial data-access terms.
- Exchange: Binance.
- Assets: `BTC-USDT` and `ETH-USDT`.
- Period: full year 2024.
- Observation type: snapshot-level L2 order book.
- Depth: 20 bid levels and 20 ask levels.
- Core columns: timestamps, sequence number, symbol, exchange, and per-level
  bid/ask price and size.

Locked paper statistics are stored in:

```text
outputs/paper_assets/table_1_dataset_stats.csv
```

## Public Synthetic Data

The repository includes synthetic L2 data for reproducibility checks:

```text
sample_data/l2_synthetic_sample.parquet
sample_data/BOOK_BINANCE_SYNTH-USDT_JAN-2024.parquet
supplementary_artifact/data/synthetic/raw/book_snapshots.parquet
```

The synthetic data match the expected 20-level schema and exercise the pipeline,
but they do not represent real market distributions and do not support paper
metrics.

## Raw-Format Minimal Sample Policy

The supplementary artifact has a `data/raw_sample/` path for a minimal
Crypto-Lake-style sample. A raw-format sample may be packaged only if it is a
provider-public sample or an excerpt explicitly allowed for redistribution.
Otherwise reviewers can place their own provider sample there and run the raw
sample validator.

## Data Limitations

- No L3 order-event stream is included.
- No exact queue priority, cancellation race, hidden liquidity, passive fill, or
  venue-routing model is claimed.
- L2 replay is a visible-depth approximation.
- BTC-USDT/ETH-USDT transfer evidence is limited to Binance 2024.
- Full raw-data reproduction requires licensed access to the same data source.
