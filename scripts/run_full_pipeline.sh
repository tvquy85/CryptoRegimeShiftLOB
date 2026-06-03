#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python scripts/00_audit_data.py --config configs/data_crypto_lake.yaml --run-id full_audit --stage stage_3_full_scale
python scripts/01_build_features.py --config configs/features.yaml --run-id full_features --stage stage_3_full_scale
python scripts/02_label_regimes.py --config configs/regimes.yaml --run-id full_regimes --stage stage_3_full_scale
python scripts/03_make_splits.py --config configs/experiments_full.yaml --run-id full_splits --stage stage_3_full_scale
python scripts/04_train_forecasters.py --config configs/models.yaml --run-id full_train_sgd --stage stage_3_full_scale --model sgd
python scripts/05_backtest_forecasts.py --config configs/simulator.yaml --run-id full_backtest --stage stage_3_full_scale
python scripts/06_run_rsep.py --config configs/simulator.yaml --run-id full_rsep --stage stage_3_full_scale
python scripts/07_run_stress_grid.py --config configs/simulator.yaml --run-id full_stress --stage stage_3_full_scale
python scripts/08_generate_report_pack.py --config configs/experiments_full.yaml --run-id full_report --stage stage_3_full_scale

