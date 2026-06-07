# Environment

Tested baseline environment:

- Python: 3.10 or 3.11.
- OS: Windows or Linux.
- Required packages: see `requirements.txt`.
- GPU: not required for the public synthetic artifact.

## Public Synthetic Mode

The public smoke pipeline is CPU-bound and intended to finish in a few minutes
on a normal laptop or workstation. It generates a deterministic two-asset
20-level L2 sample, validates schema and splits, trains a small SGD baseline,
runs visible-depth replay, stress diagnostics, bootstrap summaries, and writes a
manifest. No GPU or commercial raw data are required.

## Reported Full-Year Evidence

The paper results were produced from licensed BTC-USDT and ETH-USDT Crypto Lake
2024 L2 snapshots. The full pipeline is substantially more demanding than the
public synthetic path because it processes full-year snapshot-level data and
large derived artifacts. Audit, feature, split, replay, stress, bootstrap, and
report steps are mostly CPU/storage-bound. GPU acceleration is useful for the
neural and nonlinear forecasting baselines when those baselines are regenerated.

The project documentation records use of a workstation-class environment with
an NVIDIA GeForce RTX 3090 for GPU-accelerated model experiments. Exact full
runtime is not asserted as a portable benchmark because it depends strongly on
local storage throughput, available RAM, GPU availability, and whether all
optional baselines are regenerated.

## Packaged Artifact Boundary

The public package does not include full raw snapshots, large prediction or
backtest parquet files, logs, checkpoints, or model weights. Licensed-data users
should regenerate those artifacts from the included code and configs.
