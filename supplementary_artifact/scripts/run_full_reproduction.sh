#!/usr/bin/env bash
set -euo pipefail
python scripts/01_validate_schema.py --config configs/btc_usdt_2024.yaml --mode full
python scripts/01_validate_schema.py --config configs/eth_usdt_2024.yaml --mode full
echo "[ERROR] Full numerical reproduction requires running the root repository pipeline on licensed data."
echo "Use the documented order: audit, features/labels, regimes, splits, forecasting, tuning/replay, stress, bootstrap, evidence pack."
exit 2

