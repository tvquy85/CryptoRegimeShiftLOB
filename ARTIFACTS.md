# Artifact Inventory

This file explains what the public repository contains and what is intentionally
excluded. It is written for reviewers who need to audit the paper without access
to commercial raw order-book data.

## Public Reviewer Artifacts

- `Paper_ICDM_2026/`: paper source, bibliography, figures, and compiled PDF.
- `supplementary_artifact/`: self-contained synthetic end-to-end artifact,
  verifier, checksums, and data-access instructions.
- `src/`, `scripts/`, `configs/`, `tests/`: benchmark implementation,
  command-line entry points, reproducibility configs, and protocol tests.
- `sample_data/`: small synthetic L2 snapshots with the same 20-level schema.
- `outputs/paper_assets/`: paper-ready tables and figures.
- `artifacts/`: compact audit CSV/JSON files for splits, regimes, references,
  bootstrap summaries, model-selection ledger, and cross-asset diagnostics.
- `docs/`: executable specifications for labels, RSEP, replay, stress tests,
  regime taxonomy, and reproducibility controls.

## Restricted or Excluded Artifacts

The following are intentionally not committed:

- commercial BTC/ETH Crypto Lake raw snapshots;
- derived full-year feature, split, prediction, and backtest parquet files;
- checkpoints, model weights, `.pt`, `.ckpt`, and `.joblib` files;
- logs, caches, temporary archives, and local planning notes;
- full raw-data paths, credentials, API keys, or tokens.

## Reviewer-Relevant Evidence Files

Important compact evidence files include:

- `outputs/paper_assets/table_1_dataset_stats.csv`
- `outputs/paper_assets/table_13_claim_to_evidence_map.csv`
- `outputs/paper_assets/table_19_chronological_split_audit.csv`
- `outputs/paper_assets/table_20_rsep_term_mapping.csv`
- `outputs/paper_assets/table_22_execution_ci_stage3.csv`
- `outputs/paper_assets/table_23_regime_taxonomy_inputs.csv`
- `outputs/paper_assets/table_26_cross_asset_distribution_shift.csv`
- `artifacts/split_audit.csv`
- `artifacts/model_selection_ledger.csv`
- `artifacts/reference_audit.csv`

These files support auditability of the paper claims, but full numerical
reproduction still requires licensed raw data.

## Synthetic Artifact Scope

Synthetic outputs in `supplementary_artifact/artifacts/synthetic/` demonstrate
that the code paths run end to end. They do not reproduce paper numbers and must
not be used as empirical market evidence.
