# Reproducibility Checklist

This checklist maps the supplementary artifact to the ICDM Applied Track
reproducibility guidance and the McGill-style checklist categories. Items that
cannot be public because of the commercial data license are marked explicitly as
`N/A / license restricted`; they are not omitted.

## Models and Algorithms

| Checklist item | Status | Artifact evidence |
|---|---|---|
| Mathematical setting, assumptions, and model definitions | PASS | `SCHEMA.md`, `docs/l2_replay_spec.md`, `docs/rsep_spec.md`, `docs/regime_taxonomy_spec.md`, paper Methods. |
| Cost-aware label formula and constants | PASS | `configs/benchmark_default.yaml`, `outputs/paper_assets/table_18_default_benchmark_configuration.csv`. |
| RSEP gate variables, coefficients, and validation rule | PASS | `configs/rsep_grid.yaml`, `docs/rsep_spec.md`, `outputs/paper_assets/table_20_rsep_term_mapping.csv`. |
| L2 replay fill, fee, latency, and partial-fill rules | PASS | `docs/l2_replay_spec.md`, replay unit tests, synthetic pipeline outputs. |
| Algorithm complexity or proof | N/A | The paper is an applied benchmark/evaluation protocol, not a theoretical algorithm paper. |

## Datasets and Splits

| Checklist item | Status | Artifact evidence |
|---|---|---|
| Dataset statistics | PASS | `outputs/paper_assets/table_1_dataset_stats.csv`, `DATA_CARD.md`. |
| Train/validation/test splits | PASS | `artifacts/split_audit.csv`, `outputs/paper_assets/table_19_chronological_split_audit.csv`. |
| Horizon purge/no-leakage protocol | PASS | Split audit and split-leakage tests. |
| Preprocessing and feature construction | PASS | `SCHEMA.md`, configs, source code under `src/` and `scripts/`. |
| Downloadable full raw dataset | N/A / license restricted | Full BTC-USDT and ETH-USDT Crypto Lake snapshots are commercial and not redistributed. |
| Public simulation or smoke dataset | PASS | Deterministic synthetic 20-level L2 sample under `sample_data/` and `supplementary_artifact/`. |
| Optional raw-format sample | N/A / user supplied unless license permits | `data/raw_sample/README.md` documents how to place a provider-public or license-permitted sample. |
| Data collection/generation details | PASS | `DATA_CARD.md`, `LICENSE_AND_DATA_ACCESS.md`, `scripts/00_make_synthetic_l2_sample.py`. |

## Code and Commands

| Checklist item | Status | Artifact evidence |
|---|---|---|
| Source code and configs | PASS | `src/`, `scripts/`, `configs/`, `supplementary_artifact/configs/`. |
| Dependency list | PASS | `requirements.txt`, `supplementary_artifact/requirements.txt`, `ENVIRONMENT.md`. |
| Training/evaluation code | PASS | Forecasting, replay, stress, bootstrap, and verifier scripts are included. |
| README with exact result commands | PASS | Root `README.md` and `REPRODUCIBILITY.md` list paper build, synthetic, verifier, manifest, and licensed full reproduction commands. |
| Pretrained full-year models | N/A / not packaged | Large checkpoints are excluded; licensed-data users can regenerate them from configs. |
| Smoke pipeline without commercial data | PASS | `scripts/run_synthetic_end_to_end.ps1`, `scripts/run_synthetic_end_to_end.sh`, `make synthetic`. |
| Checksum manifest | PASS | Root `checksums.json` and synthetic manifest generation. |

## Experimental Results

| Checklist item | Status | Artifact evidence |
|---|---|---|
| Hyperparameter ranges and selection rules | PASS | Model configs, `configs/rsep_grid.yaml`, `configs/stress_grid.yaml`, model-selection audit. |
| Number of runs/evaluation units | PASS | Day-level bootstrap artifacts and paper-ready tables. |
| Evaluation metrics | PASS | Forecasting, replay, stress, bootstrap, and transfer paper assets. |
| Central tendency and variation | PASS | `outputs/paper_assets/table_22_execution_ci_stage3.csv` and bootstrap summaries. |
| Figures/tables generated from saved artifacts | PASS | `outputs/paper_assets/`, `artifacts/`, checksum manifest. |
| Computing infrastructure | PASS / bounded | Synthetic runtime is documented. Full-year runtime depends on licensed data layout, storage throughput, and optional GPU availability. |

## Claim Boundaries

| Boundary | Status |
|---|---|
| Synthetic outputs are not paper numerical claims. | PASS |
| Raw-format samples verify schema/loader behavior only. | PASS |
| L2 replay is a visible-depth approximation, not live execution. | PASS |
| RSEP is a diagnostic gate, not a deployable trading strategy. | PASS |
| Full numerical reproduction requires licensed raw data. | PASS |
