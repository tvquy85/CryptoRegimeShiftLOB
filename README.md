# CryptoRegimeShift-LOB

Reviewer-facing artifact repository for the ICDM 2026 Applied Track submission:

**CryptoRegimeShift-LOB: Regime-Aware Forecast-to-Execution Evaluation for Crypto L2 Order Books**

This repository is an artifact-backed benchmark and evaluation protocol. It is
not a trading bot, not a live-execution system, and not a public redistribution
of commercial Crypto Lake raw data.

## What This Repository Provides

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

## Reproducibility Results and Commands

| Result or check | Output | Command | Scope |
|---|---|---|---|
| Synthetic end-to-end pipeline | `supplementary_artifact/artifacts/synthetic/` | `cd supplementary_artifact && powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_synthetic_end_to_end.ps1` | Public executable smoke path; validates code paths only. |
| Synthetic table verifier | `supplementary_artifact/artifacts/synthetic/verification_report.json` | `cd supplementary_artifact && python scripts/09_verify_paper_tables.py --mode synthetic` | Public synthetic checks; does not reproduce paper numbers. |
| Artifact verifier | `checksums.json` plus required public docs, configs, schema, sample data, and paper assets | `python scripts/verify_artifacts.py` | Public artifact surface and checksum verification. |
| Manifest generation | `supplementary_artifact/artifacts/synthetic/manifest.json` | `cd supplementary_artifact && python scripts/10_make_artifact_manifest.py --mode synthetic` | Public synthetic hashes, environment, and command metadata. |
| Split audit artifact | `artifacts/split_audit.csv` and `outputs/paper_assets/table_19_chronological_split_audit.csv` | Saved paper artifact; regeneration requires licensed-data-derived split artifacts and the full pipeline scripts in `scripts/`. | Paper evidence for purged chronological splits. |
| Claim-to-evidence map | `outputs/paper_assets/table_13_claim_to_evidence_map.csv` | Saved paper artifact; see `REPRODUCIBILITY.md` for the full evidence-pack command sequence. | Maps major claims to tables, checks, and limitations. |
| Licensed full reproduction | Full BTC/ETH outputs under the documented data and output layout | `cd supplementary_artifact && make validate-full-data && make full && make verify-full` | Requires licensed Crypto Lake snapshots; no commercial raw data are redistributed. |

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
