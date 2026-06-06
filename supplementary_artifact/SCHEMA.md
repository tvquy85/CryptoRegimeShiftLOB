# Schema

The canonical raw-format schema matches the paper pipeline:

```text
origin_time
received_time
sequence_number
symbol
exchange
bid_0_price, bid_0_size, ..., bid_19_price, bid_19_size
ask_0_price, ask_0_size, ..., ask_19_price, ask_19_size
```

All timestamps are interpreted as UTC. `origin_time` is the preferred event timestamp; `received_time` is retained for audit and fallback checks.

## Compatibility Mapping

If a provider sample uses one-indexed names, configure a mapping in YAML:

```yaml
column_mapping:
  timestamp: origin_time
  bid_px_1: bid_0_price
  bid_sz_1: bid_0_size
  ask_px_1: ask_0_price
  ask_sz_1: ask_0_size
```

The supplementary validator accepts only the canonical output schema after mapping.

## Validation Checks

`scripts/01_validate_schema.py` checks:

- all 20 bid and ask levels exist;
- timestamps parse as UTC and are monotonic per symbol;
- best bid is strictly below best ask;
- bid prices are non-increasing by depth;
- ask prices are non-decreasing by depth;
- sizes are non-negative;
- sequence numbers are present;
- duplicate timestamps are reported.

The validator writes `schema_report.json` with row counts, time ranges, levels per side, and check statuses.

