# License and Data Access

The artifact intentionally separates public auditability from full numerical reproduction. The public release contains code, configurations, schema documentation, deterministic synthetic Level-2 samples, optional raw-format sample validation, tests, manifest generation, and claim-to-evidence mapping.

It does not redistribute the full BTC-USDT or ETH-USDT Crypto Lake snapshots because those data require a separate license. Users with licensed access can place the raw snapshots under:

```text
data/external/cryptolake/BTC-USDT/book/2024/
data/external/cryptolake/ETH-USDT/book/2024/
```

Without licensed raw data, synthetic mode verifies method surface, schema checks, split purging, labeling, visible-depth replay, RSEP accounting, stress tests, bootstrap diagnostics, and artifact checksums. It must not be interpreted as reproducing the empirical paper numbers.

The optional raw-format sample may be packaged only when its source is one of:

- `provider_public_sample`;
- `license_permitted_excerpt`;
- `user_supplied_not_packaged`.

Full monthly/yearly commercial raw data must never be packaged or checksummed in this public artifact.

