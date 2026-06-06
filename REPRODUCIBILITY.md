# REPRODUCIBILITY.md

## Mục tiêu

Tài liệu này mô tả cách reviewer chạy smoke pipeline public và cách audit full paper artifacts khi raw BTC/ETH không thể redistributable.

## Cài đặt tối thiểu

```bash
pip install -r requirements.txt
```

Khuyến nghị dùng Python 3.11. Smoke pipeline là CPU-bound và không cần GPU.

## Một lệnh smoke pipeline

Từ thư mục `CryptoRegimeShift`:

```bash
bash scripts/run_smoke_pipeline.sh
```

Trên PowerShell/Windows, dùng lệnh tương đương:

```powershell
.\scripts\run_smoke_pipeline.ps1
```

Pipeline này sẽ:

1. Sinh synthetic L2 sample.
2. Audit raw sample.
3. Build features và cost-aware labels.
4. Gán regime.
5. Tạo chronological train/validation/test split có purge.
6. Train SGD baseline.
7. Chạy forecast-to-execution, RSEP, validation tuning và stress grid.
8. Sinh report pack smoke vào `outputs/smoke/paper_assets/`.
9. Verify artifact pack.

Smoke output chỉ kiểm tra khả năng tái lập pipeline; không dùng cho paper metrics.

## Verify artifact pack

```bash
python scripts/verify_artifacts.py --require-smoke-outputs
```

Để regenerate checksum manifest sau khi cập nhật artifact public:

```bash
python scripts/verify_artifacts.py --write-checksums
```

## Exact commands for artifact review

Run all commands from the `CryptoRegimeShift` directory.

### a. Run smoke pipeline on synthetic sample

```bash
bash scripts/run_smoke_pipeline.sh
```

Windows PowerShell:

```powershell
.\scripts\run_smoke_pipeline.ps1
```

### b. Verify schema and public artifact surface

This command checks required public docs/configs, the synthetic 20-level L2 parquet schema, smoke outputs if requested, and restricted-path hygiene:

```bash
python scripts/verify_artifacts.py --require-smoke-outputs
```

### c. Verify artifact checksums

Checksum verification is part of the default verifier path:

```bash
python scripts/verify_artifacts.py
```

To regenerate the checksum manifest after updating public artifacts:

```bash
python scripts/verify_artifacts.py --write-checksums
```

### d. Regenerate paper tables from saved prediction/replay outputs

These commands read existing saved artifacts and regenerate paper-facing tables and narratives; they do not require raw snapshots:

```bash
python scripts/15_build_icdm_evidence_pack.py --config configs/simulator_stage3_tcn_stride1_gpu.yaml --stage stage_3_full_scale --symbol BTC-USDT --run-id repro_evidence_pack
python scripts/16_build_paper_draft_pack.py --config configs/simulator_stage3_tcn_stride1_gpu.yaml --stage stage_3_full_scale --symbol BTC-USDT --run-id repro_paper_draft_pack
python scripts/21_build_cross_asset_paper_pack.py --config configs/simulator_stage3_tcn_stride1_gpu.yaml --stage stage_3_full_scale --symbol BTC-USDT --run-id repro_cross_asset_pack
```

### e. Full reproduction path for licensed raw data

Users with access to the same Crypto Lake L2 snapshots can rerun the full path in this order:

```bash
python scripts/00_audit_data.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/01_build_features.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/02_label_regimes.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/03_make_splits.py --config <experiment_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/04_train_forecasters.py --config <model_config> --stage stage_3_full_scale --symbol <SYMBOL> --model sgd --run-id <RUN_ID>
python scripts/09_tune_execution_policies.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --model-label <MODEL_LABEL> --run-id <RUN_ID>
python scripts/05_backtest_forecasts.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/06_run_rsep.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
python scripts/07_run_stress_grid.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --model-label <MODEL_LABEL> --use-tuned-policy --run-id <RUN_ID>
python scripts/15_build_icdm_evidence_pack.py --config <simulator_config> --stage stage_3_full_scale --symbol <SYMBOL> --run-id <RUN_ID>
```

## Full pipeline map

Các script full paper pipeline:

- `00_audit_data.py`: audit schema/timestamps/spread/depth.
- `01_build_features.py`: causal features và labels.
- `02_label_regimes.py`: refined regime taxonomy và diagnostics.
- `03_make_splits.py`: chronological train/validation/test split.
- `04_train_forecasters.py`: SGD/XGBoost tabular forecasts.
- `13_train_temporal_baseline_from_predictions.py`: temporal GPU pilot.
- `14_temporal_inference_execution_ready.py`: TCN execution-ready inference.
- `05_backtest_forecasts.py`: forecast-to-execution baseline.
- `09_tune_execution_policies.py`: validation-only threshold tuning.
- `06_run_rsep.py`: RSEP và ablations.
- `07_run_stress_grid.py`: fee/latency/spread/depth stress.
- `15_build_icdm_evidence_pack.py`, `16_build_paper_draft_pack.py`, `21_build_cross_asset_paper_pack.py`, `22_build_ieee_draft_skeleton.py`: paper assets.

## Restricted data note

Full BTC/ETH results require restricted raw L2 snapshots. Public artifact pack cung cấp schema, synthetic sample, configs, checksums và paper-ready tables để audit claim boundaries mà không phân phối raw data.
