#!/usr/bin/env bash
set -euo pipefail
python scripts/00_make_synthetic_l2_sample.py --config configs/synthetic.yaml
python scripts/01_validate_schema.py --config configs/synthetic.yaml --mode synthetic
python scripts/02_build_features.py --config configs/synthetic.yaml --mode synthetic
python scripts/03_make_labels_regimes_splits.py --config configs/synthetic.yaml --mode synthetic
python scripts/04_train_or_load_baselines.py --config configs/synthetic.yaml --mode synthetic
python scripts/05_run_visible_depth_replay.py --config configs/synthetic.yaml --mode synthetic
python scripts/06_run_rsep_diagnostic.py --config configs/synthetic.yaml --mode synthetic
python scripts/07_run_stress_tests.py --config configs/synthetic.yaml --mode synthetic
python scripts/08_run_bootstrap_and_transfer.py --config configs/synthetic.yaml --mode synthetic
python scripts/10_make_artifact_manifest.py --mode synthetic

