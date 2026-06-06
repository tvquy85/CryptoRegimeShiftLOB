# Chronological Split Audit

This audit summarizes the locked purged train/validation/test splits used by the
paper-facing evidence pack.

## Summary

- Audited assets: `BTC-USDT` and `ETH-USDT`.
- Split protocol: chronological `60/20/20` by rows.
- Label horizon: `50` events.
- Boundary purge: `50` rows at train-to-validation and validation-to-test
  boundaries.
- Horizon overlap rows after purge: `0`.
- Status: `PASS`.

## Leakage Control

The final `50` rows before each non-test boundary are removed so that the
future label index for every remaining train row stays inside train, and every
remaining validation row stays inside validation. The test split is used only
for final reporting.

Detailed row counts, date ranges, and boundary status are stored in:

```text
artifacts/split_audit.csv
outputs/paper_assets/table_19_chronological_split_audit.csv
```
