#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

CONFIG="configs/repro_smoke.yaml"
STAGE="stage_0_sanity_check"
SYMBOL="SYNTH-USDT"
MODEL_LABEL="sgd_synthetic_smoke"

python scripts/create_synthetic_l2_sample.py
python scripts/00_audit_data.py --config "$CONFIG" --run-id repro_smoke_audit_v001 --stage "$STAGE" --symbol "$SYMBOL"
python scripts/01_build_features.py --config "$CONFIG" --run-id repro_smoke_features_v001 --stage "$STAGE" --symbol "$SYMBOL"
python scripts/02_label_regimes.py --config "$CONFIG" --run-id repro_smoke_regimes_v001 --stage "$STAGE" --symbol "$SYMBOL"
python scripts/03_make_splits.py --config "$CONFIG" --run-id repro_smoke_splits_v001 --stage "$STAGE" --symbol "$SYMBOL"
python scripts/04_train_forecasters.py --config "$CONFIG" --run-id repro_smoke_train_sgd_v001 --stage "$STAGE" --symbol "$SYMBOL" --model sgd
python scripts/05_backtest_forecasts.py --config "$CONFIG" --run-id repro_smoke_backtest_v001 --stage "$STAGE" --symbol "$SYMBOL"
python scripts/06_run_rsep.py --config "$CONFIG" --run-id repro_smoke_rsep_v001 --stage "$STAGE" --symbol "$SYMBOL"
python scripts/09_tune_execution_policies.py --config "$CONFIG" --run-id repro_smoke_tune_v001 --stage "$STAGE" --symbol "$SYMBOL" --model-label "$MODEL_LABEL"
python scripts/07_run_stress_grid.py --config "$CONFIG" --run-id repro_smoke_stress_v001 --stage "$STAGE" --symbol "$SYMBOL" --model-label "$MODEL_LABEL" --use-tuned-policy
python scripts/08_generate_report_pack.py --config "$CONFIG" --run-id repro_smoke_report_v001 --stage "$STAGE" --symbol "$SYMBOL" --model-label "$MODEL_LABEL"
python scripts/verify_artifacts.py --require-smoke-outputs
