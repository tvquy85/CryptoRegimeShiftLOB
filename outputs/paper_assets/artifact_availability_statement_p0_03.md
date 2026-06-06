# Data and Artifact Availability Statement

The raw BTC-USDT and ETH-USDT L2 order book snapshots used in this benchmark are licensed commercial data and are not redistributed with the artifact package. The public artifact package therefore focuses on reproducibility of the benchmark construction rather than redistribution of the raw market feed. It includes the source code, configuration files, schema documentation, checksum manifest, paper-ready result tables, split audits, and a synthetic L2 sample with the same 20-level snapshot schema.

Reviewers can run the one-command smoke pipeline on `sample_data/l2_synthetic_sample.parquet` without access to commercial data. This smoke run exercises data audit, feature construction, cost-aware labels, regime assignment, chronological splitting, forecasting, execution replay, policy tuning, RSEP, stress-grid evaluation, and report generation. The synthetic sample is not used for scientific claims; it is provided only to verify that the released code paths and artifact checks are executable.

The full BTC/ETH results remain auditable through locked paper assets, checksum summaries, configuration files, and stage audit reports. The paper does not claim live trading readiness, exact queue-position replay, hidden-liquidity reconstruction, or redistributability of the raw commercial snapshots.
