# Reproducibility Guide

This guide describes how reviewers can exercise the public artifact and how
licensed users can reproduce the full paper pipeline.

## Minimal Environment

Python 3.10 or 3.11 is recommended. Install dependencies from the repository
root:

```bash
python -m pip install -r requirements.txt
```

For the self-contained artifact package:

```bash
cd supplementary_artifact
python -m pip install -r requirements.txt
```

## Public Synthetic End-to-End Check

From `supplementary_artifact/`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_synthetic_end_to_end.ps1
python scripts\09_verify_paper_tables.py --mode synthetic
python scripts\10_make_artifact_manifest.py --mode synthetic
pytest -q
```

Unix-like shell:

```bash
bash scripts/run_synthetic_end_to_end.sh
python scripts/09_verify_paper_tables.py --mode synthetic
python scripts/10_make_artifact_manifest.py --mode synthetic
pytest -q
```

This path runs only on public synthetic data. It verifies the executable surface
but does not reproduce paper numbers.

## Root Smoke Pipeline

From the repository root:

```bash
bash scripts/run_smoke_pipeline.sh
python scripts/verify_artifacts.py --require-smoke-outputs
```

Windows PowerShell:

```powershell
.\scripts\run_smoke_pipeline.ps1
python scripts\verify_artifacts.py --require-smoke-outputs
```

## Artifact Checksums

Verify public artifact presence and checksums:

```bash
python scripts/verify_artifacts.py
```

Regenerate `checksums.json` only after intentionally changing public artifacts:

```bash
python scripts/verify_artifacts.py --write-checksums
```

## Paper Build

```powershell
cd Paper_ICDM_2026
..\tectonic.exe main.tex
```

The committed `main.pdf` is the reviewer-facing Applied Track draft.

## Regenerating Paper-Ready Tables from Saved Outputs

These scripts read saved compact artifacts and table sources. They do not fetch
or redistribute raw snapshots:

```bash
python scripts/15_build_icdm_evidence_pack.py --config configs/simulator_stage3_tcn_stride1_gpu.yaml --stage stage_3_full_scale --symbol BTC-USDT --run-id repro_evidence_pack
python scripts/16_build_paper_draft_pack.py --config configs/simulator_stage3_tcn_stride1_gpu.yaml --stage stage_3_full_scale --symbol BTC-USDT --run-id repro_paper_draft_pack
python scripts/21_build_cross_asset_paper_pack.py --config configs/simulator_stage3_tcn_stride1_gpu.yaml --stage stage_3_full_scale --symbol BTC-USDT --run-id repro_cross_asset_pack
```

If large licensed-data-derived prediction or replay outputs are absent, these
commands should fail clearly instead of fabricating paper results.

## Full Licensed-Data Reproduction Path

Users with licensed Crypto Lake BTC-USDT and ETH-USDT L2 snapshots can rerun the
full pipeline in this order:

```bash
python scripts/00_audit_data.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/01_build_features.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/02_label_regimes.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/03_make_splits.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/04_train_forecasters.py --config <model_config> --stage stage_3_full_scale --symbol <SYMBOL> --model sgd --run-id <RUN_ID>
python scripts/09_tune_execution_policies.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --model-label <MODEL_LABEL> --run-id <RUN_ID>
python scripts/07_run_stress_grid.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --model-label <MODEL_LABEL> --use-tuned-policy --run-id <RUN_ID>
python scripts/15_build_icdm_evidence_pack.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
```

The full path requires local licensed data and will not run from the public
repository alone.
