# CryptoRegimeShift-LOB

Reviewer-facing artifact repository for the ICDM 2026 Applied Track paper:

**CryptoRegimeShift-LOB: Regime-Aware Forecast-to-Execution Evaluation for Crypto L2 Order Books**

This repository is an artifact-backed benchmark and evaluation protocol. It is
not a trading bot, not a live-execution system, and not a public redistribution
of commercial Crypto Lake raw data.

## What This Repository Provides

- Paper source and compiled PDF under `Paper_ICDM_2026/`.
- Source code, configs, and tests for the L2 benchmark pipeline.
- A public synthetic 20-level L2 sample for smoke testing.
- A self-contained `supplementary_artifact/` package with commands, verifier,
  checksums, schema documentation, and synthetic end-to-end outputs.
- Paper-ready evidence tables and figures under `outputs/paper_assets/`.
- Audit CSV/JSON artifacts that connect the paper claims to reproducible checks.

## What Is Not Included

The full BTC-USDT and ETH-USDT 2024 L2 snapshots are commercial data and are not
redistributed. Full numerical reproduction requires licensed access to the same
provider data and the documented configuration. The public synthetic data are
only for exercising code paths and schema checks; they are not used for paper
metrics or scientific claims.

The repository also excludes checkpoints, model weights, large prediction and
backtest parquet files, logs, caches, and temporary build archives.

## Quick Start for Reviewers

Run the self-contained supplementary artifact:

```bash
cd supplementary_artifact
python -m pip install -r requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_synthetic_end_to_end.ps1
python scripts/09_verify_paper_tables.py --mode synthetic
python scripts/10_make_artifact_manifest.py --mode synthetic
pytest -q
```

On Unix-like systems, use:

```bash
cd supplementary_artifact
python -m pip install -r requirements.txt
bash scripts/run_synthetic_end_to_end.sh
python scripts/09_verify_paper_tables.py --mode synthetic
python scripts/10_make_artifact_manifest.py --mode synthetic
pytest -q
```

The synthetic pipeline validates schema compatibility, cost-aware labels,
purged chronological splits, a small forecasting baseline, visible-depth replay,
RSEP diagnostics, stress tests, bootstrap summaries, and manifest checksums.

## Paper Build

The paper candidate is:

```text
Paper_ICDM_2026/main.tex
Paper_ICDM_2026/main.pdf
```

To rebuild locally:

```powershell
cd Paper_ICDM_2026
..\tectonic.exe main.tex
```

The committed `main.pdf` is the reviewer-facing 10-page Applied Track draft.

## Repository Layout

```text
supplementary_artifact/   self-contained reviewer artifact package
src/                      benchmark implementation modules
scripts/                  full-pipeline and audit scripts
configs/                  benchmark, replay, stress, and model configs
tests/                    unit and protocol tests
sample_data/              small public synthetic L2 sample
outputs/paper_assets/     paper-ready tables and figures
artifacts/                compact audit CSV/JSON files
docs/                     executable method specifications
```

## Core Claim Boundaries

The paper supports an artifact-backed evaluation protocol for:

- cost-aware L2 forecasting labels;
- diagnostic microstructure regimes;
- forecast-to-execution degradation;
- visible-depth L2 replay under fees, latency, spread, and depth stress;
- RSEP as an inspectable diagnostic gate;
- BTC-USDT and ETH-USDT transfer diagnostics only.

The paper does **not** claim profitability, live-trading readiness, exact L3
queue reconstruction, hidden-liquidity modeling, passive-fill realism, or
universal market generalization.
