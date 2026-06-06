# Audit cleanup tr??c purged rerun

- run_id: `stage3_16_disk_cleanup_pre_purged_rerun_v001`
- M?c ti?u: gi?i ph?ng disk cho P0-02B purged rerun, kh?ng x?a source b?t bu?c BTC/ETH.
- Manifest CSV: `artifacts/stage3_16_disk_cleanup_pre_purged_rerun_v001.csv`
- T?ng dung l??ng ?ng vi?n x?a: `150.95 GB`.

## File gi? b?t bu?c

- `data/predictions/predictions.parquet`
- `data/splits/splits_eth_stage3.parquet`

## File x?a c?p 1/c?p 2

- `data/predictions/predictions_stage3_xgboost_gpu.parquet` (delete_tier1, 41.3501 GB, rows=167751306)
- `data/predictions/predictions_stage3_tcn_gpu_stride1_execution_ready.parquet` (delete_tier1, 9.534 GB, rows=68088247)
- `data/predictions/predictions_stage3_tcn_gpu_execution_ready.parquet` (delete_tier1, 2.0348 GB, rows=7709170)
- `data/predictions/predictions_stage3_tcn_gpu_pilot.parquet` (delete_tier1, 0.0432 GB, rows=750000)
- `data/predictions/predictions_stage3_deeplob_faithful_lite_pilot.parquet` (delete_tier1, 0.0433 GB, rows=750000)
- `data/predictions/predictions_stage3_deeplob_pilot.parquet` (delete_tier1, 0.0009 GB, rows=15000)
- `data/predictions/predictions_stage3_lob_transformer_pilot.parquet` (delete_tier1, 0.0009 GB, rows=15000)
- `data/predictions/predictions_asset_eth_to_btc_sgd.parquet` (delete_tier1, 8.7365 GB, rows=33550262)
- `data/predictions/predictions_asset_btc_to_eth_sgd.parquet` (delete_tier1, 6.9138 GB, rows=22882887)
- `data/predictions/predictions_stage3_tcn_gpu_execution_ready_smoke.parquet` (delete_tier1, 0.0002 GB, rows=300)
- `data/predictions/predictions_stage3_tcn_gpu_stride1_execution_ready_smoke.parquet` (delete_tier1, 0.0001 GB, rows=300)
- `data/predictions/predictions_stage3_tcn_gpu_execution_ready_compile_probe.parquet` (delete_tier1, 0.0001 GB, rows=30)
- `data/features/features_eth_stage3.parquet` (delete_tier2_if_needed, 26.7644 GB, rows=114414433)
- `data/labels/labels_eth_stage3.parquet` (delete_tier2_if_needed, 26.7716 GB, rows=114414433)
- `data/regimes/regimes_eth_stage3.parquet` (delete_tier2_if_needed, 28.7535 GB, rows=114414433)

## Quy?t ??nh

- Ch? x?a c?c file listed trong manifest, kh?ng x?a raw data, paper assets, audits, configs ho?c BTC `predictions.parquet`.
- Sau cleanup ph?i verify row count c?a source b?t bu?c v? free disk `>=120 GB`.
## K?t qu? sau cleanup

- Free disk sau cleanup: `188.59 GB`.
- Gate 120 GB: `PASS`.
- Post-cleanup CSV: `artifacts/stage3_16_disk_cleanup_pre_purged_rerun_v001_post.csv`.
- `compileall`: PASS.
- `pytest CryptoRegimeShift\tests -q`: PASS.

## Source b?t bu?c ?? verify

- `data/predictions/predictions.parquet`: rows `167751306` / expected `167751306`, columns `121`.
- `data/splits/splits_eth_stage3.parquet`: rows `114414433` / expected `114414433`, columns `117`.

## Ghi ch?

- ?? gi? BTC `data/predictions/predictions.parquet` v? ETH `data/splits/splits_eth_stage3.parquet`.
- Kh?ng x?a paper assets, audit, configs, tests ho?c raw `data/full2024` n?u t?n t?i.