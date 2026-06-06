# Reproducibility Checklist

## Data Availability

- [x] Code is included in the supplementary artifact.
- [x] Synthetic sample is public and deterministic.
- [x] Optional raw-format sample path is documented.
- [ ] Raw Crypto Lake full-year snapshots are not redistributed because they require a commercial license.
- [x] Instructions are provided for licensed-data users to reproduce full numerical results.

## Code Availability

- [x] Pipeline scripts are included.
- [x] Commands are documented.
- [x] Package versions are listed.
- [x] Smoke tests run without commercial data.

## Experimental Protocol

- [x] Chronological splits are specified.
- [x] Horizon purging is implemented.
- [x] Feature construction is time-causal.
- [x] Label thresholds are config-defined.
- [x] Replay assumptions are documented.
- [x] Stress axes are documented.
- [x] Bootstrap unit is day-level.

## Claim Boundaries

- [x] Synthetic outputs are not claimed to reproduce paper numbers.
- [x] Optional raw-format sample verifies schema compatibility only.
- [x] Replay is not live trading.
- [x] RSEP is not a deployable trading strategy.
- [x] Full numerical reproduction requires licensed raw data.

