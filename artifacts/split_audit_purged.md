# Purged Split Audit

This file records the purged split gate used before the 10-page Applied Track
paper revision.

## Gate Result

- `explicit_purge_rows = 50`
- `horizon_events = 50`
- `horizon_overlap_rows = 0`
- `status = PASS`

The purged split gate prevents h-step label leakage at train/validation and
validation/test boundaries. It does not change the core benchmark semantics:
cost-aware labels, causal feature construction, validation-only model/policy
tuning, and test-only reporting remain unchanged.

The machine-readable audit is:

```text
artifacts/split_audit_purged.csv
```
