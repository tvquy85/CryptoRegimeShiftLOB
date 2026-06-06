# Data Card

## Dataset Identity

- Name: CryptoRegimeShift-LOB.
- Assets in the paper: BTC-USDT and ETH-USDT.
- Source for paper numbers: licensed Crypto Lake Level-2 order-book snapshots.
- Period for paper numbers: full-year 2024.
- Raw-data redistribution: not included in this public artifact unless a provider-public sample or license-permitted excerpt is explicitly supplied.
- Public executable data: deterministic synthetic 20-level L2 sample.
- Optional compatibility data: minimal raw-format sample under `data/raw_sample/cryptolake_minimal/`.

## Public vs Licensed Components

| Component | Public in artifact | Requires Crypto Lake license | Purpose |
|---|---:|---:|---|
| Source code | Yes | No | Pipeline and accounting reproduction |
| Configs | Yes | No | Exact protocol definition |
| Synthetic 20-level L2 sample | Yes | No | End-to-end smoke and method-surface audit |
| Raw-format minimal sample | Optional | Maybe | Schema and loader compatibility, not paper evidence |
| Raw BTC/ETH 2024 snapshots | No | Yes | Full numerical reproduction |
| Split manifests/checksum templates | Yes | Full values require data | Chronological construction audit |
| Paper table verifier | Yes | Full values require data | Claim-to-evidence validation |

## Known Limitations

- Snapshot-level L2 only; no hidden liquidity.
- No exact queue priority or passive fill model.
- Visible-depth market-order replay is an approximation, not live execution.
- No live-trading or profitability claim.
- Full-year numeric reproduction depends on access to licensed raw snapshots.

