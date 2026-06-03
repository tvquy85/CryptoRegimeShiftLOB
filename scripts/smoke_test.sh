#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python scripts/00_audit_data.py --config configs/data_crypto_lake.yaml --run-id smoke_audit --stage stage_0_sanity_check
python scripts/01_build_features.py --config configs/features.yaml --run-id smoke_features --stage stage_0_sanity_check
python scripts/02_label_regimes.py --config configs/regimes.yaml --run-id smoke_regimes --stage stage_0_sanity_check
python scripts/03_make_splits.py --config configs/experiments_smoke.yaml --run-id smoke_splits --stage stage_0_sanity_check
python scripts/04_train_forecasters.py --config configs/models.yaml --run-id smoke_train --stage stage_0_sanity_check --model sgd
python scripts/05_backtest_forecasts.py --config configs/simulator.yaml --run-id smoke_backtest --stage stage_0_sanity_check
python scripts/06_run_rsep.py --config configs/simulator.yaml --run-id smoke_rsep --stage stage_0_sanity_check
python scripts/07_run_stress_grid.py --config configs/simulator.yaml --run-id smoke_stress --stage stage_0_sanity_check
python scripts/08_generate_report_pack.py --config configs/experiments_smoke.yaml --run-id smoke_report --stage stage_0_sanity_check
pytest

