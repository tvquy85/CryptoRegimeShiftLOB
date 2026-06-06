# Stress Grid Specification

This document defines the benchmark stress grid used by CryptoRegimeShift-LOB.

## Scope

The stress grid is a diagnostic perturbation of the L2 visible-depth replay simulator. It is not a live venue model, not a routing model, and not evidence of trading profitability.

## Source of truth

The canonical grid is `configs/stress_grid.yaml`.

Default replay assumptions:

- `fee_bps = 1.0`
- `latency_events = 1`
- `spread_multiplier = 1.0`
- `depth_multiplier = 1.0`
- `partial_fill = true`
- `min_fill_ratio = 0.5`
- `trade_notional = 1000.0`
- `cooldown_events = 3`

Stress levels:

| Axis | Unit | Levels |
|---|---:|---:|
| `fee_bps` | basis points | `0, 1, 2, 5, 10` |
| `latency_events` | snapshot events | `0, 1, 5, 10` |
| `spread_multiplier` | multiplier around mid-price | `1.0, 1.5, 2.0` |
| `depth_multiplier` | multiplier on visible displayed size | `1.0, 0.75, 0.5` |

## Protocol

For a trained model and selected policy:

1. Load the saved held-out prediction artifact.
2. Load train-derived class-return means from the same prediction artifact.
3. Load validation-selected policy thresholds and RSEP parameters.
4. Compute policy actions once under the default replay assumptions.
5. For each stress axis and level, create a copy of `ExecutionConfig` with exactly one field changed.
6. Replay the same actions under the stressed `ExecutionConfig`.
7. Report net PnL, stress curves, RobustnessAUC, and latency half-life.

No model is retrained under stress. No probability is recomputed under stress. No threshold, RSEP lambda, or RSEP theta is retuned under stress. Test data remains final-reporting only.

## Axis semantics

- `fee_bps`: changes only the fee charged during replay.
- `latency_events`: changes only the event-index delay from signal time to entry time.
- `spread_multiplier`: widens or narrows executable bid/ask distances from the snapshot mid-price.
- `depth_multiplier`: scales visible displayed size at each L2 level before sweep/partial-fill logic.

The grid is one-axis-at-a-time: all non-stressed axes remain at default replay values.

## Interpretation

Stress curves are robustness diagnostics. Negative net PnL under stress should be read as forecast-to-execution degradation, not as a live trading result. A model or policy may mitigate loss under one stress axis while remaining net negative overall.
